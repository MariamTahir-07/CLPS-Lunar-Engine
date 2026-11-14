# Architecture
React/Vite UI --(JSON /api)--> FastAPI --> science modules (NumPy). Backend is the only place numbers are computed; the UI only formats them.
```
UI pages -> api.ts -> /api/analyze -> demo_dem -> slope.py
                                   -> horizon.py (ray march, curvature)
                                   -> geometry.py (Sun/Earth az/el)
                                   -> horizon.visible_mask -> decision_engine.py
frame_align.py (SPICE PA->ME, optional)   scripts/prepare_data.py (offline data fetch)
```
Choices: no database (nothing to persist); hand-rolled SVG charts instead of Plotly (fewer dependencies, less breakage; trade-off: less interactivity); no Tailwind/shadcn (plain CSS, faster to stabilise).
Modules: slope (finite-difference gradient), horizon (max elevation angle along each azimuth), geometry (Sun/Earth direction), decision_engine (threshold classifier), frame_align (frame rotation displacement).
