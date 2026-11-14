# Limitations
- Default run is demonstration mode: synthetic terrain, approximate Sun/Earth geometry. Results are not mission data. Site comparison is labelled illustrative and never ranks.
- SPICE is NOT integrated into the analysis. frame_align.py is tested only on a synthetic frames kernel; real NAIF kernels untested (host unreachable). 870 m claim unverified.
- The DEM loader/ prepare_data validation is tested on synthetic GeoTIFFs only, never on a real LOLA file. LOLA scale/units/CRS must be confirmed from its label. PDS3 .IMG/.LBL reading via GDAL is untested.
- No PSR data, thermal model, power model or RF link model. Sun/Earth treated as point centres; no refraction needed on the Moon, but disc size is ignored.
- Horizon limited to DEM coverage (<=4 km synthetic; up to 20 km window cap for real DEMs). No 100 km analysis.
- No custom-coordinate entry (it would require real terrain at arbitrary points). No slope map. No deployment config.
- run-dev.ps1 and Windows commands were not run on Windows. No real-browser/Playwright test.
