import numpy as np
from fastapi.testclient import TestClient
from app import main
from app.main import app
from app.science.geometry import sun_azel, earth_azel, validate_latlon
import pytest
c = TestClient(app)

def test_health_and_sites():
    assert c.get("/api/health").json()["status"] == "ok"
    assert len(c.get("/api/sites").json()) == 3

def test_frontend_serving_and_fallback(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (tmp_path / "index.html").write_text("<html>app shell</html>", encoding="utf-8")
    (assets / "app.js").write_text("window.app = true", encoding="utf-8")
    monkeypatch.setattr(main, "FRONTEND_DIST", tmp_path)

    assert c.get("/").text == "<html>app shell</html>"
    assert c.get("/mission/simulation").text == "<html>app shell</html>"
    assert c.get("/assets/app.js").text == "window.app = true"
    assert c.get("/assets/missing.js").status_code == 404
    assert c.get("/api/not-a-route").status_code == 404
    assert c.get("/api/health").json()["status"] == "ok"

def test_analyze_ok_and_honest():
    r = c.post("/api/analyze", json={"site_id": "malapert", "start": "2026-11-14", "days": 10})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["decision"]["overall"] != "Favorable"   # psr missing -> must not be GO
    assert j["decision"]["criteria"]["psr_km"]["status"] == "Insufficient data"
    assert len(j["horizon"]["azimuth_deg"]) == 360 and "illustrative" in j["labels"]["geometry"]

@pytest.mark.parametrize("body,code", [
  ({"site_id": "nope", "start": "2026-11-14"}, 404),
  ({"site_id": "malapert", "start": "1999-01-01"}, 422),
  ({"site_id": "malapert", "start": "2026-11-14", "days": 120, "step_hours": 0.5}, 422),
  ({"site_id": "malapert", "start": "bad"}, 422)])
def test_invalid(body, code): assert c.post("/api/analyze", json=body).status_code == code

def test_geometry_sanity():
    az, el = sun_azel(-89.5, 0, np.linspace(0, 29.5, 200))
    assert el.min() >= -2.0 and el.max() <= 2.0      # polar site: Sun within a few degrees of horizon
    _, ee = earth_azel(-89.5, 0, np.linspace(0, 27, 200))
    assert ee.min() < 0 < ee.max()                   # Earth rises and sets with libration
    az, el = sun_azel(-60.0, 0, 0.0)                 # sub-solar lon 0, equinox-ish: sun due north at lat -60
    assert el == pytest.approx(30, abs=1.6) and (az < 5 or az > 355)

def test_latlon_validation():
    for bad in [(10, 0), (-95, 0), (-89, 400)]:
        with pytest.raises(ValueError): validate_latlon(*bad)
