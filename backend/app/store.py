"""Repository functions over the ORM. This is the ONLY module that touches
app/tables.py directly -- domain/engine/agent code goes through here and
only ever sees plain Pydantic models, never ORM rows. Every function takes
session_id and filters on it; there is no cross-session read in this file."""

from app.db import get_session_factory
from app.models import JourneyPlan, PassengerInput, PNRRecord
from app.tables import AgentSessionItem, ClockOffset, FiredAlert, Journey, Message, Passenger, PNR

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


def get_demo_state(session_id: str) -> str | None:
    Session = get_session_factory()
    with Session() as db:
        row = db.get(ClockOffset, session_id)
        return row.demo_state if row else None


def set_clock_offset_and_demo_state(
    session_id: str, offset_seconds: int, demo_state: str | None
) -> None:
    Session = get_session_factory()
    with Session() as db:
        row = db.get(ClockOffset, session_id)
        if row is None:
            db.add(
                ClockOffset(
                    session_id=session_id, offset_seconds=offset_seconds, demo_state=demo_state
                )
            )
        else:
            row.offset_seconds = offset_seconds
            row.demo_state = demo_state
        db.commit()


# --- Fired alerts (dedup) ------------------------------------------------------------


def has_fired(session_id: str, pnr_number: str, alert_id: str, dedup_key: str) -> bool:
    Session = get_session_factory()
    with Session() as db:
        row = (
            db.query(FiredAlert)
            .filter(
                FiredAlert.session_id == session_id,
                FiredAlert.pnr_number == pnr_number,
                FiredAlert.alert_id == alert_id,
                FiredAlert.dedup_key == dedup_key,
            )
            .first()
        )
        return row is not None


def record_fired(
    session_id: str, pnr_number: str, alert_id: str, severity: str, dedup_key: str, payload: dict
) -> None:
    Session = get_session_factory()
    with Session() as db:
        db.add(
            FiredAlert(
                session_id=session_id,
                pnr_number=pnr_number,
                alert_id=alert_id,
                severity=severity,
                dedup_key=dedup_key,
                payload_json=payload,
            )
        )
        db.commit()


def list_fired_alerts(session_id: str, pnr_number: str) -> list[dict]:
    Session = get_session_factory()
    with Session() as db:
        rows = (
            db.query(FiredAlert)
            .filter(FiredAlert.session_id == session_id, FiredAlert.pnr_number == pnr_number)
            .order_by(FiredAlert.fired_at.asc())
            .all()
        )
        return [
            {"alert_id": r.alert_id, "severity": r.severity, **r.payload_json} for r in rows
        ]


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


# --- PNRs and passengers ------------------------------------------------------------


def create_pnr(
    session_id: str,
    pnr_number: str,
    train_number: str,
    train_name: str,
    from_station: str,
    to_station: str,
    date: str,
    departure: str,
    travel_class: str,
    status: str,
    fare_total: int,
    passengers: list[PassengerInput],
) -> None:
    Session = get_session_factory()
    with Session() as db:
        pnr_row = PNR(
            session_id=session_id,
            journey_id=None,
            pnr_number=pnr_number,
            train_number=train_number,
            train_name=train_name,
            from_station=from_station,
            to_station=to_station,
            date=date,
            departure=departure,
            travel_class=travel_class,
            status=status,
            fare_total=fare_total,
        )
        db.add(pnr_row)
        db.flush()
        for p in passengers:
            db.add(
                Passenger(
                    session_id=session_id,
                    pnr_id=pnr_row.id,
                    name=p.name,
                    age=p.age,
                    berth_preference=p.berth_preference,
                    concession_flag=None,
                )
            )
        db.commit()


def _pnr_row_to_record(db, pnr_row) -> PNRRecord:
    passenger_rows = db.query(Passenger).filter(Passenger.pnr_id == pnr_row.id).all()
    return PNRRecord(
        pnr=pnr_row.pnr_number,
        train_number=pnr_row.train_number,
        train_name=pnr_row.train_name,
        from_station=pnr_row.from_station,
        to_station=pnr_row.to_station,
        date=pnr_row.date,
        departure=pnr_row.departure,
        travel_class=pnr_row.travel_class,
        status=pnr_row.status,
        total_fare=pnr_row.fare_total,
        passengers=[
            PassengerInput(name=p.name, age=p.age, berth_preference=p.berth_preference)
            for p in passenger_rows
        ],
    )


def get_pnr(session_id: str, pnr_number: str) -> PNRRecord | None:
    Session = get_session_factory()
    with Session() as db:
        pnr_row = (
            db.query(PNR)
            .filter(PNR.session_id == session_id, PNR.pnr_number == pnr_number)
            .first()
        )
        return _pnr_row_to_record(db, pnr_row) if pnr_row else None


def latest_pnr(session_id: str) -> PNRRecord | None:
    Session = get_session_factory()
    with Session() as db:
        pnr_row = (
            db.query(PNR)
            .filter(PNR.session_id == session_id)
            .order_by(PNR.created_at.desc())
            .first()
        )
        return _pnr_row_to_record(db, pnr_row) if pnr_row else None


# --- Agent SDK conversation history (separate from Message -- see AgentSessionItem) --


def get_agent_session_items(session_id: str, limit: int | None = None) -> list[dict]:
    Session = get_session_factory()
    with Session() as db:
        query = (
            db.query(AgentSessionItem)
            .filter(AgentSessionItem.session_id == session_id)
            .order_by(AgentSessionItem.sequence.asc())
        )
        rows = query.all()
        if limit is not None:
            rows = rows[-limit:]
        return [row.item_json for row in rows]


def add_agent_session_items(session_id: str, items: list[dict]) -> None:
    Session = get_session_factory()
    with Session() as db:
        next_sequence = (
            db.query(AgentSessionItem)
            .filter(AgentSessionItem.session_id == session_id)
            .count()
        )
        for i, item in enumerate(items):
            db.add(
                AgentSessionItem(
                    session_id=session_id, sequence=next_sequence + i, item_json=item
                )
            )
        db.commit()


def pop_agent_session_item(session_id: str) -> dict | None:
    Session = get_session_factory()
    with Session() as db:
        row = (
            db.query(AgentSessionItem)
            .filter(AgentSessionItem.session_id == session_id)
            .order_by(AgentSessionItem.sequence.desc())
            .first()
        )
        if row is None:
            return None
        item = row.item_json
        db.delete(row)
        db.commit()
        return item


def clear_agent_session(session_id: str) -> None:
    Session = get_session_factory()
    with Session() as db:
        db.query(AgentSessionItem).filter(AgentSessionItem.session_id == session_id).delete()
        db.commit()
