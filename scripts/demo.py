"""Deterministic end-to-end demo against a running server: python scripts/demo.py [http://127.0.0.1:8000]"""
import sys, httpx
B = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000") + "/api"
c = httpx.Client(timeout=120)
g = lambda p: c.get(B + p).json(); p = lambda u, j=None: c.post(B + u, json=j or {})
s = p("/dataset/load").json(); p("/session/reset")
print("1 LOAD", s["dataset"], s["n_devices"], "devices", s["counts"], "| banner:", s["banner"])
rk = p("/nextprobe/rank", {"budget": 50}).json(); print("2-4 NEXTPROBE rank: selected", rk["selected_count"], "/ 50; top:", [r["device_id"] for r in rk["ranking"][:5]])
hero = g("/evaluation/hero"); print("   auto hero:", hero["device_id"], "early P", round(hero["early_p_anomaly"], 4), "rank", hero["nextprobe_rank"])
al = p("/nextprobe/allocate", {"budget": 50}).json(); print("5 ALLOCATE", al["allocated_count"])
d = hero["device_id"] if hero["device_id"] in al["allocated_ids"] else al["allocated_ids"][0]
b = g(f"/devices/{d}"); print("   before:", d, "96h =", b["observations"]["96h_status"], "P", round(b["p_anomaly"], 4), "168h", round(b["prediction"]["median_168h"], 2), b["gate"]["disposition"])
rv = p("/nextprobe/reveal").json(); ch = sum(r["changed"] for r in rv["revealed"]); print("6 REVEAL", len(rv["revealed"]), "devices; gate dispositions changed:", ch)
a = g(f"/devices/{d}"); print("7-8 after:", d, "96h =", a["observations"]["96h"], "P", round(a["p_anomaly"], 4), "168h", round(a["prediction"]["median_168h"], 2), a["gate"]["disposition"])
print("   repeat reveal ->", p("/nextprobe/reveal", {"device_ids": [d]}).status_code, "(expected 409)")
pp = g(f"/passport/{d}"); print("10 PASSPORT events", len(pp["events"]), "head", pp["head_hash"][:12])
ev = g("/evaluation"); print("11 EVALUATION (SIMULATION RESULTS); decision loss @ budget 50:")
for pol in ev["policies"]: m = ev["sweep"][pol]["50"]; print(f"   {pol:24s} loss {m['decision_loss']:.1f}  FNR {m['fnr']:.3f}  early-miss recovery {m['early_miss_recovery']:.3f}  probes {m['n_probed']:.0f}")
