# NEXTPROBE-X - Risk-Controlled Sequential Burn-In Screening
**SIMULATED DATA.** Prototype validated on supplied synthetic engineering benchmark (SIH26170, 1000 devices). Not ISRO/production data. Cost values are simulation-only.

NEXTPROBE recommends which devices get the limited 96h observation. The safety gate (separate module) decides RELEASE/CONTINUE/HOLD/UNKNOWN.

## Run (one command)
    pip install -r requirements.txt
    ./run.sh          # builds frontend if needed, serves UI+API at http://127.0.0.1:8000

Dev mode: `cd backend && python3 -m uvicorn nextprobe.api:app --reload` and `cd frontend && npm install && npm run dev` (http://localhost:5173 proxies /api).

## Tests / demo
    cd backend && python3 -m pytest tests -q      # 36 tests
    python3 scripts/demo.py                        # deterministic E2E demo against a running server

## Demo flow (UI)
Load dataset -> Command Center -> NEXTPROBE page: pick budget -> RUN NEXTPROBE -> ALLOCATE 96H SCREENING -> CONFIRM -> REVEAL 96H RESULTS (before/after table)
-> open a device (updated trajectory, prediction, gate) -> passport -> Evaluation (sweeps, sensitivity, hero, misses).

## Layout
`config/risk_policy.json` (FN=20, FP=1, probe=0.25, simulation_only) · `backend/nextprobe/{data,model,evoi,gate,engine,evaluation,api}.py` · `frontend/src` · `data/` canonical xlsx.

## Method
Early model: multinomial logistic on 0h/24h + lot-relative robust z (5-fold cross-fitted). Class-conditional Gaussian models of log(y96/y24) and log(y168/y24)
give the predictive distribution of the 96h reading. EVOI = current Bayes decision risk - expected post-96h risk - probe cost; only EVOI>0 devices are selected.
After reveal, hypotheses and the 168h forecast update by Bayes; the gate re-evaluates independently.
