# E-D129 — prospective MiniGrid Memory scientific-qualification request (2026-10-30)

**Disposition: PROPOSED / NOT FROZEN / NOT APPROVED. This is an independent-review packet, not authorization to run a scientific benchmark, unseal a holdout, train models, merge PR #1194, or promote FORGE research.**

## 1. Authenticated starting point — engineering evidence, not scientific success

- FORGE E Research draft PR [#1194](https://github.com/spoonman136668-ai/FORGE/pull/1194), source head `3733a4f5bcbd5728cd8f31c81abc5860e0944ab0`, unmerged. Source file `research/e_research/ed116_memory_causal_junction.py`, blob `81e121942d713c29714b084de0cb085821fd1def`.
- [GitHub Actions run #41154473127](https://github.com/spoonman136668-ai/FORGE/actions/runs/41154473127): Linux job `124398300719` and Windows job `124398300526` **completed/success**. Original Linux stdout was retrieved and copied into the bounded [E-D127 PR evidence](https://github.com/spoonman136668-ai/FORGE/pull/1194#issuecomment-6537151438); include immutable per-trial action/prechoice SHA-256 digests there.
- Four **previously exposed** engineering seed pairs: 4/4 matched and terminal; cue-dependent decision differences 3/4. Retained register positive reward 4/4, fixed-north erased control 1/4. Mean retained reward `0.9800295858`, erased `0.2452071006`, paired gain `+0.7348224852`; gains 3, ties 1, losses 0. This is a hand-engineered source-geometry-informed controller, not a trained native intelligence architecture, independently grounded model of the world, or untouched holdout.
- The Linux and Windows original CI logs also emit `RAR_G111_PERIODIC_20MS_SHORT_CHILD_CAPTURE=FAIL_CLOSED_UNVERIFIED`. The overall jobs passed; preserve this separate diagnostic qualification caveat.
- Original DoorKey run artifacts remain unverified under existing issue [#1245](https://github.com/spoonman136668-ai/FORGE/issues/1245). Do not conflate the Memory CI PASS with DoorKey validation.

## 2. Source and cohort proposal (reuse; do not silently redefine)

Use *only* the pre-existing E-D100 candidate manifest `research/e_research/ed100_prospective_memory_protocol.py`, blob `bbbc7d21c33778c72a1183f29f903e3ba93bb458`:

| Lane | Environment | Proposed episodes/seeds | Permitted use before approval |
|---|---|---|---|
| FIT | `MiniGrid-MemoryS11-v0` | 100 predeclared seed IDs | **None**; protocol review only |
| VAL | `MiniGrid-MemoryS13-v0` | 30 predeclared seed IDs | **None**; protocol review only |
| DEV shift | `MiniGrid-MemoryS13Random-v0` | 30 predeclared seed IDs | **None**; protocol review only |
| Sealed HOLDOUT | `MiniGrid-MemoryS17Random-v0` | 60 reserved seed IDs | **PROHIBITED** absent separate independent first-use approval |

The existing four E-D116 engineering seed IDs are outside those candidate ranges but already exposed; they **must not be reclassified as unseen validation or holdout evidence**. Merely writing down seed lists does not constitute an approved or sealed registry.

Upstream Farama MiniGrid commit `7f5853792ea7f04f75614661006d87fcf949f26d`, original `minigrid/envs/memory.py` Git blob `660b0a1b769948034c87bb421759c2b9a4f24548`, version `3.2.0`; pin the complete runtime dependency environment, wrappers and qualification harness before any scientific execution. Source uses `max_steps=5*size**2` unless explicitly overridden: S11=605, S13=845, S17=1445. The current E-D100 `max_evaluation_steps_per_episode=1500` is a **proposed ceiling**, not proof of equal effective interactions. Log the environment's actual episode cap and stop reason on every arm.

## 3. Preregister the question and methods before any cohort exposure

**Primary question:** Under equal permitted observations and action opportunities, can an agent retain the initial cue after it leaves sight and thereby improve end-of-corridor correct-target selection and episode return relative to a causally matched cue-erased controller, beyond a task-specific, source-informed hand-engineered heuristic?

**Required comparisons:**

1. **Identical-policy cue-memory ablation** — same navigation and decision logic, same permitted observation prefix and action budget; delete only the retained cue before the choice. This isolates a causal storage mechanism, *not native learning*.
2. **Reactive/no-memory control** — current observation and legitimate task instructions only, with frozen rule choices; no privileged cue, location, map or target.
3. **Explicit last-visible-cue control** — small engineered cache, fixed before VAL/DEV; disclose task geometry assumptions and capacity.
4. **Matched history-window conventional model** and **trained recurrent control** — same frozen training interaction stream and evaluation observations; independently qualify training loop, model count, checkpoints and deterministic seeding.
5. **Native Wingless and Yggdrasil**, as **independent separate candidates only when authentic implementation/training/adapters exist and are independently qualified**. Do not substitute a generic transformer, a shared learning core, precomputed oracle or named placeholder and claim native integration.

**Controls:** Use the official observable `image`, `direction`, `mission`, rewards, `terminated`, `truncated`; only `reset`/`step` to acquire task evidence. Prohibit `env.unwrapped`, `grid`, `agent_pos`, `success_pos`, `failure_pos`, RNG peeks, future frames or any action chosen using unobservable world coordinates. An observer-based cue label derived from prior knowledge of source geometry is *hand-engineered*, not acquired learning. Predefine how original cue authentication, ambiguity/abstention, decision-junction identification and cold replay of an observation prefix are validated. Distinguish episode-state replay from persistent knowledge across process restart; the latter needs a genuine saved learner checkpoint and no future observations.

## 4. Equal information, bounded budgets, resource provenance

**Currently unverified; must be fixed in a reviewed, signed protocol before the first prospective run.** E-D100 proposes 100 training episodes/model and 1500 maximum evaluation steps/episode. These are not approved thresholds or actual resource-accounting receipts. In particular, the environment may terminate earlier.

Pre-register exact per-method and per-split ceilings and report **actual** values for: episode count, legal observations, environment interactions, action count, effective environment horizon, training updates, parameters/persistent-state bytes, optimizer and inference operations (FLOPs if measurable or a documented proxy), CPU time, wall time, peak process RSS, hardware/OS/toolchain and energy if legitimately measured. A model with a higher update count or longer compute is not automatically equivalent simply because episodes were capped. Freeze a bounded compute/resource-matching policy, deviations/abort rule and identical final regression requirement. No retrospective budget equalization or tuning on DEV/holdout labels.

Reuse identical initial environment seed *within each paired arm* only after the cohort and split custodian has separately approved exposure; record the exact matched observation/action prefix where causal comparison is claimed. Frozen, nonadaptive action/observation interface per benchmark; training may only use approved FIT. VAL selects prespecified hyperparameters with logged multiplicity; DEV shift tests unfamiliar generalization without further fitting or repeated threshold shopping. The HOLDOUT is sealed pending independent first-use witness and approval.

## 5. Metrics, negatives and frozen admission rules

- **Primary outcomes proposed:** paired target-selection success rate and mean episode reward/return, each with per-seed provenance; valid terminal-pair count and cue-specific benefit. Report all failures, incorrect turns, abstentions and truncations, including zero valid-pair counts. Do not discard failures to report only matched successes.
- **Secondary:** actions to terminal, pre-choice observability and delay, deterministic replay, process restart retention when applicable, parameter/state budget, training/inference CPU and memory. Disclose any navigation advantage that is not memory-causal.
- **Scientific analysis:** predefine minimum meaningful improvement, permitted confidence/uncertainty analysis, multiplicity adjustment, confidence-interval or paired-test method, robustness criteria and decision thresholds **before** seeing prospective outcomes. **No numerical admission threshold is approved by this document.**
- **Mandatory negatives:** random/no-memory control; incorrect-cue intervention; erased-memory intervention; source-geometry/position-shift ablation; trained conventional matched controls; explicit unfamiliar-family transfer if the scientific claim includes transfer. Preserve E-D80/81/82 and all E-D116 caveats; no selection based only on positive exposed cases.
- **Falsification triggers:** data leakage, mismatched observation prefixes, hidden-state access, resource-budget mismatch, cross-split contamination, unqualified original-source/runtime, changed source SHA after qualification, absent independent witness, empty valid cohort, unplanned holdout access or undocumented model architecture => **FAIL_CLOSED/UNVERIFIED**, with no scientific promotion.

## 6. Required independent freeze and receipts (all still missing)

The existing offline `research/e_research/ed103/audit.py` (Git blob `9ee5bc417d45d15890daf2f03ffafe406959817d`) accepts syntactically complete data only as `SCHEMA_COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION`; **it cannot authenticate approvals or attestations**. Do not create a duplicate acceptance authority.

Approval reviewer must establish and record: (i) authorized frozen FIT/VAL/DEV identities and separately sealed HOLDOUT custody, (ii) strict source/tree/CI dependency and runtime hashes, (iii) frozen policies, baselines, model implementations and interfaces, (iv) numerical acceptance thresholds and all budgets, (v) approved first-use timing, (vi) independent original logs/witness receipts, and (vii) native Wingless/Yggdrasil interfaces separately if later relevant. If a document says approved without verified approval evidence, it remains **NOT APPROVED**.

### E-D129 verdict

| Gate | Verdict |
|---|---|
| Prior E-D116 exposed-seed engineering reward improvement | **PASS — verified** |
| Original source and proposal identity readback | **PASS — read-only authenticated** |
| Proposed independent prospective protocol description | **PREPARED — ADVISORY ONLY** |
| Resource/observation equality under trained comparisons | **UNVERIFIED** |
| Independently signed/frozen splits, budgets, and thresholds | **NOT APPROVED** |
| Prospective FIT/VAL/DEV experiment | **NOT RUN** |
| Sealed HOLDOUT and first-use scientific acceptance | **PROHIBITED / NOT ACCEPTED** |
| Native Wingless/Yggdrasil model learning and transfer | **NOT DEMONSTRATED** |

**Next authority boundary:** an independent scientific reviewer may approve and freeze the qualified protocol through the established project mechanism. Only after that, an existing authorized qualification runner may execute the bounded prospective FIT/VAL/DEV plan; HOLDOUT needs its own first-use gate. Do not alter FORGE production autonomy, CKB-plane, trading systems, or research promotion.
