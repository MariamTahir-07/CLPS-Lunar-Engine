"""Real-browser smoke test (headless Chromium via Playwright). Requires: pip install playwright; playwright install chromium.
Run with backend on :8000 and the frontend on APP (default http://localhost:4173 = `npm run build && npx vite preview`).
Optional second backend on :8001 started with CLPS_DEM_PATH=/nope.tif for the missing-dataset check."""
import os, sys, json
from playwright.sync_api import sync_playwright, expect
APP = os.environ.get("APP", "http://localhost:4173"); SHOTS = os.environ.get("SHOTS", "/tmp/shots")
NAV = [("Overview", "CLPS Lunar Landing Site"), ("Lunar Site Explorer", "Compare sites"), ("Terrain Analysis", "No analysis yet"),
       ("Solar Analysis", "No analysis yet"), ("Earth / DTE Analysis", "No analysis yet"), ("Mission Simulation", "Mission simulation"),
       ("Decision Support", "No analysis yet"), ("Data & Methodology", "Data & methodology")]
results, problems = [], []
def check(name, fn):
    try: fn(); results.append((name, "PASS"))
    except Exception as e: results.append((name, "FAIL: " + str(e).splitlines()[0][:160]))
def new_page(ctx, label, expect_failures=False):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: problems.append(f"[{label}] pageerror: {e}"))
    if not expect_failures:   # the backend-down page aborts /api calls on purpose
        pg.on("console", lambda m: m.type == "error" and not any(c in m.text for c in ("status of 422", "status of 503", "status of 404")) and problems.append(f"[{label}] console.error: {m.text}"))
        pg.on("requestfailed", lambda r: problems.append(f"[{label}] requestfailed: {r.url} {r.failure}"))
    return pg
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={"width": 1280, "height": 900}); pg = new_page(ctx, "main")
    pg.goto(APP); expect(pg.get_by_role("option", name="Malapert Massif")).to_be_attached(timeout=10000)
    for label, marker in NAV:
        def nav(label=label, marker=marker):
            pg.get_by_role("navigation").get_by_role("button", name=label, exact=True).click(); expect(pg.get_by_text(marker).first).to_be_visible(timeout=5000)
        check(f"nav: {label}", nav)
    # --- complete simulation: 7 d / 1 h preset
    def sim():
        pg.get_by_role("navigation").get_by_role("button", name="Mission Simulation").click()
        pg.get_by_role("button", name="7 d · 1 h").click(); expect(pg.get_by_text("This run will compute 168 samples")).to_be_visible()
        pg.get_by_role("button", name="Run simulation").click()
        expect(pg.get_by_text("Samples: 168 (every 1 h)")).to_be_visible(timeout=20000)
        expect(pg.get_by_role("img", name="Elevation vs time")).to_be_visible(); expect(pg.get_by_text("Sun visibility windows")).to_be_visible()
        pg.screenshot(path=f"{SHOTS}/simulation.png", full_page=True)
    check("simulation 7d/1h runs and renders", sim)
    for label, marker in [("Terrain Analysis", "Terrain & horizon"), ("Solar Analysis", "Solar visibility"), ("Earth / DTE Analysis", "Earth / DTE geometry"), ("Decision Support", "Screening result")]:
        def after(label=label, marker=marker):
            pg.get_by_role("navigation").get_by_role("button", name=label).click(); expect(pg.get_by_text(marker).first).to_be_visible(timeout=5000)
            pg.screenshot(path=f"{SHOTS}/{label.split()[0].lower()}.png", full_page=True)
        check(f"results shown on: {label}", after)
    def mode():
        pg.get_by_role("button", name="Public Explorer").click(); pg.get_by_role("navigation").get_by_role("button", name="Solar Analysis").click()
        expect(pg.get_by_text("This is not electricity")).to_be_visible(); pg.get_by_role("button", name="Mission Planner").click()
        expect(pg.get_by_text("Electrical power is not computed")).to_be_visible()
    check("mode switch Public/Planner", mode)
    # --- comparison
    def compare():
        pg.get_by_role("navigation").get_by_role("button", name="Lunar Site Explorer").click(); pg.get_by_role("button", name="Compare all sites").click()
        expect(pg.get_by_role("note")).to_contain_text("ILLUSTRATIVE ONLY", timeout=30000); expect(pg.locator("table tbody tr")).to_have_count(3)
        pg.screenshot(path=f"{SHOTS}/compare.png", full_page=True)
    check("site comparison (3 rows, illustrative banner)", compare)
    # --- invalid inputs
    def invalid_client():
        pg.get_by_role("navigation").get_by_role("button", name="Mission Simulation").click()
        d = pg.get_by_label("Duration days"); d.fill("1"); pg.get_by_label("Step hours").select_option("48")
        expect(pg.get_by_role("alert")).to_contain_text("too large"); expect(pg.get_by_role("button", name="Run simulation")).to_be_disabled()
    check("invalid: step>duration blocked in UI", invalid_client)
    def invalid_server():
        pg.get_by_label("Duration days").fill("30"); pg.get_by_label("Step hours").select_option("6")
        pg.get_by_label("Start date and time").fill("2019-01-01T00:00"); pg.get_by_role("button", name="Run simulation").click()
        expect(pg.get_by_text("Analysis failed:")).to_contain_text("2020-01-01", timeout=10000)
    check("invalid: out-of-range date -> backend 422 shown", invalid_server)
    def raw_api():
        r = pg.evaluate("""async()=>{const f=(b)=>fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(async r=>[r.status,(await r.json()).detail]);
          return [await f({site_id:'malapert',start:'2026-11-14',days:1,step_hours:48}), await f({site_id:'malapert',start:'2026-11-14',days:'nan'}), await f({site_id:'zzz',start:'2026-11-14'})]}""")
        assert [x[0] for x in r] == [422, 422, 404], r; assert all(isinstance(x[1], str) for x in r), r
    check("invalid: raw API calls (422, 422, 404 with readable text)", raw_api)
    # --- missing dataset: page whose /api calls are routed to the backend started with a missing DEM
    pg2 = new_page(ctx, "missing-dem")
    pg2.route("**/api/**", lambda route: route.continue_(url=route.request.url.replace("4173", "8001").replace("5173", "8001")))
    def missing():
        pg2.goto(APP); expect(pg2.get_by_role("option", name="Malapert Massif")).to_be_attached(timeout=10000)
        pg2.get_by_role("button", name="Run analysis").click(); expect(pg2.get_by_text("Terrain dataset unavailable")).to_be_visible(timeout=10000)
        pg2.get_by_role("navigation").get_by_role("button", name="Terrain Analysis").click(); expect(pg2.get_by_text("No analysis yet")).to_be_visible()  # nothing fake shown
        pg2.screenshot(path=f"{SHOTS}/missing_dem.png", full_page=True)
    check("missing dataset: clear error, no fabricated results", missing)
    # --- backend down: app must stay navigable
    pg3 = new_page(ctx, "backend-down", expect_failures=True); pg3.route("**/api/**", lambda r: r.abort())
    def down():
        pg3.goto(APP); expect(pg3.get_by_text("Cannot reach backend")).to_be_visible(timeout=10000)
        pg3.get_by_role("navigation").get_by_role("button", name="Data & Methodology").click(); expect(pg3.get_by_role("heading", name="Data & methodology")).to_be_visible()
    check("backend down: error + app still navigable", down)
    b.close()
w = max(len(n) for n, _ in results)
for n, r in results: print(f"{n:<{w}}  {r}")
print("\nbrowser console/page errors (excluding expected 4xx/5xx from invalid-input tests):", problems or "none")
sys.exit(0 if all(r == "PASS" for _, r in results) and not problems else 1)
