"""Direct and single-interchange connecting route search. Pure Python -- no
FastAPI, no OpenAI, no ORM imports.

Day-offset convention: every train in trains.json runs daily, so a
connection's layover is computed purely from time-of-day at the interchange
station (rolling to the next day if the connecting train's departure time
has already passed) -- there is no need to reconcile two trains' day_offset
fields against different origin dates. Each Leg's own day_offset fields are
expressed relative to the *user's search date* (0 = the date searched), not
relative to either train's own origin."""

from app.dataset import TRAINS, availability_for_train, schedule_for_train
from app.models import JourneyPlan, Leg

MIN_INTERCHANGE_MINUTES = 15


def search(
    from_code: str, to_code: str, date: str, travel_class: str | None = None
) -> list[JourneyPlan]:
    direct = _direct_journey_plans(from_code, to_code, travel_class)
    if direct:
        return direct
    return _connecting_journey_plans(from_code, to_code, travel_class)


def _time_to_minutes(time_str: str) -> int:
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


def _direct_journey_plans(from_code: str, to_code: str, travel_class: str | None) -> list[JourneyPlan]:
    plans = []
    for train in TRAINS:
        stops = schedule_for_train(train.number)
        from_stop = next((s for s in stops if s.station_code == from_code), None)
        to_stop = next((s for s in stops if s.station_code == to_code), None)
        if not from_stop or not to_stop or from_stop.sequence >= to_stop.sequence:
            continue

        for entry in availability_for_train(train.number):
            if travel_class and entry.travel_class != travel_class:
                continue
            leg = Leg(
                train_number=train.number,
                train_name=train.name,
                from_station=from_code,
                to_station=to_code,
                departure=from_stop.departure,
                arrival=to_stop.arrival,
                departure_day_offset=0,
                arrival_day_offset=to_stop.day_offset - from_stop.day_offset,
                travel_class=entry.travel_class,
                status=entry.status,
                seats_or_position=entry.seats_or_position,
                fare_per_passenger=entry.fare_per_passenger,
            )
            plans.append(JourneyPlan(legs=[leg], direct=True))
    return plans


def _connecting_journey_plans(
    from_code: str, to_code: str, travel_class: str | None
) -> list[JourneyPlan]:
    plans = []
    for train_a in TRAINS:
        stops_a = schedule_for_train(train_a.number)
        from_stop = next((s for s in stops_a if s.station_code == from_code), None)
        if not from_stop or from_stop.departure is None:
            continue

        for interchange_stop in stops_a:
            if interchange_stop.sequence <= from_stop.sequence:
                continue
            if interchange_stop.station_code == to_code or interchange_stop.arrival is None:
                continue

            interchange_code = interchange_stop.station_code
            arrival_time = _time_to_minutes(interchange_stop.arrival)
            leg1_arrival_day = interchange_stop.day_offset - from_stop.day_offset

            for train_b in TRAINS:
                if train_b.number == train_a.number:
                    continue
                stops_b = schedule_for_train(train_b.number)
                depart_stop = next((s for s in stops_b if s.station_code == interchange_code), None)
                to_stop = next((s for s in stops_b if s.station_code == to_code), None)
                if not depart_stop or not to_stop or depart_stop.sequence >= to_stop.sequence:
                    continue
                if depart_stop.departure is None or to_stop.arrival is None:
                    continue

                departure_time = _time_to_minutes(depart_stop.departure)
                if departure_time - arrival_time >= MIN_INTERCHANGE_MINUTES:
                    layover = departure_time - arrival_time
                    rollover_days = 0
                else:
                    layover = (departure_time + 24 * 60) - arrival_time
                    rollover_days = 1

                leg2_departure_day = leg1_arrival_day + rollover_days
                leg2_arrival_day = leg2_departure_day + (to_stop.day_offset - depart_stop.day_offset)

                for entry_a in availability_for_train(train_a.number):
                    if travel_class and entry_a.travel_class != travel_class:
                        continue
                    for entry_b in availability_for_train(train_b.number):
                        if travel_class and entry_b.travel_class != travel_class:
                            continue
                        leg1 = Leg(
                            train_number=train_a.number,
                            train_name=train_a.name,
                            from_station=from_code,
                            to_station=interchange_code,
                            departure=from_stop.departure,
                            arrival=interchange_stop.arrival,
                            departure_day_offset=0,
                            arrival_day_offset=leg1_arrival_day,
                            travel_class=entry_a.travel_class,
                            status=entry_a.status,
                            seats_or_position=entry_a.seats_or_position,
                            fare_per_passenger=entry_a.fare_per_passenger,
                        )
                        leg2 = Leg(
                            train_number=train_b.number,
                            train_name=train_b.name,
                            from_station=interchange_code,
                            to_station=to_code,
                            departure=depart_stop.departure,
                            arrival=to_stop.arrival,
                            departure_day_offset=leg2_departure_day,
                            arrival_day_offset=leg2_arrival_day,
                            travel_class=entry_b.travel_class,
                            status=entry_b.status,
                            seats_or_position=entry_b.seats_or_position,
                            fare_per_passenger=entry_b.fare_per_passenger,
                        )
                        plans.append(
                            JourneyPlan(
                                legs=[leg1, leg2],
                                direct=False,
                                interchange=interchange_code,
                                layover_minutes=layover,
                            )
                        )
    return plans
