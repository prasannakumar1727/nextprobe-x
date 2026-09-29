"""Three strict data views: INFERENCE (0h/24h), REPLAY (96h, gated), EVALUATION (offline)."""
import hashlib
import numpy as np, pandas as pd

CLASSES = ["NONE", "NORMAL_AGING", "LATENT_DRIFT", "ACCELERATING_DRIFT", "OBVIOUS_FAILURE"]
ANOM = np.array([0, 0, 1, 1, 1], bool)
INFERENCE_COLS = ["device_id", "lot_id", "slot", "temperature_c", "param", "v0", "v24", "limit"]


class ReplayStore:
    """Holds hidden 96h values. Only Engine.reveal (after allocation) may call .get()."""
    def __init__(self, values): self._v = dict(values)
    def has_replay(self): return len(self._v) > 0
    def get(self, device_id): return self._v[device_id]


class EvaluationView:
    """Offline only. Imported solely by evaluation.py / evaluation API routes."""
    def __init__(self, df): self.df = df.reset_index(drop=True)


class Dataset:
    def __init__(self, inference, replay, evaluation, name, version_hash, validation):
        self.inference, self.replay, self._evaluation = inference, replay, evaluation
        self.name, self.version_hash, self.validation = name, version_hash, validation
    @property
    def has_evaluation(self): return self._evaluation is not None
    def evaluation_view(self): return self._evaluation


def load_canonical(path):
    raw = pd.read_excel(path)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
    raw["slot"] = "S" + (raw.groupby("Lot_ID").cumcount() + 1).astype(str).str.zfill(3)  # derived, not in source
    inf = pd.DataFrame({
        "device_id": raw.Component_ID, "lot_id": raw.Lot_ID, "slot": raw.slot,
        "temperature_c": raw.Temperature_C, "param": raw.Parameter,
        "v0": raw.Value_0h, "v24": raw.Value_24h, "limit": raw.Absolute_Limit_uA})
    ev = pd.DataFrame({
        "device_id": raw.Component_ID, "v96": raw.Value_96h, "v168": raw.Value_168h,
        "label": raw.Ground_Truth_Anomaly.astype(int), "defect": raw.Defect_Type, "mode": raw.Drift_Mode})
    ev["cls"] = ev.defect.map({c: i for i, c in enumerate(CLASSES)})
    # NORMAL_AGING vs NONE come from Defect_Type; check
    rep = ReplayStore(dict(zip(raw.Component_ID, raw.Value_96h)))
    val = {"status": "VALID", "issues": [], "n_devices": len(raw), "n_lots": int(raw.Lot_ID.nunique()), "replay_96h": True}
    return Dataset(inf, rep, EvaluationView(ev), "SIH26170_BurnIn_Dataset_1000", h, val)


def validate_upload(df, limit_default=50.0):
    """Wide CSV: device_id/Component_ID, lot_id/Lot_ID, Value_0h, Value_24h, [Value_96h]. Never silently repairs."""
    issues, status = [], "VALID"
    ren = {"Component_ID": "device_id", "Lot_ID": "lot_id", "Value_0h": "v0", "Value_24h": "v24", "Value_96h": "v96",
           "Absolute_Limit_uA": "limit", "Temperature_C": "temperature_c", "Slot": "slot"}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    if {"device_id", "lot_id", "t_hours", "value"} <= set(df.columns):  # long format -> pivot
        p = df.pivot_table(index=["device_id", "lot_id"], columns="t_hours", values="value", aggfunc="first").reset_index()
        p.columns = [{0.0: "v0", 24.0: "v24", 96.0: "v96"}.get(c, c) if not isinstance(c, str) else c for c in p.columns]
        df = p
    missing = [c for c in ["device_id", "lot_id", "v0", "v24"] if c not in df.columns]
    if missing:
        return None, {"status": "INVALID", "issues": [f"missing required columns: {missing}"], "replay_96h": False}
    if df.device_id.duplicated().any():
        issues.append(f"duplicate device_id: {df.device_id[df.device_id.duplicated()].unique()[:5].tolist()}"); status = "INVALID"
    for c in ["v0", "v24"] + (["v96"] if "v96" in df.columns else []):
        num = pd.to_numeric(df[c], errors="coerce")
        n_bad = int(num.isna().sum() - df[c].isna().sum())
        if n_bad: issues.append(f"{c}: {n_bad} non-numeric values"); status = "INVALID"
        df[c] = num
    for c in ["v0", "v24"]:
        nm = int(df[c].isna().sum())
        if nm: issues.append(f"{c}: {nm} missing values"); status = "INVALID"
        if (df[c] <= 0).any(): issues.append(f"{c}: non-positive leakage values present"); status = "INVALID"
    if status == "INVALID":
        return None, {"status": status, "issues": issues, "replay_96h": False}
    lots = df.groupby("lot_id").size()
    if (lots < 10).any():
        issues.append(f"lots with <10 devices (lot baseline unreliable): {lots[lots < 10].index.tolist()}"); status = "DEGRADED"
    if "limit" not in df.columns: df["limit"] = limit_default
    if "temperature_c" not in df.columns: df["temperature_c"] = 125.0
    if "slot" not in df.columns: df["slot"] = "S" + (df.groupby("lot_id").cumcount() + 1).astype(str).str.zfill(3)
    df["param"] = "Leakage_Current"
    has96 = "v96" in df.columns and bool(df.v96.notna().all())
    inf = df[INFERENCE_COLS].copy()
    rep = ReplayStore(dict(zip(df.device_id, df.v96)) if has96 else {})
    h = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
    if not has96: issues.append("no 96h replay column: ANALYSIS-ONLY MODE (sequential reveal disabled)")
    val = {"status": status, "issues": issues, "n_devices": len(df), "n_lots": int(df.lot_id.nunique()), "replay_96h": has96}
    return Dataset(inf, rep, None, "uploaded_csv", h, val), val
