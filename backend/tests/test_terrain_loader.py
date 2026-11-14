import math, numpy as np, pytest, os
rasterio = pytest.importorskip("rasterio"); pyproj = pytest.importorskip("pyproj")
from rasterio.transform import from_origin
from rasterio.crs import CRS
from app.science import terrain_loader as tl
from app.main import app
from fastapi.testclient import TestClient
MOON = CRS.from_wkt(pyproj.CRS.from_proj4("+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m +no_defs").to_wkt())

def make(path, data, crs=MOON, px=20.0, py=None, nodata=None, scales=None):
    h, w = data.shape
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1, dtype=data.dtype, crs=crs,
                       transform=from_origin(-w * px / 2, h * px / 2, px, py or px), nodata=nodata) as d:
        d.write(data, 1)
        if scales: d.scales = scales
    return str(path)
SITE = dict(lat_deg=-89.9, lon_deg=129.0, radius_m=1000.0)
POLE = dict(lat_deg=-90.0, lon_deg=0.0, radius_m=1000.0)   # pole = raster centre pixel (500,500)
def flat(): return np.zeros((1000, 1000), "float32")

def test_valid_window_and_grid_north(tmp_path):
    p = make(tmp_path / "ok.tif", flat()); t = tl.load_window(p, **SITE)
    assert t.dem.shape == (101, 101) and t.pixel_m == 20 and (t.row, t.col) == (50, 50)
    tr = pyproj.Transformer.from_crs(pyproj.CRS.from_user_input(MOON).geodetic_crs, MOON.to_wkt(), always_xy=True)
    sx, sy = tr.transform(129.0, -89.9)
    assert t.grid_north_bearing_deg == pytest.approx(math.degrees(math.atan2(sx, sy)) % 360, abs=0.05)  # north = radially outward from the S pole
    assert tl.load_window(p, lat_deg=-89.9, lon_deg=90.0, radius_m=1000).grid_north_bearing_deg == pytest.approx(90, abs=0.05)

def test_earth_crs_rejected(tmp_path):
    p = make(tmp_path / "earth.tif", flat(), crs=CRS.from_epsg(3031))
    with pytest.raises(tl.DatasetError, match="lunar"): tl.load_window(p, **SITE)

def test_no_crs_rejected(tmp_path):
    with pytest.raises(tl.DatasetError, match="no CRS"): tl.load_window(make(tmp_path / "n.tif", flat(), crs=None), **SITE)

def test_integer_without_scale_is_ambiguous_but_ok_with_explicit_scale_and_nodata(tmp_path):
    d = np.zeros((1000, 1000), "int16"); d[530:534, 530:534] = -32768; d[500, 500] = 200
    p = make(tmp_path / "i.tif", d, nodata=-32768)
    with pytest.raises(tl.DatasetError, match="scale"): tl.load_window(p, **POLE)
    t = tl.load_window(p, z_scale=0.5, **POLE)
    assert np.nanmax(t.dem) == 100.0                      # 200 DN * 0.5 m
    assert np.isnan(t.dem).sum() == 16               # nodata -> NaN, never a number
    assert tl.inspect_dem(p, z_scale=0.5)["valid_fraction_sampled"] < 1.0

def test_nodata_becomes_nan_and_too_much_missing_rejected(tmp_path):
    d = flat(); d[:, :500] = -9999
    p = make(tmp_path / "m.tif", d, nodata=-9999)
    with pytest.raises(tl.DatasetError): tl.load_window(p, lat_deg=-89.9, lon_deg=129.0, radius_m=6000.0)  # window half-missing
    d2 = flat(); d2[495:505, 495:505] = -9999        # hole at the site
    with pytest.raises(tl.DatasetError, match="missing data"): tl.load_window(make(tmp_path / "h.tif", d2, nodata=-9999), lat_deg=-90.0, lon_deg=0.0, radius_m=1000)

def test_outside_coverage_rejected(tmp_path):
    p = make(tmp_path / "c.tif", flat())
    with pytest.raises(tl.DatasetError, match="not fully covered"): tl.load_window(p, **{**SITE, "radius_m": 50000.0, })
    with pytest.raises(tl.DatasetError): tl.load_window(p, lat_deg=-80.0, lon_deg=0.0, radius_m=1000)

def test_implausible_elevations_and_bad_geometry_rejected(tmp_path):
    d = flat(); d[480:520, 480:520] = 5e6
    with pytest.raises(tl.DatasetError, match="implausible"): tl.load_window(make(tmp_path / "e.tif", d), **POLE)
    with pytest.raises(tl.DatasetError, match="non-square"): tl.load_window(make(tmp_path / "ns.tif", flat(), py=25.0), **SITE)
    with pytest.raises(tl.DatasetError, match="not found"): tl.inspect_dem(str(tmp_path / "nope.tif"))

def test_bad_inputs(tmp_path):
    p = make(tmp_path / "b.tif", flat())
    for kw in [dict(radius_m=0), dict(radius_m=float("nan")), dict(lat_deg=95)]:
        with pytest.raises(tl.DatasetError): tl.load_window(p, **{**SITE, **kw})
    with pytest.raises(tl.DatasetError, match="exceeds limit"): tl.load_window(p, **SITE, max_pixels=100)

def test_api_uses_validated_dem(tmp_path, monkeypatch):
    monkeypatch.setenv("CLPS_DEM_PATH", make(tmp_path / "api.tif", flat()))
    r = TestClient(app).post("/api/analyze", json={"site_id": "shackleton_rim", "start": "2026-11-14", "days": 5, "radius_m": 1000})
    j = r.json(); assert r.status_code == 200, r.text
    assert j["labels"]["data_mode"] == "user_dem" and "user-supplied" in j["labels"]["terrain"] and "synthetic" not in j["labels"]["terrain"]
    assert j["horizon"]["unknown_fraction"] == 0 and max(j["horizon"]["elevation_deg"]) < 0   # flat ground: negative horizon via curvature
    d = np.zeros((1000, 1000), "float32"); monkeypatch.setenv("CLPS_DEM_PATH", make(tmp_path / "e3031.tif", d, crs=CRS.from_epsg(3031)))
    assert TestClient(app).post("/api/analyze", json={"site_id": "shackleton_rim", "start": "2026-11-14"}).status_code == 503
