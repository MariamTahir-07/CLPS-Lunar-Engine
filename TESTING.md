# Testing
Backend: `cd backend; python -m pytest -q`. Covers horizon (analytic flat-ground curvature, observer-height dip, NaN/incomplete data, boundaries, grid-north rotation, validation),
sample planning (never an empty timeline), API errors (422/404/503/500), compare, windows, DEM loader on synthetic lunar-CRS GeoTIFFs (Earth CRS, nodata, scale, coverage, plausibility),
prepare_data CLI (garbage/renamed kernels rejected), SPICE call path on a synthetic frames kernel.
Frontend: `cd frontend; npm test; npm run build` (Vitest + Testing Library, fetch mocked): navigation, modes, simulation run + validation + presets, comparison, errors, gaps warning.
Not tested: real LOLA/NAIF data, real browser, Windows PowerShell script, deployment.
