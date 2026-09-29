"""OFFLINE evaluation engine (uses hidden replay + ground truth). Simulation results only. Never used for inference."""
import numpy as np
from sklearn.metrics import average_precision_score
from . import evoi as E
from .data import CLASSES, ANOM

POLICIES = ["RANDOM", "HIGHEST_ANOMALY", "HIGHEST_PREDICTED_RISK", "NEXTPROBE_EVOI"]
N_RANDOM = 20


class Evaluator:
    def __init__(self, eng):
        self.e = e = eng; ev = e.ds.evaluation_view().df; self.ev = ev; N = e.N
        self.y = ev.label.values.astype(bool); self.v168 = ev.v168.values
        z96 = np.log(ev.v96.values) - e.F["lv24"]
        self.Ppost, self.ppost, self.qpost, self.oodpost = e.post_state(np.arange(N), z96)
        g = e.policy["gate"]
        self.disp_early = np.array([e.early_disposition(i)["disposition"] for i in range(N)])
        from . import gate as G
        self.disp_post = np.array([G.evaluate(e._gate_input(self.ppost[i], self.qpost[i], self.oodpost[i], i, "revealed", float(ev.v96.values[i])), e.th)["disposition"] for i in range(N)])
        self.cache = {}

    # -------- selection policies (early information only, same eligible set, same budget) --------
    def select(self, policy, budget, fn, fp, pc, seed=0):
        e = self.e
        if policy == "NEXTPROBE_EVOI":
            _, _, ev = E.evoi(e.p0, e.Pg, e.Wg, fn, fp, pc); order = np.argsort(-ev, kind="stable"); sel = [i for i in order[:budget] if ev[i] > 0]
        elif policy == "HIGHEST_ANOMALY": sel = list(np.argsort(-e.anomaly_score(), kind="stable")[:budget])
        elif policy == "HIGHEST_PREDICTED_RISK": sel = list(np.argsort(-e.p0, kind="stable")[:budget])
        else: sel = list(np.random.RandomState(1000 + seed).permutation(e.N)[:budget])
        m = np.zeros(e.N, bool); m[sel] = True; return m

    def metrics(self, sel, fn, fp, pc):
        e = self.e; ts = fp / (fp + fn); y = self.y; n = int(sel.sum())
        flag0 = (e.p0 >= ts) | e.ood_early
        pf = np.where(sel, self.ppost, e.p0); oodf = np.where(sel, self.oodpost, e.ood_early); flag = (pf >= ts) | oodf
        FN = int((y & ~flag).sum()); FP = int((~y & flag).sum()); TP = int((y & flag).sum()); P = int(y.sum())
        FN0 = int((y & ~flag0).sum()); FP0 = int((~y & flag0).sum()); loss0 = fn * FN0 + fp * FP0
        loss_ex = fn * FN + fp * FP; miss0 = y & ~flag0
        disp = np.where(sel, self.disp_post, self.disp_early)
        _, r_post, ev = E.evoi(e.p0, e.Pg, e.Wg, fn, fp, pc); r_now = E.decision_risk(e.p0, fn, fp)
        q = np.where(sel[:, None], self.qpost, e.q0); pt = q[:, 1]
        return {"n_probed": n, "decision_loss": loss_ex + pc * n, "decision_loss_excl_probe": loss_ex, "decision_loss_no_probe": loss0,
                "fnr": FN / P, "false_negatives": FN, "false_positives": FP, "recall": TP / P, "precision": TP / max(TP + FP, 1),
                "pr_auc": float(average_precision_score(y, pf)), "raw_defect_capture": float((y & sel).sum() / P),
                "early_misses": int(miss0.sum()), "early_miss_recovery": float((miss0 & sel & flag).sum() / max(miss0.sum(), 1)),
                "decision_changes": int(((flag != flag0) & sel).sum()),
                "mean_evoi": float(ev[sel].mean()) if n else 0.0, "mean_risk_reduction": float((r_now - r_post)[sel].mean()) if n else 0.0,
                "probe_efficiency": float((loss0 - loss_ex) / n) if n else 0.0,
                "gate_escape_rate": float((y & (disp == "RELEASE")).sum() / P), "gate_release_count": int((disp == "RELEASE").sum()),
                "mae_168h": float(np.abs(pt - self.v168).mean()), "rmse_168h": float(np.sqrt(((pt - self.v168) ** 2).mean())),
                "interval_coverage_90": float(((self.v168 >= q[:, 0]) & (self.v168 <= q[:, 2])).mean())}

    def run(self, policy, budget, fn, fp, pc):
        if policy == "RANDOM":
            ms = [self.metrics(self.select(policy, budget, fn, fp, pc, s), fn, fp, pc) for s in range(N_RANDOM)]
            return {k: float(np.mean([m[k] for m in ms])) for k in ms[0]} | {"random_seeds": N_RANDOM}
        return self.metrics(self.select(policy, budget, fn, fp, pc), fn, fp, pc)

    def sweep(self):
        if "sweep" in self.cache: return self.cache["sweep"]
        p = self.e.policy; fn, fp, pc = p["false_negative_cost"], p["false_positive_cost"], p["probe_cost"]
        out = {pol: {str(b): self.run(pol, b, fn, fp, pc) for b in p["budgets"]} for pol in POLICIES}
        self.cache["sweep"] = out; return out

    def sensitivity(self):
        if "sens" in self.cache: return self.cache["sens"]
        p = self.e.policy; s = p["sensitivity"]; b = s["budget"]; rows = []
        for r in s["fn_fp_ratios"]:
            for c in s["probe_costs"]:
                row = {"fn_fp_ratio": r, "probe_cost": c, "budget": b, "loss": {}, "n_probed_nextprobe": None}
                for pol in POLICIES:
                    m = self.run(pol, b, float(r), 1.0, c); row["loss"][pol] = m["decision_loss"]
                    if pol == "NEXTPROBE_EVOI": row["n_probed_nextprobe"] = m["n_probed"]
                row["no_probe_loss"] = m["decision_loss_no_probe"]; row["best_policy"] = min(row["loss"], key=row["loss"].get); rows.append(row)
        self.cache["sens"] = rows; return rows

    def summary(self):
        p = self.e.policy; sw = self.sweep(); e = self.e
        fn, fp, pc = p["false_negative_cost"], p["false_positive_cost"], p["probe_cost"]
        by_budget = {}
        for b in p["budgets"]:
            l = {pol: sw[pol][str(b)]["decision_loss"] for pol in POLICIES}
            by_budget[str(b)] = {"best_policy": min(l, key=l.get), "nextprobe_beats": [pol for pol in POLICIES if pol != "NEXTPROBE_EVOI" and l["NEXTPROBE_EVOI"] < l[pol]],
                                 "nextprobe_loses_to": [pol for pol in POLICIES if pol != "NEXTPROBE_EVOI" and l["NEXTPROBE_EVOI"] >= l[pol]]}
        early = {"pr_auc_early": float(average_precision_score(self.y, e.p0)), "mae_168h_early": float(np.abs(e.q0[:, 1] - self.v168).mean()),
                 "rmse_168h_early": float(np.sqrt(((e.q0[:, 1] - self.v168) ** 2).mean())),
                 "coverage_90_early": float(((self.v168 >= e.q0[:, 0]) & (self.v168 <= e.q0[:, 2])).mean())}
        return {"banner": "SIMULATION RESULTS - prototype validated on supplied synthetic engineering benchmark; not production validation",
                "policy": {k: p[k] for k in ["policy_version", "policy_status", "disclaimer", "false_negative_cost", "false_positive_cost", "probe_cost"]},
                "policies": POLICIES, "budgets": p["budgets"], "sweep": sw, "by_budget": by_budget, "early": early, "calibration": e.gate_thresholds(),
                "random_note": f"RANDOM averaged over {N_RANDOM} seeds", "evaluation_note": "cross-fitted predictions on the full 1000-device pool; gate thresholds calibrated on a 150-device validation subset that is also part of the pool (simulation-only)"}

    def hero(self, budget=50):
        e = self.e; fn, fp, pc = e.costs(); ts = e.tstar(); sel = self.select("NEXTPROBE_EVOI", budget, fn, fp, pc)
        _, r_post, ev = E.evoi(e.p0, e.Pg, e.Wg, fn, fp, pc); flag0 = e.p0 >= ts
        flagf = self.ppost >= ts
        tiers = [self.y & ~flag0 & sel & flagf & (e.F["zl"] < 2.5), self.y & ~flag0 & sel & flagf, self.y & sel & flagf, self.y & sel]
        for ti, t in enumerate(tiers):
            c = np.where(t)[0]
            if len(c):
                i = int(c[np.argmax(ev[c] * (self.ppost[c] - e.p0[c]))])
                rank = int((ev > ev[i]).sum() + 1); d = e.ids[i]; rev = d in e.v96
                out = {"device_id": d, "lot_id": e.inf.lot_id[i], "budget": budget, "nextprobe_rank": rank, "early_p_anomaly": float(e.p0[i]),
                       "early_gate": self.disp_early[i], "evoi": float(ev[i]), "lot_level_z_24h": float(e.F["zl"][i]), "v24_below_limit": bool(e.inf.v24[i] < e.inf.limit[i]),
                       "criteria_tier": ti, "criteria": ["true anomaly, not flagged early, selected by NEXTPROBE, flagged after 96h, lot-relative normal at 24h",
                                 "true anomaly, not flagged early, selected by NEXTPROBE, flagged after 96h (no early miss met the stricter tier 0 criteria)",
                                 "true anomaly, selected by NEXTPROBE, flagged after 96h (relaxed)", "true anomaly selected by NEXTPROBE (relaxed)"][ti],
                       "outcome_disclosed": rev}
                if rev: out |= {"revealed_p_anomaly": float(e.cur_p[i]), "revealed_gate": e.gate(i)["disposition"]}
                else: out["note"] = "96h outcome hidden until this device is allocated and revealed in the session"
                return out
        return {"device_id": None, "note": "no device meets hero criteria at this budget"}

    def misses(self, budget=50):
        e = self.e; fn, fp, pc = e.costs(); ts = e.tstar(); sel = self.select("NEXTPROBE_EVOI", budget, fn, fp, pc)
        flag0 = (e.p0 >= ts) | e.ood_early; pf = np.where(sel, self.ppost, e.p0); flagf = (pf >= ts) | np.where(sel, self.oodpost, e.ood_early)
        miss = np.where(self.y & ~flag0)[0]; rows = []
        for i in miss:
            top = np.argsort(-e.P0[i])[:2]
            outc = "UNKNOWN_OOD" if (sel[i] and self.oodpost[i]) else ("RECOVERED_AFTER_96H" if (sel[i] and flagf[i]) else ("PROBED_STILL_UNRESOLVED" if sel[i] else "NOT_PROBED_WITHIN_BUDGET"))
            rows.append({"device_id": e.ids[i], "lot_id": e.inf.lot_id[i], "outcome": outc, "early_p_anomaly": float(e.p0[i]), "early_gate": self.disp_early[i],
                         "why_missed_early": {"lot_drift_z": float(e.F["zd"][i]), "lot_level_z": float(e.F["zl"][i]), "early_p_below_threshold": float(ts),
                                              "main_early_hypotheses": f"{CLASSES[top[0]]} vs {CLASSES[top[1]]}", "absolute_spec_ok_at_24h": bool(e.inf.v24[i] < e.inf.limit[i])},
                         "what_contained_it": {"kept_out_of_release_by_gate": bool(self.disp_early[i] != "RELEASE"), "early_gate": self.disp_early[i],
                                               "probed": bool(sel[i]), "post_96h_p_anomaly": float(self.ppost[i]) if sel[i] else None,
                                               "final_gate": self.disp_post[i] if sel[i] else self.disp_early[i]}})
        cnt = {k: sum(r["outcome"] == k for r in rows) for k in ["RECOVERED_AFTER_96H", "PROBED_STILL_UNRESOLVED", "NOT_PROBED_WITHIN_BUDGET", "UNKNOWN_OOD"]}
        released = sum(r["what_contained_it"]["final_gate"] == "RELEASE" for r in rows)
        return {"budget": budget, "early_misses": len(rows), "counts": cnt, "still_released_by_gate": released, "rows": rows,
                "note": "EVALUATION-ONLY view (uses ground truth); simulation results"}
