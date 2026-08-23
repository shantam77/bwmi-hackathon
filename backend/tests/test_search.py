from app.domain.search import search

DATE = "2026-09-04"


def test_no_direct_route_from_bengaluru_to_varanasi():
    plans = search("SBC", "BSB", DATE)
    assert all(not p.direct for p in plans)


def test_connecting_route_via_nagpur_exists():
    plans = search("SBC", "BSB", DATE)
    assert plans
    assert any(p.interchange == "NGP" for p in plans)
    assert all(len(p.legs) == 2 for p in plans)


def test_flagship_layover_matches_pdd_exactly():
    # docs/03-product-design-document.md Flow A3: "Layover at Nagpur: 2h 25m"
    # for 12295 (arrives 06:15) -> 12539 (departs 08:40).
    plans = search("SBC", "BSB", DATE)
    flagship = [
        p
        for p in plans
        if p.legs[0].train_number == "12295" and p.legs[1].train_number == "12539"
    ]
    assert flagship
    assert flagship[0].layover_minutes == 145  # 2h25m


def test_flagship_leg_dates_roll_forward_correctly():
    plans = search("SBC", "BSB", DATE, travel_class="SL")
    flagship = next(
        p
        for p in plans
        if p.legs[0].train_number == "12295" and p.legs[1].train_number == "12539"
    )
    leg1, leg2 = flagship.legs
    assert leg1.departure_day_offset == 0
    assert leg1.arrival_day_offset == 1  # SBC 4 Sep 20:00 -> NGP 5 Sep 06:15
    assert leg2.departure_day_offset == 1  # NGP 5 Sep 08:40
    assert leg2.arrival_day_offset == 1  # BSB 5 Sep 21:10, same day as departure


def test_rebooking_option_from_pdd_flow_h_exists():
    # Flow H: "There's a 14:20 Nagpur-Varanasi, 6 sleeper seats, same ₹1,890."
    plans = search("SBC", "BSB", DATE, travel_class="SL")
    rebooking_legs = [
        p.legs[1]
        for p in plans
        if p.legs[1].train_number == "15665" and p.legs[1].departure == "14:20"
    ]
    assert rebooking_legs
    leg = rebooking_legs[0]
    assert leg.status == "AVAILABLE"
    assert leg.seats_or_position == 6
    assert leg.fare_per_passenger == 945  # x2 passengers = ₹1,890


def test_direct_sbc_to_ngp_finds_sanghamitra_waitlisted():
    plans = search("SBC", "NGP", DATE, travel_class="SL")
    sanghamitra = [p for p in plans if p.legs[0].train_number == "12295"]
    assert sanghamitra
    leg = sanghamitra[0].legs[0]
    assert leg.status == "WL"
    assert leg.seats_or_position == 18
    assert leg.fare_per_passenger == 620


def test_at_least_three_leg1_trains_across_the_bengaluru_group():
    # PDD Flow A1: Bengaluru resolves to four stations; the agent checks all
    # of them. At least 3 distinct trains should turn up in aggregate.
    train_numbers = set()
    for origin in ["SBC", "YPR", "KJM", "BNC"]:
        for plan in search(origin, "NGP", DATE):
            train_numbers.add(plan.legs[0].train_number)
    assert len(train_numbers) >= 3


def test_at_least_three_leg2_trains_from_nagpur():
    train_numbers = {p.legs[0].train_number for p in search("NGP", "BSB", DATE)}
    assert len(train_numbers) >= 3


def test_no_route_between_disconnected_stations():
    plans = search("MAS", "CSMT", DATE)
    assert plans == []


def test_direct_route_preferred_over_connecting_when_both_could_exist():
    # SBC -> NGP has a direct train, so no connecting search should even run.
    plans = search("SBC", "NGP", DATE)
    assert all(p.direct for p in plans)
