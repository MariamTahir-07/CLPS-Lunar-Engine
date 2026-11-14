#!/usr/bin/env python3
"""Controlled data preparation (run where NASA hosts are reachable).
  python scripts/prepare_data.py --check                       HEAD requests only
  python scripts/prepare_data.py --download                    download NAIF kernels (atomic, size-checked, SHA-256, load-tested)
  python scripts/prepare_data.py --validate-dem FILE [--z-scale 0.5]   inspect + validate a DEM (CRS, units, nodata, coverage)
  python scripts/prepare_data.py --validate-kernel FILE        load a SPICE kernel with spiceypy
Nothing is trusted until validated. URLs marked verify=True must be checked by you against the NAIF/PDS listings."""
import argparse, datetime, hashlib, json, pathlib, sys, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "data"
NAIF = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/"
SOURCES = [
 {"name": "LSK leapseconds", "url": NAIF + "lsk/naif0012.tls", "dest": "kernels/naif0012.tls", "verify": False},
 {"name": "DE440 planetary ephemeris (~115 MB)", "url": NAIF + "spk/planets/de440.bsp", "dest": "kernels/de440.bsp", "verify": False},
 {"name": "Lunar PA orientation (DE440)", "url": NAIF + "pck/moon_pa_de440_200625.bpc", "dest": "kernels/moon_pa_de440_200625.bpc", "verify": True},
 {"name": "Lunar frames kernel (PA/ME)", "url": NAIF + "fk/satellites/", "manual": "Pick the current moon_*.tf from the listing; frame names in it must match frame_align arguments"},
 {"name": "LOLA south-polar DEM", "url": "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/", "manual": "Find LDEM_80S_* in the PDS archive; read its label for scale/units/CRS, then --validate-dem"},
]
EXPECT = {".bsp": "SPK", ".bpc": "PCK", ".tls": "LSK", ".tf": "FK"}
def validate_kernel(path):
    try: import spiceypy as sp
    except ImportError: raise SystemExit("spiceypy not installed: pip install -r backend/requirements-data.txt")
    ext = pathlib.Path(path).suffix.lower()
    if ext not in EXPECT: raise ValueError(f"unknown kernel extension '{ext}' (expected one of {sorted(EXPECT)})")
    try: arch, typ = sp.getfat(str(path))
    except Exception as e: raise ValueError(f"not a recognisable SPICE kernel: {e}")
    if typ != EXPECT[ext]: raise ValueError(f"file is {arch}/{typ}, but a '{ext}' file must be {EXPECT[ext]} (renamed or corrupt file?)")
    sp.kclear()
    try:
        sp.furnsh(str(path))
        if ext == ".tls": sp.str2et("2026-01-01T00:00:00")     # leapseconds really usable
    finally: sp.kclear()
    return True
def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True); part = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
        expected = r.headers.get("Content-Length"); h = hashlib.sha256()
        for chunk in iter(lambda: r.read(1 << 20), b""): f.write(chunk); h.update(chunk)
    if expected and part.stat().st_size != int(expected):
        part.unlink(); raise IOError(f"incomplete download: got {part.stat().st_size} of {expected} bytes")
    part.replace(dest); return h.hexdigest()
def main():
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true"); g.add_argument("--download", action="store_true")
    g.add_argument("--validate-dem"); g.add_argument("--validate-kernel"); ap.add_argument("--z-scale", type=float)
    a = ap.parse_args()
    if a.validate_dem:
        from app.science.terrain_loader import inspect_dem, DatasetError
        try: print(json.dumps(inspect_dem(a.validate_dem, a.z_scale), indent=2)); print("DEM VALID (structure only; verify provenance yourself)")
        except DatasetError as e: print("DEM INVALID:", e); sys.exit(2)
        return
    if a.validate_kernel:
        try: validate_kernel(a.validate_kernel); print("KERNEL LOADS OK")
        except Exception as e: print("KERNEL INVALID:", e); sys.exit(2)
        return
    prov, failed = [], False
    for s in SOURCES:
        if "manual" in s: print(f"[MANUAL] {s['name']}: {s['url']} -> {s['manual']}"); continue
        try:
            with urllib.request.urlopen(urllib.request.Request(s["url"], method="HEAD"), timeout=20) as r: size = r.headers.get("Content-Length")
            print(f"[OK] {s['name']} size={size}" + ("  (verify URL/filename)" if s["verify"] else ""))
            if a.download:
                sha = download(s["url"], OUT / s["dest"]); validate_kernel(OUT / s["dest"])
                prov.append({**s, "sha256": sha, "downloaded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}); print("     downloaded + loads OK")
        except Exception as e:
            failed = True; print(f"[FAIL] {s['name']}: {e}")
    if prov: (OUT / "provenance.json").write_text(json.dumps(prov, indent=2))
    sys.exit(1 if failed else 0)
if __name__ == "__main__": main()
