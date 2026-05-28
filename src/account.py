import asyncio
import random
from pathlib import Path

from pyrogram import Client
from pyrogram import errors as pe

from config import CONFIG
from .errors import Outcome, classify
from .logger import get_logger
from .proxy import build_proxy, short_proxy_label
from .storage import Storage
from .user_loader import UserQueue


class AccountState:
    IDLE = "idle"
    READY = "ready"
    DEAD = "dead"
    FROZEN = "frozen"
    STOPPED = "stopped"


class Account:
    def __init__(self, session_path: Path, storage: Storage, queue: UserQueue):
        self.session_path = session_path
        self.name = session_path.stem
        self.storage = storage
        self.queue = queue
        self.state = AccountState.IDLE
        self.invited_count = 0
        self.log = get_logger(self.name[:16])
        self._client: Client | None = None

    def _build_client(self) -> Client:
        proxy = build_proxy(CONFIG.proxy_url, rotate_session=CONFIG.proxy_rotate_session)
        if proxy:
            self.log.info(f"proxy: {short_proxy_label(proxy)}")
        kwargs: dict = dict(
            name=self.name,
            api_id=CONFIG.api_id,
            api_hash=CONFIG.api_hash,
            workdir=str(self.session_path.parent),
            device_model=CONFIG.device_model,
            system_version=CONFIG.system_version,
            app_version=CONFIG.app_version,
            lang_code=CONFIG.lang_code,
            no_updates=True,
            sleep_threshold=0,
        )
        if proxy:
            kwargs["proxy"] = proxy
        return Client(**kwargs)

    async def _connect(self) -> bool:
        try:
            self._client = self._build_client()
            await self._client.start()
            me = await self._client.get_me()
            who = f"@{me.username}" if me.username else f"id:{me.id}"
            self.log.success(f"connected as {who} ({me.phone_number or 'no-phone'})")
            self.state = AccountState.READY
            return True
        except Exception as e:
            verdict = classify(e)
            if verdict.outcome == Outcome.SESSION_DEAD:
                self.log.error(f"session dead at startup: {verdict.reason}")
                await self.storage.dead_sessions.add(self.name)
                self.state = AccountState.DEAD
            elif verdict.outcome == Outcome.FLOOD_SLEEP:
                self.log.warning(f"flood wait at startup {verdict.sleep}s")
                if verdict.sleep < CONFIG.flood_wait_threshold:
                    await asyncio.sleep(verdict.sleep)
                    return await self._connect()
                ttl = max(verdict.sleep, CONFIG.long_flood_freeze_seconds)
                await self.storage.frozen_sessions.add(self.name, ttl, verdict.reason)
                self.state = AccountState.FROZEN
            else:
                self.log.exception(f"failed to start session: {e}")
                self.state = AccountState.DEAD
            await self._safe_stop()
            return False

    async def _safe_stop(self) -> None:
        if self._client is None:
            return
        try:
            if self._client.is_connected:
                await self._client.stop()
        except Exception:
            pass
        self._client = None

    async def _join_target(self) -> bool:
        assert self._client is not None
        target = CONFIG.target_chat
        try:
            chat = await self._client.get_chat(target)
            self.log.info(f"target resolved: {chat.title or chat.id}")
            try:
                await self._client.join_chat(target)
                self.log.info("joined target chat")
            except pe.UserAlreadyParticipant:
                self.log.debug("already in target")
            except pe.InviteHashExpired:
                self.log.error("invite hash expired")
                return False
            except pe.InviteHashInvalid:
                self.log.error("invite hash invalid")
                return False
            except Exception as e:
                verdict = classify(e)
                if verdict.outcome in (Outcome.SESSION_DEAD, Outcome.SESSION_FROZEN, Outcome.TARGET_FATAL):
                    self.log.error(f"join failed: {verdict.reason}")
                    return False
                self.log.warning(f"join soft error: {verdict.reason}")
            await asyncio.sleep(random.randint(*CONFIG.join_target_delay))
            return True
        except Exception as e:
            verdict = classify(e)
            self.log.error(f"cannot resolve target {target}: {verdict.reason}")
            return False

    async def _verify_member(self, username: str) -> bool:
        assert self._client is not None
        try:
            await asyncio.sleep(2)
            await self._client.get_chat_member(CONFIG.target_chat, username)
            return True
        except pe.UserNotParticipant:
            return False
        except Exception:
            return True

    async def _invite_user(self, username: str) -> Outcome:
        assert self._client is not None
        try:
            await self._client.add_chat_members(CONFIG.target_chat, username)
            if not await self._verify_member(username):
                self.log.warning(f"{username} -> silent privacy (not actually added)")
                await self.storage.mark_failed(username, "SilentPrivacy")
                await self.queue.consume(username)
                return Outcome.SKIP_USER
            self.log.success(f"invited {username}")
            await self.storage.invited.add(username)
            await self.queue.consume(username)
            self.invited_count += 1
            return Outcome.INVITED
        except Exception as e:
            verdict = classify(e)
            tag = self.log.warning if verdict.outcome == Outcome.SKIP_USER else self.log.error
            tag(f"{username} -> {verdict.outcome.value} ({verdict.reason})")

            if verdict.outcome == Outcome.INVITED:
                return Outcome.INVITED
            if verdict.outcome == Outcome.SKIP_USER:
                await self.storage.mark_failed(username, verdict.reason)
                await self.queue.consume(username)
                return Outcome.SKIP_USER
            if verdict.outcome == Outcome.FLOOD_SLEEP:
                if verdict.sleep >= CONFIG.flood_wait_threshold:
                    ttl = max(verdict.sleep, CONFIG.long_flood_freeze_seconds)
                    self.log.warning(f"flood {verdict.sleep}s too long, freezing for {ttl // 60}m")
                    await self.storage.frozen_sessions.add(self.name, ttl, verdict.reason)
                    self.state = AccountState.FROZEN
                    return Outcome.SESSION_FROZEN
                self.log.warning(f"sleeping flood {verdict.sleep}s")
                await asyncio.sleep(verdict.sleep + 1)
                await self.queue.requeue(username)
                return Outcome.FLOOD_SLEEP
            if verdict.outcome == Outcome.SESSION_DEAD:
                await self.storage.dead_sessions.add(self.name)
                self.state = AccountState.DEAD
                await self.queue.requeue(username)
                return Outcome.SESSION_DEAD
            if verdict.outcome == Outcome.SESSION_FROZEN:
                ttl = CONFIG.peer_flood_freeze_seconds
                self.log.warning(f"freezing session for {ttl // 3600}h ({verdict.reason})")
                await self.storage.frozen_sessions.add(self.name, ttl, verdict.reason)
                self.state = AccountState.FROZEN
                await self.queue.requeue(username)
                return Outcome.SESSION_FROZEN
            if verdict.outcome == Outcome.TARGET_FATAL:
                self.log.critical(f"target fatal: {verdict.reason}")
                await self.queue.requeue(username)
                return Outcome.TARGET_FATAL
            if verdict.outcome == Outcome.RETRY_LATER:
                if verdict.sleep:
                    await asyncio.sleep(verdict.sleep)
                await self.queue.requeue(username)
                return Outcome.RETRY_LATER

            await asyncio.sleep(verdict.sleep or CONFIG.error_retry_delay)
            await self.queue.requeue(username)
            return Outcome.UNKNOWN

    async def run(self) -> None:
        if not await self._connect():
            return
        try:
            if not await self._join_target():
                self.state = AccountState.STOPPED
                return
            while self.state == AccountState.READY:
                if self.invited_count >= CONFIG.max_invites_per_session:
                    self.log.info(f"hit per-session cap {CONFIG.max_invites_per_session}, releasing")
                    break
                user = await self.queue.pop()
                if user is None:
                    self.log.info("queue empty, releasing")
                    break
                outcome = await self._invite_user(user)
                if outcome in (Outcome.SESSION_DEAD, Outcome.SESSION_FROZEN, Outcome.TARGET_FATAL):
                    break
                delay = random.randint(*CONFIG.invite_delay)
                self.log.debug(f"cooldown {delay}s")
                await asyncio.sleep(delay)
        finally:
            await self._safe_stop()
            if self.state == AccountState.READY:
                self.state = AccountState.STOPPED
            self.log.info(f"done. invited this run: {self.invited_count}")
