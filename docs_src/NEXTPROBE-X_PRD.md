# NEXTPROBE-X — Product Requirements Document (PRD)

## 1. Product
**Name:** NEXTPROBE-X  
**Tagline:** Don't just predict failure. Decide what to test next.  
**Problem Statement:** SIH26170 — AI-Driven Anomaly Detection in Component Burn-In & Screening  
**Product Type:** Desktop-first web application / reliability engineering workbench  
**Prototype Status:** Simulation-first MVP; ATE/STDF-ready architecture

## 2. Problem
A component may remain inside its absolute electrical specification while its burn-in trajectory is abnormal relative to its production lot. The SIH problem asks for dynamic outlier detection, 168h drift prediction and explainability.

The product extends that workflow by answering a fourth question:
**When current evidence is ambiguous, what additional measurement is most useful before a QA disposition is made?**

## 3. Product Goal
Turn early burn-in observations into a controlled decision loop:

`Observe → Compare → Predict → Quantify uncertainty → Check evidence → Probe next → Update → Safety-gated disposition`

## 4. Non-goals
- Do not claim replacement of mandatory burn-in standards.
- Do not claim guaranteed zero false negatives.
- Do not claim real ISRO/Intel/AMD data.
- Do not use a chatbot as the primary UX.
- Do not invent confidence percentages.
- Do not use a generic LLM to make safety decisions.

## 5. Primary user
**QA / reliability engineer** reviewing components after burn-in read points.

Secondary users:
- Reliability engineer
- Test/ATE engineer
- Manufacturing quality engineer
- Judge/demo operator

## 6. Core user journey
1. Upload a simulated burn-in lot CSV.
2. System validates data and creates a trusted/ degraded/ invalid quality status.
3. Lot Intelligence calculates robust peer baselines.
4. Each device receives a Reliability Trajectory Fingerprint.
5. Dynamic anomaly and 168h prediction modules run.
6. Uncertainty and OOD checks run.
7. Evidence engine determines whether the decision is sufficiently supported.
8. If insufficient, NEXTPROBE ranks candidate tests using one-step EVOI.
9. Operator selects the recommended test; simulator reveals the held-out observation.
10. Posterior and prediction update.
11. Independent Safety Gate decides RELEASE / CONTINUE / TARGETED TEST / HOLD / UNKNOWN.
12. A Reliability Passport is generated with the evidence and audit trail.

## 7. Required screens
### Screen 1 — Reliability Command Center
Purpose: answer “what needs my attention now?”

Must show:
- total devices
- release / continue / targeted / hold / unknown counts
- lot health and baseline trust
- top 5 devices needing review
- test-read coverage
- simulation mode indicator
- current model/calibration version

### Screen 2 — Lot Intelligence
Must show:
- lot median and MAD
- drift distribution
- contamination status
- percentile distribution
- anomaly clusters
- parameter selector
- lot trust banner

### Screen 3 — Device Analysis
Must show:
- device ID, lot, slot
- absolute specification state
- lot percentile
- trajectory chart
- 168h prediction
- prediction interval
- failure-mode hypotheses
- evidence in bits
- OOD status
- current decision status

### Screen 4 — NEXTPROBE Decision
Must show:
- “Evidence sufficient?” state
- candidate tests
- EVOI score
- information gain
- test cost/stress penalty
- recommended next test
- “why this test?” explanation
- run/reveal simulation action

### Screen 5 — Reliability Passport
Must show:
- device history timeline
- observations
- model versions
- evidence changes
- tests requested
- final decision
- assumptions
- simulated-data label
- hash-chain audit ID

### Screen 6 — Evaluation Lab
Must show:
- false negative rate
- defect recall
- precision
- 168h MAE
- conformal interval coverage
- average tests/device
- targeted escalation rate
- avoided read-hours vs FNR constraint
- distribution-shift performance

## 8. Decision states
- RELEASE: evidence meets release policy, OOD veto off, lot baseline trusted.
- CONTINUE: no concerning trajectory; continue normal screening.
- TARGETED TEST: evidence insufficient; next test selected.
- HOLD: evidence supports latent-defect risk or release gate fails.
- UNKNOWN: OOD or invalid evidence prevents safe automated release.

## 9. Model design
### Baseline
Median/MAD with small-lot shrinkage.

### Dynamic anomaly
Robust multivariate distance + calibration conformal rank/p-value.

### 168h prediction
Primary: hierarchical log-time drift model.  
Challenger: gradient boosting/XGBoost on fingerprint features.

### Failure hypotheses
Healthy, slow drift, accelerating drift, transient, abrupt, unknown.

### Uncertainty
Split conformal normalized residual intervals plus model/posterior uncertainty.

### OOD
Feature-space distance + posterior-predictive misfit + lot distribution shift.

### Evidence
Log posterior odds / bits. Never display arbitrary AI-confidence percentages.

### Next-test selector
One-step EVOI. Candidate actions are simulated/interim reads or additional parameter tests. Each action has a measurement/stress cost.

### Safety gate
Independent from the selector. Gate uses calibrated defect-risk threshold, OOD veto, baseline trust and data quality. Calibration must be clearly labelled as simulation-only unless real labelled data is available.

## 10. Candidate test actions in MVP
Use exactly 5:
1. 48h interim read
2. 72h interim read
3. 96h interim read
4. extended dwell
5. secondary electrical parameter

MVP can simulate their outcomes. Do not create an arbitrary random chooser.

## 11. Data realism requirements
The simulator must include:
- stable healthy
- healthy but noisy
- slow latent drift
- accelerating drift
- transient anomaly
- within-spec anomaly
- abrupt failure
- borderline
- OOD
- delayed-onset/adversarial trajectory
- missing data
- lot shift
- tester noise
- slot/chamber effect

Fault labels are generated from latent severity/mode, not merely from whether 168h exceeds a spec limit.

## 12. Performance targets for the prototype
These are engineering targets, not claims:
- Analyze 5,000 simulated devices interactively in under 3 seconds for the MVP dataset.
- Device detail transition under 300 ms after data is loaded.
- Produce deterministic results for a fixed random seed.
- Never release an OOD component.
- Never use future observations before the simulation reveals them.
- Keep model decisions reproducible with stored seed/model version.

## 13. Acceptance criteria
The product is MVP-complete when:
- CSV upload works.
- Validation catches malformed rows.
- Lot baseline is visible.
- Device fingerprint is calculated.
- 168h prediction and interval are visible.
- At least one component is demonstrably within spec yet trajectory-abnormal.
- NEXTPROBE selects a non-random next test.
- Simulator reveals the requested held-out measurement only after selection.
- Prediction/evidence updates after the new observation.
- Safety Gate produces a final state.
- Passport records the entire sequence.
- Evaluation screen renders metrics.
- Every screen carries a “SIMULATED DATA” indicator.

## 14. Hard safety rules
1. Selector cannot directly set RELEASE.
2. UNKNOWN can never auto-release.
3. OOD veto blocks release.
4. Future observations cannot leak into current prediction.
5. No fabricated confidence score.
6. No hard-coded “successful” metrics.
7. Every displayed metric must be computed from actual simulator output.

## 15. Demo path
The entire 2-minute demo follows one device, A173:

Upload lot → show PASS by absolute limit → reveal abnormal lot position → show 168h interval crossing the boundary → evidence insufficient → NEXTPROBE recommends 72h → reveal held-out 72h → update trajectory → Safety Gate = HOLD → export passport.
