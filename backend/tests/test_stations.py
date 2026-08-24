from app.domain.stations import resolve


def test_exact_code_resolves_to_a_single_station():
    result = resolve("NGP")
    assert not result.ambiguous
    assert len(result.matches) == 1
    assert result.matches[0].station.code == "NGP"


def test_exact_code_is_case_insensitive():
    result = resolve("ngp")
    assert len(result.matches) == 1
    assert result.matches[0].station.code == "NGP"


def test_bangalore_is_ambiguous_across_all_four_stations():
    result = resolve("bangalore")
    assert result.ambiguous
    codes = {m.station.code for m in result.matches}
    assert codes == {"SBC", "YPR", "KJM", "BNC"}


def test_bengaluru_alias_is_also_ambiguous_across_the_same_four_stations():
    result = resolve("bengaluru")
    codes = {m.station.code for m in result.matches}
    assert codes == {"SBC", "YPR", "KJM", "BNC"}


def test_unambiguous_alias_resolves_to_one_station():
    result = resolve("nagpur")
    assert not result.ambiguous
    assert result.matches[0].station.code == "NGP"


def test_varanasi_aliases_resolve_correctly():
    for alias in ["varanasi", "banaras", "benares"]:
        result = resolve(alias)
        assert not result.ambiguous, alias
        assert result.matches[0].station.code == "BSB"


def test_typo_still_finds_bengaluru_stations_via_fuzzy_fallback():
    result = resolve("banglore")  # missing the second 'a'
    codes = {m.station.code for m in result.matches}
    assert "SBC" in codes or "YPR" in codes


def test_nonsense_query_returns_no_matches():
    result = resolve("zzzznotarealplace123")
    assert result.matches == []
    assert not result.ambiguous


def test_empty_query_returns_no_matches():
    result = resolve("")
    assert result.matches == []
    assert not result.ambiguous


def test_exact_full_name_match_is_not_diluted_by_noisy_fuzzy_matches():
    # Regression test: "Ahmedabad Junction" exactly names one station (ADI),
    # but the generic word "Junction" also appears in a dozen+ unrelated
    # station names (Guntakal Junction, Jhansi Junction, Mysuru Junction...).
    # Before this fix, SequenceMatcher's ratio on the shared "Junction"
    # substring pushed several of those over FUZZY_THRESHOLD, so an exact
    # full-name match got incorrectly reported as ambiguous across 18
    # stations -- found via live E2E, not by this suite originally.
    result = resolve("ahmedabad junction")
    assert not result.ambiguous
    assert len(result.matches) == 1
    assert result.matches[0].station.code == "ADI"
    assert result.matches[0].score == 1.0


def test_exact_name_match_wins_even_when_sharing_a_city_with_another_station():
    # "Chennai Egmore" exactly names MS, but MAS (Chennai Central) shares
    # the city "Chennai" closely enough to also clear the fuzzy threshold.
    # The exact name match should win outright, not be bundled with it.
    result = resolve("chennai egmore")
    assert not result.ambiguous
    assert result.matches[0].station.code == "MS"
