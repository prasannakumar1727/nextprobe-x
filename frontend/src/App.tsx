import { useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, post, useApi } from "./api";
import { Chart } from "./Chart";

const f = (x: number | null | undefined, d = 3) => (x === null || x === undefined ? "-" : x.toFixed(d));
const Err = ({ e }: { e: string | null }) => (e ? <div className="err"><strong>Unable to complete this request.</strong><details><summary>Technical details</summary><div>{e}</div></details></div> : null);
function FriendlyError({ message, detail }: { message: string; detail?: string | null }) {
  return <div className="panel error-state"><strong>{message}</strong>{detail && <details><summary>Technical details</summary><div>{detail}</div></details>}</div>;
}
const statusMeta: Record<string, { label: string; tone: string }> = {
  RELEASE: { label: "Release", tone: "release" },
  CONTINUE: { label: "Review", tone: "review" },
  HOLD: { label: "Hold", tone: "hold" },
  UNKNOWN: { label: "Unknown", tone: "unknown" },
  NORMAL: { label: "Normal", tone: "normal" },
  "QA ESCALATION": { label: "QA Escalation", tone: "qa" },
};

const criterionLabels: Record<string, string> = {
  data_quality: "Data quality",
  ood: "Model domain",
  absolute_spec: "Absolute specification",
  lot_baseline: "Lot baseline",
  calibrated_risk: "Calibrated risk",
  uncertainty: "Prediction uncertainty",
};

function humanReason(reason?: string) {
  if (!reason) return "No additional reason provided";
  return reason
    .replace("RELEASE_CRITERIA_NOT_MET", "Release criteria not satisfied")
    .replace("OOD_OR_INVALID_DATA", "Data requires manual review")
    .replace("HIGH_CALIBRATED_ANOMALY_RISK", "Calibrated anomaly risk is high")
    .replace("ABSOLUTE_LIMIT_EXCEEDED", "Absolute specification limit exceeded")
    .split("_").join(" ")
    .split(",").join(", ");
}

function StatusBadge({ value }: { value?: string | null }) {
  const key = (value ?? "UNKNOWN").toUpperCase();
  const meta = statusMeta[key] ?? { label: key, tone: "unknown" };
  return <span className={`status-badge ${meta.tone}`}>{meta.label}</span>;
}

function EventResult({ event }: { event: any }) {
  const payload = event.payload ?? {};
  if (event.type === "observed_0h" || event.type === "observed_24h") {
    return <span>Leakage current <strong>{f(payload.v, 3)} uA</strong></span>;
  }
  if (event.type === "analysis_early") {
    return <span>Anomaly probability <strong>{f(payload.p_anomaly * 100, 2)}%</strong> · 168h median <strong>{f(payload.pred_168h_median, 3)} uA</strong></span>;
  }
  if (event.type === "gate_early" || event.type === "gate_current") {
    const criteria = Array.isArray(payload.criteria) ? payload.criteria : [];
    const passed = criteria.filter((criterion: any) => criterion[1]).length;
    return <span><StatusBadge value={payload.disposition} />{criteria.length > 0 && <span className="result-detail"> {passed}/{criteria.length} criteria passed</span>}{payload.reasons?.length > 0 && <span className="result-detail"> · {humanReason(payload.reasons[0])}</span>}</span>;
  }
  if (event.type === "96h_revealed") {
    return <span>96h measurement <strong>{f(payload.v96, 3)} uA</strong></span>;
  }
  if (event.type === "nextprobe_ranked" || event.type === "probe_allocated") {
    return <span>{payload.budget ? `96h screening budget: ${payload.budget}` : "NEXTPROBE allocation recorded"}{payload.policy && <span className="result-detail"> · {payload.policy}</span>}</span>;
  }
  if (event.type === "analysis_updated") return <span>Posterior updated with 96h evidence</span>;
  if (event.type === "gate_evaluated") return <span>Current safety gate evaluated</span>;
  if (event.type === "dataset_loaded") return <span>Dataset: <strong>{payload.dataset ?? "-"}</strong></span>;
  return <span>{Object.keys(payload).length ? JSON.stringify(payload) : "Recorded"}</span>;
}

function eventActionLabel(type: string) {
  const labels: Record<string, string> = {
    observed_0h: "Record initial measurement",
    observed_24h: "Record early measurement",
    analysis_early: "Compute early inference",
    gate_early: "Evaluate early gate",
    nextprobe_ranked: "Rank next measurements",
    probe_allocated: "Allocate 96h screening",
    "96h_revealed": "Reveal 96h result",
    analysis_updated: "Update posterior",
    gate_evaluated: "Evaluate current gate",
    gate_current: "Record current gate",
    dataset_loaded: "Load dataset",
  };
  return labels[type] ?? type.split("_").join(" ");
}

function eventContextLabel(type: string) {
  const labels: Record<string, string> = {
    observed_0h: "Initial measurement",
    observed_24h: "24h measurement",
    analysis_early: "Early trajectory analysis",
    gate_early: "Early safety gate",
    nextprobe_ranked: "Next measurement selection",
    probe_allocated: "Additional measurement selected",
    "96h_revealed": "96h new evidence",
    analysis_updated: "Evidence updated",
    gate_evaluated: "Safety gate review",
    gate_current: "Current safety gate",
    dataset_loaded: "Dataset loaded",
  };
  return labels[type] ?? eventActionLabel(type);
}

