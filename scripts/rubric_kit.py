"""Judge-style spot-check kit + latency, through the real HTTP API.

usage (repo root, models/ present): MAYA_RATE_LIMIT=0 python scripts/rubric_kit.py [custom_cases.json]
The optional JSON holds "Your own payment" scenarios produced by frontend/shared/custom.js.
"""
import json, statistics, sys, time, concurrent.futures as cf
sys.path.insert(0, "src")
from fastapi.testclient import TestClient
import api
c = TestClient(api.create_app())
scen = c.get("/v1/demo/scenarios").json()
scen = scen if isinstance(scen, list) else scen["scenarios"]
def call(s, **over):
    body = {"features": dict(s["features"]), "amount_inr": s["amount_inr"],
            "soft_signals": dict(s.get("soft_signals") or {}), "mulehunter_status": s.get("mulehunter_status")}
    for k, v in over.items():
        if k == "features": body["features"].update(v)
        elif k == "soft": body["soft_signals"].update(v)
        else: body[k] = v
    return c.post("/v1/score", json=body).json()
by = {s["key"]: s for s in scen}
expect = {"normal": "release", "investment": "hold", "police": "hold", "unclear": "nudge"}
rows = []
def kit(name, s, want, **over):
    r = call(s, **over); ok = r["action"] in want
    rows.append((name, "/".join(want), r["action"], r["conformal_set"], round(r["p_scam"], 4), ok,
                 "; ".join(r.get("reasons", [])[:2])))
for k, w in expect.items(): kit(f"scenario:{k}", by[k], [w])
# judge varies inputs on the scam scenarios
for k in ("investment", "police"):
    kit(f"{k}: amount x0.1", by[k], ["hold", "nudge"], amount_inr=by[k]["amount_inr"] * 0.1)
    kit(f"{k}: amount x10", by[k], ["hold"], amount_inr=by[k]["amount_inr"] * 10)
    kit(f"{k}: no soft signals", by[k], ["hold", "nudge"], soft_signals={})
    kit(f"{k}: soft + mule flag", by[k], ["hold"], soft={"is_screen_shared": True}, mulehunter_status="mule")
# benign controls a judge might try
n = by["normal"]
kit("normal: amount x5", n, ["release", "nudge"], amount_inr=n["amount_inr"] * 5)
kit("normal: on a call + screen share", n, ["release", "nudge"], soft={"is_screen_shared": True, "is_voice_active": True})
kit("normal: chat 'payment_demand' only", n, ["release", "nudge"], soft={"chat_stage": "payment_demand"})
kit("normal: payee 'suspicious' (provider)", n, ["release", "nudge"], mulehunter_status="suspicious")
# custom-form cases (model lab)
for nm, s in (json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 else {}).items():
    want = {"ordinary": ["release"], "first_pressure": ["hold"], "reported": ["hold", "nudge"], "first_only": ["nudge", "release"]}[nm]
    kit(f"custom:{nm}", s, want)
ok = sum(r[5] for r in rows)
print(f"KIT {ok}/{len(rows)} as expected")
for r in rows: print(("PASS " if r[5] else "MISS ") + " | ".join(map(str, r[:5])) + " | " + r[6][:90])
# latency: sequential and concurrent
body = {"features": by["investment"]["features"], "amount_inr": 5000, "soft_signals": {}}
for _ in range(20): c.post("/v1/score", json=body)
lat = []
for _ in range(300):
    t = time.perf_counter(); c.post("/v1/score", json=body); lat.append((time.perf_counter() - t) * 1000)
lat.sort(); print(f"LATENCY sequential n=300 p50={lat[149]:.1f}ms p95={lat[284]:.1f}ms p99={lat[296]:.1f}ms")
lat = []
for _ in range(100):
    t = time.perf_counter(); c.post("/v1/score", json={**body, "explain": True}); lat.append((time.perf_counter() - t) * 1000)
lat.sort(); print(f"LATENCY with SHAP explanation n=100 p50={lat[49]:.1f}ms p95={lat[94]:.1f}ms")
