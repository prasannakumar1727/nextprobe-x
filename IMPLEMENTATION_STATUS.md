# IMPLEMENTATION_STATUS (Phase 1 inspection + end-of-session state)

## Inspection result
The supplied ZIP contained **only 5 spec documents** (PRD, BUILD_SPEC, DATA_CONTRACT, STITCH_PROMPT, MASTER_BUILD_PROMPT).
The handoff says a loader, three views, leakage tests, baselines, DESIGN.md, DATASET_AUDIT.md, DATASET_DIAGNOSTICS.json and
BASELINE_RESULTS.json exist, but **none of that code/those files were in the upload**. They were rebuilt here from the handoff + dataset.
If you have the earlier codebase, diff/merge module-by-module (`data.py`, `model.py`, `evoi.py`, `gate.py`, `evaluation.py`).

## DONE (implemented and tested)
Three-view loader (inference/replay/evaluation) · cross-fitted early model (0h+24h only) · lot-relative features and baseline trust · 168h mixture prediction
with 90% intervals · OOD/UNKNOWN · real EVOI (`evoi.py`) · 4 policies at identical budget · allocate/reveal with replay isolation · independent gate (`gate.py`)
· evaluation (sweep, sensitivity, hero, misses) · passport hash chain · CSV upload validation · FastAPI · minimal React UI (6 routes + load/upload) · 36 backend tests.

## PARTIAL
Frontend: functional only, NOT visually verified in a browser, no frontend unit tests (TypeScript build + route serving checked only).
Evaluation endpoints use ground truth server-side; hero/misses reveal which devices are early misses (label-derived) - evaluation-lab only.

## MISSING
Frontend tests · polished UI · stress-test module (missing-data/shift/noise; lot-grouped split) · APK (not requested).

## CONFLICTING
PRD's 48h/72h/96h/extended-dwell tests vs handoff's single 96h replay -> followed handoff.
Handoff "TARGETED_TEST" state -> not used; four states RELEASE/CONTINUE/HOLD/UNKNOWN.

## BROKEN
Nothing known. (An aliasing bug in `allocate()` was found by tests and fixed.)