function policyLabel(policy: string) {
  const labels: Record<string, string> = {
    RANDOM: "Random baseline",
    HIGHEST_ANOMALY: "Highest anomaly",
    HIGHEST_PREDICTED_RISK: "Highest predicted risk",
    NEXTPROBE_EVOI: "NEXTPROBE decision value",
  };
  return labels[policy] ?? policy;
}

export default function App() {
  const navigate = useNavigate();
  const [tick, setTick] = useState(0);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [importBusy, setImportBusy] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const importInputRef = useRef<HTMLInputElement>(null);
  const refresh = () => setTick((t) => t + 1);
  const state = useApi("/state", [tick]);
  const hero = useApi(state.data?.loaded ? "/devices?limit=1&sort=evoi" : null, [tick, state.data?.loaded]);
  const openInvestigation = (id: string) => {
    setSelectedDeviceId(id);
    setDrawerOpen(false);
    navigate(`/investigate?device=${id}`);
  };

  useEffect(() => {
    if (!selectedDeviceId && hero.data?.rows?.[0]?.device_id) {
      setSelectedDeviceId(hero.data.rows[0].device_id);
    }
  }, [hero.data, selectedDeviceId]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">NX</div>
          <div>
            <div className="brand-name">NEXTPROBE-X</div>
            <div className="brand-subtitle">Risk-Controlled Workbench</div>
          </div>
        </div>

        <nav className="nav-group" aria-label="Main navigation">
          <NavLink to="/screen" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            SCREEN
          </NavLink>
          <NavLink to="/investigate" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            INVESTIGATE
          </NavLink>
          <NavLink to="/nextprobe" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            NEXTPROBE
          </NavLink>
          <NavLink to="/decision" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            DECISION
          </NavLink>
          <NavLink to={selectedDeviceId ? `/passport/${selectedDeviceId}` : "/"} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            PASSPORT
          </NavLink>
        </nav>

        <div className="sidebar-panel">
          <div className="eyebrow">SIMULATED DATA</div>
          <div className="sidebar-status">Connected / Demo mode</div>
          <div className="sidebar-row">
            <span>Dataset scope</span>
            <strong>Multi-lot</strong>
          </div>
          <div className="sidebar-row">
            <span>Screening mode</span>
            <strong>SEQUENTIAL</strong>
          </div>
          <Link className="secondary-nav-link" to="/validation">Validation results</Link>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <div className="topbar-title">NEXTPROBE-X</div>
            <div className="topbar-subtitle">Risk-controlled sequential screening</div>
          </div>
          <div className="topbar-meta">
            <div className="meta-field"><span>Dataset</span><strong>SIMULATED ENGINEERING BENCHMARK</strong></div>
            <div className="meta-field"><span>Mode</span><strong>SIMULATION</strong></div>
            <div className="meta-field"><span>Data quality</span><strong>VALIDATED</strong></div>
            <input
              ref={importInputRef}
              className="visually-hidden"
              type="file"
              accept=".csv,text/csv"
              onChange={async (event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (!file) return;
                setImportBusy(true);
                setImportError(null);
                try {
                  const form = new FormData();
                  form.append("file", file);
                  const result = await api("/dataset/upload", { method: "POST", body: form });
                  if (!result.loaded) {
                    throw new Error("The CSV was rejected. Review the validation details on the workspace.");
                  }
                  refresh();
                } catch (error: any) {
                  setImportError(error.message ?? "Import failed");
                } finally {
                  setImportBusy(false);
                }
              }}
            />
            <button
              className="button-primary compact-button"
              disabled={importBusy}
              onClick={() => importInputRef.current?.click()}
            >
              {importBusy ? "IMPORTING…" : "+ IMPORT DATA"}
            </button>
          </div>
          {importError && <div className="topbar-import-error"><Err e={importError} /></div>}
        </header>

        <main className="page-shell">
          <Err e={state.error} />
          {!state.data?.loaded ? (
            <LoadPanel onLoaded={refresh} />
          ) : (
            <Routes>
              <Route path="/" element={<OverviewPage refresh={refresh} onOpenDevice={openInvestigation} />} />
              <Route path="/screen" element={<OverviewPage refresh={refresh} onOpenDevice={openInvestigation} />} />
              <Route path="/investigate" element={<InvestigationPage fallbackDevice={selectedDeviceId ?? hero.data?.rows?.[0]?.device_id ?? "C0001"} />} />
              <Route path="/lot/:lotId" element={<LotPage />} />
              <Route path="/device/:deviceId" element={<DevicePage tick={tick} />} />
              <Route path="/nextprobe" element={<NextProbePage tick={tick} refresh={refresh} deviceId={selectedDeviceId ?? hero.data?.rows?.[0]?.device_id ?? "C0001"} onOpenDevice={(id) => { setSelectedDeviceId(id); setDrawerOpen(false); navigate(`/investigate?device=${id}`); }} />} />
              <Route path="/decision" element={<DecisionPage tick={tick} deviceId={selectedDeviceId ?? hero.data?.rows?.[0]?.device_id ?? "C0001"} />} />
              <Route path="/passport/:deviceId" element={<PassportPage tick={tick} />} />
              <Route path="/validation" element={<EvaluationPage tick={tick} />} />
              <Route path="/evaluation" element={<EvaluationPage tick={tick} />} />
            </Routes>
          )}
        </main>
      </div>

      {selectedDeviceId && (
        <DeviceDrawer
          deviceId={selectedDeviceId}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        />
      )}
    </div>
  );
}

