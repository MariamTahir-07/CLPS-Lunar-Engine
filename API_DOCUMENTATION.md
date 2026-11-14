# API
GET /api/health -> status, mode (demonstration|user_dem), spice_pipeline ("not connected"), geometry_model, terrain_source
GET /api/sites -> id, name, lat, lon, coordinates_verified (false), provenance, data_support{terrain, sun_earth_geometry, psr_map}
POST /api/analyze  {site_id, start (ISO datetime, naive = UTC), days 0.5-120, step_hours 0.5-48, az_step_deg 0.5-10, radius_m 200-20000}
  Samples n = floor(days*24/step_hours); each represents [t, t+step). Need 2 <= n <= 4000, else 422 with an explanation. Range 2020-2040 UTC.
  Returns: labels (data_mode, terrain, geometry, time_system, observer height, coverage radius), window{start,end,step_hours,n_samples}, slope,
  horizon{azimuth_deg, elevation_deg (null = unknown), unknown_fraction, incomplete_fraction, coverage_min/max_m}, timeline{time_iso, sun/earth el/az, visible, unknown flags},
  windows{sun,earth: windows[], n_windows, longest_window_h, longest_gap_h}, decision.
POST /api/compare {start, days, step_hours} -> per-site summary + notice + real_data:false. Never ranks.
Errors: 404 unknown site; 422 invalid input (readable string); 503 configured terrain dataset unusable; 500 generic (details only in server log).
