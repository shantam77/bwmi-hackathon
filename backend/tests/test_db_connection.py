import pytest
from sqlalchemy import text

from app.config import DATABASE_URL
from app.db import get_engine, init_db

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL not set -- skipping live Postgres check"
)


def test_can_connect_and_run_a_query():
    engine = get_engine()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


def test_init_db_does_not_raise():
    # Base has no tables yet (Phase 1 adds them) -- this just proves the
    # create_all() call path works against the real database.
    init_db()


def test_a_trivial_row_round_trips():
    # Phase 0 test gate: prove write access works over the public proxy, not
    # just SELECT 1. Uses a scratch table it creates and drops itself.
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE TEMPORARY TABLE _phase0_check (id INT, note TEXT)"))
        conn.execute(
            text("INSERT INTO _phase0_check (id, note) VALUES (:id, :note)"),
            {"id": 1, "note": "phase 0 round trip"},
        )
        row = conn.execute(text("SELECT id, note FROM _phase0_check WHERE id = 1")).fetchone()
        assert row == (1, "phase 0 round trip")
