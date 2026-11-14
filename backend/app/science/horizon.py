"""360-degree terrain horizon. Label: CALCULATED.
Conventions: azimuth 0=local North, clockwise (90=East). The DEM grid is assumed 'north-up' unless
grid_north_bearing_deg says otherwise (bearing of local north measured clockwise from grid +y/up).
Geometry: exact spherical (R = 1,737,400 m). For a target at ground distance s and height z, with
theta = s/R:  x=(R+z)sin(theta), y=(R+z)cos(theta)-(R+z0), elevation=atan2(y, x).  Flat ground
gives -theta/2 (negative: the Moon curves away). Unknown terrain is NaN, never 0."""
from dataclasses import dataclass
import numpy as np
R_MOON_M = 1_737_400.0

@dataclass
class HorizonResult:
    azimuth_deg: np.ndarray
    elevation_deg: np.ndarray      # NaN where no valid terrain sample exists along the ray
    coverage_m: np.ndarray         # distance to last in-bounds sample along each ray (0 if none)
    incomplete: np.ndarray = None  # True where valid samples exist but some in-bounds samples are missing: horizon is a LOWER BOUND

    @property
    def unknown_fraction(self) -> float:
        return float(np.isnan(self.elevation_deg).mean())

    @property
    def incomplete_fraction(self) -> float:
        return float(np.mean(self.incomplete)) if self.incomplete is not None else 0.0

def _bilinear(dem, r, c):
    r0 = np.clip(np.floor(r).astype(int), 0, dem.shape[0] - 2)
    c0 = np.clip(np.floor(c).astype(int), 0, dem.shape[1] - 2)
    fr, fc = r - r0, c - c0
    return (dem[r0, c0] * (1 - fr) * (1 - fc) + dem[r0, c0 + 1] * (1 - fr) * fc +
            dem[r0 + 1, c0] * fr * (1 - fc) + dem[r0 + 1, c0 + 1] * fr * fc)  # NaN if any corner NaN

def horizon_detail(dem, pixel_m, row, col, observer_height_m=0.0, az_step_deg=1.0,
                   max_radius_m=None, grid_north_bearing_deg=0.0) -> HorizonResult:
    dem = np.asarray(dem, float)
    if dem.ndim != 2 or min(dem.shape) < 3: raise ValueError("DEM must be 2-D, at least 3x3")
    if np.isinf(dem).any(): raise ValueError("DEM contains infinite values")
    if not (np.isfinite(pixel_m) and pixel_m > 0): raise ValueError("pixel_m must be positive and finite")
    if not (np.isfinite(observer_height_m) and observer_height_m >= 0): raise ValueError("observer_height_m must be >= 0")
    if not (0 < az_step_deg <= 45): raise ValueError("az_step_deg must be in (0, 45]")
    if max_radius_m is not None and not (np.isfinite(max_radius_m) and max_radius_m > 0): raise ValueError("max_radius_m must be positive")
    if not (0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]): raise ValueError("observer outside DEM")
    if not np.isfinite(dem[row, col]): raise ValueError("observer pixel has no data")
    z0 = dem[row, col] + observer_height_m
    rmax = max(dem.shape) * pixel_m if max_radius_m is None else max_radius_m
    s = np.arange(pixel_m, rmax + 1e-9, pixel_m)
    theta = s / R_MOON_M
    az = np.arange(0, 360, az_step_deg)
    el = np.full(az.shape, np.nan); cov = np.zeros(az.shape); inc = np.zeros(az.shape, bool)
    for i, a in enumerate(az):
        b = np.radians(a + grid_north_bearing_deg)
        r = row - s * np.cos(b) / pixel_m
        c = col + s * np.sin(b) / pixel_m
        inb = (r >= 0) & (r <= dem.shape[0] - 1) & (c >= 0) & (c <= dem.shape[1] - 1)
        if not inb.any(): continue
        cov[i] = s[inb].max()
        z = _bilinear(dem, r[inb], c[inb]); ok = np.isfinite(z)
        inc[i] = bool((~ok).any())
        if not ok.any(): continue
        th, zz = theta[inb][ok], z[ok]
        # y = (zz - z0) - 2(R+zz)sin^2(theta/2): algebraically identical to (R+zz)cos(th)-(R+z0), but no cancellation error
        ang = np.arctan2((zz - z0) - 2 * (R_MOON_M + zz) * np.sin(th / 2) ** 2, (R_MOON_M + zz) * np.sin(th))
        el[i] = np.degrees(ang.max())
    return HorizonResult(az, el, cov, inc)

def horizon_profile(dem, pixel_m, row, col, observer_height_m=0.0, az_step_deg=1.0, max_radius_m=None,
                    grid_north_bearing_deg=0.0):
    """Backwards-compatible wrapper -> (azimuths_deg, elevation_deg). NaN = unknown."""
    h = horizon_detail(dem, pixel_m, row, col, observer_height_m, az_step_deg, max_radius_m, grid_north_bearing_deg)
    return h.azimuth_deg, h.elevation_deg

def visibility_state(body_az_deg, body_el_deg, hor_az_deg, hor_el_deg):
    """-> (visible, unknown) boolean arrays. Unknown = horizon not computed at that azimuth."""
    hor_az, hor_el = np.asarray(hor_az_deg, float), np.asarray(hor_el_deg, float)
    h = np.interp(np.asarray(body_az_deg, float) % 360, np.append(hor_az, 360.0), np.append(hor_el, hor_el[0]))
    unknown = np.isnan(h)
    return (np.asarray(body_el_deg) > h) & ~unknown, unknown

def visible_mask(sun_az_deg, sun_el_deg, hor_az_deg, hor_el_deg):
    return visibility_state(sun_az_deg, sun_el_deg, hor_az_deg, hor_el_deg)[0]

def visibility_percent(mask, unknown=None):
    """Percent visible over samples whose horizon is KNOWN; None if nothing is known."""
    mask = np.asarray(mask)
    if mask.size == 0: return None
    if unknown is None: return float(100.0 * mask.mean())
    known = ~np.asarray(unknown)
    return float(100.0 * mask[known].mean()) if known.any() else None
