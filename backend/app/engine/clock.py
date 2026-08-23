"""The ONLY source of "now" in the application. Per-session, persisted in
Postgres via app/store.py. Nothing else in this app may call datetime.now()
for current time -- retrofitting that later means touching every module."""

from datetime import datetime, timedelta, timezone

from app import store


def now(session_id: str) -> datetime:
    offset_seconds = store.get_clock_offset_seconds(session_id)
    return datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)


def jump_to(session_id: str, target: datetime) -> None:
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    offset_seconds = (target - datetime.now(timezone.utc)).total_seconds()
    store.set_clock_offset_seconds(session_id, int(offset_seconds))


def advance_by(session_id: str, delta: timedelta) -> None:
    current = store.get_clock_offset_seconds(session_id)
    store.set_clock_offset_seconds(session_id, current + int(delta.total_seconds()))


def reset(session_id: str) -> None:
    store.set_clock_offset_seconds(session_id, 0)
