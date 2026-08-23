import pytest

from app.domain.waitlist import predict


def test_available_status_is_always_confirm_at_100_percent():
    result = predict("AVAILABLE", "GN", 26)
    assert result.band == "confirm"
    assert result.probability == 100.0


def test_rac_counts_as_confirmed():
    result = predict("RAC", "GN", 3)
    assert result.band == "confirm"
    assert result.probability == 100.0
    assert "RAC" in result.explanation


def test_unknown_status_raises():
    with pytest.raises(ValueError):
        predict("BOGUS", "GN", 1)


def test_matches_the_flagship_pdd_figure_exactly():
    # docs/03-product-design-document.md Flow A3: 12295 SL GNWL/18 -> Probable 30-70%.
    # GN ceiling=40, modifier=1.0 -> 1 - 18/40 = 0.55 -> 55%.
    result = predict("WL", "GN", 18)
    assert result.band == "probable"
    assert result.probability == 55.0


def test_boundary_at_exactly_70_percent_is_probable_not_confirm():
    # GN ceiling 40: position 12 -> 1 - 12/40 = 0.70 exactly.
    result = predict("WL", "GN", 12)
    assert result.probability == 70.0
    assert result.band == "probable"


def test_boundary_at_exactly_30_percent_is_probable_not_low():
    # GN ceiling 40: position 28 -> 1 - 28/40 = 0.30 exactly.
    result = predict("WL", "GN", 28)
    assert result.probability == 30.0
    assert result.band == "probable"


def test_clearly_above_70_is_confirm():
    result = predict("WL", "GN", 5)  # 1 - 5/40 = 87.5%
    assert result.band == "confirm"


def test_clearly_below_30_is_low():
    result = predict("WL", "GN", 35)  # 1 - 35/40 = 12.5%
    assert result.band == "low"


def test_position_beyond_ceiling_clamps_to_zero_not_negative():
    result = predict("WL", "GN", 999)
    assert result.probability == 0.0
    assert result.band == "low"


def test_gnwl_beats_rlwl_beats_tqwl_at_an_identical_position():
    gn = predict("WL", "GN", 12)
    rl = predict("WL", "RL", 12)
    tq = predict("WL", "TQ", 12)
    assert gn.probability > rl.probability > tq.probability


def test_explanation_names_waitlist_type_position_and_season():
    result = predict("WL", "GN", 18)
    assert "GNWL" in result.explanation
    assert "18" in result.explanation
    assert "normal week" in result.explanation
