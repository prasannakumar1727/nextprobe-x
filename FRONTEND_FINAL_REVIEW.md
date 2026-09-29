# NEXTPROBE-X Frontend Final Review

## 1. What was removed

- WORKSPACE as a primary destination.
- Hard-coded device, EVOI, risk-reduction, probe-cost, and scenario values from primary operational pages.
- The generic trajectory summary chart that was not tied to the selected device.
- The default database-style passport audit table.
- Visible model version and raw hash emphasis from the primary shell.
- Raw backend gate reason codes and event names from the primary passport hierarchy.
- Misleading queue columns that displayed predicted values as current measurements.

## 2. What was redesigned

- Primary workflow is now SCREEN -> INVESTIGATE -> NEXTPROBE -> DECISION -> PASSPORT.
- SCREEN is the operational landing page with four useful metrics and a real screening queue.
- Queue rows use real 24h measurements and 0h-to-24h deltas from the backend.
- INVESTIGATE now presents current evidence, lot context, the actual lot baseline, measured trajectory, prediction interval, why-flagged reasoning, and next action.
- NEXTPROBE uses the selected device's real `nextprobe` values and real rank/allocate/reveal responses.
- DECISION is a dedicated independent safety-gate page showing disposition, criteria, reason, and approved next action.
- PASSPORT is a readable vertical evidence timeline; cryptographic material is under Audit integrity / View technical record.
- VALIDATION is secondary and remains explicitly simulation-only.
- Error messages are user-facing by default, with backend details behind a technical disclosure.
- The global CSV import button now opens the file picker and uploads through the real API.

## 3. New interactions

- Select a queue device to enter INVESTIGATE.
- Move from INVESTIGATE to NEXTPROBE using the real selected device.
- Run NEXTPROBE, confirm allocation, and reveal held-out 96h evidence.
- Review updated evidence and gate outcome.
- Open DECISION and PASSPORT for the same device.
- Reset the session from SCREEN.
- Import a CSV from the global header action or initial load screen.
- Expand technical error and audit details only when needed.

## 4. Routes

- `/` — compatibility entry to SCREEN
- `/screen` — operational screening landing page
- `/investigate?device=<id>` — selected-device investigation
- `/device/:deviceId` — compatibility device investigation route
- `/lot/:lotId` — lot context
- `/nextprobe` — NEXTPROBE selection, allocation, and reveal
- `/decision` — independent safety gate
- `/passport/:deviceId` — screening passport
- `/validation` — secondary simulation validation
- `/evaluation` — compatibility alias for validation

## 5. Backend endpoints used

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

## 6. Import capabilities

- Supported: CSV through `POST /api/dataset/upload`.
- Validation is performed by the backend and the frontend refreshes only after a valid load.
- Invalid CSV responses are shown as understandable user-facing errors, with technical details available separately.
- Selecting the same file again is supported because the file input is reset after each selection.
- Not supported: XLSX and PDF. The backend currently uses `pandas.read_csv`; the UI does not claim support for formats it cannot parse.
- Current backend behavior commits a valid upload immediately; a separate preview/confirm transaction is not available without changing the API contract.

## 7. Known limitations

- Backend session state is in memory and intended for a single demo session.
- The benchmark is simulation-only and does not establish production qualification.
- Uploaded datasets without 96h replay remain analysis-only and cannot use sequential NEXTPROBE reveal.
- Evaluation requires ground truth and may be unavailable for user-uploaded data.
- Backend event records provide sequence/hash-chain order rather than wall-clock timestamps.
- The existing SVG chart is intentionally lightweight and does not provide interactive zoom/pan.

## 8. Build result

- `cd frontend && npm run build` — passed.
- TypeScript diagnostics for the modified frontend files — no errors.

## 9. Test result

- `\.venv\Scripts\python -m pytest backend/tests -q` — 36 passed.
- Existing warning: Starlette/httpx test-client deprecation only.

## 10. Browser QA result

Using the local FastAPI server at `http://127.0.0.1:8000`:

- SCREEN loaded and displayed real 1000-device and queue metrics.
- NEXTPROBE ranked candidates for the selected device.
- Allocation confirmation worked.
- Reveal returned real 96h values and updated before/after decisions.
- DECISION displayed the independent gate and all six criteria.
- PASSPORT displayed the evidence timeline, updated 96h observation, and current gate.
- VALIDATION displayed real simulation metrics.
- Initial pre-load device request was removed to avoid expected 409 console errors.
- Browser invalid-file picker automation was not completed; backend invalid upload coverage remains covered by the existing test suite.

## 11. SIH demo flow

1. Open `/screen`.
2. Select a priority device from the screening queue.
3. Show the 0h/24h evidence, lot baseline, and trajectory difference in INVESTIGATE.
4. Click Find next best test.
5. Run NEXTPROBE and show the live expected decision value and cost.
6. Confirm allocation, then reveal the 96h result.
7. Show the updated evidence path and changed gate outcome.
8. Open DECISION and state that NEXTPROBE selected the measurement while the independent gate determined disposition.
9. Open PASSPORT and show the traceable screening timeline.

## 12. Remaining issues

- The upload backend would need a new staged preview/confirm contract to implement a true two-step import wizard.
- The browser QA pass used the canonical dataset; invalid-file UI behavior should receive one manual click-through with a malformed CSV before the live SIH presentation.
- The existing Starlette/httpx deprecation warning can be resolved separately by upgrading the test-client dependency path.

## Strict SIH judge review

- Innovation is visible in the sequence: evidence -> next measurement -> new evidence -> independent gate.
- NEXTPROBE is differentiated from ordinary anomaly detection by its expected-decision-value recommendation and explicit gate separation.
- The interface reads as an engineering decision-support tool rather than a generic AI dashboard.
- The remaining risks are documented backend/API limitations, not fabricated frontend capabilities.
