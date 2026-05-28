import asyncio
import random
import time

from config import CONFIG
from .account import Account, AccountState
from .logger import get_logger
from .session_manager import discover_sessions, format_eta, next_unfreeze
from .storage import Storage
from .user_loader import UserQueue, UsersFile

log = get_logger("inviter")


async def _run_account(account: Account) -> None:
    try:
        await account.run()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        account.log.exception(f"crash inside worker: {e}")
        account.state = AccountState.STOPPED


async def _run_pass(storage: Storage, queue: UserQueue) -> int:
    sessions = discover_sessions(storage)
    if not sessions:
        log.error("no usable sessions, sleeping")
        return 0

    total_invited = 0
    accounts = [Account(p, storage, queue) for p in sessions]

    sem = asyncio.Semaphore(max(1, CONFIG.workers_concurrency))

    async def bounded(account: Account):
        nonlocal total_invited
        async with sem:
            log.info(f"=== switching to session: {account.name} ===")
            await _run_account(account)
            total_invited += account.invited_count
            await asyncio.sleep(random.randint(*CONFIG.session_switch_delay))

    await asyncio.gather(*(bounded(a) for a in accounts), return_exceptions=False)

    log.success(f"pass complete, invited this pass: {total_invited}")
    return total_invited


async def run_forever() -> None:
    storage = Storage(CONFIG.data_dir)
    log.info(
        f"start. invited so far: {len(storage.invited)}, "
        f"failed: {len(storage.failed)}, "
        f"dead sessions: {len(storage.dead_sessions)}, "
        f"frozen sessions: {len(storage.frozen_sessions)}"
    )

    while True:
        try:
            users_file = UsersFile(CONFIG.users_file)
            users = users_file.usernames()
            queue = UserQueue(users, storage, users_file)

            if len(queue) == 0:
                log.warning(f"no pending users, idle for {CONFIG.restart_idle_delay}s")
                await asyncio.sleep(CONFIG.restart_idle_delay)
                if not CONFIG.forever:
                    return
                continue

            invited = await _run_pass(storage, queue)

            if not CONFIG.forever:
                log.info("forever=False, exiting")
                return

            if invited == 0:
                eta = next_unfreeze(storage)
                if eta:
                    wait = max(60, int(eta - time.time()) + 5)
                    log.warning(
                        f"zero invites this pass — all sessions frozen. "
                        f"next unfreeze at {format_eta(eta)} (sleeping {wait // 60}m {wait % 60}s)"
                    )
                    await asyncio.sleep(wait)
                else:
                    log.warning(f"zero invites this pass, sleeping {CONFIG.restart_idle_delay}s")
                    await asyncio.sleep(CONFIG.restart_idle_delay)
            else:
                await asyncio.sleep(random.randint(*CONFIG.session_switch_delay))
        except asyncio.CancelledError:
            log.warning("cancelled, shutting down")
            raise
        except Exception as e:
            log.exception(f"top-level crash: {e}, restart in {CONFIG.error_retry_delay}s")
            await asyncio.sleep(CONFIG.error_retry_delay)
