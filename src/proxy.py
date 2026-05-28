import re
import secrets
from urllib.parse import unquote, urlparse


_SESSION_RE = re.compile(r"session-[A-Za-z0-9]+")


def build_proxy(url: str, rotate_session: bool = True) -> dict | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.hostname or not parsed.port:
        return None

    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")

    if rotate_session and username:
        new_sid = secrets.token_hex(7)
        if _SESSION_RE.search(username):
            username = _SESSION_RE.sub(f"session-{new_sid}", username, count=1)
        else:
            username = f"{username}-session-{new_sid}"

    return {
        "scheme": (parsed.scheme or "http").lower(),
        "hostname": parsed.hostname,
        "port": parsed.port,
        "username": username,
        "password": password,
    }


def short_proxy_label(proxy: dict | None) -> str:
    if not proxy:
        return "no-proxy"
    user = proxy.get("username") or ""
    m = _SESSION_RE.search(user)
    sid = m.group(0) if m else "no-sid"
    return f"{proxy.get('hostname')}:{proxy.get('port')} {sid}"
