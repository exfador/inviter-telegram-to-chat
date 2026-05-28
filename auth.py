import asyncio
import sys

from colorama import Fore, Style

from config import CONFIG
from src.logger import get_logger, setup_logging
from src.proxy import build_proxy, short_proxy_label

from pyrogram import Client
from pyrogram import errors as pe


BANNER = f"""
{Fore.LIGHTCYAN_EX}{Style.BRIGHT}
  session creator
{Style.RESET_ALL}
  {Fore.LIGHTBLACK_EX}sessions dir: {Fore.WHITE}{CONFIG.sessions_dir}{Style.RESET_ALL}
  {Fore.LIGHTBLACK_EX}api_id:       {Fore.WHITE}{CONFIG.api_id}{Style.RESET_ALL}
  {Fore.LIGHTBLACK_EX}device:       {Fore.WHITE}{CONFIG.device_model} / {CONFIG.system_version} / {CONFIG.app_version}{Style.RESET_ALL}
"""


def _ask(prompt: str) -> str:
    return input(f"{Fore.LIGHTYELLOW_EX}? {prompt}{Style.RESET_ALL} ").strip()


async def _create_one(phone: str, log) -> bool:
    session_name = phone.lstrip("+").replace(" ", "").replace("-", "")
    session_path = CONFIG.sessions_dir / f"{session_name}.session"
    if session_path.exists():
        log.warning(f"session already exists: {session_path}")
        if _ask("overwrite? (y/N):").lower() != "y":
            return False
        session_path.unlink()

    proxy = build_proxy(CONFIG.proxy_url, rotate_session=CONFIG.proxy_rotate_session)
    if proxy:
        log.info(f"using proxy: {short_proxy_label(proxy)}")

    kwargs: dict = dict(
        name=session_name,
        api_id=CONFIG.api_id,
        api_hash=CONFIG.api_hash,
        workdir=str(CONFIG.sessions_dir),
        device_model=CONFIG.device_model,
        system_version=CONFIG.system_version,
        app_version=CONFIG.app_version,
        lang_code=CONFIG.lang_code,
        phone_number=phone,
    )
    if proxy:
        kwargs["proxy"] = proxy

    client = Client(**kwargs)
    try:
        await client.start()
    except pe.PhoneNumberInvalid:
        log.error(f"invalid phone number: {phone}")
        return False
    except pe.PhoneNumberBanned:
        log.error(f"phone number is banned: {phone}")
        return False
    except pe.PhoneNumberFlood:
        log.error("too many login attempts, try later")
        return False
    except Exception as e:
        log.exception(f"login failed: {e}")
        return False

    try:
        me = await client.get_me()
        who = f"@{me.username}" if me.username else f"id:{me.id}"
        log.success(f"logged in as {who} ({me.phone_number})")
        log.success(f"session saved: {session_path}")
        return True
    finally:
        try:
            await client.stop()
        except Exception:
            pass


async def main_async() -> int:
    print(BANNER)
    setup_logging()
    log = get_logger("auth")

    CONFIG.sessions_dir.mkdir(parents=True, exist_ok=True)

    log.info("enter phone numbers (one per prompt), empty line to finish")
    log.info("format: +1234567890 (with country code)")

    created = 0
    failed = 0
    while True:
        try:
            phone = _ask("phone:")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not phone:
            break
        if not phone.startswith("+"):
            phone = "+" + phone
        ok = await _create_one(phone, log)
        if ok:
            created += 1
        else:
            failed += 1

    log.info(f"done. created: {created}, failed: {failed}")
    return 0


def main() -> int:
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
