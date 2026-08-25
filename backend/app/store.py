"""Repository functions over the ORM. This is the ONLY module that touches
app/tables.py directly -- domain/engine/agent code goes through here and
only ever sees plain Pydantic models, never ORM rows. Every function takes
session_id and filters on it; there is no cross-session read in this file."""

from datetime import datetime, timedelta, timezone

from app.db import get_session_factory
from app.models import JourneyPlan, PassengerInput, PNRRecord, TDRClaimRecord
from app.tables import (
    AgentSessionItem,
    ClockOffset,
    FiredAlert,
    Journey,
    Message,
    Passenger,
    PNR,
    TDRClaim,
)

TDR_REFUND_DAYS = 45  # docs/01-research-context-log.md section 5

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
    arrival: str,
    arrival_day_offset: int,
    travel_class: str,
    status: str,
    fare_total: int,
    passengers: list[PassengerInput],
    linked_pnr: str | None = None,
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
            arrival=arrival,
            arrival_day_offset=arrival_day_offset,
            travel_class=travel_class,
            status=status,
            fare_total=fare_total,
            linked_pnr=linked_pnr,
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

        if linked_pnr:
            other = db.query(PNR).filter(
                PNR.session_id == session_id, PNR.pnr_number == linked_pnr
            ).first()
            if other is not None:
                other.linked_pnr = pnr_number
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
        arrival=pnr_row.arrival,
        arrival_day_offset=pnr_row.arrival_day_offset,
        travel_class=pnr_row.travel_class,
        status=pnr_row.status,
        total_fare=pnr_row.fare_total,
        passengers=[
            PassengerInput(name=p.name, age=p.age, berth_preference=p.berth_preference)
            for p in passenger_rows
        ],
        linked_pnr=pnr_row.linked_pnr,
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


def primary_pnr(session_id: str) -> PNRRecord | None:
    """The PNR Demo Controls should act on: the FIRST-booked PNR in the
    session, not the most recently booked one. For a two-leg connecting
    journey, leg 2 is booked after leg 1 (booking leg 2 requires already
    knowing leg 1's PNR to link it) but leg 1 is the train that's actually
    running late -- using latest_pnr() here would silently apply the delay
    to the wrong leg.

    Deliberately sorts by created_at, NOT by (date, departure): the date
    string on a booking is whatever the agent supplied, and a connecting
    leg 2 booked with an incorrectly-computed date (e.g. reusing leg 1's
    date instead of the correct next day) would otherwise look like it
    departs earlier than leg 1 and get picked as "primary" by mistake --
    this happened in testing. created_at is a fact this system controls
    itself, not something an upstream caller can get wrong."""
    Session = get_session_factory()
    with Session() as db:
        pnr_row = (
            db.query(PNR)
            .filter(PNR.session_id == session_id)
            .order_by(PNR.created_at.asc())
            .first()
        )
        return _pnr_row_to_record(db, pnr_row) if pnr_row else None


def linked_pnr_record(session_id: str, pnr: PNRRecord) -> PNRRecord | None:
    if not pnr.linked_pnr:
        return None
    return get_pnr(session_id, pnr.linked_pnr)


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


# --- TDR claims ------------------------------------------------------------


def file_tdr_claim(
    session_id: str, pnr: str, reason_code: str, reason_label: str, refund_amount: int
) -> TDRClaimRecord:
    Session = get_session_factory()
    with Session() as db:
        filed_at = datetime.now(timezone.utc)
        expected = filed_at + timedelta(days=TDR_REFUND_DAYS)
        row = TDRClaim(
            session_id=session_id,
            pnr_number=pnr,
            reason_code=reason_code,
            reason_label=reason_label,
            status="accepted",
            filed_at=filed_at,
            expected_refund_date=expected,
            refund_amount=refund_amount,
        )
        db.add(row)
        db.commit()
        return TDRClaimRecord(
            tdr_id=row.id,
            pnr=pnr,
            reason_code=reason_code,
            reason_label=reason_label,
            status=row.status,
            filed_at_iso=row.filed_at.isoformat(),
            expected_refund_date_iso=row.expected_refund_date.isoformat(),
            refund_amount=refund_amount,
        )


def get_tdr_claim(session_id: str, pnr: str) -> TDRClaimRecord | None:
    Session = get_session_factory()
    with Session() as db:
        row = (
            db.query(TDRClaim)
            .filter(TDRClaim.session_id == session_id, TDRClaim.pnr_number == pnr)
            .order_by(TDRClaim.filed_at.desc())
            .first()
        )
        if row is None:
            return None
        return TDRClaimRecord(
            tdr_id=row.id,
            pnr=row.pnr_number,
            reason_code=row.reason_code,
            reason_label=row.reason_label,
            status=row.status,
            filed_at_iso=row.filed_at.isoformat(),
            expected_refund_date_iso=row.expected_refund_date.isoformat(),
            refund_amount=row.refund_amount,
        )


# --- Admin: wipe every session's data ---------------------------------------


def reset_all_data() -> dict[str, int]:
    """Deletes every row in every table, across ALL sessions -- not scoped to
    one session_id like everything else in this file. Only ever called from
    the admin-token-gated endpoint in app/routers/admin.py; never from
    session-facing code. Deletes children before parents (Passenger -> PNR,
    PNR -> Journey) to respect foreign keys. Returns a per-table row count so
    the caller can report what was actually cleared."""
    Session = get_session_factory()
    with Session() as db:
        counts = {}
        for model in (
            Passenger,
            PNR,
            Journey,
            TDRClaim,
            FiredAlert,
            Message,
            AgentSessionItem,
            ClockOffset,
        ):
            counts[model.__tablename__] = db.query(model).delete()
        db.commit()
        return counts
