# Changes in this revision
Fixed: no-data horizon rays returned a fake 0 deg (now NaN + flagged); weak flat-terrain test (now analytic); horizon now exact spherical + bilinear; empty timeline for step>duration (now 422, min 2 samples);
UI/selected-site mismatch when the default site is absent; garbage `.bsp` accepted by prepare_data; Earth-CRS rasters could be misread (now rejected); rays over data gaps silently under-estimated horizon (now flagged).
Added: Mission Simulation page, site comparison (labelled illustrative), time-window tables, validated DEM loader + CLPS_DEM_PATH, readable errors, Windows run script.
