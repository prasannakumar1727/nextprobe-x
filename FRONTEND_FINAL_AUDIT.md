# NEXTPROBE-X Frontend Final Audit

## Current architecture

The frontend is a React + TypeScript + Vite single-page application. `frontend/src/App.tsx` owns the app shell, route declarations, page components, upload flow, and API state. `frontend/src/api.ts` provides the fetch wrapper and `useApi` hook. `frontend/src/Chart.tsx` is a small SVG chart primitive. `frontend/src/style.css` contains the complete visual system.

The backend is FastAPI. `backend/nextprobe/api.py` is the authoritative HTTP contract; `engine.py` owns inference, NEXTPROBE allocation/reveal, gating, summaries, and passport construction. `gate.py` remains independent from `evoi.py` and must stay independent in the interface.

## Current routes

- `/` — workspace/overview dashboard
- `/investigate` — investigation page using a fallback selected device
- `/lot/:lotId` — lot analysis
- `/device/:deviceId` — device investigation
- `/nextprobe` — NEXTPROBE rank, allocation, and reveal
- `/passport/:deviceId` — reliability passport
- `/evaluation` — simulation evaluation

The requested operational architecture is SCREEN -> INVESTIGATE -> NEXTPROBE -> DECISION -> PASSPORT. Evaluation should remain a secondary validation area rather than a primary operational destination.

## Existing API dependencies

- `GET /api/state`
- `POST /api/dataset/load`
- `POST /api/dataset/upload`
- `POST /api/session/reset`
- `GET /api/lots`
- `GET /api/lots/{lot_id}`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `POST /api/nextprobe/rank`
- `POST /api/nextprobe/allocate`
- `POST /api/nextprobe/reveal`
- `GET /api/nextprobe/status`
- `GET /api/passport/{device_id}`
- `GET /api/evaluation`
- `GET /api/evaluation/sensitivity`
- `GET /api/evaluation/hero`
- `GET /api/evaluation/misses`

The backend supports CSV upload only. It parses the upload with `pandas.read_csv`, validates it, and returns validation information. XLSX and PDF are not supported by the current upload endpoint and must not be presented as supported.

## UI problems

- The primary landing page is labelled WORKSPACE instead of SCREEN.
- Evaluation is currently presented as a primary navigation destination even though it is simulation validation, not the operational workflow.
- There is no dedicated DECISION page that makes the independent safety gate visible.
- The screen queue maps `pred_168h` into the current-value column and `p_anomaly` into `24h delta`; these are not the displayed concepts they claim to be.
- Several charts use hard-coded sample values instead of the active device or lot API response.
- NEXTPROBE shows hard-coded device ID, state, EVOI, expected improvement, and cost in its hero summary, despite ranking and costs being available from the backend.
- Investigation uses generic explanatory text and does not clearly separate current evidence, lot context, why flagged, and next action.
- Passport previously exposed a database-like audit table by default; technical hashes and event keys compete with engineering meaning.
- Technical names such as `p_anomaly`, `analysis_early`, and raw gate reasons leak into primary UI hierarchy.
- Error rendering exposes raw backend messages through the generic `Error:` component.
- Loading and empty states are minimal and inconsistent across pages.
- The sidebar displays internal model/version information that does not help the primary demo.

## Redundant text and components

- The overview repeats the same screening statement in the heading and lead paragraph.
- Simulation warnings and implementation explanations are repeated across primary views.
- Overview metrics include multiple gate buckets while the requested landing page needs only the few metrics required for action.
- The current overview includes both a queue and a generic trajectory summary that is not tied to the selected device.
- Device drawer, device route, and investigation route overlap in purpose without a consistent transition into the main flow.

## Confusing terminology

- `WORKSPACE` obscures the screening operation.
- `Evaluation & Results` sounds operational although it is simulation validation.
- `CONTINUE` is displayed as `Review` in some contexts but not explained.
- `p_anomaly`, EVOI, raw reason codes, and backend event names are too implementation-oriented for primary content.
- `Timestamp` is shown for passport events even though the backend only supplies sequence/hash-chain order.
- `Gate` and `NEXTPROBE` are adjacent without explicitly stating that only the gate determines disposition.

## Missing states

- Dedicated empty screening state when no rows are available.
- Explicit device-not-found state with a recovery link.
- Backend unavailable state with a retry action.
- Probe unavailable/analysis-only state when uploaded data has no 96h replay.
- Already allocated and already revealed states described in user language.
- Evaluation unavailable state for uploaded datasets without ground truth.
- Import preview/validation summary for rows, columns, lots, timepoints, missing values, duplicates, and unit consistency.

## Design inconsistencies

- Generic dashboard cards coexist with engineering tables without a clear information hierarchy.
- Some values are hard-coded while neighboring values are real API values.
- Page actions do not consistently lead into the next workflow step.
- Status colors and labels are not consistently contextualized.
- Charts do not consistently distinguish measured, predicted, baseline, and limit values.
- The default passport view is too close to a database dump rather than a traceable engineering timeline.

## Technical risks

- `api.ts` forwards raw error strings and does not normalize network failures.
- The current queue response lacks true 24h/current fields, so the frontend cannot honestly render the requested queue columns without an additive backend field or per-device requests.
- The frontend relies on `any` for nearly all response payloads, increasing the chance of silently showing undefined values.
- The backend uses a single in-memory session, which is appropriate for the demo but not multi-user production deployment.
- Upload validation can report warnings, but there is no explicit confirm step; the backend commits a valid upload immediately.
- The backend supports CSV only; claiming XLSX/PDF support would be false.

## Proposed final information architecture

Primary navigation:

1. SCREEN — landing page, screening summary, queue, and recommended next action.
2. INVESTIGATE — why a selected device is suspicious, with measured evidence, lot context, trajectory, and next action.
3. NEXTPROBE — backend-ranked next measurement, allocation, reveal, and before/after evidence.
4. DECISION — independent safety gate, criteria, disposition, and approved next action.
5. PASSPORT — readable vertical screening timeline with technical audit integrity behind a secondary detail control.

Secondary validation route:

- `/validation` (with `/evaluation` retained as a compatibility alias) — simulation-only metrics and plots.

Global action:

- `IMPORT DATA` opens the real CSV picker and reports backend validation clearly. XLSX/PDF remain explicitly unsupported.

The redesign will preserve backend calculations, use only returned data, add only the true queue fields needed for honest labels, and make the distinction between selector and gate visible at every relevant step.
