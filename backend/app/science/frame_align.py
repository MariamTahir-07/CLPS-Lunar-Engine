"""PA -> ME frame displacement via SPICE. STATUS: NOT connected to the Sun/Earth pipeline.
Verified only against a synthetic text frames kernel (tests), NOT against real NAIF lunar kernels
(NAIF was unreachable). Frame names must match the frames kernel (FK) you load: the generic names
MOON_PA/MOON_ME belong to the older DE421-era FK; DE440-era FKs define suffixed names - read the FK.
Convention: R = pxform(PA, ME, et) maps PA-frame vectors to ME-frame vectors; the displacement is
the chord |R r - r| for a surface point of radius 1,737,400 m. Nothing here asserts the ~870 m figure."""
import os
import numpy as np
R_MOON_M = 1_737_400.0
class KernelUnavailable(RuntimeError): pass

def displacement_m(rot, lat_deg, lon_deg) -> float:
    rot = np.asarray(rot, float)
    if rot.shape != (3, 3) or not np.isfinite(rot).all() or not np.allclose(rot @ rot.T, np.eye(3), atol=1e-9) or np.linalg.det(rot) < 0:
        raise ValueError("rot must be a proper 3x3 rotation matrix")
    if not (-90 <= lat_deg <= 90): raise ValueError("lat out of range")
    la, lo = np.radians(lat_deg), np.radians(lon_deg)
    r = R_MOON_M * np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    return float(np.linalg.norm(rot @ r - r))

def pa_to_me_displacement(lat, lon, kernels, et=None, epoch_utc=None, frame_pa="MOON_PA", frame_me="MOON_ME"):
    try: import spiceypy as sp
    except ImportError as e: raise KernelUnavailable("spiceypy not installed (pip install -r requirements-data.txt)") from e
    missing = [k for k in kernels if not os.path.isfile(k)]
    if missing: raise KernelUnavailable(f"missing kernels: {missing}")
    if (et is None) == (epoch_utc is None): raise ValueError("give exactly one of et or epoch_utc")
    sp.kclear()
    try:
        for k in kernels: sp.furnsh(k)
        for f in (frame_pa, frame_me):
            if sp.namfrm(f) == 0: raise KernelUnavailable(f"frame '{f}' is not defined by the loaded kernels (check the FK's frame names)")
        t = sp.str2et(epoch_utc) if epoch_utc is not None else float(et)   # str2et needs a leapseconds kernel
        rot = np.array(sp.pxform(frame_pa, frame_me, t))
    except KernelUnavailable: raise
    except Exception as e: raise KernelUnavailable(f"SPICE error: {e}") from e
    finally: sp.kclear()
    return displacement_m(rot, lat, lon)
