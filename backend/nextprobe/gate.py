"""INDEPENDENT SAFETY GATE. Depends on no selector module. The selector recommends; the gate disposes."""
from dataclasses import dataclass

RELEASE, CONTINUE, HOLD, UNKNOWN = "RELEASE", "CONTINUE", "HOLD", "UNKNOWN"


@dataclass
class GateInput:
    p_anomaly: float
    lot_status: str            # TRUSTED | CAUTION | UNTRUSTED
    ood: bool
    data_valid: bool
    pred_lower: float
    pred_median: float
    pred_upper: float
    limit: float
    max_observed: float
    stage: str                 # early | revealed


@dataclass
class GateThresholds:
    release_p: dict            # stage -> max p_anomaly allowed for release (calibrated)
    hold_p: float
    max_rel_interval_width: float
    calibration: str = "SIMULATION-ONLY CALIBRATION"


def evaluate(g: GateInput, th: GateThresholds):
    rel_w = (g.pred_upper - g.pred_lower) / max(g.pred_median, 1e-9)
    rp = th.release_p[g.stage]
    crit = [
        {"key": "data_quality", "ok": bool(g.data_valid), "text": "data quality valid" if g.data_valid else "data quality invalid"},
        {"key": "ood", "ok": not g.ood, "text": "OOD check clear" if not g.ood else "outside reliable model domain (OOD)"},
        {"key": "absolute_spec", "ok": bool(g.max_observed < g.limit),
         "text": f"absolute limit satisfied (max observed {g.max_observed:.2f} < {g.limit:g} uA)" if g.max_observed < g.limit else "absolute limit exceeded"},
        {"key": "lot_baseline", "ok": g.lot_status == "TRUSTED", "text": f"lot baseline {g.lot_status}"},
        {"key": "calibrated_risk", "ok": bool(g.p_anomaly <= rp),
         "text": f"calibrated anomaly risk {g.p_anomaly:.4f} {'<=' if g.p_anomaly <= rp else '>'} release threshold {rp:.4f}"},
        {"key": "uncertainty", "ok": bool(rel_w <= th.max_rel_interval_width and g.pred_upper < g.limit),
         "text": f"168h interval relative width {rel_w:.2f} (max {th.max_rel_interval_width}), upper {g.pred_upper:.2f} uA"},
    ]
    if not g.data_valid or g.ood:
        d, why = UNKNOWN, ["OOD_OR_INVALID_DATA: automatic release forbidden; route to reliability engineer for manual review"]
    elif g.max_observed >= g.limit:
        d, why = HOLD, ["ABSOLUTE_LIMIT_EXCEEDED"]
    elif g.p_anomaly >= th.hold_p:
        d, why = HOLD, ["HIGH_CALIBRATED_ANOMALY_RISK"]
    elif all(c["ok"] for c in crit):
        d, why = RELEASE, ["ALL_RELEASE_CRITERIA_SATISFIED"]
    else:
        d, why = CONTINUE, ["RELEASE_CRITERIA_NOT_MET: " + ",".join(c["key"] for c in crit if not c["ok"])]
    assert not (d == RELEASE and (g.ood or not g.data_valid))
    return {"disposition": d, "criteria": crit, "reasons": why, "stage": g.stage}
