import datetime as dt, logging, math, os
from pathlib import Path
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from .science import geometry, horizon, slope, decision_engine, terrain_loader, windows

log = logging.getLogger("clps")
app = FastAPI(title="CLPS Lunar Landing Site Engine", version="0.2.0")
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# In production (Render), allow the same origin; in dev, allow Vite's dev server.
_cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_render_url = os.environ.get("RENDER_EXTERNAL_URL")
if _render_url:
    _cors_origins.append(_render_url.rstrip("/"))
app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_methods=["*"], allow_headers=["*"])

# DEMONSTRATION scenarios: coordinates are approximate placeholders, NOT verified site data.
SITES = {
  "connecting_ridge": {"name": "Connecting Ridge", "lat": -89.45, "lon": 222.0, "relief_m": 120},
  "shackleton_rim":   {"name": "Shackleton South Rim", "lat": -89.9, "lon": 129.0, "relief_m": 250},
  "malapert":         {"name": "Malapert Massif", "lat": -86.0, "lon": 0.0, "relief_m": 80},
}
MAX_STEPS, MIN_STEPS, PIXEL_M, OBSERVER_H_M = 4000, 2, 40.0, 2.0
EPOCH_J2000 = dt.datetime(2000, 1, 1, 12, tzinfo=dt.timezone.utc)
RANGE = (dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc), dt.datetime(2041, 1, 1, tzinfo=dt.timezone.utc))

