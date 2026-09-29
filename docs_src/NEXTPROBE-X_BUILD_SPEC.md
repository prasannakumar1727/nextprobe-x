# NEXTPROBE-X — Build Specification for Vibe Coding

## 1. Source of truth order
When instructions conflict, use this order:
1. SIH26170 requirements.
2. NEXTPROBE-X PRD.
3. This build specification.
4. UI design produced in Google Stitch.
5. Existing source code.

Do not invent requirements that are not in these documents.

## 2. Recommended stack
Frontend: React + TypeScript + Vite + Tailwind CSS  
Charts: Plotly or Recharts  
Backend: Python + FastAPI  
Numerical: NumPy + Pandas + SciPy + scikit-learn  
Optional challenger: XGBoost  
Storage: SQLite for MVP  
Audit: SHA-256 hash chain

## 3. Frontend route map
`/` → Command Center
`/lot/:lotId` → Lot Intelligence
`/device/:deviceId` → Device Analysis
`/device/:deviceId/probe` → NEXTPROBE
`/passport/:deviceId` → Reliability Passport
`/evaluation` → Evaluation Lab

## 4. UI component map
- AppShell
- Sidebar
- Header
- SimulationBanner
- KPIStat
- StatusBadge
- LotTrustBanner
- DeviceTable
- TrajectoryChart
- PredictionIntervalChart
- HypothesisPanel
- EvidencePanel
- OODPanel
- NextTestTable
- ProbeReasonPanel
- DecisionGateCard
- PassportTimeline
- MetricCard
- DistributionChart

## 5. Backend endpoint contract
POST /api/simulator/generate
POST /api/lots/load
GET /api/lots/{lotId}
GET /api/lots/{lotId}/devices
GET /api/devices/{deviceId}
POST /api/devices/{deviceId}/probe
GET /api/devices/{deviceId}/passport
GET /api/evaluation/summary

## 6. State machine
States:
`LOADED → ANALYZED → EVIDENCE_INSUFFICIENT → PROBE_SELECTED → OBSERVATION_REVEALED → REANALYZED → GATED`

Terminal outcomes:
`RELEASE | CONTINUE | TARGETED_TEST | HOLD | UNKNOWN`

## 7. Important implementation rule
Do not implement NEXTPROBE by selecting the visually highest bar.
The backend must calculate an EVOI-like quantity for each candidate action using the same posterior and loss model used by the decision engine.

## 8. MVP simplification
To keep the prototype buildable:
- use one main parameter called `leakage_current_uA`
- support optional secondary parameters
- use five hypothesis states
- use five candidate test actions
- use a fixed loss configuration stored in `config/risk_policy.json`
- support replayed hidden observations

## 9. Config file
Create `/config/risk_policy.json` containing:
- alpha
- delta
- cost_false_negative
- cost_false_positive
- test_costs
- max_escalations
- ood_thresholds
- conformal_quantile

Never scatter these values across code.

## 10. Determinism
All simulator runs accept a `seed` parameter. Store the seed in the passport. A device result must be reproducible from:
`dataset_version + seed + model_version + policy_version`.

## 11. No hallucination policy for the coding agent
Before implementing any feature:
- identify which requirement supports it;
- if unsupported, do not add it;
- do not invent API endpoints;
- do not invent data fields;
- do not invent benchmark numbers;
- mark TODOs for genuinely unknown integration details.

If a library/API detail is uncertain, inspect installed packages or official documentation instead of guessing.

## 12. Error handling
All calculations must return explicit status values:
`OK | DEGRADED | INVALID | OOD`.

Missing data must widen uncertainty or route to review; never silently impute and continue without marking it.

## 13. Explainability
Every recommendation must return structured reasons:
- evidence_for_defect
- evidence_for_healthy
- uncertainty_reason
- ood_reason
- selected_test_reason
- decision_gate_reason

The UI renders these fields. Do not let an LLM generate safety reasons.
