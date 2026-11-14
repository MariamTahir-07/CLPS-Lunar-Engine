import numpy as np, pytest
from app.science.slope import slope_deg, slope_stats
from app.science.horizon import horizon_profile, visible_mask, visibility_percent
from app.science.decision_engine import classify, evaluate

def test_flat_slope_zero():
    assert slope_stats(slope_deg(np.zeros((20, 20)), 20.0))["max_deg"] == pytest.approx(0)

def test_45deg_ramp():
    dem = np.tile(np.arange(30) * 20.0, (30, 1))  # 20 m rise per 20 m pixel
    assert slope_deg(dem, 20.0)[15, 15] == pytest.approx(45, abs=0.01)

def test_slope_nan_and_bad_input():
    d = np.zeros((10, 10)); d[5, 5] = np.nan
    assert slope_stats(slope_deg(d, 20.0))["valid_fraction"] < 1
    with pytest.raises(ValueError): slope_deg(np.zeros((2, 2)), 20.0)

def test_flat_horizon_near_zero():
    az, el = horizon_profile(np.zeros((101, 101)), 20.0, 50, 50)
    assert len(az) == 360 and np.all(el <= 0) and np.all(el > -0.1)

def test_ridge_east_raises_horizon():
    dem = np.zeros((101, 101)); dem[:, 70] = 200.0  # 200 m wall, 400 m east
    az, el = horizon_profile(dem, 20.0, 50, 50)
    assert el[90] == pytest.approx(np.degrees(np.arctan(200 / 400)), abs=0.5)
    assert el[270] < 1

def test_obstructed_vs_geometric_sun():
    az = np.arange(360.0); el = np.zeros(360); el[90] = 26.6
    m = visible_mask([90, 270], [10, 10], az, el)
    assert list(m) == [False, True]       # above horizon geometrically, blocked at az 90 only
    assert visibility_percent(m) == 50.0 and visibility_percent([]) is None

def test_horizon_input_validation():
    with pytest.raises(ValueError): horizon_profile(np.zeros((10, 10)), 20, 99, 0)
    d = np.zeros((10, 10)); d[5, 5] = np.nan
    with pytest.raises(ValueError): horizon_profile(d, 20, 5, 5)

@pytest.mark.parametrize("n,v,exp", [("slope_deg", 7.0, "Favorable"), ("slope_deg", 7.01, "Marginal"),
  ("slope_deg", 10.0, "Marginal"), ("slope_deg", 10.01, "Unfavorable"),
  ("solar_pct", 70, "Favorable"), ("solar_pct", 69.9, "Marginal"), ("solar_pct", 50, "Marginal"),
  ("solar_pct", 49.9, "Unfavorable"), ("earth_pct", 55, "Favorable"), ("earth_pct", 40, "Marginal"),
  ("earth_pct", 39.9, "Unfavorable"), ("psr_km", 2, "Favorable"), ("psr_km", 5, "Marginal"),
  ("psr_km", 5.1, "Unfavorable"), ("psr_km", None, "Insufficient data")])
def test_thresholds(n, v, exp): assert classify(n, v) == exp

def test_overall_never_go_with_missing():
    r = evaluate({"slope_deg": 3, "solar_pct": 90, "earth_pct": 80, "psr_km": None})
    assert r["overall"] == "Insufficient data"
    assert evaluate({"slope_deg": 3, "solar_pct": 90, "earth_pct": 80, "psr_km": 1})["overall"] == "Favorable"
