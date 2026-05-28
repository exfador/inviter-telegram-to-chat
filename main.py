import asyncio
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from colorama import Fore, Style

from config import CONFIG
from src.inviter import run_forever
from src.logger import get_logger


BANNER = f"""
{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}
  ███████╗██╗  ██╗███████╗ █████╗ ██████╗  ██████╗ ██████╗
  ██╔════╝╚██╗██╔╝██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
  █████╗   ╚███╔╝ █████╗  ███████║██║  ██║██║   ██║██████╔╝
  ██╔══╝   ██╔██╗ ██╔══╝  ██╔══██║██║  ██║██║   ██║██╔══██╗
  ███████╗██╔╝ ██╗██║     ██║  ██║██████╔╝╚██████╔╝██║  ██║
  ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝
{Style.RESET_ALL}
   {Fore.CYAN}async pyrogram invite worker{Style.RESET_ALL}
   {Fore.LIGHTBLACK_EX}author:  {Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}t.me/exfador{Style.RESET_ALL}
   {Fore.LIGHTBLACK_EX}sponsor: {Fore.LIGHTGREEN_EX}{Style.BRIGHT}neversmm.com{Style.RESET_ALL}
   {Fore.LIGHTBLACK_EX}target:       {Fore.WHITE}{CONFIG.target_chat}{Style.RESET_ALL}
   {Fore.LIGHTBLACK_EX}sessions dir: {Fore.WHITE}{CONFIG.sessions_dir}{Style.RESET_ALL}
   {Fore.LIGHTBLACK_EX}users file:   {Fore.WHITE}{CONFIG.users_file}{Style.RESET_ALL}
"""


def main() -> int:
    print(BANNER)
    log = get_logger("main")

    if CONFIG.target_chat == "@your_target_chat_here":
        log.critical("set CONFIG.target_chat in config.py to your real target chat")
        return 2

    try:
        asyncio.run(run_forever())
        return 0
    except KeyboardInterrupt:
        log.warning("interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
