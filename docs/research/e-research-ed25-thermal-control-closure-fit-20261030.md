# E Research E-D25 — thermal control comparative FIT closure (2026-10-30)

**Engineering PASS; advantage over fixed-closed NOT SUPPORTED.** Advisory-only. No FORGE owner, controller, autonomy, model selection or scientific admission modifications.

## Execution

Original E-D24 thermal physics reused without modification: 80 steps, target 20, ambient 27 at 18–42, ambient 15 at 43–65 and 20 otherwise, actuator coefficients 0.16 open / 0.035 closed, random disturbance ±0.12 and switching penalty 0.35. All seven controllers share the same 24 new but unsealed FIT development seeds 91000–91023 and per-timestep random disturbances, yielding **168 actual trajectories**. All numerical budget/range assertions and exact deterministic replay PASS.

Policies: closed baseline; E-D24 seven-step receding-horizon conventional prediction with short-state estimate; E-D24 selective recent-state estimate plus seven-step search; conventional one-step EWMA ambient estimation/controller; conservative switching threshold; three-consecutive-observations delayed switching; fixed-clock intervention schedule. The last is a **privileged time-schedule prior** and is not an observation-matched learner. All controllers are written rules; none trained.

| Policy | Mean net (higher better) | Paired wins vs closed /24 | Mean shutter-switch energy |
|---|---:|---:|---:|
| Fixed closed | -108.66544 | — | 0 |
| Conventional MPC | -114.72638 | 4 | 1.25417 |
| Selective recent-state MPC | -115.80476 | 5 | 1.93958 |
| Conservative | -120.15852 | 0 | .64167 |
| Delayed switching | -124.88152 | 0 | .70000 |
| EWMA conventional estimate | -126.43797 | 0 | .71458 |
| Fixed clock | -152.96431 | 0 | .70000 |

**Decision:** All tested online controls have worse average net score than fixed-closed. E-D23's full-future DP *reference* showed at least one achievable intervention sequence that wins with privileged information, but this cannot be interpreted as the existence of an information-feasible learning advantage. **Close this specific E-D21–25 thermal configuration for autonomous-learning advancement on current FIT evidence; do not close thermal control generally.** Original source and data are isolated-local, not FORGE FSA authenticated. No independent holdout, externally sourced task, native cognition or scientific first-use.

**Original local Python SHA256:** `5cdcd45e758eddedb009b6bcfba4848677feb7113fca93c09607feba11db752d` at `/mnt/data/e_research/ed25/run_ed25.py`.
**Raw JSON SHA256:** `74a50475f94687cbf84283fe971d531355d195975cdac398ff1e2ca270c610a8` at `/mnt/data/e_research/ed25/results.json`. These originals are not included in this docs-only commit; no repo-only reproduction or scientific first-use claim.

**Next E-D26:** Stop bespoke synthetic tuning. Select independently sourced interactive causal environments already used by Native Intelligence research (e.g. properly source-authenticated MiniGrid, CausalGym, Memory Gym), or run a bounded mechanism falsification in a validated world; predefine actionable native mechanism, strong conventional controls, FIT/VAL/held-out family, resource costs and immutable original code custody before further compute. Do not interfere with FORGE autonomy or present advisory findings as first-use.

**Plain English:** Trying more careful temperature control still loses to doing nothing. This test environment isn't giving us a useful learning result, so close this version and move to a better validated environment.
