from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ORM tables (journeys, pnrs, passengers, tdr_claims, fired_alerts, messages,
# clock_offsets) are added in Phase 1. Every table must carry a session_id
# column, and every query against it must filter on that column.