function LoadPanel({ onLoaded }: { onLoaded: () => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  return (
    <div className="load-panel panel">
      <div className="page-header-row">
        <div>
          <div className="eyebrow">DATASET LOAD</div>
          <h1>Load engineering benchmark</h1>
        </div>
        <div className="sim-badge">SIMULATED DATA</div>
      </div>

      <p className="lead">
        Canonical prototype dataset: SIH26170 synthetic burn-in benchmark. This workflow is evaluated on the supplied benchmark and does not constitute production validation.
      </p>

      <div className="cta-row">
        <button disabled={busy} className="button-primary" onClick={async () => {
          setBusy(true);
          setErr(null);
          try { await post("/dataset/load"); onLoaded(); }
          catch (e: any) { setErr(e.message); }
          finally { setBusy(false); }
        }}>
          {busy ? "Loading…" : "Load canonical dataset"}
        </button>
      </div>

      <Err e={err} />
      <Upload onLoaded={onLoaded} />
    </div>
  );
}

function Upload({ onLoaded }: { onLoaded: () => void }) {
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  return (
    <div className="upload-panel">
      <h3>Load CSV</h3>
      <input
        type="file"
        accept=".csv"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          setErr(null);
          const fd = new FormData();
          fd.append("file", file);
          try {
            const r = await api("/dataset/upload", { method: "POST", body: fd });
            setRes(r);
            if (r.loaded) onLoaded();
          } catch (x: any) {
            setErr(x.message);
          }
        }}
      />

      <Err e={err} />

      {res && (
        <div className="validation-box">
          <div className="validation-title">Validation status: {res.validation.status}</div>
          {res.validation.replay_96h === false && <div className="validation-meta">Analysis-only mode: replay data unavailable</div>}
          <ul>
            {res.validation.issues?.map((issue: string) => <li key={issue}>{issue}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function OverviewPage({ refresh, onOpenDevice }: { refresh: () => void; onOpenDevice: (id: string) => void }) {
  const state = useApi("/state");
  const queue = useApi("/devices?limit=1000&sort=evoi", [state.data?.summary?.n_revealed]);
  const lots = useApi("/lots", [state.data?.summary?.n_revealed]);
  const summary = state.data?.summary;
  const rows = queue.data?.rows ?? [];

  const metrics = useMemo(() => [
    ["Devices screened", summary?.n_devices ?? 0],
    ["Require review", (summary?.counts?.CONTINUE ?? 0) + (summary?.counts?.UNKNOWN ?? 0) + (summary?.counts?.HOLD ?? 0)],
    ["Additional tests recommended", rows.filter((row: any) => row.evoi !== null && row.evoi > 0).length],
    ["Screening completion", `${summary?.n_devices ? Math.round(((summary?.n_revealed ?? 0) / summary.n_devices) * 100) : 0}%`],
  ], [summary, rows]);

  return (
    <>
      <div className="page-header-row">
        <div>
          <div className="eyebrow">SCREEN</div>
          <h1>Identify trajectory-abnormal devices before endpoint failure.</h1>
        </div>
        <button className="button-secondary" onClick={async () => { await post("/session/reset"); refresh(); }}>Reset session</button>
      </div>

      <p className="lead">Instead of testing every device equally, NEXTPROBE identifies where an additional measurement has the highest expected decision value.</p>

      <div className="metrics-grid">
        {metrics.map(([label, value]) => (
          <div className="metric-card" key={label}>
            <div className="metric-label">{label}</div>
            <div className="metric-value">{value}</div>
          </div>
        ))}
      </div>

      <div className="content-grid">
        <section className="panel">
          <div className="section-header">
            <h3>Lot context</h3>
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Lot ID</th>
                <th>Devices</th>
                <th>Median</th>
                <th>MAD</th>
                <th>Baseline</th>
              </tr>
            </thead>
            <tbody>
              {lots.data?.map((lot: any) => (
                <tr key={lot.lot_id}>
                  <td><Link to={`/lot/${lot.lot_id}`}>{lot.lot_id}</Link></td>
                  <td>{lot.n_devices}</td>
                  <td>{f(lot.median_v24, 2)}</td>
                  <td>{f(lot.mad_v24_log, 3)}</td>
                  <td>{lot.baseline_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel panel-large">
          <div className="section-header">
            <h3>Screening queue</h3>
            <Link to="/investigate">Open investigation</Link>
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Device</th>
                <th>Lot</th>
                <th>Current</th>
                <th>24h Δ</th>
                <th>Trajectory</th>
                <th>Gate</th>
                <th>Next action</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 8).map((row: any) => (
                <tr key={row.device_id} onClick={() => onOpenDevice(row.device_id)} className="clickable-row">
                  <td>{row.device_id}</td>
                  <td>{row.lot_id}</td>
                  <td>{f(row.current_v24, 3)} uA</td>
                  <td>{row.delta_0_24h >= 0 ? "+" : ""}{f(row.delta_0_24h, 3)} uA</td>
                  <td><span className={row.lot_percentile >= 95 ? "trajectory-flag" : "trajectory-normal"}>{row.lot_percentile >= 95 ? "Abnormal trajectory" : "Within lot baseline"}</span></td>
                  <td><StatusBadge value={row.disposition} /></td>
                  <td>{row.evoi !== null && row.evoi > 0 ? "96h probe" : row.disposition === "HOLD" ? "Hold for review" : "Continue screening"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <div className="action-strip">
        <button className="button-primary" onClick={() => onOpenDevice(rows[0]?.device_id ?? "C0001")}>Review priority device</button>
        <Link className="button-secondary" to="/nextprobe">Open NEXTPROBE</Link>
      </div>
    </>
  );
}

function LotPage() {
  const { lotId } = useParams();
  const { data, error } = useApi(`/lots/${lotId}`);
  const nav = useNavigate();

  if (error) return <Err e={error} />;
  if (!data) return <div className="panel">Loading lot analysis…</div>;

  return (
    <>
      <div className="page-header-row">
        <div>
          <div className="eyebrow">LOT ANALYSIS</div>
          <h1>{data.lot_id}</h1>
        </div>
      </div>

      <div className="metrics-grid compact-grid">
        {[
          ["Devices", data.n_devices],
          ["Median", f(data.median_v24, 2)],
          ["MAD", f(data.mad_v24_log, 4)],
          ["Contamination", f(data.contamination, 3)],
          ["Baseline", data.baseline_status],
        ].map(([label, value]) => (
          <div className="metric-card" key={String(label)}>
            <div className="metric-label">{label}</div>
            <div className="metric-value">{String(value)}</div>
          </div>
        ))}
      </div>

      <div className="panel">
        <Chart
          width={1100}
          height={280}
          xLabel="Lot percentile"
          yLabel="Drift z"
          xMax={100}
          hlines={[{ y: 3.5, label: "+3.5" }, { y: -3.5, label: "-3.5" }]}
          points={data.devices.map((p: any) => ({
            x: p.lot_percentile,
            y: p.drift_z,
            color: p.disposition === "HOLD" ? "#d64343" : p.disposition === "UNKNOWN" ? "#7d6ecf" : "#2d4a6b",
            onClick: () => nav(`/device/${p.device_id}`),
            title: p.device_id,
          }))}
        />
      </div>
    </>
  );
}

function DevicePage({ tick }: { tick: number }) {
  const { deviceId } = useParams();
  const activeDevice = deviceId ?? "C0001";
  return <InvestigationPage fallbackDevice={activeDevice} tick={tick} />;
}

function InvestigationPage({ fallbackDevice, tick }: { fallbackDevice: string; tick?: number }) {
  const { deviceId } = useParams();
  const [searchParams] = useSearchParams();
  const activeDevice = deviceId ?? searchParams.get("device") ?? fallbackDevice;
  const a = useApi(`/devices/${activeDevice}`, [activeDevice, tick]);
  const lot = useApi(a.data ? `/lots/${a.data.lot_id}` : null, [a.data?.lot_id]);

  if (a.error) return <FriendlyError message="This device investigation is unavailable." detail={a.error} />;
  if (!a.data) return <div className="panel loading-state">Loading device investigation…</div>;

  const A = a.data;
  const c = A.chart;
  const gauge = A.gate?.disposition ?? "UNKNOWN";
  const hypothesisValues = Object.values(A.hypotheses ?? {}) as number[];
  const slowDriftPct = (Number(hypothesisValues[0] ?? 0) * 100);
  const normalAgeingPct = (Number(hypothesisValues[1] ?? 0) * 100);

  return (
    <>
      <div className="page-header-row">
        <div>
          <div className="eyebrow">DEVICE INVESTIGATION</div>
          <h1>{A.device_id}</h1>
          <div className="header-submeta">Lot {A.lot_id} · Status <StatusBadge value={gauge} /></div>
        </div>
      </div>

      <div className="callout-box">
        The current value is {A.absolute_spec?.status === "PASS" ? "within the absolute specification limit" : "outside the absolute specification limit"}, while the lot-relative trajectory indicates {A.lot_position?.percentile_24h >= 95 ? "an abnormal position within the lot" : "a trajectory that needs continued observation"}.
      </div>

      <section className="evidence-band">
        <div><span className="eyebrow">CURRENT EVIDENCE</span><strong>0h {f(A.observations?.["0h"], 3)} uA</strong><strong>24h {f(A.observations?.["24h"], 3)} uA</strong><span>Current read</span></div>
        <div><span className="eyebrow">LOT CONTEXT</span><strong>{f(A.observations?.["24h"], 3)} uA</strong><span>Lot baseline {lot.data ? `${f(lot.data.median_v24, 3)} uA` : "-"}</span><span>Deviation {f(A.lot_position?.mad_z_level, 2)} robust z</span></div>
        <div><span className="eyebrow">SAFETY GATE</span><strong><StatusBadge value={gauge} /></strong><span>{A.observations?.["96h_status"] === "OBSERVED" ? "Updated with 96h evidence" : "Early evidence only"}</span></div>
      </section>

      <div className="content-grid investigation-grid">
        <section className="panel panel-large">
          <div className="section-header">
            <h3>Device trajectory</h3>
            <span className="muted">Time (hours)</span>
          </div>
          <Chart
            width={780}
            height={320}
            xLabel="Time (hours)"
            yLabel="Measured parameter (µA)"
            xMax={180}
            hlines={[{ y: c.limit, label: `Spec limit ${f(c.limit, 1)}` }, ...(lot.data ? [{ y: lot.data.median_v24, label: "Lot baseline" }] : [])]}
            line={c.observed.map((o: any) => ({ x: o.t, y: o.v }))}
            points={c.observed.map((o: any) => ({ x: o.t, y: o.v, color: "#141c2b" }))}
            pred={{ x: 168, lo: c.predicted_168.lo, mid: c.predicted_168.median, hi: c.predicted_168.hi }}
            hiddenX={c.hidden_t}
          />
        </section>

        <aside className="panel">
          <div className="section-header">
            <h3>What the system sees</h3>
          </div>
          <div className="evidence-stack">
            <div className="evidence-item">
              <div className="label">Lot relative behaviour</div>
              <div className="strong">98th percentile</div>
              <div className="meta">MAD score: {f(A.lot_position?.mad_z_level, 2)}</div>
            </div>
            <div className="evidence-item">
              <div className="label">Predicted 168h</div>
              <div className="strong">{f(A.prediction?.median_168h, 2)} µA</div>
              <div className="meta">Interval: {f(A.prediction?.lower, 2)} – {f(A.prediction?.upper, 2)} µA</div>
            </div>
            <div className="evidence-item">
              <div className="label">Evidence</div>
              <div className="strong">Conformal p-value: {f(A.gate?.p_value ?? A.p_anomaly, 3)}</div>
              <div className="meta">Slow drift: {f(slowDriftPct, 2)}% · Normal ageing: {f(normalAgeingPct, 2)}%</div>
            </div>
          </div>
        </aside>
      </div>

      <section className="panel explanation-panel">
        <div className="section-header">
          <h3>Why is this device flagged?</h3>
        </div>
          <p>{A.absolute_spec?.status === "PASS" ? "The current value remains inside the absolute specification limit, but the trajectory differs from the lot baseline." : "The current value exceeds the absolute specification limit."} {A.gate?.disposition === "RELEASE" ? "The safety gate criteria are currently satisfied." : "The current evidence is not sufficient for an automatic release."}</p>
      </section>

      <section className="decision-card panel">
        <div className="decision-label">Current decision</div>
        <div className="decision-status">{A.gate?.disposition === "CONTINUE" ? "REVIEW REQUIRED" : A.gate?.disposition}</div>
        <div className="decision-body">
          <div><strong>Reason</strong><span>{humanReason(A.gate?.reasons?.[0])}</span></div>
          <div><strong>Next action</strong><span>{A.nextprobe?.evoi > 0 ? "Evaluate the recommended additional measurement." : "Continue with the independent safety gate."}</span></div>
        </div>
        <div className="cta-row">
          {A.nextprobe?.evoi > 0 && <Link className="button-primary" to="/nextprobe">Find next best test</Link>}
          <Link className="button-secondary" to="/decision">View independent decision</Link>
        </div>
      </section>
    </>
  );
}

function NextProbePage({ tick, refresh, deviceId, onOpenDevice }: { tick: number; refresh: () => void; deviceId: string; onOpenDevice: (id: string) => void }) {
  const [budget, setBudget] = useState(25);
  const [rank, setRank] = useState<any>(null);
  const [alloc, setAlloc] = useState<any>(null);
  const [revealed, setRevealed] = useState<any[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);

  const status = useApi("/nextprobe/status", [tick, alloc, revealed]);
  const device = useApi(`/devices/${deviceId}`, [deviceId, tick, alloc, revealed]);
  const selected = device.data;
  const probe = selected?.nextprobe;

  const run = async (fn: () => Promise<void>) => {
    setErr(null);
    try { await fn(); }
    catch (e: any) { setErr(e.message); }
  };

  return (
    <>
      <div className="page-header-row">
        <div>
          <div className="eyebrow">NEXTPROBE</div>
          <h1>Choose the next measurement with the highest expected decision value.</h1>
        </div>
      </div>

      <div className="mini-grid">
        <div className="mini-card"><span>Selected device</span><strong>{selected?.device_id ?? deviceId}</strong></div>
        <div className="mini-card"><span>Current gate</span><strong>{selected?.gate?.disposition ?? "Loading"}</strong></div>
        <div className="mini-card"><span>Evidence state</span><strong>{selected?.stage === "revealed" ? "Updated" : "Insufficient"}</strong></div>
      </div>

      <section className="panel recommendation-panel">
        <div className="section-header">
          <h3>Recommended next test</h3>
        </div>
        <div className="recommendation-main">
          <div>
            <div className="eyebrow">96h MEASUREMENT</div>
            <h2>Expected decision value: {probe ? f(probe.evoi, 3) : "Unavailable"}</h2>
            <div className="recommendation-meta">Expected risk reduction: {probe ? f(probe.expected_risk_reduction, 3) : "-"} · Test cost: {probe ? f(probe.probe_cost, 2) : "-"}</div>
          </div>
        </div>
        <p className="lead small-lead">This measurement is selected by the backend because it is expected to provide the most useful additional evidence for resolving the current screening uncertainty.</p>
      </section>

      <div className="panel budget-panel">
        <div className="section-header">
          <h3>Budget</h3>
        </div>
        <div className="button-row inline-buttons">
          {[10, 25, 50, 100, 150].map((value) => (
            <button key={value} className={value === budget ? "button-primary" : "button-secondary"} onClick={() => { setBudget(value); setRank(null); }}>
              {value}
            </button>
          ))}
          <button className="button-primary" onClick={() => run(async () => setRank(await post("/nextprobe/rank", { budget })))}>Run NEXTPROBE</button>

        </div>
      </div>

      <Err e={err} />

      {rank && (
        <section className="panel">
          <div className="section-header">
            <h3>Test candidates</h3>
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Test</th>
                <th>Expected decision value</th>
                <th>Risk reduction</th>
                <th>Cost</th>
                <th>EVOI</th>
                <th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {rank.ranking.slice(0, 5).map((row: any) => (
                <tr key={row.device_id}>
                  <td>96h read</td>
                  <td>{f(row.evoi, 3)}</td>
                  <td>{f(row.expected_risk_reduction, 3)}</td>
                  <td>{f(rank.costs?.probe, 2)}</td>
                  <td>{f(row.evoi, 3)}</td>
                  <td>{row.selected ? "Selected" : "Candidate"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="panel">
        <div className="section-header">
          <h3>Current evidence path</h3>
        </div>
        {selected?.chart ? <Chart
          width={1080}
          height={250}
          xLabel="Time (hours)"
          yLabel="Leakage current (uA)"
          xMax={180}
          hlines={[{ y: selected.chart.limit, label: "Specification limit" }]}
          line={selected.chart.observed.map((point: any) => ({ x: point.t, y: point.v }))}
          points={selected.chart.observed.map((point: any) => ({ x: point.t, y: point.v, color: "#172133" }))}
          pred={{ x: 168, lo: selected.chart.predicted_168.lo, mid: selected.chart.predicted_168.median, hi: selected.chart.predicted_168.hi }}
          hiddenX={selected.chart.hidden_t}
        /> : <div className="empty-state">Select a device to view its evidence path.</div>}
        <div className="muted">Measured values are solid points. The forecast and uncertainty interval are generated from the current backend evidence state.</div>
      </section>

      <div className="action-strip narrow-strip">
        <button
          className="button-primary"
          disabled={!rank || !rank.selected_count || (status.data?.pending.length ?? 0) > 0}
          onClick={() => setConfirm(true)}
        >
          Allocate screening
        </button>
        {confirm && !alloc && (
          <button
            className="button-secondary"
            onClick={() => run(async () => {
              setAlloc(await post("/nextprobe/allocate", { budget }));
              setConfirm(false);
              refresh();
            })}
          >
            Confirm allocation
          </button>
        )}
        <button
          className="button-secondary"
          disabled={(status.data?.pending.length ?? 0) === 0}
          onClick={() => run(async () => {
            const r = await post("/nextprobe/reveal", {});
            setRevealed(r.revealed);
            setAlloc(null);
            setRank(null);
            refresh();
          })}
        >
          Reveal result
        </button>
      </div>

      {revealed && (
        <section className="panel">
          <div className="section-header">
            <h3>Updated decision</h3>
          </div>
          <table className="table compact-table">
            <thead>
              <tr>
                <th>Device</th>
                <th>96h value</th>
                <th>P before</th>
                <th>P after</th>
                <th>Gate before</th>
                <th>Gate after</th>
                <th>Changed</th>
              </tr>
            </thead>
            <tbody>
              {revealed.map((row: any) => (
                <tr key={row.device_id} onClick={() => onOpenDevice(row.device_id)} className="clickable-row">
                  <td>{row.device_id}</td>
                  <td>{f(row.v96, 3)}</td>
                  <td>{f(row.p_before, 4)}</td>
                  <td>{f(row.p_after, 4)}</td>
                  <td><StatusBadge value={row.disposition_before} /></td>
                  <td><StatusBadge value={row.disposition_after} /></td>
                  <td>{row.changed ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}

function DecisionPage({ tick, deviceId }: { tick: number; deviceId: string }) {
  const decision = useApi(`/devices/${deviceId}`, [deviceId, tick]);
  const data = decision.data;
  const gate = data?.gate;

  if (decision.error) return <FriendlyError message="The safety gate could not be loaded." detail={decision.error} />;
  if (!data || !gate) return <div className="panel loading-state">Loading independent safety gate…</div>;

  const nextAction = gate.disposition === "RELEASE"
    ? "Device may proceed under the release policy."
    : gate.disposition === "HOLD"
      ? "Hold the device for reliability review."
      : gate.disposition === "UNKNOWN"
        ? "Route to a reliability engineer for manual review."
        : "Continue screening or evaluate the recommended additional measurement.";

  return (
    <>
      <div className="page-header-row">
        <div>
          <div className="eyebrow">DECISION · INDEPENDENT SAFETY GATE</div>
          <h1>Can this device be released?</h1>
          <div className="header-submeta">{data.device_id} · Lot {data.lot_id}</div>
        </div>
        <StatusBadge value={gate.disposition} />
      </div>

      <section className={`gate-hero ${gate.disposition.toLowerCase()}`}>
        <div>
          <div className="eyebrow">GATE STATUS</div>
          <div className="gate-status">{gate.disposition === "CONTINUE" ? "REVIEW" : gate.disposition}</div>
          <p>{humanReason(gate.reasons?.[0])}</p>
        </div>
        <div className="gate-boundary">NEXTPROBE selected the additional measurement. The independent safety gate determines disposition.</div>
      </section>

      <section className="panel">
        <div className="section-header"><h3>Gate criteria</h3><span className="muted">Current evidence</span></div>
        <div className="criteria-list">
          {gate.criteria.map((criterion: any) => (
            <div className="criterion-row" key={criterion.key}>
              <span className={`criterion-icon ${criterion.ok ? "pass" : "fail"}`}>{criterion.ok ? "✓" : "!"}</span>
              <div><strong>{criterionLabels[criterion.key] ?? criterion.key}</strong><div className="muted">{criterion.text}</div></div>
              <span className={criterion.ok ? "criterion-state pass-text" : "criterion-state fail-text"}>{criterion.ok ? "Satisfied" : "Not satisfied"}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="decision-card panel">
        <div className="decision-label">NEXT APPROVED ACTION</div>
        <div className="decision-body"><div><strong>{nextAction}</strong><span>Disposition is determined by gate criteria, not by the NEXTPROBE selector.</span></div></div>
        <div className="cta-row">
          {data.stage !== "revealed" && <Link className="button-secondary" to="/nextprobe">Review NEXTPROBE</Link>}
          <Link className="button-primary" to={`/passport/${data.device_id}`}>Open screening passport</Link>
        </div>
      </section>
    </>
  );
}

function EvaluationPage({ tick }: { tick: number }) {
  const ev = useApi("/evaluation", [tick]);
  const se = useApi("/evaluation/sensitivity");
  const hero = useApi("/evaluation/hero", [tick]);
  const misses = useApi("/evaluation/misses", [tick]);

  if (ev.error) return <Err e={ev.error} />;
  if (!ev.data) return <div className="panel">Running evaluation…</div>;

  const E = ev.data;
  const palette: Record<string, string> = {
    RANDOM: "#8a97a6",
    HIGHEST_ANOMALY: "#d58a2d",
    HIGHEST_PREDICTED_RISK: "#7b62d1",
    NEXTPROBE_EVOI: "#2e7d7a",
  };

  return (
    <>
      <div className="page-header-row">
        <div>
          <div className="eyebrow">VALIDATION</div>
          <h1>Simulation validation</h1>
          <div className="header-submeta">Simulation results on the supplied engineering benchmark.</div>
        </div>
      </div>

      <div className="warning-banner panel">
        <strong>SIMULATED DATA</strong> · supplied engineering benchmark only · not production validation.
      </div>

      <div className="metrics-grid compact-grid">
        {[
          ["168h MAE", f(E.early.mae_168h_early, 3)],
          ["RMSE", f(E.early.rmse_168h_early, 3)],
          ["Interval coverage", f(E.early.coverage_90_early, 3)],
          ["PR-AUC", f(E.early.pr_auc_early, 3)],
        ].map(([label, value]) => (
          <div className="metric-card" key={String(label)}>
            <div className="metric-label">{label}</div>
            <div className="metric-value">{String(value)}</div>
          </div>
        ))}
      </div>

      <section className="panel">
        <div className="section-header">
          <h3>Screening performance</h3>
        </div>
        <table className="table compact-table">
          <thead>
            <tr>
              <th>Policy</th>
              <th>Decision loss</th>
              <th>FNR</th>
              <th>Early-miss recovery</th>
            </tr>
          </thead>
          <tbody>
            {E.policies.map((policy: string) => (
              <tr key={policy}>
                <td>{policyLabel(policy)}</td>
                <td>{f(E.sweep[policy]["50"].decision_loss, 2)}</td>
                <td>{f(E.sweep[policy]["50"].fnr, 3)}</td>
                <td>{f(E.sweep[policy]["50"].early_miss_recovery, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <div className="section-header">
          <h3>Decision-loss comparison</h3>
        </div>
        <Chart
          width={1080}
          height={260}
          xLabel="Probe budget"
          yLabel="Decision loss"
          xMax={Math.max(...E.budgets) * 1.05}
          multi={E.policies.map((policy: string) => ({
            color: palette[policy],
            label: policyLabel(policy),
            pts: E.budgets.map((budget: number) => ({ x: budget, y: E.sweep[policy][String(budget)].decision_loss })),
          }))}
        />
      </section>

      <section className="panel explanation-panel">
        <div className="section-header">
          <h3>Important interpretation</h3>
        </div>
        <p>NEXTPROBE optimizes decision value rather than simply selecting the highest-risk devices. This is a screening decision-support workflow evaluated on a supplied engineering benchmark.</p>
      </section>
    </>
  );
}

function PassportPage({ tick }: { tick: number }) {
  const { deviceId } = useParams();
  const id = deviceId ?? "C0001";
  const p = useApi(`/passport/${id}`, [tick, id]);

  if (p.error) return <Err e={p.error} />;
  if (!p.data) return <div className="panel">Loading passport…</div>;

  const P = p.data;

  return (
    <>
      <div className="page-header-row">
        <div>
          <div className="eyebrow">RELIABILITY PASSPORT</div>
          <h1>{P.device_id}</h1>
          <div className="header-submeta">Lot {P.lot_id} · Audit trail</div>
        </div>
      </div>

      <div className="metrics-grid compact-grid">
        {[
          ["Device ID", P.device_id],
          ["Lot ID", P.lot_id],
          ["Current stage", P.analysis?.stage === "revealed" ? "96h evidence received" : "Early screening"],
          ["Gate status", P.analysis?.gate?.disposition ?? "-"],
        ].map(([label, value]) => (
          <div className="metric-card" key={String(label)}>
            <div className="metric-label">{label}</div>
            <div className="metric-value">{String(value)}</div>
          </div>
        ))}
      </div>

      <section className="panel">
        <div className="section-header">
          <h3>Screening timeline</h3>
          <span className="muted">Evidence in sequence</span>
        </div>
        <div className="passport-timeline">
          {P.events.map((event: any) => (
            <div key={event.seq} className="passport-event">
              <div className="passport-marker" />
              <div className="passport-event-content">
                <div className="passport-event-header"><strong>{eventActionLabel(event.type)}</strong><span className="sequence-cell">Evidence {String(event.seq).padStart(2, "0")}</span></div>
                <div className="passport-event-type">{eventContextLabel(event.type)}</div>
                <div className="passport-event-result"><EventResult event={event} /></div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <h3>Audit integrity</h3>
          <span className="muted">Cryptographic record available on demand</span>
        </div>
        <p className="muted">The screening sequence is protected by a SHA-256 hash chain. Technical records are retained for traceability without competing with the engineering decision.</p>
        <details className="technical-record">
          <summary>View technical record</summary>
          <div className="technical-record-grid">
            <span>Dataset version</span><strong>{P.dataset_version}</strong>
            <span>Policy status</span><strong>{P.policy_status}</strong>
            <span>Head hash</span><strong className="hash-cell">{P.head_hash}</strong>
          </div>
        </details>
      </section>
    </>
  );
}

function DeviceDrawer({ deviceId, open, onClose }: { deviceId: string; open: boolean; onClose: () => void }) {
  const { data, error } = useApi(`/devices/${deviceId}`, [deviceId, open]);

  if (!open) return null;

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="device-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <div className="eyebrow">DEVICE DETAIL</div>
            <h3>{deviceId}</h3>
          </div>
          <button className="button-close" onClick={onClose}>Close</button>
        </div>

        {error && <Err e={error} />}
        {!error && !data && <div className="panel">Loading device…</div>}

        {data && (
          <>
            <div className="drawer-summary">
              <div><span>Lot</span><strong>{data.lot_id}</strong></div>
              <div><span>Current measurement</span><strong>{f(data.observations?.["24h"], 2)}</strong></div>
              <div><span>24h change</span><strong>{f(data.fingerprint?.slope_uA_per_h_0_24h, 3)}</strong></div>
              <div><span>168h prediction</span><strong>{f(data.prediction?.median_168h, 2)}</strong></div>
            </div>

            <div className="drawer-badges">
              <StatusBadge value={data.gate?.disposition ?? "UNKNOWN"} />
              <span className="spec-badge">Within specification</span>
            </div>

            <div className="drawer-rows">
              <div><span>Lot-relative score</span><strong>{f(data.lot_position?.percentile_24h, 1)}%</strong></div>
              <div><span>Prediction interval</span><strong>{f(data.prediction?.lower, 2)} – {f(data.prediction?.upper, 2)}</strong></div>
              <div><span>Conformal evidence</span><strong>{f(data.gate?.p_value ?? data.p_anomaly, 3)}</strong></div>
              <div><span>Gate state</span><strong>{data.gate?.disposition ?? "UNKNOWN"}</strong></div>
            </div>

            <div className="drawer-actions">
              <Link className="button-primary" to={`/device/${deviceId}`} onClick={onClose}>Open full investigation</Link>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
