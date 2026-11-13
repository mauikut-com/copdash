# Synthetic dataset requirements for the SimPy verdict engine

The SimPy engine (`app/engines/simpy.py`) answers the same question as the rules
engine — "will this server survive this load?" — but by *simulating* requests
flowing through CPU, RAM, and network blocks. Building it immediately surfaced a problem: **there is no ground truth
to validate it against.** No production trace exists that records "server X,
load Y, and here is the observed crash/survive outcome." So any validation
dataset must be *synthesized*, and it needs deliberate *augmentation* to be
useful.

This document records what that dataset must contain. It is a requirements doc,
not a generator.

## 1. Why there is no ground truth

- The service is deterministic and stateless: every verdict is computed on the
  fly, nothing is logged (see README "No persistence").
- There is no historical corpus of real `(spec, load) → outcome` pairs.
- A simulation and a closed-form formula are both *models*; neither is the
  "true" outcome. Their disagreement at the edges is exactly what needs data to
  resolve.

Consequence: the dataset is generated, and its labels come from the two engines
themselves (see §2). The dataset is therefore a *consistency/cross-check*
instrument first, not a ground-truth oracle.

## 2. Label sources

Every record is a `(spec, load)` input with a label derived from the existing
`VerdictResult` shape (`verdict`, `confidence`, `bottleneck`,
`resources.{cpu,ram,network}.utilization/status`, `reasons`).

| Source | Role | Notes |
| ------ | ---- | ----- |
| Rules engine | Primary labeler | Deterministic, closed-form. Cheap and reproducible. |
| SimPy engine (high fidelity) | Secondary / reference | Run with many replications and a long horizon; the *mean* over replications is the "reference" label. |
| Hand-crafted edge cases | Spot-check truth | A small set of inputs where the answer is obvious by inspection (idle, absurd overload). |

A record can carry **both** labels (rules and simpy) plus an
`agreement` field, so divergence is measurable rather than assumed away.

## 3. Augmentation axes

The naive `(spec, load)` space is continuous and mostly boring — most points are
clearly "survive" or clearly "crash". Augmentation targets the regions and
relationships that actually matter:

### 3.1 Boundary values (the critical axis)

The verdict flips at exactly **80%** (`will_survive → at_risk`) and **100%**
(`at_risk → will_crash`). Generate inputs on and infinitesimally around each
boundary, per resource:

- 79.9% / 80.0% / 80.1%
- 99.9% / 100.0% / 100.1%

Why: this is where the deterministic rules and the stochastic simulator most
likely disagree, because the simulator's measured utilization jitters around the
boundary while the rules engine is exact. Every boundary case must be labeled
with **many** simulator replications to characterize the variance.

### 3.2 Bottleneck dominance

Each of the three blocks must be the bottleneck in some records, plus near-ties:

- CPU-dominated, RAM-dominated, network-dominated (bandwidth and connection
  sub-cases separately).
- Two- and three-way near-ties (all utilizations within a few % of each other).

Why: a block that is never the bottleneck ships untested; a near-tie stresses
the `bottleneck = argmax` logic and the `max()` network sub-rule.

### 3.3 Load shapes

- **Idle** (`rps = 0`, `concurrent_connections = 0`) → the `bottleneck = null`
  "No load" path.
- Micro-loads just above zero.
- Moderate loads spanning the three verdict bands.
- Explosive loads far past capacity (the tail where `will_crash` actually
  appears, and where the simulator saturates — see §4).

### 3.4 Spec diversity

Vary capacity independently of load so the same load lands in different bands:

- 1 core vs many cores; non-integer core counts (exercises the `ceil(cores)`
  rounding in the SimPy engine vs the float `cores` in the rules engine).
- Tiny vs huge RAM.
- Low vs high bandwidth.
- Small vs large `max_connections`.

### 3.5 Distribution and arrival-process jitter

Today the schema collapses cost to single **means** (`avg_cpu_ms_per_req`,
`avg_mem_mb_per_req`, `payload_kb`). The dataset must augment around those means:

- Sample per-request costs from distributions (e.g. log-normal/Erlang) with
  controlled variance, not just the mean — the simulator is sensitive to jitter,
  the rules engine is not.
- Vary the arrival process: Poisson (what the engine uses) vs bursty vs
  periodic — to expose sensitivity to the `expovariate(rps)` assumption.

## 4. Known simplifications the dataset must cover

The current slice makes deliberate shortcuts. The dataset should be designed to
flag (and later fix) them:

1. **`concurrent_connections` is a declared input, not an emergent quantity.**
   The simulator drives arrivals from `rps` and lets concurrency emerge, but RAM
   and connection *offered* utilization still use `concurrent_connections`
   directly (to stay comparable with the rules engine). Records where the
   declared concurrency and the emergent concurrency diverge are exactly the
   interesting ones.
2. **Measured utilization saturates at ~100%.** An oversubscribed block reports
   its *offered* ratio instead (the engine's `_util` fallback). The dataset must
   include overload cases to confirm this fallback agrees with the rules engine.
3. **Deterministic seed.** The engine uses a fixed seed, so its variance is
   hidden by default; the dataset's *reference* labels must be multi-seed /
   multi-replication to expose it.
4. **`clock_ghz` is unused** by both engines. It is reserved; records should
   vary it anyway so future clock-aware behavior is not silently ignored.

## 5. Parity metric and tiebreaker

- **Metric:** verdict agreement rate between `simpy` and `rules` over the
  dataset, plus `bottleneck` agreement and mean absolute utilization error.
- **Boundary tiebreaker:** near 80%/100%, define *which* engine is authoritative
  before the dataset is built (recommended: rules is authoritative at exact
  boundaries for determinism; simpy is authoritative for variance/queueing
  questions). Without this, boundary records have ambiguous labels.

## 6. Format

One JSON object per line (JSONL), so it can grow and be streamed:

```json
{
  "id": "boundary-cpu-0800",
  "spec": {"cpu": {"cores": 4, "clock_ghz": 2.5}, "ram": {"total_mb": 8192}, "network": {"bandwidth_mbps": 1000, "max_connections": 10000}},
  "load": {"rps": 320, "avg_cpu_ms_per_req": 10, "avg_mem_mb_per_req": 5, "concurrent_connections": 250, "payload_kb": 10},
  "labels": {
    "rules":   {"verdict": "at_risk", "bottleneck": "cpu", "cpu": 0.8},
    "simpy":   {"verdict": "at_risk", "bottleneck": "cpu", "cpu": 0.81},
    "agreement": true
  },
  "tags": ["boundary", "cpu-dominant"]
}
```

Each record's label shape mirrors `VerdictResult`, so the dataset can be
re-generated and diffed against `/verdict` output directly.
