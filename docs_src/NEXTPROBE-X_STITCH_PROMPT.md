# Google Stitch Master Prompt — NEXTPROBE-X

Create a desktop-first enterprise reliability engineering web application called **NEXTPROBE-X — Risk-Controlled Sequential Screening** for semiconductor component burn-in analysis.

This is NOT a generic SaaS analytics dashboard, NOT a chatbot, NOT a futuristic AI control room, and NOT a consumer-tech UI.

## Product context
A QA/reliability engineer uses the application to review electronic components during high-reliability burn-in screening. The system compares each device with its production lot, builds a temporal reliability trajectory, predicts the 168h endpoint with uncertainty, detects out-of-distribution behaviour, and — when evidence is insufficient — recommends the next most informative test. A separate safety gate produces the final disposition.

The main UX story is:
**OBSERVE → COMPARE → PREDICT → CHECK EVIDENCE → PROBE → VERIFY → RELEASE/HOLD**

## Visual direction
Design language: **instrumentation workstation + aerospace test laboratory + semiconductor ATE console**.

Use:
- deep graphite/navy background
- near-white data panels
- muted steel-blue secondary surfaces
- restrained teal for healthy/normal states
- amber for review/targeted-test states
- red only for HOLD/high-risk states
- thin 1px borders
- compact tables
- dense but readable information hierarchy
- monospaced or tabular numerals for measurements
- strong chart axes and engineering units
- subtle grid/measurement-line motifs
- minimal rounded corners (4–8px)
- professional technical typography
- clear hierarchy rather than decorative cards

Do NOT use:
- purple/blue AI gradients
- glowing neon
- glassmorphism
- giant hero text
- robot/brain AI illustrations
- floating chat widgets
- excessive pill-shaped cards
- stock imagery
- generic fintech dashboard styling
- excessive shadows
- unnecessary 3D

The interface should feel like software an aerospace reliability engineer could plausibly use.

## Navigation
Left sidebar with:
1. Command Center
2. Lot Intelligence
3. Device Analysis
4. NEXTPROBE
5. Reliability Passport
6. Evaluation Lab

Top bar:
- NEXTPROBE-X mark
- current lot
- simulation/live indicator
- model version
- policy version
- system health
- timestamp

Always show a visible but understated **SIMULATED DATA** banner in prototype mode.

## Screen 1 — Command Center
Title: **Reliability Command Center**

Top strip:
- Components: 500
- Release: 421
- Continue: 51
- Targeted Test: 21
- Hold: 5
- Unknown: 2

Main area:
Left: large **Lot Risk Distribution** chart.
Right: **Priority Review Queue** table.

Table columns:
Device | Lot | Absolute Spec | Lot Percentile | 168h Prediction | Evidence | State

The most interesting row is A173:
Absolute Spec = PASS
Lot Percentile = 98.4%
168h Prediction = 47.8 µA
Evidence = 4.7 bits
State = TARGETED TEST

Bottom strip:
- Lot baseline trusted
- Conformal coverage
- Current read-point
- Dataset version

## Screen 2 — Lot Intelligence
Show:
- lot identity
- parameter selector
- robust median
- MAD
- baseline trust
- distribution plot
- device percentile distribution
- contamination warning area

Main visualization: a dense engineering scatter/distribution plot rather than a colorful KPI card grid.

Include a small callout:
**Baseline status: TRUSTED**

## Screen 3 — Device Analysis
This is the most visually important screen.

Header:
**DEVICE A173 / LOT L2026A / SLOT S03**

Left column:
- Absolute specification: PASS
- Lot-relative position: 98.4 percentile
- Dynamic anomaly p-value: 0.018
- Evidence: +4.7 bits
- OOD: OFF

Center:
Large trajectory chart.
X-axis: Burn-in hours.
Y-axis: Leakage current (µA).

Show:
- observed points as solid markers
- predicted 168h trajectory as dashed line
- 95% prediction envelope as a restrained shaded region
- absolute specification limit as a red horizontal line
- lot-normal trajectory band as a thin neutral envelope

Make the visual comparison obvious:
**The component is currently inside the specification but its future uncertainty crosses the boundary.**

Right column:
**Failure-mode hypotheses** horizontal bars:
Healthy / Slow Drift / Accelerating / Transient / Unknown

Below:
**Evidence Stack**
- Lot-relative anomaly
- Positive drift
- Forecast near limit
- Prediction interval crosses limit

No AI confidence percentage.

## Screen 4 — NEXTPROBE
This is the product's hero interaction.

Title:
**Evidence insufficient — select next measurement**

Main left panel:
Candidate tests in a ranked engineering table:

Test | Expected Risk Reduction | Information Gain | Test Cost | Recommendation

Rows:
48h interim read
72h interim read
96h interim read
Extended dwell
Secondary electrical parameter

Highlight 72h with a thin amber selection line, NOT a giant colorful card.

Right panel:
**Why 72h?**

Explain:
- dominant uncertainty is healthy-noisy vs slow-drift hypotheses
- 72h has highest expected decision value
- measurement cost is low
- current evidence is not sufficient for release

A primary button:
**REVEAL 72H OBSERVATION**

This is a simulation control, so make it feel like operating a test station rather than pressing an app CTA.

After clicking, the trajectory chart updates and the decision gate changes.

## Screen 5 — Safety Gate
Show a large but restrained engineering status area:

**RELIABILITY DECISION**

For the demo state:
**HOLD / QA ESCALATION**

Reasons:
- current absolute measurement still passes
- lot-relative trajectory abnormal
- predicted endpoint crosses safety boundary within uncertainty
- release policy threshold not met
- OOD veto off

Show a vertical decision audit timeline.

## Screen 6 — Reliability Passport
Create a technical traceability record.

Header:
**RELIABILITY PASSPORT / A173**

Sections:
- Device identity
- Lot context
- Observations used
- Model versions
- Evidence evolution
- NEXTPROBE actions
- Safety-gate decisions
- assumptions
- simulation disclaimer

Use a compact timeline with timestamped events.

Include an audit hash field styled like a real engineering trace record.

## Screen 7 — Evaluation Lab
Make this feel like a research/test bench rather than a management dashboard.

Show:
- False-negative rate
- defect recall
- 168h MAE
- prediction interval coverage
- average tests/device
- targeted escalations
- avoided read-hours at constrained FNR

Main chart:
**Safety-Constrained Test Efficiency Frontier**
X = avoided read-hours
Y = empirical FNR upper bound

Include a clear subtitle:
**Simulation counterfactual — not production validation**

## Interaction requirements
Prototype these flows:
1. click A173 from Command Center → Device Analysis
2. inspect trajectory and evidence
3. click NEXTPROBE
4. rank tests
5. reveal 72h observation
6. update chart
7. show Safety Gate = HOLD
8. open Reliability Passport

## Responsive behaviour
Primary target: desktop 1440×900.
Also support 1280×800.
Do not redesign the entire layout at tablet width; preserve desktop density as much as possible.

## Component behavior
Use realistic engineering states, not placeholder lorem ipsum.
Use exact labels supplied above.
Do not add random charts, chatbots, AI assistant panels, notification feeds, “insight” widgets, or marketing sections.

## Design goal
A judge should understand in five seconds:
1. this is semiconductor reliability software
2. the component can PASS an absolute limit and still be suspicious
3. the system predicts future behaviour with uncertainty
4. when evidence is insufficient, NEXTPROBE decides what to measure next
5. a separate safety gate controls release

The interface must communicate **engineering evidence before AI spectacle**.