def demo_dem(site_id) -> terrain_loader.LocalDEM:
    """ILLUSTRATIVE synthetic terrain (seeded noise). Not LOLA."""
    rng = np.random.default_rng(sum(map(ord, site_id)))
    n = 201; z = rng.normal(0, 1, (n, n))
    for _ in range(40): z = (z + np.roll(z, 1, 0) + np.roll(z, 1, 1) + np.roll(z, -1, 0) + np.roll(z, -1, 1)) / 5
    z = z / z.std() * SITES[site_id]["relief_m"] / 10
    return terrain_loader.LocalDEM(z, PIXEL_M, n // 2, n // 2, 0.0, "illustrative synthetic DEM (seeded noise; not LOLA)")

def get_terrain(site_id, radius_m):
    path = os.environ.get("CLPS_DEM_PATH")
    if not path: return demo_dem(site_id), "demonstration"
    zs = os.environ.get("CLPS_DEM_ZSCALE")
    try:
        s = SITES[site_id]
        return terrain_loader.load_window(path, s["lat"], s["lon"], radius_m, float(zs) if zs else None), "user_dem"
    except (terrain_loader.DatasetError, ValueError) as e:   # never fall back silently to fake terrain
        raise HTTPException(503, f"Terrain dataset unavailable: {e}")

class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    site_id: str
    start: dt.datetime
    days: float = Field(30, ge=0.5, le=120)
    step_hours: float = Field(6, ge=0.5, le=48)
    az_step_deg: float = Field(1.0, ge=0.5, le=10)
    radius_m: float = Field(3000, ge=200, le=20000)

class CompareRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    start: dt.datetime
    days: float = Field(30, ge=0.5, le=120)
    step_hours: float = Field(6, ge=0.5, le=48)

def plan_samples(start: dt.datetime, days: float, step_hours: float):
    """-> (utc_start, n_samples). Rejects (never silently empties) impossible requests."""
    start = start.replace(tzinfo=dt.timezone.utc) if start.tzinfo is None else start.astimezone(dt.timezone.utc)
    dur_h = days * 24.0
    n = int(math.floor(dur_h / step_hours + 1e-9))
    if n < MIN_STEPS:
        raise HTTPException(422, f"step_hours ({step_hours} h) is too large for a {days}-day simulation: need at least {MIN_STEPS} samples "
                                 f"(step <= {dur_h / MIN_STEPS:g} h)")
    if n > MAX_STEPS:
        raise HTTPException(422, f"Too many samples ({n} > {MAX_STEPS}); shorten the period or use step >= {dur_h / MAX_STEPS:.2f} h")
    end = start + dt.timedelta(hours=n * step_hours)
    if start < RANGE[0] or end > RANGE[1]:
        raise HTTPException(422, "Simulation must lie within 2020-01-01 .. 2040-12-31 UTC (range of the approximate model)")
    return start, n

def run_site(site_id, start, days, step_hours, az_step_deg=1.0, radius_m=3000.0):
    if site_id not in SITES: raise HTTPException(404, "Unknown site_id")
    start, n = plan_samples(start, days, step_hours)
    s = SITES[site_id]
    try:
        geometry.validate_latlon(s["lat"], s["lon"])
        ter, mode = get_terrain(site_id, radius_m)
        dem = ter.dem
        sl = slope.slope_stats(slope.slope_deg(dem, ter.pixel_m))
        hz = horizon.horizon_detail(dem, ter.pixel_m, ter.row, ter.col, OBSERVER_H_M, az_step_deg, radius_m, ter.grid_north_bearing_deg)
        times = [start + dt.timedelta(hours=k * step_hours) for k in range(n)]
        t = (start - EPOCH_J2000).total_seconds() / 86400 + np.arange(n) * step_hours / 24
        sa, se = geometry.sun_azel(s["lat"], s["lon"], t); ea, ee = geometry.earth_azel(s["lat"], s["lon"], t)
        sv, su = horizon.visibility_state(sa, se, hz.azimuth_deg, hz.elevation_deg)
        ev, eu = horizon.visibility_state(ea, ee, hz.azimuth_deg, hz.elevation_deg)
    except ValueError as e:
        raise HTTPException(422, str(e))
    vals = {"slope_deg": sl["max_deg"], "solar_pct": horizon.visibility_percent(sv, su),
            "earth_pct": horizon.visibility_percent(ev, eu), "psr_km": None}
    cov = hz.coverage_m[hz.coverage_m > 0]
    return {"site": {"id": site_id, **s},
      "labels": {"data_mode": mode, "terrain": ter.source, "geometry": "illustrative analytic model (no SPICE)",
                 "time_system": "UTC (approximate analytic model; no leap-second / TDB handling)",
                 "observer_height_m": OBSERVER_H_M, "observer_height_label": "configurable engineering assumption",
                 "radius_m": float(cov.min()) if cov.size else 0.0, "psr_km": "no PSR data loaded"},
      "window": {"start": start.isoformat(), "end": times[-1].isoformat(), "step_hours": step_hours, "n_samples": n, "days": days},
      "slope": sl,
      "horizon": {"azimuth_deg": hz.azimuth_deg.tolist(), "elevation_deg": [None if np.isnan(v) else round(float(v), 4) for v in hz.elevation_deg],
                  "unknown_fraction": hz.unknown_fraction, "incomplete_fraction": hz.incomplete_fraction, "coverage_min_m": float(cov.min()) if cov.size else 0.0,
                  "coverage_max_m": float(cov.max()) if cov.size else 0.0},
      "timeline": {"time_iso": [x.isoformat() for x in times], "sun_el": np.round(se, 3).tolist(), "sun_az": np.round(sa, 2).tolist(),
                   "sun_visible": sv.tolist(), "sun_above_geometric_horizon": (se > 0).tolist(), "sun_unknown": su.tolist(),
                   "earth_el": np.round(ee, 3).tolist(), "earth_az": np.round(ea, 2).tolist(), "earth_visible": ev.tolist(), "earth_unknown": eu.tolist()},
      "windows": {"sun": windows.visibility_windows(sv, start, step_hours), "earth": windows.visibility_windows(ev, start, step_hours)},
      "decision": decision_engine.evaluate(vals)}

@app.exception_handler(RequestValidationError)
async def _validation(_: Request, exc: RequestValidationError):
    msg = "; ".join(f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}" for e in exc.errors())
    return JSONResponse(status_code=422, content={"detail": msg})

@app.exception_handler(Exception)
async def _unexpected(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Internal error while computing the analysis. See server log."})

@app.get("/api/health")
def health():
    p = os.environ.get("CLPS_DEM_PATH")
    return {"status": "ok", "mode": "user_dem" if p else "demonstration", "spice_pipeline": "not connected",
            "geometry_model": "analytic approximation", "terrain_source": os.path.basename(p) if p else "synthetic"}

@app.get("/api/sites")
def sites():
    p = os.environ.get("CLPS_DEM_PATH")
    return [{"id": k, "name": v["name"], "lat": v["lat"], "lon": v["lon"], "coordinates_verified": False,
             "provenance": "illustrative placeholder coordinates; unverified",
             "data_support": {"terrain": "user-supplied DEM (validated structure)" if p else "synthetic (illustrative)",
                              "sun_earth_geometry": "analytic approximation (not SPICE)", "psr_map": "not loaded"}} for k, v in SITES.items()]

@app.post("/api/analyze")
def analyze(r: AnalyzeRequest):
    return run_site(r.site_id, r.start, r.days, r.step_hours, r.az_step_deg, r.radius_m)

@app.post("/api/compare")
def compare(r: CompareRequest):
    rows, mode = [], "demonstration"
    for sid in SITES:
        j = run_site(sid, r.start, r.days, r.step_hours)
        mode = j["labels"]["data_mode"]
        c = j["decision"]["criteria"]
        rows.append({"id": sid, "name": j["site"]["name"], "slope_max_deg": j["slope"]["max_deg"], "solar_pct": c["solar_pct"]["value"],
                     "earth_pct": c["earth_pct"]["value"], "psr_km": c["psr_km"]["value"], "overall": j["decision"]["overall"],
                     "longest_sun_gap_h": j["windows"]["sun"]["longest_gap_h"], "terrain": j["labels"]["terrain"]})
    note = ("ILLUSTRATIVE ONLY: every site uses synthetic terrain and an approximate Sun/Earth model, so differences between sites reflect random "
            "seeds and placeholder parameters, not real lunar sites. Do not rank or select sites from this table." if mode == "demonstration" else
            "Same user-supplied DEM file used for each site; provenance of the file is not verified; geometry is still an approximate model; no PSR data.")
    return {"data_mode": mode, "real_data": False, "notice": note, "window": {"start": r.start.isoformat(), "days": r.days, "step_hours": r.step_hours}, "sites": rows}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404, "Not Found")

    dist = FRONTEND_DIST.resolve()
    index = dist / "index.html"
    if not index.is_file():
        raise HTTPException(404, "Frontend build not found")

    if path:
        requested_file = (dist / path).resolve()
        if requested_file != dist and dist not in requested_file.parents:
            raise HTTPException(404, "Not Found")
        if requested_file.is_file():
            return FileResponse(requested_file)
        if requested_file.exists() or Path(path).suffix or path == "assets" or path.startswith("assets/"):
            raise HTTPException(404, "Not Found")

    return FileResponse(index)
