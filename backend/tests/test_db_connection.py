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
