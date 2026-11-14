# Setup and deployment

## Local development

Requirements: Python 3.11+ and Node.js 20+.

From the repository root in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd frontend
npm ci
cd ..
```

In two terminals from the repository root:

```powershell
cd backend
python -m uvicorn app.main:app --port 8000
```

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to the local backend. The frontend itself uses relative `/api/...` URLs.

To run the tests:

```powershell
cd backend
python -m pytest -q
cd ..\frontend
npm test
npm run build
```

Optional real-data tools: `pip install -r backend\requirements-data.txt` (rasterio, pyproj, spiceypy). Tests requiring these tools are skipped if they are unavailable.

Real DEM (optional): `python scripts\prepare_data.py --validate-dem C:\path\dem.tif [--z-scale 0.5]`, then set `$env:CLPS_DEM_PATH="C:\path\dem.tif"` and optionally `$env:CLPS_DEM_ZSCALE="0.5"` before starting the backend. A configured but invalid or missing DEM returns HTTP 503; it never falls back to synthetic terrain.

## Deploy one service on Render

The root `render.yaml` configures one Render Web Service using the native Python runtime. Render's native runtime already provides Node.js and npm; the build uses `npm ci` and generates `frontend/dist/`.

If entering the settings manually, use the repository root as the **Root Directory**, select **Python 3**, and set:

- **Build Command:** `bash build.sh`
- **Start Command:** `python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/api/health`

The `.python-version` file selects Python 3.13. No application secrets or environment variables are required for demonstration mode. Render supplies `PORT` automatically. To use a real DEM, set `CLPS_DEM_PATH` to an available raster file and optionally `CLPS_DEM_ZSCALE` to its elevation scale. Files stored on a Render service's ephemeral filesystem do not persist across redeploys; use a Render persistent disk or an accessible external source for a DEM that must remain available.

After deployment, the same service origin serves the React app and `/api/health`, `/api/sites`, `/api/analyze`, and `/api/compare`. The FastAPI SPA fallback supports direct page loads and refreshes, while missing built assets and unknown `/api` paths return 404.
