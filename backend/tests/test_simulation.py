import datetime as dt, pytest, numpy as np
from fastapi.testclient import TestClient
from app import main
from app.main import app
from app.science.windows import visibility_windows
c = TestClient(app)
def post(**kw):
    b = {"site_id": "malapert", "start": "2026-11-14T00:00:00Z", "days": 2, "step_hours": 6}; b.update(kw)
    return c.post("/api/analyze", json=b)

def test_sample_count_and_consistent_arrays():
    j = post().json(); n = j["window"]["n_samples"]
    assert n == 8 and all(len(j["timeline"][k]) == n for k in ("time_iso", "sun_el", "sun_visible", "earth_visible", "earth_el"))

def test_step_larger_than_duration_is_rejected_not_empty():
    r = post(days=1, step_hours=48)
    assert r.status_code == 422 and "step_hours" in r.json()["detail"]

def test_minimum_two_samples():
    assert post(days=1, step_hours=12).json()["window"]["n_samples"] == 2
    assert post(days=1, step_hours=13).status_code == 422

@pytest.mark.parametrize("days", [0.5, 1, 3.5, 30, 120])
@pytest.mark.parametrize("step", [0.5, 1, 6, 24, 48])
def test_never_200_with_empty_timeline(days, step):
    r = post(days=days, step_hours=step)
    if r.status_code == 200: assert len(r.json()["timeline"]["time_iso"]) >= 2
    else: assert r.status_code == 422 and isinstance(r.json()["detail"], str)

def test_fractional_day():
    assert post(days=0.5, step_hours=0.5).json()["window"]["n_samples"] == 24

def test_time_axis_is_utc_and_evenly_stepped():
    t = [dt.datetime.fromisoformat(x) for x in post().json()["timeline"]["time_iso"]]
    assert t[1] - t[0] == dt.timedelta(hours=6) and t[0].utcoffset() == dt.timedelta(0)
    assert post(start="2026-11-14T00:00:00").json()["window"]["start"].endswith("+00:00")   # naive -> UTC
    j = post(start="2026-11-14T03:00:00+05:00").json(); assert j["window"]["start"].startswith("2026-11-13T22:00")

def test_range_checks():
    assert post(start="2040-12-30T00:00:00Z", days=5).status_code == 422
    assert post(start="2019-12-31T00:00:00Z").status_code == 422

@pytest.mark.parametrize("bad", [{"days": "nan"}, {"days": "inf"}, {"days": 0}, {"step_hours": -1}, {"start": "not a date"}, {"radius_m": 5}])
def test_bad_numbers_give_readable_422(bad):
    r = post(**bad); assert r.status_code == 422 and isinstance(r.json()["detail"], str)

def test_unexpected_error_is_clean_json_500(monkeypatch):
    monkeypatch.setattr(main.slope, "slope_deg", lambda *a, **k: 1 / 0)
    r = TestClient(app, raise_server_exceptions=False).post("/api/analyze", json={"site_id": "malapert", "start": "2026-11-14"})
    assert r.status_code == 500 and "Traceback" not in r.text and "detail" in r.json()

def test_missing_dem_gives_503_not_fake_terrain(monkeypatch):
    monkeypatch.setenv("CLPS_DEM_PATH", "/definitely/not/here.tif")
    r = post(); assert r.status_code == 503 and "Terrain dataset unavailable" in r.json()["detail"]
    assert c.get("/api/health").json()["mode"] == "user_dem"

def test_health_does_not_claim_spice():
    assert c.get("/api/health").json()["spice_pipeline"] == "not connected"

def test_compare_is_labelled_illustrative_and_has_no_ranking():
    j = c.post("/api/compare", json={"start": "2026-11-14", "days": 10, "step_hours": 6}).json()
    assert len(j["sites"]) == 3 and j["real_data"] is False and "ILLUSTRATIVE" in j["notice"]
    assert all("rank" not in k for s in j["sites"] for k in s) and all(s["overall"] != "Favorable" for s in j["sites"])
    assert c.post("/api/compare", json={"start": "2026-11-14", "days": 1, "step_hours": 48}).status_code == 422

def test_windows():
    w = visibility_windows([False, True, True, False, True], dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc), 6)
    assert w["n_windows"] == 2 and w["windows"][0]["duration_h"] == 12 and w["longest_gap_h"] == 6 and w["windows"][0]["start"].startswith("2026-01-01T06")
    assert visibility_windows([False] * 5, dt.datetime(2026, 1, 1), 6)["longest_gap_h"] == 30
    assert visibility_windows([], dt.datetime(2026, 1, 1), 6)["n_windows"] == 0
