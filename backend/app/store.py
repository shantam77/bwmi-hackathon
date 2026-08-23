"""Repository functions over the ORM. This is the ONLY module that touches
app/tables.py directly -- domain/engine/agent code goes through here and
only ever sees plain Pydantic models, never ORM rows. Every function takes
session_id and filters on it; there is no cross-session read in this file."""

from app.db import get_session_factory
from app.models import JourneyPlan
from app.tables import ClockOffset, Journey, Message

# --- Clock offset ------------------------------------------------------------


def get_clock_offset_seconds(session_id: str) -> int:
    Session = get_session_factory()
    with Session() as db:
        row = db.get(ClockOffset, session_id)
        return row.offset_seconds if row else 0


def set_clock_offset_seconds(session_id: str, offset_seconds: int) -> None:
    Session = get_session_factory()
    with Session() as db:
        row = db.get(ClockOffset, session_id)
        if row is None:
            db.add(ClockOffset(session_id=session_id, offset_seconds=offset_seconds))
        else:
            row.offset_seconds = offset_seconds
        db.commit()


# --- Journeys ------------------------------------------------------------


def save_journey(session_id: str, plan: JourneyPlan, state: str = "DRAFT") -> str:
    Session = get_session_factory()
    with Session() as db:
        row = Journey(session_id=session_id, plan_json=plan.model_dump(), state=state)
        db.add(row)
        db.commit()
        return row.id


def get_journey(session_id: str, journey_id: str) -> JourneyPlan | None:
    Session = get_session_factory()
    with Session() as db:
        row = db.get(Journey, journey_id)
        if row is None or row.session_id != session_id:
            return None
        return JourneyPlan(**row.plan_json)


def latest_journey(session_id: str) -> JourneyPlan | None:
    Session = get_session_factory()
    with Session() as db:
        row = (
            db.query(Journey)
            .filter(Journey.session_id == session_id)
            .order_by(Journey.created_at.desc())
            .first()
        )
        return JourneyPlan(**row.plan_json) if row else None


# --- Messages ------------------------------------------------------------


def append_message(
    session_id: str, role: str, content: str, component: dict | None = None
) -> None:
    Session = get_session_factory()
    with Session() as db:
        db.add(
            Message(session_id=session_id, role=role, content=content, component_json=component)
        )
        db.commit()


def list_messages(session_id: str) -> list[Message]:
    Session = get_session_factory()
    with Session() as db:
        rows = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        db.expunge_all()
        return rows
