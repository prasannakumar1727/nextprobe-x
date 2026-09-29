import os, sys, io, json, inspect, re
import numpy as np, pandas as pd, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), "..", ".."))
from fastapi.testclient import TestClient
from nextprobe import gate as G, evoi as E, data as D
from nextprobe.api import app
from nextprobe.engine import Engine, load_policy
from nextprobe.evaluation import Evaluator, POLICIES

DS = D.load_canonical("data/SIH26170_BurnIn_Dataset_1000.xlsx")

@pytest.fixture()
def eng(): return Engine(DS, load_policy())
@pytest.fixture(scope="module")
def client():
    c = TestClient(app); c.post("/api/dataset/load"); return c
@pytest.fixture()
def fresh(client): client.post("/api/session/reset"); return client

# ---- leakage / views ----
def test_inference_view_has_no_hidden_columns():
    assert set(DS.inference.columns) == set(D.INFERENCE_COLS)
    assert not any(c in DS.inference.columns for c in ["v96", "v168", "label", "defect", "mode"])

def test_no_hidden_value_in_api_before_reveal(fresh):
    ev = DS.evaluation_view().df
    fresh_txt = json.dumps([fresh.get("/api/summary").json(), fresh.get("/api/devices?limit=1000").json(), fresh.get("/api/lots/L01").json()])
    a = fresh.get("/api/devices/C0001").json(); assert a["observations"]["96h"] is None and a["observations"]["96h_status"] == "HIDDEN"
    txt = json.dumps(a) + fresh_txt + json.dumps(fresh.post("/api/nextprobe/rank", json={"budget": 25}).json()) + json.dumps(fresh.get("/api/passport/C0001").json())
    for k in ("v168", "ground_truth", "label", "defect_type", "Value_96h", "Value_168h"): assert k not in txt
    for v in ev.v168.values[:200]: assert f'{v:.3f}' not in json.dumps(a["observations"])

def test_early_features_do_not_depend_on_hidden_data():
    from nextprobe.model import early_features
    i1 = DS.inference.copy(); f1 = early_features(i1)["X"]
    assert np.allclose(f1, early_features(DS.inference.copy())["X"])
    src = inspect.getsource(early_features); assert "v96" not in src and "v168" not in src

def test_evoi_module_never_touches_replay_or_eval():
    s = inspect.getsource(E); assert "replay" not in s.lower() and "evaluation" not in s.lower() and "v168" not in s

def test_only_selected_receive_96h(eng):
    r = eng.allocate(10); ids = set(r["allocated_ids"]); eng.reveal(); assert set(eng.v96) == ids
    other = [d for d in eng.ids if d not in ids][0]
    assert eng.analysis(other)["observations"]["96h"] is None
    with pytest.raises(KeyError): eng.reveal([other])

def test_repeated_reveal_rejected(eng):
    r = eng.allocate(5); eng.reveal(); 
    with pytest.raises(KeyError): eng.reveal([r["allocated_ids"][0]])

def test_reveal_without_allocation_rejected(eng):
    with pytest.raises(KeyError): eng.reveal(["C0001"])

def test_api_repeated_reveal_409(fresh):
    a = fresh.post("/api/nextprobe/allocate", json={"budget": 5}).json(); assert fresh.post("/api/nextprobe/reveal", json={}).status_code == 200
    assert fresh.post("/api/nextprobe/reveal", json={"device_ids": [a["allocated_ids"][0]]}).status_code == 409

# ---- budget ----
@pytest.mark.parametrize("b", [10, 25, 50, 100])
def test_budget_enforced(eng, b):
    for pol in POLICIES:
        assert eng.rank(pol, b)["selected_count"] <= b
    assert eng.allocate(b)["allocated_count"] <= b

def test_pending_allocation_blocks_second(eng):
    eng.allocate(5)
    with pytest.raises(RuntimeError): eng.allocate(5)

# ---- EVOI ----
def test_evoi_is_nonnegative_before_cost_and_martingale(eng):
    fn, fp, pc = eng.costs(); r0, r1, ev = E.evoi(eng.p0, eng.Pg, eng.Wg, fn, fp, pc)
    assert (r0 - r1 >= -1e-9).all()
    assert np.abs((eng.Wg * eng.Pg).sum(1) - eng.p0).max() < 1e-4   # E[posterior]=prior

