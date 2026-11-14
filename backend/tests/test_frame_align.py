import numpy as np, pytest
from app.science.frame_align import displacement_m, pa_to_me_displacement, KernelUnavailable, R_MOON_M
def rz(t): c,s=np.cos(t),np.sin(t); return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def test_identity_zero(): assert displacement_m(np.eye(3), -89.5, 10) == pytest.approx(0, abs=1e-6)
def test_known_rotation_chord():
    t=1e-3; assert displacement_m(rz(t), 0, 0) == pytest.approx(2*R_MOON_M*np.sin(t/2), rel=1e-9)
def test_rotation_about_z_leaves_pole_fixed(): assert displacement_m(rz(0.5), -90, 0) < 1e-6
def test_rejects_non_rotation():
    with pytest.raises(ValueError): displacement_m(np.ones((3,3)), 0, 0)
def test_missing_kernels_graceful():
    with pytest.raises(KernelUnavailable): pa_to_me_displacement(-89, 0, ["/nope.tf"])

# ---- SPICE code path against a SYNTHETIC text frames kernel (not real NAIF lunar kernels) ----
FK = """KPL/FK
\\begindata
FRAME_TEST_PA = 1400001
FRAME_1400001_NAME = 'TEST_PA'
FRAME_1400001_CLASS = 4
FRAME_1400001_CLASS_ID = 1400001
FRAME_1400001_CENTER = 301
TKFRAME_1400001_RELATIVE = 'J2000'
TKFRAME_1400001_SPEC = 'ANGLES'
TKFRAME_1400001_UNITS = 'DEGREES'
TKFRAME_1400001_AXES = ( 1, 2, 3 )
TKFRAME_1400001_ANGLES = ( 0.0, 0.0, 0.0 )
FRAME_TEST_ME = 1400002
FRAME_1400002_NAME = 'TEST_ME'
FRAME_1400002_CLASS = 4
FRAME_1400002_CLASS_ID = 1400002
FRAME_1400002_CENTER = 301
TKFRAME_1400002_RELATIVE = 'TEST_PA'
TKFRAME_1400002_SPEC = 'ANGLES'
TKFRAME_1400002_UNITS = 'DEGREES'
TKFRAME_1400002_AXES = ( 1, 2, 3 )
TKFRAME_1400002_ANGLES = ( 0.0, 0.0, 0.03 )
\\begintext
"""
sp = pytest.importorskip("spiceypy")
def test_spice_path_matches_analytic_chord(tmp_path):
    k = tmp_path / "fk.tf"; k.write_text(FK)
    d = pa_to_me_displacement(0, 0, [str(k)], et=0.0, frame_pa="TEST_PA", frame_me="TEST_ME")
    assert d == pytest.approx(2 * R_MOON_M * np.sin(np.radians(0.03) / 2), rel=1e-6)      # ~909.7 m for a 0.03 deg rotation
    assert pa_to_me_displacement(-90, 0, [str(k)], et=5.0, frame_pa="TEST_PA", frame_me="TEST_ME") < 1e-6   # pole fixed under z-rotation
def test_spice_unknown_frame_and_argument_errors(tmp_path):
    k = tmp_path / "fk.tf"; k.write_text(FK)
    with pytest.raises(KernelUnavailable, match="not defined"): pa_to_me_displacement(0, 0, [str(k)], et=0.0)   # default MOON_PA absent
    with pytest.raises(ValueError): pa_to_me_displacement(0, 0, [str(k)], frame_pa="TEST_PA", frame_me="TEST_ME")   # no epoch
    with pytest.raises(KernelUnavailable): pa_to_me_displacement(0, 0, [str(k)], epoch_utc="2026-11-14", frame_pa="TEST_PA", frame_me="TEST_ME")  # no LSK
