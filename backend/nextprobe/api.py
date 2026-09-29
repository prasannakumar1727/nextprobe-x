import io, os
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .data import load_canonical, validate_upload
from .engine import Engine, load_policy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data", "SIH26170_BurnIn_Dataset_1000.xlsx")
POLICY = os.path.join(ROOT, "config", "risk_policy.json")

app = FastAPI(title="NEXTPROBE-X", version="0.1")
S = {"engine": None, "eval": None, "canon": None}


def eng():
    if S["engine"] is None: raise HTTPException(409, "no dataset loaded: POST /api/dataset/load")
    return S["engine"]


def evaluator():
    e = eng()
    if not e.ds.has_evaluation: raise HTTPException(409, "evaluation unavailable: uploaded dataset has no ground truth")
    if S["eval"] is None:
        from .evaluation import Evaluator
        S["eval"] = Evaluator(e)
    return S["eval"]


class Budget(BaseModel): budget: int; policy: str = "NEXTPROBE_EVOI"
class Reveal(BaseModel): device_ids: list[str] | None = None


@app.get("/api/health")
def health(): return {"ok": True, "banner": "SIMULATED DATA"}


@app.get("/api/policy")
def policy(): return load_policy(POLICY)


@app.get("/api/state")
def state():
    e = S["engine"]
    return {"loaded": e is not None, "banner": "SIMULATED DATA", **({"summary": e.summary()} if e else {})}


@app.post("/api/dataset/load")
def load():
    ds = load_canonical(DATA); S["canon"] = ds
    S["engine"] = Engine(ds, load_policy(POLICY)); S["eval"] = None
    return S["engine"].summary()


@app.post("/api/session/reset")
def reset():
    eng().reset(); return eng().summary()


@app.post("/api/dataset/upload")
async def upload(file: UploadFile = File(...)):
    try: df = pd.read_csv(io.BytesIO(await file.read()))
    except Exception as ex: raise HTTPException(400, f"cannot parse CSV: {ex}")
    ds, val = validate_upload(df)
    if ds is None: return {"loaded": False, "validation": val}
    if S["canon"] is None: S["canon"] = load_canonical(DATA)
    base = S["canon"]
    from .model import early_features
    S["engine"] = Engine(ds, load_policy(POLICY), train_ds=(base, early_features(base.inference))); S["eval"] = None
    return {"loaded": True, "validation": val, "summary": S["engine"].summary()}


@app.get("/api/summary")
def summary(): return eng().summary()


@app.get("/api/lots")
def lots():
    e = eng(); rows = []
    for l, v in e.lots.items():
        m = (e.inf.lot_id == l).values
        rows.append({**v, "flagged_count": int(((e.cur_p >= e.tstar()) & m).sum())})
    return rows


@app.get("/api/lots/{lot_id}")
def lot(lot_id: str):
    e = eng()
    if lot_id not in e.lots: raise HTTPException(404, "unknown lot")
    m = (e.inf.lot_id == lot_id).values; rows = e.device_rows(); dev = [r for r in rows if r["lot_id"] == lot_id]
    pts = [{"device_id": e.ids[i], "lot_percentile": float(e.lot_pct[i]), "drift_log_0_24h": float(e.F["d24"][i]), "drift_z": float(e.F["zd"][i]), "v24": float(e.inf.v24[i]),
            "disposition": e.gate(i)["disposition"]} for i in range(e.N) if m[i]]
    return {**e.lots[lot_id], "flagged_count": sum(1 for r in dev if r["p_anomaly"] >= e.tstar()), "devices": pts, "healthy_envelope_z": [-3.5, 3.5]}


@app.get("/api/devices")
def devices(limit: int = 100, sort: str = "evoi", lot_id: str | None = None):
    rows = eng().device_rows()
    if lot_id: rows = [r for r in rows if r["lot_id"] == lot_id]
    key = {"evoi": lambda r: -(r["evoi"] if r["evoi"] is not None else -1e9), "risk": lambda r: -r["p_anomaly"], "id": lambda r: r["device_id"]}[sort]
    rows = sorted(rows, key=key)[:limit]
    for k, r in enumerate(rows): r["rank"] = k + 1
    return {"rows": rows}


@app.get("/api/devices/{device_id}")
def device(device_id: str):
    e = eng()
    if device_id not in e.idx: raise HTTPException(404, "unknown device")
    return e.analysis(device_id)


@app.post("/api/nextprobe/rank")
def rank(b: Budget):
    e = eng()
    if b.budget < 1 or b.budget > e.N: raise HTTPException(400, "budget out of range")
    if not e.ds.replay.has_replay(): raise HTTPException(409, "ANALYSIS-ONLY MODE: no 96h replay; sequential screening disabled")
    try: return e.rank(b.policy, b.budget)
    except ValueError: raise HTTPException(400, "unknown policy")


@app.post("/api/nextprobe/allocate")
def allocate(b: Budget):
    e = eng()
    if b.budget < 1 or b.budget > e.N: raise HTTPException(400, "budget out of range")
    try: return e.allocate(b.budget)
    except PermissionError as ex: raise HTTPException(409, str(ex))
    except RuntimeError as ex: raise HTTPException(409, str(ex))


@app.post("/api/nextprobe/reveal")
def reveal(r: Reveal):
    e = eng()
    if not e.ds.replay.has_replay(): raise HTTPException(409, "ANALYSIS-ONLY MODE")
    try: return {"revealed": e.reveal(r.device_ids), "summary": e.summary()}
    except KeyError as ex: raise HTTPException(409, str(ex.args[0]))


@app.get("/api/nextprobe/status")
def np_status(): e = eng(); return {"pending": e.pending, "rounds": e.rounds, "revealed_count": len(e.v96)}


@app.get("/api/passport/{device_id}")
def passport(device_id: str):
    e = eng()
    if device_id not in e.idx: raise HTTPException(404, "unknown device")
    return e.passport(device_id)


@app.get("/api/evaluation")
def evaluation(): return evaluator().summary()


@app.get("/api/evaluation/sensitivity")
def sensitivity(): return {"rows": evaluator().sensitivity(), "policy_status": "simulation_only"}


@app.get("/api/evaluation/hero")
def hero(budget: int = 50): return evaluator().hero(budget)


@app.get("/api/evaluation/misses")
def misses(budget: int = 50): return evaluator().misses(budget)


DIST = os.path.join(ROOT, "frontend", "dist")
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")
    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"): raise HTTPException(404)
        return FileResponse(os.path.join(DIST, "index.html"))
