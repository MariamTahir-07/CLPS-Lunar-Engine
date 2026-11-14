# Setup (Windows PowerShell; Python 3.11+ and Node 20+; tested here on Python 3.12 / Node 22 on Linux)
```powershell
cd clps-lunar-engine                       # the unzipped folder
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1               # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r backend\requirements.txt
cd frontend; npm install; cd ..
# Terminal 1 (backend)           # Terminal 2 (frontend)
cd backend                       cd frontend
python -m uvicorn app.main:app --port 8000      npm run dev        # open http://localhost:5173
```
One command instead: `powershell -ExecutionPolicy Bypass -File .\scripts\run-dev.ps1` (creates the venv, installs, uses `npm ci`, opens backend + frontend windows, waits for /api/health, opens the browser). It passes a PowerShell 7 syntax check but has NOT been run on Windows. If `npm` complains about scripts being disabled, use `npm.cmd` instead of `npm`.
Tests: `cd backend; python -m pytest -q`   |   `cd frontend; npm test; npm run build`
Optional real-data tools: `pip install -r backend\requirements-data.txt` (rasterio, pyproj, spiceypy; Windows wheels exist). Tests that need them are skipped if absent.
Real DEM (optional): `python scripts\prepare_data.py --validate-dem C:\path\dem.tif [--z-scale 0.5]`, then
`$env:CLPS_DEM_PATH="C:\path\dem.tif"; $env:CLPS_DEM_ZSCALE="0.5"` before starting the backend. A configured but invalid/missing DEM gives HTTP 503; it never falls back to synthetic terrain.
