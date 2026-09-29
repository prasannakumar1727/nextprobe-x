"""Analysis engine + sequential session. NEXTPROBE (evoi.py) and the safety gate (gate.py) are separate modules."""
import json, hashlib, copy
import numpy as np, pandas as pd
from scipy.special import ndtr
from . import gate as G, evoi as E
from .data import CLASSES, ANOM, load_canonical
from .model import FoldModel, early_features, mixture_quantiles, K

POLICY_PATH = "config/risk_policy.json"


def load_policy(path=POLICY_PATH): return json.load(open(path))


class Engine:
    def __init__(self, ds, policy=None, train_ds=None):
        self.ds, self.policy = ds, policy or load_policy()
        self.seed = self.policy["seed"]; g = self.policy["gate"]
        inf = ds.inference.reset_index(drop=True); self.inf = inf; N = self.N = len(inf)
        self.ids = inf.device_id.tolist(); self.idx = {d: i for i, d in enumerate(self.ids)}
        F = self.F = early_features(inf)
        rng = np.random.RandomState(self.seed)
        # ---- models (cross-fitted for canonical; canonical-fit for uploads) ----
        if ds.has_evaluation:
            ev = ds.evaluation_view().df
            tr = (ds, F); fold_of = np.zeros(N, int); perm = rng.permutation(N); fold_of[perm] = np.arange(N) % 5
            self.val_idx = np.sort(np.random.RandomState(self.seed + 1).permutation(N)[:150])
            models = []
            z96 = np.log(ev.v96.values) - F["lv24"]; z168 = np.log(ev.v168.values) - F["lv24"]; cls = ev.cls.values
            for f in range(5):
                m = fold_of != f
                models.append(FoldModel().fit({k: v[m] for k, v in F.items()}, cls[m], z96[m], z168[m]))
            self.models = models; self.fold_of = fold_of
            self.model_note = "5-fold cross-fitted: no device is scored by a model trained on it"
        else:
            base, bF = train_ds
            ev = base.evaluation_view().df; z96 = np.log(ev.v96.values) - bF["lv24"]; z168 = np.log(ev.v168.values) - bF["lv24"]
            models = [FoldModel().fit(bF, ev.cls.values, z96, z168)]; self.models = models; self.fold_of = np.zeros(N, int)
            self.val_idx = np.array([], int)
            self.model_note = "model fit on canonical SIH26170 benchmark, applied to uploaded data"
        fo = self.fold_of
        self.P0 = np.vstack([models[f].prior({k: v[i:i + 1] for k, v in F.items()}) for i, f in enumerate(fo)]) if False else self._prior_all()
        self.w96 = np.stack([models[f].w96 for f in fo]); self.s96 = np.stack([models[f].s96 for f in fo])
        self.w168a = np.stack([models[f].w168a for f in fo]); self.s168a = np.stack([models[f].s168a for f in fo])
        self.w168b = np.stack([models[f].w168b for f in fo]); self.s168b = np.stack([models[f].s168b for f in fo])
        # ---- lot intelligence ----
        self._lot_stats()
        # ---- OOD reference (unlabelled early features of the canonical benchmark) ----
        refF = F if ds.has_evaluation else train_ds[1]
        R = refF["X"][:, :3]; self.ood_mu = R.mean(0); self.ood_ic = np.linalg.inv(np.cov(R.T))
        d2 = self._maha(R); self.ood_thr = float(np.quantile(d2, g["ood_mahalanobis_quantile"]))
        self.ood_range = (float(np.exp(refF["lv0"].min()) * 0.5), float(np.exp(refF["lv24"].max()) * 1.5))
        self.ood_early = (self._maha(F["X"][:, :3]) > self.ood_thr) | (inf.v24.values > self.ood_range[1]) | (inf.v0.values < self.ood_range[0] * 0.2) \
            | (inf.temperature_c.values != 125.0)
        # ---- early predictive quantities ----
        mu = F["lv24"][:, None] + F["d24"][:, None] * self.w168a[:, :, 1] + self.w168a[:, :, 0]
        q = mixture_quantiles(self.P0, mu, self.s168a)
        self.q0 = np.exp(F["lv24"][:, None] + (q - F["lv24"][:, None]))  # q already absolute log-values
        # ---- NEXTPROBE grid (early information only) ----
        m96 = self.w96[:, :, 0] + F["d24"][:, None] * self.w96[:, :, 1]
        self.Pg, self.Wg = E.build_grid(self.P0, m96, self.s96)
        self.p0 = self.P0[:, ANOM].sum(1)
        self.th = self._calibrate_gate()
        self.reset()

    # ---------- helpers ----------
    def _prior_all(self):
        P = np.zeros((self.N, K))
        for f, m in enumerate(self.models):
            s = self.fold_of == f
            if s.any(): P[s] = m.prior({k: v[s] for k, v in self.F.items()})
        return P

    def _maha(self, X):
        d = X - self.ood_mu; return np.einsum("ij,jk,ik->i", d, self.ood_ic, d)

    def _lot_stats(self):
        g = self.policy["gate"]; inf, F = self.inf, self.F; self.lots = {}
        self.lot_pct = np.zeros(self.N)
        for l in sorted(inf.lot_id.unique()):
            m = (inf.lot_id == l).values
            zd = F["zd"][m]; contam = float((zd > 3.5).mean())
            st = "TRUSTED" if contam < g["lot_contamination_caution"] else ("CAUTION" if contam < g["lot_contamination_untrusted"] else "UNTRUSTED")
            if m.sum() < 10 and st == "TRUSTED": st = "CAUTION"
            med_d, med_l = float(np.median(F["d24"][m])), float(np.median(F["lv24"][m]))
            self.lots[l] = dict(lot_id=l, n_devices=int(m.sum()), median_v24=float(np.exp(med_l)),
                mad_v24_log=float(1.4826 * np.median(np.abs(F["lv24"][m] - med_l))), median_drift_log=med_d,
                mad_drift_log=float(1.4826 * np.median(np.abs(F["d24"][m] - med_d))), contamination=contam, baseline_status=st)
            self.lot_pct[m] = pd.Series(F["lv24"][m]).rank(pct=True).values * 100
        self.lot_status = np.array([self.lots[l]["baseline_status"] for l in inf.lot_id])

    # ---------- posterior after a 96h observation ----------
    def post_state(self, idx, z96):
        idx = np.atleast_1d(idx); z96 = np.atleast_1d(z96).astype(float); d = self.F["d24"][idx]
        m96 = self.w96[idx, :, 0] + d[:, None] * self.w96[idx, :, 1]
        lp = np.log(self.P0[idx]) - 0.5 * ((z96[:, None] - m96) / self.s96[idx]) ** 2 - np.log(self.s96[idx])
        lp -= lp.max(1, keepdims=True); P = np.exp(lp); P /= P.sum(1, keepdims=True)
        ood = (np.abs(z96[:, None] - m96) / self.s96[idx]).min(1) > self.policy["gate"]["ood_sigma"]
        mu = self.F["lv24"][idx][:, None] + self.w168b[idx, :, 0] + d[:, None] * self.w168b[idx, :, 1] + z96[:, None] * self.w168b[idx, :, 2]
        q = np.exp(mixture_quantiles(P, mu, self.s168b[idx]))
        return P, P[:, ANOM].sum(1), q, ood

    # ---------- gate ----------
    def _gate_input(self, P_anom, q, ood, i, stage, v96=None):
        mo = max(self.inf.v0[i], self.inf.v24[i], v96 or 0)
        return G.GateInput(float(P_anom), self.lot_status[i], bool(ood), True, float(q[0]), float(q[1]), float(q[2]),
                           float(self.inf.limit[i]), float(mo), stage)

    def _calibrate_gate(self):
        pol = self.policy; fn, fp = pol["false_negative_cost"], pol["false_positive_cost"]; tstar = fp / (fp + fn); g = pol["gate"]
        rel = {"early": tstar * 0.25, "revealed": tstar * 0.25}
        if self.ds.has_evaluation and len(self.val_idx):
            ev = self.ds.evaluation_view().df; v = self.val_idx; lab = ev.label.values[v]
            pe = self.p0[v]
            _, pp, _, _ = self.post_state(v, np.log(ev.v96.values[v]) - self.F["lv24"][v])   # offline validation replay for calibration only
            for st, p in (("early", pe), ("revealed", pp)):
                best = 0.0
                for r in np.unique(np.concatenate([[0], p[p <= tstar]])):
                    m = p <= r
                    if m.sum() and lab[m].mean() <= g["target_release_escape_rate"]: best = float(r)
                rel[st] = min(best, tstar)
        return G.GateThresholds(release_p=rel, hold_p=g["hold_probability"], max_rel_interval_width=g["max_rel_interval_width"],
                                calibration=g["calibration"])

    def gate_thresholds(self):
        return {"release_p": self.th.release_p, "hold_p": self.th.hold_p, "max_rel_interval_width": self.th.max_rel_interval_width,
                "calibration": self.th.calibration, "n_calibration_devices": int(len(self.val_idx))}

    # ---------- session state ----------
    def reset(self):
        self.cur_P = self.P0.copy(); self.cur_p = self.p0.copy(); self.cur_q = self.q0.copy(); self.cur_ood = self.ood_early.copy()
        self.stage = np.array(["early"] * self.N, dtype=object); self.v96 = {}
        self.pending = []; self.rounds = []; self.events = []; self.gate_cache = {}; self.early_gate = {}
        self.log("dataset_loaded", None, {"dataset": self.ds.name, "version": self.ds.version_hash})

    def log(self, typ, ids, payload=None): self.events.append({"seq": len(self.events), "type": typ, "device_ids": ids, "payload": payload or {}})

    def gate(self, i):
        if i not in self.gate_cache:
            v = self.v96.get(self.ids[i]); st = self.stage[i]
            gi = self._gate_input(self.cur_p[i], self.cur_q[i], self.cur_ood[i], i, st, v)
            self.gate_cache[i] = G.evaluate(gi, self.th)
        return self.gate_cache[i]

    def early_disposition(self, i):
        if i not in self.early_gate:
            self.early_gate[i] = G.evaluate(self._gate_input(self.p0[i], self.q0[i], self.ood_early[i], i, "early"), self.th)
        return self.early_gate[i]

    # ---------- NEXTPROBE ----------
    def costs(self): p = self.policy; return p["false_negative_cost"], p["false_positive_cost"], p["probe_cost"]

    def eligible(self):
        e = np.array([s == "early" for s in self.stage]) & ~np.array([self.ids[i] in set(self.pending) for i in range(self.N)])
        return e if self.ds.replay.has_replay() else np.zeros(self.N, bool)

    def anomaly_score(self): return np.maximum(self.F["zd"], self.F["zl"])   # unsupervised, lot-relative

    def rank(self, policy, budget, seed=None):
        fn, fp, pc = self.costs(); el = self.eligible()
        r_now, r_post, ev = E.evoi(self.cur_p, self.Pg, self.Wg, fn, fp, pc)
        if policy == "NEXTPROBE_EVOI": score = np.where(el, ev, -np.inf)
        elif policy == "HIGHEST_ANOMALY": score = np.where(el, self.anomaly_score(), -np.inf)
        elif policy == "HIGHEST_PREDICTED_RISK": score = np.where(el, self.cur_p, -np.inf)
        elif policy == "RANDOM":
            score = np.where(el, np.random.RandomState((seed if seed is not None else self.seed) + budget).rand(self.N), -np.inf)
        else: raise ValueError(policy)
        order = np.argsort(-score, kind="stable")
        sel = [int(i) for i in order[:budget] if np.isfinite(score[i]) and (policy != "NEXTPROBE_EVOI" or ev[i] > 0)]
        rows = [self.nextprobe_row(int(i), rk + 1, r_now, r_post, ev, i in set(sel)) for rk, i in enumerate(order[:max(budget * 2, 30)]) if np.isfinite(score[i])]
        return {"policy": policy, "budget": budget, "selected_ids": [self.ids[i] for i in sel], "selected_count": len(sel), "ranking": rows,
                "n_positive_evoi": int((ev[el] > 0).sum()), "costs": {"fn": fn, "fp": fp, "probe": pc, "policy_status": self.policy["policy_status"]}}

    def nextprobe_row(self, i, rank, r_now, r_post, ev, selected):
        top = np.argsort(-self.cur_P[i])[:2]
        return {"rank": rank, "device_id": self.ids[i], "lot_id": self.inf.lot_id[i], "selected": bool(selected),
                "current_decision": "ESCALATE" if self.cur_p[i] >= self.tstar() else "ACCEPT",
                "p_anomaly": float(self.cur_p[i]), "risk_now": float(r_now[i]), "expected_risk_after_96h": float(r_post[i]),
                "expected_risk_reduction": float(r_now[i] - r_post[i]), "evoi": float(ev[i]),
                "main_uncertainty": f"{CLASSES[top[0]]} vs {CLASSES[top[1]]}",
                "reason_code": "EVOI_POSITIVE_96H_DISCRIMINATES_HYPOTHESES" if ev[i] > 0 else "EVOI_NON_POSITIVE"}

    def tstar(self): fn, fp, _ = self.costs(); return fp / (fp + fn)

    def allocate(self, budget):
        if not self.ds.replay.has_replay(): raise PermissionError("ANALYSIS-ONLY MODE: dataset has no 96h replay")
        if self.pending: raise RuntimeError("an allocation is already pending reveal")
        r = self.rank("NEXTPROBE_EVOI", budget)
        self.pending = list(r["selected_ids"])
        self.rounds.append({"round": len(self.rounds) + 1, "budget": budget, "allocated": list(self.pending), "revealed": False})
        self.log("nextprobe_ranked", list(self.pending), {"budget": budget, "policy": "NEXTPROBE_EVOI"})
        self.log("probe_allocated", list(self.pending), {"budget": budget})
        return {"budget": budget, "allocated_ids": list(self.pending), "allocated_count": len(self.pending)}

    def reveal(self, ids=None):
        ids = list(self.pending) if ids is None else ids
        bad = [d for d in ids if d not in self.pending]
        if bad:
            raise KeyError(f"not allocated or already revealed: {bad[:5]}")
        out = []
        for d in ids:
            i = self.idx[d]; y = float(self.ds.replay.get(d)); self.v96[d] = y
            P, p, q, ood = self.post_state(i, np.log(y) - self.F["lv24"][i])
            before = self.gate(i)["disposition"]; p_before = float(self.cur_p[i])
            self.cur_P[i], self.cur_p[i], self.cur_q[i], self.cur_ood[i] = P[0], p[0], q[0], ood[0]
            self.stage[i] = "revealed"; self.gate_cache.pop(i, None)
            after = self.gate(i)["disposition"]
            out.append({"device_id": d, "v96": y, "p_before": p_before, "p_after": float(p[0]), "disposition_before": before, "disposition_after": after,
                        "changed": before != after})
            self.pending.remove(d)
        self.rounds[-1]["revealed"] = not self.pending
        self.log("96h_revealed", ids); self.log("analysis_updated", ids); self.log("gate_evaluated", ids)
        return out

    # ---------- device analysis (inference-safe) ----------
    def analysis(self, d):
        i = self.idx[d]; fn, fp, pc = self.costs(); revealed = self.stage[i] == "revealed"
        r_now, r_post, ev = E.evoi(self.cur_p[i:i + 1], self.Pg[i:i + 1], self.Wg[i:i + 1], fn, fp, pc)
        gres = self.gate(i); F = self.F; v0, v24 = float(self.inf.v0[i]), float(self.inf.v24[i]); lim = float(self.inf.limit[i])
        obs = {"0h": v0, "24h": v24, "96h": self.v96.get(d) if revealed else None, "96h_status": "OBSERVED" if revealed else "HIDDEN"}
        ev_stack = [
            {"key": "absolute_spec", "status": "pass" if max(v0, v24, obs["96h"] or 0) < lim else "fail", "text": f"absolute limit {'satisfied' if max(v0, v24) < lim else 'exceeded'}"},
            {"key": "lot_relative", "status": "warn" if F["zl"][i] > 3 else "pass", "text": f"lot-relative level robust z = {F['zl'][i]:.2f}"},
            {"key": "temporal_drift", "status": "warn" if F["zd"][i] > 3 else "pass", "text": f"0h->24h drift robust z = {F['zd'][i]:.2f} (lot-relative)"},
            {"key": "forecast_uncertainty", "status": "warn" if (self.cur_q[i][2] - self.cur_q[i][0]) / self.cur_q[i][1] > self.th.max_rel_interval_width else "pass",
             "text": f"168h 90% interval {self.cur_q[i][0]:.2f}-{self.cur_q[i][2]:.2f} uA"},
            {"key": "ood", "status": "fail" if self.cur_ood[i] else "pass", "text": "outside reliable model domain" if self.cur_ood[i] else "OOD check passed"},
            {"key": "release_gate", "status": "pass" if gres["disposition"] == "RELEASE" else "fail", "text": f"gate disposition {gres['disposition']}"}]
        nx = None
        if not revealed:
            nx = {"evoi": float(ev[0]), "risk_now": float(r_now[0]), "expected_risk_after_96h": float(r_post[0]),
                  "expected_risk_reduction": float(r_now[0] - r_post[0]), "probe_cost": pc, "allocated": d in self.pending,
                  "replay_available": self.ds.replay.has_replay()}
        return {"device_id": d, "lot_id": self.inf.lot_id[i], "slot": self.inf.slot[i], "temperature_c": float(self.inf.temperature_c[i]),
                "parameter": "Leakage Current (uA)", "stage": self.stage[i], "observations": obs,
                "absolute_spec": {"limit": lim, "status": "PASS" if max(v0, v24, obs["96h"] or 0) < lim else "FAIL"},
                "lot_position": {"percentile_24h": float(self.lot_pct[i]), "mad_z_level": float(F["zl"][i]), "mad_z_drift": float(F["zd"][i])},
                "fingerprint": {"log_drift_0_24h": float(F["d24"][i]), "slope_uA_per_h_0_24h": (v24 - v0) / 24.0},
                "prediction": {"median_168h": float(self.cur_q[i][1]), "lower": float(self.cur_q[i][0]), "upper": float(self.cur_q[i][2]), "interval": 0.90,
                               "basis": "0h+24h+96h" if revealed else "0h+24h"},
                "hypotheses": {CLASSES[k]: float(self.cur_P[i][k]) for k in range(K)}, "p_anomaly": float(self.cur_p[i]),
                "ood": bool(self.cur_ood[i]), "lot_baseline": self.lot_status[i],
                "nextprobe": nx, "gate": gres, "evidence_stack": ev_stack,
                "chart": {"observed": [{"t": 0, "v": v0}, {"t": 24, "v": v24}] + ([{"t": 96, "v": obs["96h"]}] if revealed else []),
                          "hidden_t": [] if revealed else [96], "predicted_168": {"median": float(self.cur_q[i][1]), "lo": float(self.cur_q[i][0]), "hi": float(self.cur_q[i][2])},
                          "limit": lim}}

    def device_rows(self):
        fn, fp, pc = self.costs(); r_now, r_post, ev = E.evoi(self.cur_p, self.Pg, self.Wg, fn, fp, pc)
        rows = []
        for i in range(self.N):
            g = self.gate(i)
            rows.append({"device_id": self.ids[i], "lot_id": self.inf.lot_id[i], "disposition": g["disposition"], "stage": self.stage[i],
                         "current_v24": float(self.inf.v24[i]), "delta_0_24h": float(self.inf.v24[i] - self.inf.v0[i]),
                         "lot_percentile": float(self.lot_pct[i]), "pred_168h": float(self.cur_q[i][1]), "pred_lo": float(self.cur_q[i][0]), "pred_hi": float(self.cur_q[i][2]),
                         "p_anomaly": float(self.cur_p[i]), "evoi": None if self.stage[i] == "revealed" else float(ev[i]),
                         "reason": g["reasons"][0]})
        return rows

    def summary(self):
        rows = self.device_rows(); c = pd.Series([r["disposition"] for r in rows]).value_counts().to_dict()
        return {"dataset": self.ds.name, "dataset_version": self.ds.version_hash, "n_devices": self.N, "n_lots": len(self.lots), "current_read": "24h" if not self.v96 else "24h + selected 96h",
                "counts": {k: int(c.get(k, 0)) for k in ["RELEASE", "CONTINUE", "HOLD", "UNKNOWN"]}, "n_revealed": len(self.v96), "n_pending": len(self.pending),
                "model_version": self.policy["model_version"], "policy_version": self.policy["policy_version"], "policy_status": self.policy["policy_status"],
                "seed": self.seed, "replay_available": self.ds.replay.has_replay(), "mode": "SEQUENTIAL" if self.ds.replay.has_replay() else "ANALYSIS-ONLY",
                "validation": self.ds.validation, "budgets": self.policy["budgets"], "banner": "SIMULATED DATA", "model_note": self.model_note}

    # ---------- passport ----------
    def passport(self, d):
        i = self.idx[d]; a = self.analysis(d); chain = []; prev = "0" * 64
        def add(typ, payload):
            nonlocal prev
            body = json.dumps({"type": typ, "payload": payload}, sort_keys=True, default=str)
            cur = hashlib.sha256((prev + body).encode()).hexdigest(); chain.append({"seq": len(chain), "type": typ, "payload": payload, "prev_hash": prev, "hash": cur}); prev = cur
        add("observed_0h", {"v": float(self.inf.v0[i])}); add("observed_24h", {"v": float(self.inf.v24[i])})
        e = self.early_disposition(i)
        add("analysis_early", {"p_anomaly": float(self.p0[i]), "pred_168h_median": float(self.q0[i][1])}); add("gate_early", {"disposition": e["disposition"], "reasons": e["reasons"]})
        for ev in self.events:
            if ev["device_ids"] and d in ev["device_ids"]:
                pl = dict(ev["payload"]);
                if ev["type"] == "96h_revealed": pl["v96"] = self.v96.get(d)
                add(ev["type"], pl)
        add("gate_current", {"disposition": a["gate"]["disposition"], "criteria": [(c["key"], c["ok"]) for c in a["gate"]["criteria"]]})
        return {"device_id": d, "lot_id": a["lot_id"], "slot": a["slot"], "dataset": self.ds.name, "dataset_version": self.ds.version_hash, "seed": self.seed,
                "model_version": self.policy["model_version"], "policy_version": self.policy["policy_version"], "policy_status": self.policy["policy_status"],
                "observations": a["observations"], "analysis": a, "events": chain, "head_hash": prev, "banner": "SIMULATED DATA"}
