"""Slope from a DEM (metres, regular grid). Label: CALCULATED from source data."""
import numpy as np

def slope_deg(dem: np.ndarray, pixel_m: float) -> np.ndarray:
    if dem.ndim != 2 or min(dem.shape) < 3:
        raise ValueError("DEM must be 2-D with at least 3x3 pixels")
    if not (np.isfinite(pixel_m) and pixel_m > 0):
        raise ValueError("pixel_m must be positive and finite")
    if np.isinf(dem).any():
        raise ValueError("DEM contains infinite values")
    gy, gx = np.gradient(dem.astype(float), pixel_m)  # NaN propagates -> missing data stays missing
    return np.degrees(np.arctan(np.hypot(gx, gy)))

def slope_stats(s: np.ndarray) -> dict:
    v = s[np.isfinite(s)]
    if v.size == 0:
        return {"max_deg": None, "mean_deg": None, "valid_fraction": 0.0}
    return {"max_deg": float(v.max()), "mean_deg": float(v.mean()), "valid_fraction": float(v.size / s.size)}
