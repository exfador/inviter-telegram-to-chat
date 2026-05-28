from dataclasses import dataclass
from enum import Enum

from pyrogram import errors as pe


class Outcome(Enum):
    INVITED = "invited"
    SKIP_USER = "skip_user"
    RETRY_LATER = "retry_later"
    FLOOD_SLEEP = "flood_sleep"
    SESSION_DEAD = "session_dead"
    SESSION_FROZEN = "session_frozen"
    TARGET_FATAL = "target_fatal"
    UNKNOWN = "unknown"


@dataclass
class Verdict:
    outcome: Outcome
    reason: str
    sleep: int = 0


DEAD_ERRORS: tuple = (
    pe.AuthKeyUnregistered,
    pe.AuthKeyInvalid,
    pe.AuthKeyDuplicated,
    pe.AuthKeyPermEmpty,
    pe.SessionExpired,
    pe.SessionRevoked,
    pe.UserDeactivated,
    pe.UserDeactivatedBan,
)

USER_PROBLEM_ERRORS: tuple = (
    pe.UserPrivacyRestricted,
    pe.UserNotMutualContact,
    pe.UserChannelsTooMuch,
    pe.UserKicked,
    pe.UserBlocked,
    pe.UserBot,
    pe.UserIdInvalid,
    pe.UserInvalid,
    pe.InputUserDeactivated,
    pe.PeerIdInvalid,
    pe.UsernameInvalid,
    pe.UsernameNotOccupied,
    pe.BotsTooMuch,
)

TARGET_FATAL_ERRORS: tuple = (
    pe.ChannelPrivate,
    pe.ChannelInvalid,
    pe.ChatAdminRequired,
    pe.ChatWriteForbidden,
    pe.ChatIdInvalid,
    pe.ChatRestricted,
    pe.ChatAdminInviteRequired,
)

FROZEN_ERRORS: tuple = (
    pe.PeerFlood,
    pe.UserRestricted,
)


def _wait_seconds(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def classify(exc: BaseException) -> Verdict:
    if isinstance(exc, pe.FloodWait):
        secs = _wait_seconds(exc.value)
        return Verdict(Outcome.FLOOD_SLEEP, f"FLOOD_WAIT {secs}s", sleep=secs)

    if isinstance(exc, pe.SlowmodeWait):
        secs = _wait_seconds(exc.value)
        return Verdict(Outcome.FLOOD_SLEEP, f"SLOWMODE_WAIT {secs}s", sleep=secs)

    if isinstance(exc, FROZEN_ERRORS):
        return Verdict(Outcome.SESSION_FROZEN, type(exc).__name__)

    if isinstance(exc, DEAD_ERRORS):
        return Verdict(Outcome.SESSION_DEAD, type(exc).__name__)

    if isinstance(exc, USER_PROBLEM_ERRORS):
        return Verdict(Outcome.SKIP_USER, type(exc).__name__)

    if isinstance(exc, TARGET_FATAL_ERRORS):
        return Verdict(Outcome.TARGET_FATAL, type(exc).__name__)

    if isinstance(exc, pe.UserAlreadyParticipant):
        return Verdict(Outcome.SKIP_USER, "AlreadyParticipant")

    if isinstance(exc, pe.InternalServerError):
        return Verdict(Outcome.RETRY_LATER, type(exc).__name__, sleep=15)

    if isinstance(exc, pe.BadRequest):
        return Verdict(Outcome.SKIP_USER, type(exc).__name__)

    if isinstance(exc, pe.Forbidden):
        return Verdict(Outcome.TARGET_FATAL, type(exc).__name__)

    if isinstance(exc, pe.Unauthorized):
        return Verdict(Outcome.SESSION_DEAD, type(exc).__name__)

    if isinstance(exc, pe.SeeOther):
        return Verdict(Outcome.RETRY_LATER, type(exc).__name__, sleep=5)

    if isinstance(exc, pe.NotAcceptable):
        return Verdict(Outcome.SESSION_FROZEN, type(exc).__name__)

    if isinstance(exc, pe.Flood):
        return Verdict(Outcome.SESSION_FROZEN, type(exc).__name__)

    if isinstance(exc, pe.RPCError):
        return Verdict(Outcome.UNKNOWN, type(exc).__name__, sleep=10)

    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return Verdict(Outcome.RETRY_LATER, type(exc).__name__, sleep=15)

    return Verdict(Outcome.UNKNOWN, f"{type(exc).__name__}: {exc}", sleep=10)
