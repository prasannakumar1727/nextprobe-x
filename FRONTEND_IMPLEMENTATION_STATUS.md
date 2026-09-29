# Frontend Implementation Status

## DONE
- Real frontend built on the existing FastAPI backend
- Dataset load and CSV upload integrated
- Workspace/home screen implemented
- Screening / lot / device workflow implemented
- NEXTPROBE ranking and allocation flow implemented
- Passport integration implemented
- Evaluation lab integrated
- Build validated with Vite
- Backend contract validated with pytest

## PARTIAL
- Final visual language is engineering-focused but may still be sharpened further toward a more premium semiconductor reliability workstation appearance
- Import flow is present but can be further centralized as a global action in future iterations
- Decision page still relies on the backend evaluation/decision output and should stay tightly mapped to real data

## NOT IMPLEMENTED
- A full multi-step CSV/XLSX/PDF upload wizard beyond the current backend-supported ingestion flow
- Browser-based PDF parsing because the backend does not provide structured PDF ingestion support
- Production-grade audit report export beyond existing passport and hash-chain data

## BACKEND DEPENDENCIES
- FastAPI API contract in `backend/nextprobe/api.py`
- Engine logic in `backend/nextprobe/engine.py`
- Gate logic in `backend/nextprobe/gate.py`
- EVOI logic in `backend/nextprobe/evoi.py`
- Evaluation engine in `backend/nextprobe/evaluation.py`
- Data validation in `backend/nextprobe/data.py`

## KNOWN LIMITATIONS
- The dataset is simulation-only and must remain clearly labeled as such
- PDF ingestion is not supported by the backend unless a new parser is explicitly added
- Real production data is intentionally not available in this repository
- The frontend should continue to rely on backend values instead of hard-coded metrics

## HOW TO RUN
1. Open a terminal in the project root.
2. Install dependencies:
   - `python -m pip install -r requirements.txt`
   - `cd frontend && npm install`
3. Start the backend:
   - `cd backend && python -m uvicorn nextprobe.api:app --reload`
4. Start the frontend:
   - `cd frontend && npm run dev`
5. Open the application in the browser.

## DEMO STEPS
1. Load dataset or canonical benchmark.
2. Open the Workspace and inspect screening state.
3. Select a device and review early evidence.
4. Open NEXTPROBE and allocate a 96h measurement.
5. Reveal the result and inspect before/after evidence.
6. Review the safety gate decision on the decision page.
7. Open the passport to inspect the evidence chain.
8. Reset the demo to replay the full workflow.

## Verification
- Frontend build: `cd frontend && npm run build` → successful
- Backend tests: `python -m pytest backend/tests -q` → 36 passed
