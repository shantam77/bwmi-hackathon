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