def test_nextprobe_is_not_sort_by_anomaly_or_risk(eng):
    a = set(eng.rank("NEXTPROBE_EVOI", 50)["selected_ids"]); b = set(eng.rank("HIGHEST_ANOMALY", 50)["selected_ids"]); c = set(eng.rank("HIGHEST_PREDICTED_RISK", 50)["selected_ids"])
    assert a != b and a != c

def test_deterministic_replay_and_ranking():
    e1, e2 = Engine(DS, load_policy()), Engine(DS, load_policy())
    assert e1.rank("NEXTPROBE_EVOI", 25)["selected_ids"] == e2.rank("NEXTPROBE_EVOI", 25)["selected_ids"]
    e1.allocate(10); e2.allocate(10); assert e1.reveal() == e2.reveal()

# ---- gate independence ----
TH = G.GateThresholds({"early": 0.03, "revealed": 0.01}, 0.5, 1.5)
def _gi(**k):
    d = dict(p_anomaly=0.001, lot_status="TRUSTED", ood=False, data_valid=True, pred_lower=10, pred_median=11, pred_upper=13, limit=50, max_observed=11, stage="early"); d.update(k)
    return G.GateInput(**d)

def test_gate_release_when_all_criteria_ok(): assert G.evaluate(_gi(), TH)["disposition"] == "RELEASE"
def test_ood_cannot_release():
    r = G.evaluate(_gi(ood=True, p_anomaly=0.0), TH); assert r["disposition"] == "UNKNOWN" and r["disposition"] != "RELEASE"
def test_invalid_data_cannot_release(): assert G.evaluate(_gi(data_valid=False), TH)["disposition"] == "UNKNOWN"
def test_abs_limit_holds(): assert G.evaluate(_gi(max_observed=51), TH)["disposition"] == "HOLD"
def test_untrusted_lot_cannot_release(): assert G.evaluate(_gi(lot_status="UNTRUSTED"), TH)["disposition"] == "CONTINUE"
def test_gate_signature_has_no_evoi_input():
    assert not any("evoi" in f or "rank" in f for f in G.GateInput.__dataclass_fields__)
def test_gate_module_imports_no_selector():
    import ast
    mods = [n.module or "" for n in ast.walk(ast.parse(inspect.getsource(G))) if isinstance(n, ast.ImportFrom)] + \
           [a.name for n in ast.walk(ast.parse(inspect.getsource(G))) if isinstance(n, ast.Import) for a in n.names]
    assert not any(m.split(".")[-1] in ("evoi", "engine", "evaluation", "data", "model") for m in mods), mods
def test_nextprobe_cannot_release(eng):
    # selecting a device for probing never changes its disposition until 96h is revealed and the gate re-evaluates
    before = {d: eng.gate(eng.idx[d])["disposition"] for d in eng.ids}
    eng.allocate(50); eng.gate_cache.clear()
    assert {d: eng.gate(eng.idx[d])["disposition"] for d in eng.ids} == before
def test_ood_devices_never_released(eng):
    for i in np.where(eng.ood_early)[0]: assert eng.gate(int(i))["disposition"] == "UNKNOWN"
def test_gate_decision_changes_with_evidence_not_selector(eng):
    # same gate, different thresholds => different outcome; selector state irrelevant
    x = _gi(p_anomaly=0.02); assert G.evaluate(x, TH)["disposition"] == "RELEASE"
    assert G.evaluate(x, G.GateThresholds({"early": 0.01, "revealed": 0.01}, 0.5, 1.5))["disposition"] == "CONTINUE"

# ---- OOD ----
def test_ood_flags_out_of_domain_inputs():
    df = pd.read_excel("data/SIH26170_BurnIn_Dataset_1000.xlsx").head(60)[["Component_ID", "Lot_ID", "Value_0h", "Value_24h"]].copy()
    df.loc[0, ["Value_0h", "Value_24h"]] = [400.0, 900.0]
    ds, v = D.validate_upload(df); from nextprobe.model import early_features
    e = Engine(ds, load_policy(), train_ds=(DS, early_features(DS.inference)))
    assert e.ood_early[0] and e.gate(0)["disposition"] == "UNKNOWN"

