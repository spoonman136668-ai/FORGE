# AC-15 — Authentic DTR public development to existing Yggdrasil causal-cell learner

**Pre-registered source-public engineering plan.** Prior AC-14 passed exact real upstream source-owned DTR smoke on both Linux and Windows in [FORGE run #40790619395](https://github.com/spoonman136668-ai/FORGE/actions/runs/40790619395). It did not train any native model.

## Existing native research boundary

Reuse the **original existing Yggdrasil development-only `PublicCausalCells` control**, not a fabricated new model or the actual eight-cell `LocalTaskRuntime`:

- Repository `spoonman136668-ai/Yggdrasil`, exact commit `992ef142aaa551156749a1de484a971b9a0c092f`, blob `f2fda603fbed965a3b4e7cc28844b2246bf8ac2b` at `yggdrasil/public_causal_cells.py`.
- Native *development-only* public-outcome API: `PublicCausalCells.observe(address,action,public_outcome)`, `choose(address)` with abstention, `snapshot`, `restore`. 16 address cells, two actions, two binary outcomes, 128 learned bytes and 164-byte SHA-256 checkpoint. This is an **explicit-memory conventional control** in Yggdrasil; **not** established as a local distributed self-improving NCA, nor production Yggdrasil, Wingless, or FORGE scientific acceptance.
- **AC-D5 reward credit is not promoted**. Existing failure of negative-only reward gating and action-local feature collisions (FORGE #1031) take precedence. This connector does not solve identifiability. This is only the first source-public **real observation → fitted existing cell state** check.

## External original source and protocol

Pin unchanged upstream `CausalAILab/Causal-Gymnasium` commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, tree `fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0`, committed DTR SHA-256 `e31eff82f862355057653d150967bb44a5ed57a6acaad57f7ecf2a551f6c6811`. Require qualified AC-14 report with original real DTR import, authentic OGBench wheel and original public-smoke PASS; authenticate both Yggdrasil exact Git commit/blob and complete DTR source before any new episodes.

Use existing preregistered public-only seeds **FIT `760000..760007` (eight episodes), DEV `760200..760203` (four episodes)**, with **VALID `760100..760103` deliberately UNTOUCHED**. All unknown-family/heldout/scientific first-use remain unknown and unused. Scripted, fixed **two binary actions per episode**, chosen without looking at outcome or hidden source: stage-0 action `episode_index % 2`; stage-1 action `(episode_index // 2) % 2`. Same action distribution, seeds, source calls, public inputs for candidate and controls. Exactly **12 additional genuine source-owned development episodes / 24 actions per OS**, if authentic import and original `Task(learning_regime=do)` / prohibited `ctf_do` check pass. Public smoke AC-14 seeds are separate.

A separate source subprocess must strip all raw `info` and expose **only** `stage, observation, action, next_observation, reward, terminated, truncated, valid_actions`. Source environment object, latent `u`, graph, privileged `get_graph`/`ctf_do`, and original code stay inaccessible to the learner process. If source subprocess fails mid-run, actual action and episode count is **UNKNOWN**, not fabricated zero. Never synthesize a substitute environment/reward or embed original DTR transitions into the tests.

The existing learner's address is the **public** `2*stage + observed_bit` (four cells of 16). Action is public binary. Outcome to fit at stage 0 is **next public observation**; outcome to fit at stage 1 is **terminal public reward**. This is a stated binary association/decision control, not evidence that a final reward is causally assigned to the earlier action. Pass only source-observed FIT events to `observe`, never DEV. Freeze `snapshot` before DEV and restore exact original 164-byte checkpoint. Verify no mutation during DEV and same `choose` recommendations after cold restore. Explicit matched fitted tabular counts `(stage,observation,action,outcome)` receive identical FIT events and tie the `PublicCausalCells` policy decision/abstention when its implementation is intact. Also report a pooled FIT arm-count control; **do not interpret off-policy recommendations as achieved causal reward**.

Use **zero user-adjustable hyperparameters selected from DEV**. No policies are deployed to the environment; fixed source-owned action scripts are the behavior policy and both learners are fitted offline on their public events. Evaluate blinded choice/abstention and pre-outcome predictions only; report matched tabular parity, prediction errors, no-policy-return status, wall and source/learner process resource cost where measured, checkpoint bytes, count of actual FIT/DEV events and negatives. Never claim superiority when a matched tabular control ties, when candidate abstains, or when unseen address/action evidence is insufficient. A binary context projection is a known **representation bottleneck**, not native causal discovery.

## Stop and science boundary

Any upstream/source sha drift, Ygg native Git/blob drift, missing packaging, unauthorized original permission, raw privileged field, false checkpoint, FIT/DEV overlap, source failure, or sample count mismatch must **fail closed** and retain the actual error. No mutation to Yggdrasil or Wingless repositories; no controller, policy, queue, accepted result, original FSA or first-use source birth. This is public DEVELOPMENT ONLY and is insufficient to establish unfamiliar-family transfer/retention or autonomous cognitive improvement.

**AC-15 gate criterion:** exact source-owned FIT and DEV transitions on both OS; original Yggdrasil development cell `observe` actually called and checkpointed/reloaded; an equal-information fully fitted tabular reference; strict no-DEV-training and no privilege. Full CI status and archived artifacts must be exact-commit checked. Otherwise report engineering blocked rather than invented native learning.

`AC15_EXISTING_LEARNER=YGG_PUBLIC_CAUSAL_CELLS_DEV_CONTROL`  
`AC15_FIT_EPISODES=8`  
`AC15_DEV_EPISODES=4`  
`AC15_VALID_EPISODES=0`  
`AC15_SOURCE_OWNED_DEVELOPMENT_ACTIONS=24`  
`AC15_PROTECTED_SCIENCE=NO_GO`  
`AC15_NATIVE_ARCHITECTURE_CHANGED=FALSE`
