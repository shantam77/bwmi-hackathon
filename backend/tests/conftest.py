import uuid

import pytest

from app.config import DATABASE_URL

requires_db = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL not set -- skipping tests that hit Postgres"
)


@pytest.fixture
def fake_session_id():
    """A throwaway session_id, cleaned up from Postgres on teardown so
    repeated test runs don't accumulate rows in the real database."""
    session_id = f"test-{uuid.uuid4()}"
    yield session_id

    from app.db import get_session_factory
    from app.tables import AgentSessionItem, ClockOffset, Journey, Message, Passenger, PNR

    Session = get_session_factory()
    with Session() as db:
        pnr_ids = [
            row.id for row in db.query(PNR.id).filter(PNR.session_id == session_id).all()
        ]
        if pnr_ids:
            db.query(Passenger).filter(Passenger.pnr_id.in_(pnr_ids)).delete(
                synchronize_session=False
            )
        db.query(PNR).filter(PNR.session_id == session_id).delete()
        db.query(AgentSessionItem).filter(AgentSessionItem.session_id == session_id).delete()
        db.query(Message).filter(Message.session_id == session_id).delete()
        db.query(Journey).filter(Journey.session_id == session_id).delete()
        db.query(ClockOffset).filter(ClockOffset.session_id == session_id).delete()
        db.commit()
