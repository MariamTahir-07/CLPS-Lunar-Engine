"""Validated DEM loading. Nothing invalid may reach the calculations: every problem raises DatasetError.
rasterio/pyproj are optional (requirements-data.txt) and imported lazily."""
from dataclasses import dataclass, field
import math, os
import numpy as np

MOON_RADIUS_RANGE_M = (1_700_000.0, 1_740_000.0)
ELEV_PLAUSIBLE_M = (-20_000.0, 20_000.0)

class DatasetError(Exception): pass

@dataclass
class LocalDEM:
    dem: np.ndarray; pixel_m: float; row: int; col: int
    grid_north_bearing_deg: float = 0.0
    source: str = "unknown"; meta: dict = field(default_factory=dict)

def _deps():
    try:
        import rasterio, pyproj
        return rasterio, pyproj
    except ImportError as e:
        raise DatasetError("rasterio/pyproj not installed (pip install -r requirements-data.txt)") from e

def _open_checked(path):
    rasterio, pyproj = _deps()
    if not path or not os.path.isfile(path): raise DatasetError(f"file not found: {path}")
    try: ds = rasterio.open(path)
    except Exception as e: raise DatasetError(f"cannot open raster: {e}") from e
    try:
        if ds.crs is None: raise DatasetError("raster has no CRS; refusing to guess a coordinate system")
        crs = pyproj.CRS.from_user_input(ds.crs)
        if not crs.is_projected: raise DatasetError("CRS is not projected (expected polar stereographic, metres)")
        if crs.ellipsoid is None or not (MOON_RADIUS_RANGE_M[0] <= crs.ellipsoid.semi_major_metre <= MOON_RADIUS_RANGE_M[1]):
            raise DatasetError("CRS ellipsoid is not lunar-sized (semi-major axis must be ~1,737,400 m); an Earth CRS would silently misplace everything")
        if abs(crs.axis_info[0].unit_conversion_factor - 1.0) > 1e-9: raise DatasetError("CRS horizontal units are not metres")
        t = ds.transform
        if abs(t.b) > 1e-9 or abs(t.d) > 1e-9: raise DatasetError("rotated rasters are not supported")
        if not (t.a > 0 and t.e < 0): raise DatasetError("only north-up rasters (a>0, e<0) are supported")
        if abs(abs(t.e) - t.a) > 1e-6 * t.a: raise DatasetError("non-square pixels are not supported")
        if not (1.0 <= t.a <= 1000.0): raise DatasetError(f"implausible pixel size {t.a} m")
        if ds.count < 1: raise DatasetError("raster has no bands")
        return ds, crs
    except Exception:
        ds.close(); raise

def _z_scale(ds, z_scale):
    scale = (ds.scales or (1.0,))[0]; offset = (ds.offsets or (0.0,))[0]
    if z_scale is not None:
        if not (math.isfinite(z_scale) and z_scale > 0): raise DatasetError("z_scale must be positive")
        return float(z_scale), float(offset)
    if np.issubdtype(np.dtype(ds.dtypes[0]), np.integer) and scale == 1.0 and offset == 0.0:
        raise DatasetError("integer raster without scale metadata: elevation units are ambiguous. Read the product label and pass z_scale (metres per DN) explicitly")
    return float(scale), float(offset)

def _to_metres(raw, ds, z_scale):
    scale, offset = _z_scale(ds, z_scale)
    a = raw.astype("float64")
    if ds.nodata is not None: a[(raw == ds.nodata) | ~np.isfinite(a)] = np.nan
    a[~np.isfinite(a)] = np.nan
    return a * scale + offset

def inspect_dem(path, z_scale=None):
    """Metadata + decimated statistics (cheap, safe for multi-GB files)."""
    ds, crs = _open_checked(path)
    try:
        f = max(1, int(max(ds.width, ds.height) // 1000))
        raw = ds.read(1, out_shape=(ds.height // f, ds.width // f))
        z = _to_metres(raw, ds, z_scale); fin = np.isfinite(z)
        if not fin.any(): raise DatasetError("raster contains no valid elevation values")
        lo, hi = float(z[fin].min()), float(z[fin].max())
        if lo < ELEV_PLAUSIBLE_M[0] or hi > ELEV_PLAUSIBLE_M[1]: raise DatasetError(f"implausible elevations {lo:.0f}..{hi:.0f} m (wrong units/scale or nodata?)")
        return {"path": os.path.basename(path), "crs": crs.name, "semi_major_m": crs.ellipsoid.semi_major_metre,
                "pixel_m": ds.transform.a, "shape": [ds.height, ds.width], "bounds": list(ds.bounds), "dtype": ds.dtypes[0],
                "nodata": ds.nodata, "valid_fraction_sampled": float(fin.mean()), "elev_min_m": lo, "elev_max_m": hi}
    finally: ds.close()

def load_window(path, lat_deg, lon_deg, radius_m, z_scale=None, max_pixels=4_000_000, min_valid_fraction=0.9) -> LocalDEM:
    rasterio, pyproj = _deps()
    from rasterio.windows import Window
    if not (-90 <= lat_deg <= 90): raise DatasetError("latitude out of range")
    if not (math.isfinite(radius_m) and radius_m > 0): raise DatasetError("radius must be positive")
    lon = ((lon_deg + 180) % 360) - 180
    ds, crs = _open_checked(path)
    try:
        tr = pyproj.Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
        x, y = tr.transform(lon, lat_deg)
        if not (math.isfinite(x) and math.isfinite(y)): raise DatasetError("site cannot be projected")
        # grid bearing of local north: step 0.01 deg poleward-north and measure in the projected plane
        x2, y2 = tr.transform(lon, min(90.0, lat_deg + 0.01))
        bearing = math.degrees(math.atan2(x2 - x, y2 - y)) % 360
        pix = ds.transform.a; half = int(math.ceil(radius_m / pix))
        rc, cc = ds.index(x, y)
        if rc - half < 0 or cc - half < 0 or rc + half >= ds.height or cc + half >= ds.width:
            raise DatasetError("requested window is not fully covered by this raster (site outside coverage or too close to its edge)")
        if (2 * half + 1) ** 2 > max_pixels: raise DatasetError(f"window {(2*half+1)}^2 px exceeds limit {max_pixels}; reduce radius")
        raw = ds.read(1, window=Window(cc - half, rc - half, 2 * half + 1, 2 * half + 1))
        z = _to_metres(raw, ds, z_scale); fin = np.isfinite(z)
        if fin.mean() < min_valid_fraction: raise DatasetError(f"only {100*fin.mean():.0f}% of the window has valid data (need {100*min_valid_fraction:.0f}%)")
        if not fin[half - 2:half + 3, half - 2:half + 3].all(): raise DatasetError("missing data at/near the site")
        lo, hi = float(z[fin].min()), float(z[fin].max())
        if lo < ELEV_PLAUSIBLE_M[0] or hi > ELEV_PLAUSIBLE_M[1]: raise DatasetError(f"implausible elevations {lo:.0f}..{hi:.0f} m")
        return LocalDEM(z, float(pix), half, half, bearing, f"user-supplied DEM '{os.path.basename(path)}' (structure validated; provenance not verified)",
                        {"crs": crs.name, "valid_fraction": float(fin.mean()), "grid_north_bearing_deg": bearing})
    finally: ds.close()
