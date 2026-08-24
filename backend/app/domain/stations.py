"""Station resolution: exact code, alias, then fuzzy fallback. Pure Python --
no FastAPI, no OpenAI, no ORM imports. Operates only on the in-memory
reference data loaded by app/dataset.py."""

from difflib import SequenceMatcher

from app.dataset import STATIONS
from app.models import StationMatch, StationResolution

FUZZY_THRESHOLD = 0.6


def resolve(query: str) -> StationResolution:
    normalized = query.strip().lower()
    if not normalized:
        return StationResolution(query=query, matches=[], ambiguous=False)

    exact = [s for s in STATIONS if s.code.lower() == normalized]
    if exact:
        return _result(query, [(s, 1.0) for s in exact])

    alias = [s for s in STATIONS if normalized in (a.lower() for a in s.aliases)]
    if alias:
        return _result(query, [(s, 1.0) for s in alias])

    scored = []
    for s in STATIONS:
        candidates = [s.name.lower(), s.city.lower(), *(a.lower() for a in s.aliases)]
        best = max((_similarity(normalized, c) for c in candidates), default=0.0)
        if best >= FUZZY_THRESHOLD:
            scored.append((s, best))
    scored.sort(key=lambda pair: pair[1], reverse=True)

    # A perfect match (the query exactly equals a station's name, city, or
    # an alias) is unambiguous even if weaker fuzzy matches also cleared
    # the threshold -- the same "exact wins" principle already applied to
    # the code/alias tiers above, just reached via a different field.
    # Without this, a query that exactly names one station (e.g. "Chennai
    # Egmore") gets bundled with every other same-city station, and a
    # generic suffix like "Junction" pulls in unrelated stations nationwide.
    exact = [pair for pair in scored if pair[1] >= 1.0]
    if exact:
        return _result(query, exact)
    return _result(query, scored)


def _similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.85
    return SequenceMatcher(None, a, b).ratio()


def _result(query: str, scored: list[tuple]) -> StationResolution:
    matches = [StationMatch(station=s, score=score) for s, score in scored]
    return StationResolution(query=query, matches=matches, ambiguous=len(matches) > 1)
