from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class Config:
    api_id: int = 2040
    api_hash: str = "b18441a1ff607e10a989891a5462e627"

    device_model: str = "aboba-linux-custom"
    system_version: str = "1.2.3-zxc-custom"
    app_version: str = "1.0.1"
    lang_code: str = "en"

    target_chat: str = "@coxerhub"

    sessions_dir: Path = Path("sessions")
    users_file: Path = Path("users.txt")
    data_dir: Path = Path("data")

    invite_delay: Tuple[int, int] = (5, 15)
    session_switch_delay: Tuple[int, int] = (3, 8)
    join_target_delay: Tuple[int, int] = (5, 15)

    max_invites_per_session: int = 40
    flood_wait_threshold: int = 600

    peer_flood_freeze_seconds: int = 6 * 3600
    long_flood_freeze_seconds: int = 2 * 3600

    error_retry_delay: int = 30
    restart_idle_delay: int = 300

    workers_concurrency: int = 1
    # 1 = sessions run sequentially (safest — parallel invites to the same chat
    # tend to trigger PeerFlood across all accounts at once). Raise if you accept
    # the higher ban risk in exchange for throughput.

    forever: bool = True

    proxy_url: str = "http://user:password@host:port"
    proxy_rotate_session: bool = True


CONFIG = Config()

CONFIG.data_dir.mkdir(parents=True, exist_ok=True)
CONFIG.sessions_dir.mkdir(parents=True, exist_ok=True)
