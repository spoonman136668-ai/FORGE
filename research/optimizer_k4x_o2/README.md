# Optimizer K4X-O2 — Capacity-Matched Delayed-Credit Preflight

**Status: source-only handwritten development fixture.** This is not a protected scientific original, a genuine MiniGrid run, an accepted trained candidate, or an authorized FSA worker. No FIT/CHECK/DEV source roles, historical heldouts or original MiniGrid seeds were used.

## Source provenance

Checked against original, unchanged research code on October 24, 2026:

- FORGE protected main `8eca700c39223e176dea55f488b6f3397ce4e27a`.
- Original source-developed native comparison K4U [FORGE PR #877](https://github.com/spoonman136668-ai/FORGE/pull/877), source head `51b3a936e74a3132c40252f97af1c1b084d62703`, `research/lcrm01/k4u_native_minigrid.py` Git blob `6a95bbef923ca7b27d18bd7d7937739a34b79a7f`.
- Native Wingless `research/native/itd02/r1/policy.go` blob `8d1845d82dd8578a709b00e8841bdc5edc8dbc10`, at `cd108800054e7964af845137f0d9d37fae69f5a7`.
- Native Yggdrasil `research/native/itd02/r1/native_policy.py` blob `3aa22b1e418a7f8cd9619c476f02b8c614917b16`, at `1b042d6bf4832d885d80ef73f3ab29d8a600bfe2`.
- Original authenticated K4W retrospective negative [FORGE PR #879](https://github.com/spoonman136668-ai/FORGE/pull/879), exact head `0bb78beaa07a25a021513548976f765824e6ca22`. Its original published evidence found just **11 nonzero terminal rewards / 6,114 FIT transitions**; K4U native DEV remained negative. Do not tune on consumed K4U DEV.

## Exact bounded comparison

A single pair of *handwritten*, ordinary-public-shape action sequences begins from the same six-field state: `X,Y,GoalX,GoalY,Direction,FrontBlocked = (3,3,5,3,3,True)`, legal actions `0=left, 1=right, 2=forward`. In one example, turning right, then moving forward twice reaches the constructed goal and obtains a delayed scalar terminal reward. In another, turning left and moving forward twice moves away and reaches a synthetic time-limit truncation. They are explicit test fixtures, **not actual MiniGrid execution or independently sealed prospective evaluation cases**.

Two independently initialized linear action-value learners consume the *same six ordered transitions*, the same **nine** source-matched public features, the same legal action set, the same shaped reward (`environment reward + 0.15 × change in Manhattan distance`), same step size `α=0.2`, same discount `γ=0.9`, and the same 27 trainable scalar weights (3 actions × 9 features). Both use the one-step max-Q bootstrapped TD error; only `λ=0` versus accumulating eligibility `λ=0.8` differs. There is no hidden wall grid, seed, task family, shortest path, expert, or private state.

The recurrent eligibility trace adds **27 transient scalar slots** and more nonzero scalar update operations than TD(0); these costs are not swept away by matching trainable capacity. Real native policies have different parameters and training rules; they are *not* represented by these linear controls.

## Reproducible local result

On Windows PowerShell (from the extracted directory):

```powershell
py -3 -B -m unittest discover -v
py -3 -B credit_preflight.py
```

On Python-enabled Linux:

```bash
python3 -B -m unittest discover -v
python3 -B credit_preflight.py
```

**Seven tests PASS locally**, including strict public-field refusal, exact nine-feature vector, three-action/27-weight equal-budget contrast, causal terminal-reward ablation, a zero-consequence null, atomic invalid-sequence rejection, and cold-child-process authenticated model restore/tamper refusal.

- TD(0) first selection: `2` (forward, despite the fixture's blocked front).
- TD(λ) first selection: `1` (turn right, the route with delayed goal reward).
- TD(λ) learned turn-right Q-value = `0.4447350223865136`. With terminal reward removed but *distance shaping preserved*, the same fitted value is `0.13167002238651357`, a difference of `0.31306500000000006`. The difference matches the analytic credited reward `α(γλ)^2 ||φ(start)||²` on this fixed one-pass fixture.
- Both learners consumed exactly 6 events and 27 trainable weights. TD(0) used 26 nonzero scalar weight-update operations; TD(λ) used 46. Checkpoints 398 B and 524 B respectively; these are **not** full cost accounting or real-world computation estimates.
- The native original environment was never imported, reset, stepped or sampled; `FIT/CHECK/DEV` consumption is zero. There was no FORGE FSA scientific permit.

## Qualification boundaries and single next science decision

1. **Do not** call this a real MiniGrid result, native architectural comparison, scientific transfer, data-efficient Pareto advance or Q21/FSA permit.
2. Owner-controlled next gate: freeze a *new* source-owned, FIT-only intervention set and measured information-parity control tiers, with exactly the same nine-feature native input and shaped feedback, separate actual termination vs truncation, and a recurrent/eligibility baseline plus ordinary one-step TD. Preserve the full-public-map BFS only as an **information-advantaged reference**, not an equally informed algorithm.
3. Measure action switching, actual delayed sparse-success attribution, action-observation trajectories, cold restart, out-of-distribution family performance and per-method CPU/RSS/storage. Source-only zero-data, shuffled-consequence and ablated-memory falsifiers must pass first. If FIT causal action-learning or identifiability fails, STOP before consuming fresh CHECK/DEV.
4. Original K4R/K4U roles and negatives stay frozen. Only the existing Mass and independent Wingless/Yggdrasil source owners can qualify new source cohorts and authorized public-development execution. Protected novel scientific original first-use remains forbidden until a genuinely deployed and independently witnessed FORGE FSA and source-specific permit exist. Do not touch F139, CKB, KTRADE, active research queues, protected main or paid APIs.

The JSON `receipt.json` is deterministic local illustrative evidence, not a GitHub-hosted or independently archived accepted science receipt.
