# E Research E-D14 — two paid interventions and delayed outcome (2026-10-29)

**Executed local FIT engineering PASS; memory/action-consequence dependence supported; new causal planning advantage NOT SUPPORTED.** This is a documentation-only advisory record, not native FORGE scientific acceptance, independent first-use, owner/controller operation or model change.

## Execution
New standalone Python script. Each deterministic synthetic world presents a binary cue early, two distractor observations, then an orientation at each of two sequential barrier locations. Opening the correct first gate permits passage to a second; the second choice must also be correct for a delayed 12-unit harvest after two scripted traversal steps. Each gate intervention costs 4 energy and 1 material. Both paid interventions are attempted even when first gate was incorrectly opened. Construction earns zero immediate reward. The agent does not see the target gate, and outcome mapping is private to the environment.

**Train:** 2,000 randomized intervention trials, seeds 81000–82999. Model and conventional learner receive the same records and form the same context/action empirical outcome table. First-gate pass/no-pass feedback is observed; second-stage effectiveness can be inferred from final outcome only when the first succeeded. Each state-action context had >=104 supporting training observations.

**Evaluate:** 240 development seed worlds 84000–84239 times seven policies = **1,680 trajectories**, source evaluation deterministic replay PASS.

| Policy | Successful two-intervention outcomes /240 | Mean harvest minus 8 energy cost |
|---|---:|---:|
| Empirical outcome model | 240 | +4.00 |
| Conventional contextual sequence lookup | 240 | +4.00 |
| Scrambled retained cue | 0 | -8.00 |
| Stateless, cue unavailable | 61 | -4.95 |
| Reset random action choices | 51 | -5.45 |
| Random control | 58 | -5.10 |
| Fixed first choice | 58 | -5.10 |

**Engineering:** energy+spent=20; material+placed=2 at both gate actions; no negative energy/material; deterministic identical full re-evaluation PASS. Script runtime ~0.0733 seconds, process peak RSS 97,420 KiB (session-level only).

## Exact scientific limits
1. The agent controls two paid decisions, but *the implementation computes both choices before running the environment's stepwise simulator*, using each stage's correct public orientation and stored cue. This is equivalent to acting at the stipulated observations only because the second decision does not condition on intervening feedback. Thus it is **not an adaptive causal plan that replans following unexpected outcomes**.
2. The learned model and conventional contextual learner are identical in information and behavior. There is **no novel learner** or generalization advantage.
3. Four cue/orientation contexts per gate make the environment learnable by lookup. Delayed traversal is scripted; no locomotion planning.
4. Development seeds and environment generator are unsealed; no unfamiliar-family transfer, independent scientific first-use or native Wingless/Yggdrasil implementation.
5. First-stage pass is supplied directly as a training consequence; this is allowed task feedback but makes causal identification easy.

**Original source:** `/mnt/data/e_research/ed14/run_ed14.py` SHA-256 `317b7a2d523c6b8bfa16066321cced371bd636ada731347ffe9a51100fe276b7`.
**Raw results:** `/mnt/data/e_research/ed14/results.json` SHA-256 `73a7c44eb108a27631f8f34b45b5194b43d4264a5bd201219fc8c5add8d7752b`.
Neither original file is in this docs-only commit. Source SHA is an identity assertion, not original-source authentication or FORGE FSA first-use approval.

**Decision:** E-D14 action-consequence sensitivity PASS; novel sequential causal learning NOT SUPPORTED. **Next E-D15:** implement an online step-by-step simulator where first intervention produces unpredictable, partially observed structural changes and the second choice must react to fresh evidence; compare prior-cached actions, persistent learned transition models and conventional Bayesian/stateful baseline with identical observations, search and interaction budgets. Freeze source/holdout and report negative findings before any FORGE research admission.

**Plain English:** The agent learns the two correct building decisions, but a conventional memory table does exactly as well. The next task must force real adjustment after seeing what the first action changed.
