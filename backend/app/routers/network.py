"""GET /api/network -- the rail network this app's mock data actually
covers, for the in-app guide panel's station graph and train listing.
Reuses dataset.py's already-loaded reference data rather than a second,
hand-duplicated copy of stations.json/trains.json/schedules.json in the
frontend, which could silently drift from the real dataset."""

from fastapi import APIRouter

from app import dataset

router = APIRouter()


@router.get("/api/network")
async def api_network() -> dict:
    stations = [
        {"code": s.code, "name": s.name, "city": s.city, "tier": s.tier}
        for s in dataset.STATIONS
    ]

    trains = []
    for t in dataset.TRAINS:
        stops = dataset.schedule_for_train(t.number)
        trains.append(
            {
                "number": t.number,
                "name": t.name,
                "classes": t.classes,
                # A train with more than an origin+terminus stop is one of the
                # two real, richly-scheduled corridors (SBC/YPR-NGP,
                # NGP-BSB) the demo's data is actually built around; a bare
                # 2-stop train exists only for search-realism between major
                # hubs. Derived from shape, not a hardcoded number list, so
                # this stays correct if the dataset changes.
                "corridor": "flagship" if len(stops) > 2 else "filler",
                "stops": [
                    {
                        "station_code": st.station_code,
                        "sequence": st.sequence,
                        "arrival": st.arrival,
                        "departure": st.departure,
                        "day_offset": st.day_offset,
                    }
                    for st in stops
                ],
            }
        )

    return {"stations": stations, "trains": trains}
