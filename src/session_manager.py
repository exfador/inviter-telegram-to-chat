import time
from datetime import datetime
from pathlib import Path

from config import CONFIG
from .logger import get_logger
from .storage import Storage

log = get_logger("sessions")


def discover_sessions(storage: Storage) -> list[Path]:
    sessions_dir = CONFIG.sessions_dir
    if not sessions_dir.exists():
        log.error(f"sessions dir does not exist: {sessions_dir}")
        return []

    all_files = sorted(sessions_dir.glob("*.session"))
    if not all_files:
        log.error(f"no .session files in {sessions_dir}")
        return []

    dead = storage.dead_sessions.snapshot()

    usable: list[Path] = []
    dead_count = 0
    frozen_count = 0
    for p in all_files:
        if p.stem in dead:
            dead_count += 1
            continue
        if storage.frozen_sessions.is_active(p.stem):
            exp = storage.frozen_sessions.expires_at(p.stem)
            remaining = int((exp - time.time()) / 60) if exp else 0
            log.debug(f"skip frozen {p.name} ({remaining}m left)")
            frozen_count += 1
            continue
        usable.append(p)

    log.info(
        f"sessions found: total={len(all_files)} "
        f"usable={len(usable)} dead={dead_count} frozen={frozen_count}"
    )
    return usable


def next_unfreeze(storage: Storage) -> float | None:
    sessions_dir = CONFIG.sessions_dir
    if not sessions_dir.exists():
        return None
    soonest: float | None = None
    for p in sessions_dir.glob("*.session"):
        if p.stem in storage.dead_sessions.snapshot():
            continue
        exp = storage.frozen_sessions.expires_at(p.stem)
        if exp and exp > time.time():
            if soonest is None or exp < soonest:
                soonest = exp
    return soonest


def format_eta(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
