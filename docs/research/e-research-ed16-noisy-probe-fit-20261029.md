# E Research E-D16 — costly noisy observation FIT, October 29 2026

**Engineering PASS, decision-useful observation supported, novel intelligence advantage NOT SUPPORTED.** Advisory-only. No FORGE controller, science admission, autonomy or model changes.

Executed isolated local Python experiment derived from E-D15: 2,000 randomized training interventions, then 240 unsealed development worlds times seven policy arms = 1,680 evaluation trajectories. After the first barrier, environmental binary change is hidden. Optional probe costs one energy and reports a noisy 80%-correct signal. Second intervention costs 4 energy and one material; both build actions are paid, with 12 resource harvested only after both are correct. Initial energy 20 and material 2. Per-step energy/material accounting and deterministic seeded evaluation replay PASS.

| Arm | Success /240 | Mean net reward |
|---|---:|---:|
| Learned probe lookup | 192 | +0.6 |
| Conventional probe lookup (same table) | 192 | +0.6 |
| No probe | 113 | -2.35 |
| Scrambled signal probe | 48 | -6.6 |
| Uninformative paid probe | 113 | -3.35 |
| Random | 54 | -5.3 |
| No-model random second choice | 126 | -1.7 |

All probe-enabled arms pay the same one-unit probe cost; the no-probe arms avoid it. Of the 2000 training encounters, 1017 produced usable probe/outcome updates; reported signal-matched counts 412/515 and 400/502. The two successful learned and conventional arms use IDENTICAL empirical lookup—not separate explicit Bayesian inference or an independent baseline. The probe likelihood is hardcoded in the synthetic generator; there is no learned exploratory probe choice, partial-state sequence planning, externally sourced world, sealed first-use validation or native emergent cognition claim.

Executed originals remain outside this documentation-only GitHub report: local `/mnt/data/e_research/ed16/run_ed16.py` SHA256 `99944113bc601ae1367a9890936abef5c2be8c4e08127f2c6558938127ee3083`; local `results.json` SHA256 `53d833c5a666bfe0fdb216d47278520d8e67960ccec4d9d4e3b1ed850724228e`. These hashes do not authenticate FORGE FSA original custody; independent scientific qualification UNVERIFIED.

**Next E-D17:** Require agent to decide whether and when to purchase probes under variable reliability/cost, compare an independently implemented Bayesian value-of-information baseline, a fixed-probe policy, no-probe policy, scrambled observations and equal-resource conventional learning. Predeclare FIT/VAL/HOLDOUT before any transfer claim.

Plain English: Paying for a somewhat reliable clue helps, but a standard lookup agent learns the same behavior. We still need a test where deciding when information is worth paying for is itself learned.