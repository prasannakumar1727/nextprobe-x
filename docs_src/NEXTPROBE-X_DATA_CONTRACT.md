# NEXTPROBE-X — Data Contract

## Input CSV
Required columns:
- device_id:string
- lot_id:string
- slot:string
- param:string
- t_hours:float
- value:float
- test_id:string

Optional:
- temperature_c:float
- timestamp:string
- missing_flag:boolean
- chamber:string

Example:
```csv
device_id,lot_id,slot,param,t_hours,value,test_id,temperature_c
A173,L2026A,S03,leakage_current_uA,0,10.4,T0,125
A173,L2026A,S03,leakage_current_uA,24,13.2,T24,125
A173,L2026A,S03,leakage_current_uA,96,26.9,T96,125
A173,L2026A,S03,leakage_current_uA,168,53.1,T168,125
```

## Hidden replay store
The simulator retains future observations separately:
```json
{
  "device_id": "A173",
  "hidden_observations": [
    {"t_hours":72,"value":19.8},
    {"t_hours":96,"value":26.9}
  ]
}
```
These observations must not reach the current model until the test selector requests them.

## Device analysis object
```json
{
  "device_id": "A173",
  "lot_id": "L2026A",
  "absolute_spec": {"limit":50,"status":"PASS"},
  "lot_position": {"percentile":98.4,"mad_z":3.1},
  "fingerprint": {
    "drift":0.2692,
    "slope":0.31,
    "curvature":null,
    "noise":0.8
  },
  "prediction": {
    "mean_168h":47.8,
    "lower":41.6,
    "upper":54.1,
    "coverage":0.95
  },
  "hypotheses": {
    "healthy":0.18,
    "slow_drift":0.47,
    "accelerating":0.29,
    "transient":0.04,
    "unknown":0.02
  },
  "evidence_bits":4.7,
  "ood":false,
  "decision":"TARGETED_TEST"
}
```

## Next-test object
```json
{
  "device_id":"A173",
  "selected_action":"READ_72H",
  "candidates":[
    {"action":"READ_48H","evoi":0.41,"information_gain":0.31,"cost":0.10},
    {"action":"READ_72H","evoi":0.84,"information_gain":0.67,"cost":0.12},
    {"action":"READ_96H","evoi":0.61,"information_gain":0.51,"cost":0.13},
    {"action":"EXTENDED_DWELL","evoi":0.35,"information_gain":0.23,"cost":0.28},
    {"action":"SECONDARY_PARAM","evoi":0.47,"information_gain":0.39,"cost":0.20}
  ],
  "reason":"READ_72H has the highest expected reduction in decision risk between the dominant hypotheses."
}
```

## Passport
Passport must contain:
- dataset version
- seed
- model version
- policy version
- observations used
- decisions
- probe requests
- revealed observations
- evidence changes
- final decision
- timestamps
- hash of previous passport event
- current event hash
