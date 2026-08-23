"""Agents SDK Session implementation backed by our own Postgres instance
(via app/store.py) instead of a separate SQLite file. Items are opaque to
this class -- it just persists whatever the SDK hands it and returns it back
in order. Deliberately separate from the Message table: this is the SDK's
own conversation-history format, not what the UI renders on rehydration."""

from agents.memory import SessionABC
from agents.items import TResponseInputItem

from app import store


class PostgresSession(SessionABC):
    def __init__(self, session_id: str):
        self.session_id = session_id

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        return store.get_agent_session_items(self.session_id, limit=limit)

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        if items:
            store.add_agent_session_items(self.session_id, list(items))

    async def pop_item(self) -> TResponseInputItem | None:
        return store.pop_agent_session_item(self.session_id)

    async def clear_session(self) -> None:
        store.clear_agent_session(self.session_id)
