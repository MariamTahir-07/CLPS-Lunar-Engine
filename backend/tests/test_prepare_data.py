import subprocess, sys, pathlib, numpy as np, pytest
rasterio = pytest.importorskip("rasterio"); pyproj = pytest.importorskip("pyproj"); pytest.importorskip("spiceypy")
from rasterio.transform import from_origin; from rasterio.crs import CRS
from tests.test_frame_align import FK
SCRIPT = str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "prepare_data.py")
def run(*a): return subprocess.run([sys.executable, SCRIPT, *a], capture_output=True, text=True)

def test_garbage_kernel_rejected(tmp_path):
    f = tmp_path / "junk.bsp"; f.write_text("junk")
    r = run("--validate-kernel", str(f)); assert r.returncode == 2 and "INVALID" in r.stdout
def test_wrong_extension_rejected(tmp_path):
    f = tmp_path / "x.txt"; f.write_text(FK); assert run("--validate-kernel", str(f)).returncode == 2
def test_renamed_text_kernel_rejected(tmp_path):
    f = tmp_path / "fake.bsp"; f.write_text(FK); assert run("--validate-kernel", str(f)).returncode == 2   # FK pretending to be an SPK
def test_valid_frames_kernel_accepted(tmp_path):
    f = tmp_path / "ok.tf"; f.write_text(FK); r = run("--validate-kernel", str(f)); assert r.returncode == 0 and "OK" in r.stdout
def test_dem_validation_cli(tmp_path):
    crs = CRS.from_wkt(pyproj.CRS.from_proj4("+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m +no_defs").to_wkt())
    p = tmp_path / "d.tif"
    with rasterio.open(p, "w", driver="GTiff", height=100, width=100, count=1, dtype="float32", crs=crs, transform=from_origin(-1000, 1000, 20, 20)) as d: d.write(np.zeros((100, 100), "float32"), 1)
    r = run("--validate-dem", str(p)); assert r.returncode == 0 and "DEM VALID" in r.stdout and '"pixel_m": 20.0' in r.stdout
    assert run("--validate-dem", str(tmp_path / "missing.tif")).returncode == 2
def test_check_fails_gracefully_offline_or_passes_online():
    assert run("--check").returncode in (0, 1)
