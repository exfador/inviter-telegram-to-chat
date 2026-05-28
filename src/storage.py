import asyncio
import os
import time
from datetime import datetime
from pathlib import Path


class AppendLog:
    def __init__(self, path: Path):
        self._path = path
        self._lock = asyncio.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()

    async def write(self, line: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(f"{ts} | {line}\n")


class TextSet:
    def __init__(self, path: Path):
        self._path = path
        self._lock = asyncio.Lock()
        self._items: set[str] = set()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s:
                        self._items.add(s)
        else:
            path.touch()

    def __contains__(self, item: str) -> bool:
        return item in self._items

    def __len__(self) -> int:
        return len(self._items)

    def snapshot(self) -> set[str]:
        return set(self._items)

    async def add(self, item: str) -> None:
        async with self._lock:
            if item in self._items:
                return
            self._items.add(item)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(item + "\n")


class TimedSet:
    def __init__(self, path: Path):
        self._path = path
        self._lock = asyncio.Lock()
        self._items: dict[str, tuple[float, str]] = {}
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    parts = s.split("|")
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        try:
                            expires = float(parts[1].strip())
                        except ValueError:
                            continue
                        reason = parts[2].strip() if len(parts) > 2 else ""
                        self._items[name] = (expires, reason)
        else:
            path.touch()

    def is_active(self, name: str) -> bool:
        entry = self._items.get(name)
        if not entry:
            return False
        return entry[0] > time.time()

    def expires_at(self, name: str) -> float | None:
        entry = self._items.get(name)
        return entry[0] if entry else None

    def __len__(self) -> int:
        now = time.time()
        return sum(1 for exp, _ in self._items.values() if exp > now)

    async def add(self, name: str, ttl_seconds: int, reason: str = "") -> None:
        async with self._lock:
            expires = time.time() + ttl_seconds
            self._items[name] = (expires, reason)
            await self._rewrite()

    async def _rewrite(self) -> None:
        tmp = self._path.parent / (self._path.name + ".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as f:
                for name, (exp, reason) in self._items.items():
                    f.write(f"{name} | {int(exp)} | {reason}\n")
            os.replace(tmp, self._path)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass


class Storage:
    def __init__(self, data_dir: Path):
        self.invited = TextSet(data_dir / "invited.txt")
        self.failed = TextSet(data_dir / "failed.txt")
        self.failed_log = AppendLog(data_dir / "failed_log.txt")
        self.dead_sessions = TextSet(data_dir / "dead_sessions.txt")
        self.frozen_sessions = TimedSet(data_dir / "frozen_sessions.txt")

    def is_processed(self, user: str) -> bool:
        return user in self.invited or user in self.failed

    async def mark_failed(self, user: str, reason: str) -> None:
        await self.failed.add(user)
        await self.failed_log.write(f"{user} | {reason}")
