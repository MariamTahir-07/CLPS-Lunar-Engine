# Data sources
| Dataset | Status |
|---|---|
| Synthetic DEM (seeded noise, 40 m px) | Generated; ILLUSTRATIVE (default) |
| Analytic Sun/Earth model | Calculated; ILLUSTRATIVE |
| User-supplied GeoTIFF DEM (CLPS_DEM_PATH) | Optional. Structure validated (see below); provenance NOT verified; geometry still approximate |
| LRO LOLA south-polar DEM (PDS) | Not bundled/downloaded. Fetch manually; check label for scale, units, CRS; then --validate-dem |
| NAIF LSK/DE440/PCK/FK | Not loaded. scripts/prepare_data.py downloads LSK, DE440, PA PCK atomically (size check, SHA-256, type check); frames kernel is manual |
| PSR map | Not loaded -> PSR proximity "Insufficient data" |
DEM validation (terrain_loader.py): CRS present, projected, lunar-sized ellipsoid (Earth CRS rejected), metre units, square north-up unrotated pixels 1-1000 m, nodata -> NaN, integer rasters need an explicit z_scale, elevations within +-20 km, window fully covered, >=90% valid, no gap at the site, pixel cap. Any failure -> DatasetError -> HTTP 503.
Site coordinates are unverified placeholders.
