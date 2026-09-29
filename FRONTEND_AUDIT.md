# Frontend Audit — NEXTPROBE-X

## 1. Current architecture

### Frontend
- Framework: React + TypeScript + Vite
- Primary app entry: `frontend/src/main.tsx`
- UI shell: `frontend/src/App.tsx`
- Theme and layout: `frontend/src/style.css`
- Charting primitive: `frontend/src/Chart.tsx`
- HTTP wrapper: `frontend/src/api.ts`

### Backend
- Framework: Python + FastAPI
- App factory: `backend/nextprobe/api.py`
- Engine logic: `backend/nextprobe/engine.py`
- Risk gate: `backend/nextprobe/gate.py`
- EVOI selector: `backend/nextprobe/evoi.py`
- Evaluation logic: `backend/nextprobe/evaluation.py`
- Dataset validation and model data: `backend/nextprobe/data.py`, `backend/nextprobe/model.py`

## 2. Working routes

The present app exposes the following navigation flow:
- `/` → workspace/home
- `/lot/:lotId` → lot intelligence
- `/device/:deviceId` → detailed device analysis
- `/nextprobe` → NEXTPROBE allocation flow
- `/passport/:deviceId` → reliability passport
- `/evaluation` → evaluation lab

## 3. Working API endpoints

From `backend/nextprobe/api.py`:
- `GET /api/health`
- `GET /api/policy`
- `GET /api/state`
- `POST /api/dataset/load`
- `POST /api/session/reset`
- `POST /api/dataset/upload`
- `GET /api/summary`
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

## 4. Data model and backend responsibility

The backend already owns the actual product logic:
- 0h/24h/96h/168h reasoning
- lot-relative baseline detection
- model-driven anomaly / posterior estimation
- independent safety gate decisions
- NEXTPROBE EVOI recommendation for candidate measurement actions
- passport hash-chain audit trail
- simulation-only evaluation metrics

The frontend must not replace or rewrite this logic. It should consume the backend values and visualize the workflow.

## 5. Existing frontend strengths

- Real API integration already exists
- CSV upload validation is functional
- Device-level detail is available
- NEXTPROBE ranking, allocation and reveal are supported
- Passport and evaluation endpoints are wired
-Backend tests already cover core logic and API behavior

## 6. Broken routes / gaps

- Navigation is overly technical and not aligned with the engineered workflow
- Primary sections are not weakly organized around: Workspace / Screen / NEXTPROBE / Decision / Passport
- The app still exposes a more generic analytics dashboard layout rather than a reliability workstation layout
- Import-data action is not as explicit as required for the demo
- UI hierarchy does not clearly separate NEXTPROBE (selector) from the safety gate (decision authority)
- Some screens still look like utility dashboards rather than a decision-support engineering workspace
- Several labels still reflect technical implementation details instead of the reliability workflow that judges need to grasp in 10 seconds

## 7. Missing functionality relative to the requested design

- Clear “IMPORT DATA” flow from anywhere in the workspace
- Dedicated decision-oriented “DECISION” page as a safety gate that clearly separates from NEXTPROBE
- Better home/workspace summary that explains current dataset and recommended next action
- Stronger “before vs after” probe workflow demonstration
- More explicit “evidence / action / next step” hierarchy on each page
- Cleaner engineering status styling with professional semiconductor reliability patterns

## 8. Backend/frontend integration gaps

- The existing frontend is functional, but the information architecture does not yet communicate the actual decision flow with enough clarity
- The UI can still feel like a generic dashboard instead of an engineering workstation
- The route structure does not consistently mirror the actual customer story (import → screen → decide → audit)
- More of the UI should emphasize observed vs predicted data and the independent gate separation

## 9. Recommended redesign

The redesign should center around this flow:
1. Workspace
2. Screen
3. NEXTPROBE
4. Decision
5. Passport

And the global action should be:
- Import Data

The page hierarchy should clearly communicate:
- Early evidence from the dataset
- lot-relative trajectory anomaly
- NEXTPROBE-selected next test
- updated evidence after a reveal
- independent release gate decision
- passport audit trail

The design should use restrained semiconductor/industrial styling instead of generic AI SaaS styling.

## 10. Exact files intended for modification

- `frontend/src/App.tsx`
- `frontend/src/style.css`
- `frontend/src/Chart.tsx` (only if needed for better chart clarity)
- project root docs: `FRONTEND_AUDIT.md`, `FRONTEND_IMPLEMENTATION_STATUS.md`

## 11. Recommendation

Keep the backend logic intact and shape the UI around the real API contract. The current backend is already the core product; the remaining work is architectural and presentation refinement to make the decision story clear and credible to a reliability judge.
