from app.domain.retiring import room_options


def test_wl_pnr_never_sees_a_room_offer():
    options = room_options("NGP", "WL")
    assert options == []


def test_confirmed_pnr_sees_room_options():
    options = room_options("NGP", "CNF")
    assert len(options) > 0
    assert all(o.available for o in options)


def test_rac_pnr_sees_room_options_same_as_confirmed():
    cnf_options = room_options("NGP", "CNF")
    rac_options = room_options("NGP", "RAC")
    assert len(rac_options) == len(cnf_options)


def test_station_with_no_available_rooms_returns_empty():
    # GTL is marked available=false in retiring_rooms.json.
    options = room_options("GTL", "CNF")
    assert options == []


def test_unknown_status_gets_no_offer():
    options = room_options("NGP", "SOMETHING_ELSE")
    assert options == []
