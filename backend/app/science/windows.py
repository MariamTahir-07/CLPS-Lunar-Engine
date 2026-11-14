"""Visibility windows from a boolean series. Each sample represents the interval [t_i, t_i + step)."""
import datetime as dt
import numpy as np

def _runs(mask, value):
    out, s = [], None
    for i, m in enumerate(mask):
        if m == value and s is None: s = i
        if (m != value) and s is not None: out.append((s, i)); s = None
    if s is not None: out.append((s, len(mask)))
    return out

def visibility_windows(mask, start: dt.datetime, step_hours: float, max_listed=50):
    mask = np.asarray(mask, bool)
    if step_hours <= 0: raise ValueError("step_hours must be positive")
    step = dt.timedelta(hours=step_hours)
    runs = _runs(mask, True); gaps = _runs(mask, False)
    listed = [{"start": (start + a * step).isoformat(), "end": (start + b * step).isoformat(),
               "duration_h": (b - a) * step_hours} for a, b in runs[:max_listed]]
    return {"windows": listed, "n_windows": len(runs), "truncated": len(runs) > max_listed,
            "longest_window_h": max([(b - a) * step_hours for a, b in runs], default=0.0),
            "longest_gap_h": max([(b - a) * step_hours for a, b in gaps], default=0.0)}
