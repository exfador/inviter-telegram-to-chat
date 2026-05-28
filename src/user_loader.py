import asyncio
import os
from collections import deque
from pathlib import Path

from .logger import get_logger
from .storage import Storage

log = get_logger("user_loader")


def _normalize(raw: str) -> str | None:
    s = raw.strip()
    if not s or s.startswith("#"):
        return None
    if s.startswith("https://t.me/"):
        s = s[len("https://t.me/"):]
    if s.startswith("t.me/"):
        s = s[len("t.me/"):]
    if s.startswith("@"):
        s = s[1:]
    s = s.split("?")[0].split("/")[0].strip()
    if not s:
        return None
    return s.lower()


class UsersFile:
    def __init__(self, path: Path):
        self.path = path
        self._lock = asyncio.Lock()
        self._lines: list[str] = []
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                self._lines = [line.rstrip("\r\n") for line in f]
        else:
            log.warning(f"users file not found: {path}, creating empty")
            path.touch()

    def usernames(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for line in self._lines:
            n = _normalize(line)
            if n and n not in seen:
                seen.add(n)
                result.append(n)
        log.info(f"loaded {len(result)} unique users from {self.path}")
        return result

    async def consume(self, user: str) -> None:
        async with self._lock:
            new_lines = [ln for ln in self._lines if _normalize(ln) != user]
            if len(new_lines) == len(self._lines):
                return
            self._lines = new_lines
            tmp = self.path.parent / (self.path.name + ".tmp")
            try:
                with tmp.open("w", encoding="utf-8") as f:
                    for ln in self._lines:
                        f.write(ln + "\n")
                os.replace(tmp, self.path)
            except Exception as e:
                log.error(f"failed to rewrite {self.path}: {e}")
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass


class UserQueue:
    def __init__(self, users: list[str], storage: Storage, users_file: UsersFile):
        self._storage = storage
        self._file = users_file
        self._queue: deque[str] = deque(u for u in users if not storage.is_processed(u))
        self._lock = asyncio.Lock()
        log.info(f"queue ready: {len(self._queue)} users pending")

    def __len__(self) -> int:
        return len(self._queue)

    async def pop(self) -> str | None:
        async with self._lock:
            while self._queue:
                u = self._queue.popleft()
                if not self._storage.is_processed(u):
                    return u
            return None

    async def requeue(self, user: str) -> None:
        async with self._lock:
            self._queue.append(user)

    async def consume(self, user: str) -> None:
        await self._file.consume(user)
