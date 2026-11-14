"""Sun/Earth direction at a lunar surface point.
LABEL: ILLUSTRATIVE simplified analytic model (NOT SPICE/DE440). Used only when SPICE kernels
are absent. Sub-point amplitudes: Sun lat +-1.54 deg (yearly); Earth lat +-6.7 deg (27.212 d),
lon +-7.9 deg (27.555 d). Phases are arbitrary, so timing is not an ephemeris prediction."""
import numpy as np
SYNODIC_D, YEAR_D = 29.530589, 365.25

def _azel(lat, lon, sub_lat, sub_lon):
    p, d, h = np.radians(lat), np.radians(sub_lat), np.radians(lon - sub_lon)
    sin_el = np.sin(d) * np.sin(p) + np.cos(d) * np.cos(p) * np.cos(h)
    el = np.degrees(np.arcsin(np.clip(sin_el, -1, 1)))
    # azimuth of body from local north, clockwise (east positive)
    x = np.cos(d) * np.sin(-h)
    y = np.cos(p) * np.sin(d) - np.sin(p) * np.cos(d) * np.cos(h)
    return np.degrees(np.arctan2(x, y)) % 360, el

def sun_azel(lat, lon, t_days):
    t = np.asarray(t_days, float)
    return _azel(lat, lon, 1.54 * np.sin(2 * np.pi * t / YEAR_D), -360.0 * t / SYNODIC_D)

def earth_azel(lat, lon, t_days):
    t = np.asarray(t_days, float)
    return _azel(lat, lon, 6.7 * np.sin(2 * np.pi * t / 27.212), 7.9 * np.sin(2 * np.pi * t / 27.555))

def validate_latlon(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 360):
        raise ValueError("lat must be in [-90,90], lon in [-180,360]")
    if lat > -80:
        raise ValueError("Only the south-polar region (lat <= -80) is supported")
