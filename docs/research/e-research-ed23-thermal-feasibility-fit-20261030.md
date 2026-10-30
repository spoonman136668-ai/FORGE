# E Research E-D23 — thermal controllability reference FIT (2026-10-30)

**Engineering PASS; improvement opportunity physically feasible. Learned-controller advantage UNTESTED.** Advisory-only; no FORGE autonomy, controller, owner, research selection or native model updates.

## Actual independent local execution

Executed `/mnt/data/e_research/ed23/run_ed23.py` with E-D21 thermal physics: 80 steps, shutter-open exchange .16, closed .035, target temperature 20, deterministic ambient 27 for times 18–42 and 15 for 43–65, ambient 20 otherwise; fixed seeded +/- .12 exogenous random disturbances, and 0.35 energy cost per shutter switch. Comfort reward is negative cumulative distance from temperature 20 minus switch expenditure; no intrinsic action reward. Original E-D21 function independently reviewed before implementation.

**Reference:** offline **full-information** backward dynamic programming with discretized temperature grid resolution **0.05** on [10,35] and shutter status, *given future ambient regime and every future disturbance value*. Reconstruct exact shutter actions by rolling forward continuous thermal physics after grid-based DP; verify cost/energy ledger and exact deterministic solver rerun. The reference is **not** a formally certified upper bound in continuous state due to grid approximation, and certainly not a fair information-equivalent controller. It serves only as an existence witness for beneficial achievable action sequences. Other fixed baseline arms are closed all 80 steps and open all 80 steps. 24 unsealed FIT seeds 89000–89023 × 3 arms = **72 trajectories**. Shared exogenous disturbance vectors, no inter-arm sampling drift.

| Arm | Mean net score | Median net score | Positive paired net difference versus closed |
|---|---:|---:|---:|
| Offline discretized full-future DP | **-95.15268** | -94.56597 | **24/24** |
| Fixed closed | -106.56779 | -105.83956 | reference |
| Fixed open | -239.83520 | -239.93967 | 0/24 |

Mean advantage of full-future offline planning over fixed-closed = **+11.41511** net-score units. DP reference opens shutter for mean 22.25 out of 80 timesteps. Energy/switch cost accounting and nonnegative-state assertions PASS, repeat DP choice sequence PASS. The reference has far greater information and compute than trained limited-observation policies; it must **not** be presented as evidence that learning solves the task or as an attainable online target.

## Source and custody

Executed source SHA256: `c3c7f47abd4e73d5b8d5de42574d6d43b743454faa69452207acda77f3da0e19`
Raw results JSON SHA256: `ea54221f4fcb0af71de4b08295bce383aacff338f15522e7f2e69751ec55432f`.

Both local original files under `/mnt/data/e_research/ed23/` remain outside this **documentation-only** GitHub note. Thus remote original source custody, repository-only replay, FORGE FSA admission and scientific first-use are unverified.

## Decision / next E-D24

**Do not close the original thermal physics as action-inert:** a full-future reference finds genuinely better physical trajectories. Next use **information-matched** online controllers with no future disturbance access: a conventional state-space/particle-belief estimator with model-predictive control, simple stateful learner, action/memory ablations, and a never-act baseline. Preserve the original thermal transition and all costs, with development seeds disjoint from E-D21–D23. Predeclare failure if agents cannot beat fixed-closed in paired evaluation; do not tune on any independent sealed holdout. Keep authenticated original source custody and scientific first-use separate from advisory data.

**Plain English:** The shutter can be controlled profitably in the physical model, but only a benchmark that saw the future found the winning sequence. We still must show a real agent can learn to do that from observations.