# ---- CSV validation ----
def test_csv_missing_columns_invalid(): assert D.validate_upload(pd.DataFrame({"device_id": ["a"], "lot_id": ["L"], "v0": [1.0]}))[1]["status"] == "INVALID"
def test_csv_duplicates_invalid():
    df = pd.DataFrame({"device_id": ["a", "a"], "lot_id": ["L", "L"], "v0": [1.0, 2.0], "v24": [1.0, 2.0]}); assert D.validate_upload(df)[1]["status"] == "INVALID"
def test_csv_nonnumeric_invalid():
    df = pd.DataFrame({"device_id": ["a", "b"], "lot_id": ["L", "L"], "v0": ["x", 2.0], "v24": [1.0, 2.0]}); assert D.validate_upload(df)[1]["status"] == "INVALID"
def test_csv_small_lot_degraded_and_analysis_only():
    df = pd.DataFrame({"device_id": ["a", "b"], "lot_id": ["L", "L"], "v0": [10.0, 11.0], "v24": [10.1, 11.2]})
    ds, v = D.validate_upload(df); assert v["status"] == "DEGRADED" and v["replay_96h"] is False
def test_analysis_only_mode_disables_reveal():
    df = pd.read_excel("data/SIH26170_BurnIn_Dataset_1000.xlsx").head(100)[["Component_ID", "Lot_ID", "Value_0h", "Value_24h"]]
    ds, v = D.validate_upload(df); from nextprobe.model import early_features
    e = Engine(ds, load_policy(), train_ds=(DS, early_features(DS.inference)))
    assert not e.eligible().any()
    with pytest.raises(PermissionError): e.allocate(5)
def test_upload_endpoint_invalid(client):
    r = client.post("/api/dataset/upload", files={"file": ("a.csv", "device_id,lot_id\na,L\n")}).json(); assert r["loaded"] is False
    client.post("/api/dataset/load")

# ---- evaluation / integration ----
def test_evaluation_same_budget_and_reports_all_policies(eng):
    s = Evaluator(eng).summary()
    for b in s["budgets"]:
        for p in POLICIES: assert s["sweep"][p][str(b)]["n_probed"] <= b
    for k in ["fnr", "decision_loss", "early_miss_recovery", "raw_defect_capture", "precision", "recall", "pr_auc", "mae_168h", "rmse_168h", "interval_coverage_90"]:
        assert k in s["sweep"]["NEXTPROBE_EVOI"]["50"]

def test_hero_not_hardcoded_and_hidden_until_reveal(fresh):
    h = fresh.get("/api/evaluation/hero").json(); assert h["device_id"] and "revealed_p_anomaly" not in h

def test_end_to_end(client):
    c = client; c.post("/api/session/reset")
    assert c.get("/api/summary").json()["n_devices"] == 1000
    rk = c.post("/api/nextprobe/rank", json={"budget": 25}).json(); assert rk["selected_count"] <= 25
    al = c.post("/api/nextprobe/allocate", json={"budget": 25}).json(); assert al["allocated_ids"] == rk["selected_ids"]
    d = al["allocated_ids"][0]; before = c.get(f"/api/devices/{d}").json(); assert before["observations"]["96h"] is None
    rv = c.post("/api/nextprobe/reveal", json={}).json(); assert len(rv["revealed"]) == al["allocated_count"]
    after = c.get(f"/api/devices/{d}").json(); assert after["observations"]["96h"] is not None and after["stage"] == "revealed"
    assert after["prediction"]["basis"] == "0h+24h+96h" and after["gate"]["disposition"] in ("RELEASE", "CONTINUE", "HOLD", "UNKNOWN")
    p = c.get(f"/api/passport/{d}").json(); assert p["events"][-1]["hash"] == p["head_hash"] and p["events"][1]["prev_hash"] == p["events"][0]["hash"]
    assert any(e["type"] == "96h_revealed" for e in p["events"])
    assert c.get("/api/evaluation").json()["sweep"]["NEXTPROBE_EVOI"]["25"]["decision_loss"] > 0
    assert "rows" in c.get("/api/evaluation/misses").json()
