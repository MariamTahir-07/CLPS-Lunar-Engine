import numpy as np, pytest
from app.science.horizon import horizon_detail, horizon_profile, visibility_state, visibility_percent, R_MOON_M

def test_flat_terrain_has_analytic_negative_horizon():
    px = 100.0
    r = horizon_detail(np.zeros((101, 101)), px, 50, 50)
    expected = -np.degrees(px / (2 * R_MOON_M))        # flat sphere: elevation = -theta/2
    assert np.all(r.elevation_deg < 0)
    assert np.allclose(r.elevation_deg, expected, rtol=1e-6)

def test_flat_terrain_observer_height_dip():
    h, px = 2.0, 100.0
    r = horizon_detail(np.zeros((101, 101)), px, 50, 50, observer_height_m=h)
    s = np.arange(1, 51) * px; th = s / R_MOON_M      # independent exact computation along the north ray
    exp = np.degrees(np.max(np.arctan2(R_MOON_M * np.cos(th) - (R_MOON_M + h), R_MOON_M * np.sin(th))))
    assert r.elevation_deg[0] == pytest.approx(exp, abs=1e-7)
    assert r.elevation_deg[0] == pytest.approx(-np.degrees(np.sqrt(2 * h / R_MOON_M)), rel=2e-3)  # classic dip angle

def test_unknown_terrain_is_nan_not_zero():
    d = np.full((101, 101), np.nan); d[50, 50] = 0.0
    r = horizon_detail(d, 20.0, 50, 50)
    assert np.isnan(r.elevation_deg).all() and r.unknown_fraction == 1.0
    assert np.isnan(horizon_profile(d, 20.0, 50, 50)[1]).all()

def test_partial_missing_data_only_affects_those_azimuths():
    d = np.zeros((101, 101)); d[:, 60:] = np.nan
    r = horizon_detail(d, 100.0, 50, 50)
    assert np.isfinite(r.elevation_deg[90]) and r.incomplete[90]      # valid samples exist but terrain beyond the hole is unknown
    assert np.isfinite(r.elevation_deg[270]) and not r.incomplete[270]
    assert 0 < r.incomplete_fraction < 1

def test_boundary_corner_observer():
    r = horizon_detail(np.zeros((51, 51)), 100.0, 0, 0)
    assert np.isnan(r.elevation_deg[315]) and r.coverage_m[315] == 0   # ray leaves the DEM immediately
    assert np.isfinite(r.elevation_deg[135]) and r.coverage_m[135] > 0

def test_grid_north_bearing_rotates_azimuth():
    dem = np.zeros((101, 101)); dem[:, 70] = 200.0           # wall on grid +x (grid east)
    az, el = horizon_profile(dem, 20.0, 50, 50)
    assert el[90] > 20 and el[0] < 1
    az, el = horizon_profile(dem, 20.0, 50, 50, grid_north_bearing_deg=90.0)   # local north points to grid +x
    assert el[0] > 20 and el[90] < 1

def test_exact_ridge_angle_includes_curvature():
    dem = np.zeros((101, 101)); dem[:, 70] = 200.0
    az, el = horizon_profile(dem, 20.0, 50, 50)
    assert el[90] == pytest.approx(np.degrees(np.arctan(200 / 400)), abs=0.01)

@pytest.mark.parametrize("kw", [dict(pixel_m=0), dict(pixel_m=float("nan")), dict(az_step_deg=0), dict(az_step_deg=90),
                                dict(observer_height_m=-1), dict(max_radius_m=0), dict(row=-1), dict(col=500)])
def test_invalid_inputs(kw):
    args = dict(dem=np.zeros((20, 20)), pixel_m=10.0, row=10, col=10); args.update(kw)
    with pytest.raises(ValueError): horizon_detail(**args)

def test_infinite_dem_rejected():
    d = np.zeros((20, 20)); d[3, 3] = np.inf
    with pytest.raises(ValueError): horizon_detail(d, 10.0, 10, 10)

def test_visibility_unknown_is_not_visible_and_excluded_from_percent():
    az = np.arange(360.0); el = np.zeros(360); el[100:200] = np.nan
    vis, unk = visibility_state([50, 150, 250], [5, 5, 5], az, el)
    assert list(vis) == [True, False, True] and list(unk) == [False, True, False]
    assert visibility_percent(vis, unk) == 100.0                  # unknown sample excluded, not counted as dark
    assert visibility_percent([False], [True]) is None            # nothing known -> None, never 0 %
