from app.domain.catering import available_vendors


def test_vendor_exactly_at_cutoff_is_included():
    # GTL has a vendor with cutoff_minutes=20 (Guntakal Junction Tiffins).
    vendors, hidden = available_vendors("GTL", minutes_until_arrival=20)
    names = [v.name for v in vendors]
    assert "Guntakal Junction Tiffins" in names


def test_vendor_one_minute_short_of_cutoff_is_excluded():
    vendors, hidden = available_vendors("GTL", minutes_until_arrival=19)
    names = [v.name for v in vendors]
    assert "Guntakal Junction Tiffins" not in names


def test_hidden_count_matches_excluded_vendors():
    all_vendors_count = 2  # GTL has exactly 2 vendors in catering.json
    vendors, hidden = available_vendors("GTL", minutes_until_arrival=15)
    assert len(vendors) + hidden == all_vendors_count


def test_plenty_of_time_includes_everyone_at_the_station():
    vendors, hidden = available_vendors("ALD", minutes_until_arrival=999)
    assert hidden == 0
    assert len(vendors) > 0


def test_no_time_at_all_excludes_everyone():
    vendors, hidden = available_vendors("ALD", minutes_until_arrival=0)
    assert vendors == []
    assert hidden > 0


def test_station_with_no_vendors_returns_empty_not_an_error():
    vendors, hidden = available_vendors("XYZ_NOT_A_STATION", minutes_until_arrival=100)
    assert vendors == []
    assert hidden == 0
