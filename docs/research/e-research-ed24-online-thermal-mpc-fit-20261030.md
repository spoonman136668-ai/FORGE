# E Research E-D24 — observation-limited thermal predictive controls (2026-10-30)

**Engineering FIT PASS. Advantage over fixed-closed NOT SUPPORTED.** Actual 168 trajectories were executed in an isolated local Python session; advisory-only record. No native model, FORGE controller, owner, schedule, science admission or autonomy change.

## Model and test
Reused original E-D21 thermal physics and actuation costs exactly: 80 steps, target 20, ambient 27 at steps 18–42, 15 at steps 43–65, 20 otherwise; shutter open exchange .16, closed .035, independent seeded disturbance uniform [-.12,.12], shutter-state switching cost .35 energy, reward cumulative negative |temperature-20| minus switching expense. Public policy observation is rounded current temperature, previous observations/actions retained as permitted. **No policy sees future ambient or noise**. All policies receive the same exogenous per-timestep disturbance vector for each seed regardless of actions.

Seven authored controllers were tested on 24 NEW but unsealed FIT seeds 90000–90023: fixed closed; reactive; 3-observation trend-memory rule; selective recent-state ambient estimator + 7-step fixed-horizon MPC; conventional last-4 ambient estimator + 7-step MPC; same MPC with estimator ablated to default ambient=20; and full-12-observation median estimator + 7-step MPC. The MPC searches every binary action sequence through up to seven steps (2^7 at full horizon), minimizing predicted temperature deviation plus switching costs under a *constant-estimated-ambient* future. The physical exchange coefficients are provided by the experimenter, not learned, and the policies are **hand-designed**, not autonomous learners.

| Controller | Mean net | Median net | Mean switch cost | Paired wins over fixed-closed /24 |
|---|---:|---:|---:|---:|
| Fixed closed | -112.3953 | -113.1546 | 0 | reference |
| Selective recent-state + MPC | -117.9803 | -116.7005 | 1.6917 | 7 |
| Last-4-state MPC | -118.7782 | -119.0080 | 1.2542 | 5 |
| Temperature trend memory | -121.7369 | -119.0474 | 1.2250 | 1 |
| Reactive | -146.9803 | -148.6529 | .7000 | 0 |
| MPC with ambient estimate removed | -241.9334 | -241.6922 | .3500 | 0 |
| Full-12-history ambient estimate + MPC | -176.2495 | -187.0966 | 1.5896 | 0 |

Each arm's energy+switch-cost=160 invariant PASS, no energy deficit or out-of-bound thermal state. Complete 168-row identical seeded replay PASS. Time 3.34 s, process peak RSS 96136 KiB on isolated runner, not independent resource qualification.

**Interpretation:** Memory is causally useful relative to the particular prediction controller's ablation, but every tested memory or prediction controller has negative mean **paired difference** against fixed-closed. The selective-memory controller wins on only 7/24 seeds, conventional last-4 MPC only 5/24. E-D23's offline full-future discretized dynamic programming reference reported an improvement opportunity; this gate shows it is not reliably accessed by these **online information-limited authored strategies**. The model's future regime changes are unobserved, and assuming future ambient remains constant is often invalid. No useful trained learning, stronger standard nonlinear belief-state benchmark, source-sealed unfamiliar transfer, independent scientific first-use or native architecture evidence.

**Original local executed code:** /mnt/data/e_research/ed24/run_ed24.py SHA256 a4ebd68f191589fb226b1d92dbf5410a4f120373ea4909f3b73a31a3fa1759e0.
**Original raw JSON:** /mnt/data/e_research/ed24/results.json SHA256 1c2ea542588c8d8e767c7bb3a8ebadcef7a85a844bd9f598881c5a4912ef0d5f.
Both original bytes are local and NOT embedded in this docs-only GitHub commit. Remote original evidence custody, independent FORGE CI FSA qualification and first-use remain **UNVERIFIED**.

**Next E-D25:** Before another bespoke learner, compare robust information-matched conventional controls: online state-space filtering with uncertainty, conservative receding-horizon risk penalty, delayed intervention, and a fixed predeclared switching schedule to test whether the offline DP advantage can be captured without future oracle. Freeze FIT and validation and report additional search cost explicitly. If all fail, close this original thermal physics as unsuitable for a learning advantage claim, rather than tuning until the result looks positive.

**Plain English:** Short-term memory helps a predictive controller compared with forgetting, but it still fails to beat doing nothing. A future-aware reference succeeds; these real-time policies cannot.
