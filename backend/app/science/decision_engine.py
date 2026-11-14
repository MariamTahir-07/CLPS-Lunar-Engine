"""Screening classifier. Thresholds are CONFIGURABLE ASSUMPTIONS, not NASA requirements."""
from dataclasses import dataclass, field

DEFAULTS = {
    "slope_deg": {"favorable_max": 7.0, "marginal_max": 10.0},
    "solar_pct": {"favorable_min": 70.0, "marginal_min": 50.0},
    "earth_pct": {"favorable_min": 55.0, "marginal_min": 40.0},
    "psr_km":    {"favorable_max": 2.0, "marginal_max": 5.0},
}

def classify(name, value, th=None):
    th = (th or DEFAULTS)[name]
    if value is None:
        return "Insufficient data"
    if "favorable_max" in th:
        return "Favorable" if value <= th["favorable_max"] else (
               "Marginal" if value <= th["marginal_max"] else "Unfavorable")
    return "Favorable" if value >= th["favorable_min"] else (
           "Marginal" if value >= th["marginal_min"] else "Unfavorable")

def evaluate(values: dict, th=None) -> dict:
    res = {k: {"value": values.get(k), "status": classify(k, values.get(k), th)} for k in DEFAULTS}
    st = [r["status"] for r in res.values()]
    if "Unfavorable" in st: overall = "Unfavorable"
    elif "Insufficient data" in st: overall = "Insufficient data"   # never a misleading GO
    elif "Marginal" in st: overall = "Marginal"
    else: overall = "Favorable"
    return {"criteria": res, "overall": overall,
            "disclaimer": "Screening result only; not mission-safe or NASA-approved."}
