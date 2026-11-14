# ITD-02 two-bank causal-reversal DEV — actual original source-free result

**Decision: `ITD02_TWO_BANK_DEV_SIGNAL_UNVERIFIED`; not a scientific pass or autonomous improvement.**

## Source custody and method

- Original existing draft PR [#1730](https://github.com/spoonman136668-ai/FORGE/pull/1730). Frozen prospective protocol commit **before source/fixture** `6548cc25d66034db4ac0a90263444ca090b6f319`, doc blob `c1a601437be834ae1549a1ca3c5a2c40d47f22e2`; preexisting earlier reversal negative [comment #6826965806](https://github.com/spoonman136668-ai/FORGE/pull/1730#issuecomment-6826965806) untouched.
- Original numerical source Git blob `34ef34a5508fb1c5c9cac727e3d12024bc91dd09`; fixed test fixture/control Git blob `d2f4ba496c9329d46f6cd2f353548fc1fa5cffd1`. Original upstream standard-library action-specific ridge `research/itd02_online_consequence_memory.py` unchanged, Git blob `d37303b967c5fdb587bdeeb02056ee45012d7f64`.
- Genuine GitHub-hosted [run #43278498293](https://github.com/spoonman136668-ai/FORGE/actions/runs/43278498293), exact temporary source SHA `53dcecfc85f48fb45bce3be39269fe32b2600d24`, dedicated Linux job `131393201307`: **6/6 unittest PASS**; dedicated Windows job `131393201162`: **6/6 unittest PASS**. Both source-checked preregistration/source/tests Git blobs and printed identical scalar results. The temporary workflow edit causes unrelated original G145 native PR scope rejection and is removed in the final branch head. Temporary whole-run success **must not be claimed**.

## Frozen source-free result (identical on Linux and Windows)

Each of 4 deterministic fixture schedules uses `[0.,0.]` as the sole public context, 160 *delivered synthetic* feedback observations total, alternating physical-action labels and changing effects A(+1,-1) → B(-1,+1) → A → B without passing a phase label to any model. The proposal payoff is an **offline hypothetical choice-payoff**, NOT actual executed actions, unfamiliar physics, independently observed causal experiments or protected scientific first-use. Each model sees the same 160 delivered action/outcome rows. Policies scored after initial 2 observed action pairs of each phase, 72 total offline decisions. Noise magnitudes fixed at [0.0, 0.04, 0.08, 0.12] before code.

| Model / negative control | Synthetic hypothetical return, every fixture (max 72) |
|---|---:|
| Two-bank stable/working memory | **+72** |
| Fully fitted switching-Bayesian/HMM-style observed-outcome model, hazard=.02, likelihood σ=.25 | **+72** |
| Rolling recent 8 per action ridge | +62 |
| Fixed 32-event periodic reset negative | +46 |
| Rolling recent 32 per action ridge | +44 |
| Rolling recent 16 per action ridge | +38 |
| Unmodified full-history ridge | +24 |
| No-feedback action0 negative | +24 |

The two-bank candidate switches to the correct action within the frozen four-pair bound at the first reversal, familiar-mode recurrence, and return to B **in 4/4 fixtures**, meeting preregistered 3/4. Each bank retains 52 observations per action (A) or 28 per action (B). One externally SHA256-bound snapshot after first B cold-restored at 112 completed events; subsequent 48 newly delivered feedback events maintained identical cold/warm checkpoint bytes, predictions and proposals. Deliberate tampering, external hash mismatch, stale checkpoint, invalid event sequence, nonfinite consequence and action invalidity were refused. The earlier cumulative model's wrong-action reversal negative was reproduced unchanged. No hidden regime labels entered candidate or fitted controls.

Absolute per-fixture wall time on GitHub-hosted Linux for **the entire multi-model test trial** approximately 0.028–0.030 seconds; Windows ~0.056–0.065 seconds. Not matched per-model training/inference timing or a proved efficiency gain. Peak RSS, FLOPs and independent off-host recovery were **not measured**. The model is a deterministic two-bank ridge gating mechanism; switching-Bayesian **tied** at the maximum, so **no architectural superiority** can be asserted. The source fixture deliberately makes regime effects symmetric and easy; it is not a diverse unfamiliar-family causal benchmark.

**Frozen decision:** `ITD02_TWO_BANK_DEV_SIGNAL_UNVERIFIED` strictly on this small synthetic class, **`SCIENTIFIC_PASS=NO`**. ITD-02 scientific learning/transfer/interference beyond the same synthetic grammar, real autonomous intervention value, whole-process efficiency and native Wingless/Yggdrasil integration remain unverified. Original F57 untouched and blocked by independent FORGE FSA #83; all F51/F56/F58 NO_GO results preserved.

## Engineering disposition

Temporary `.github/workflows/qualify.yml` job is removed in final source-only restore to original Git blob `8b6710df902710d088fe9658da718d22244e5151`. Mandatory **final exact-SHA original Linux/Windows full 8/8 regression** must be independently observed; it is not proven by the temporary-job execution. Keep PR draft/unmerged, no new controller/runner, owner, release, scheduler, paid API, project-lane changes, model promotion, scientific original execution or deployment.

---

## P1 third-mode fail-closed correction — independently validated after initial scored fixture

A distinct **safety/negative-control flaw was found after the four original synthetic fixture results**, not concealed or reclassified. Before correction, when a genuinely **third** effect regime made both retained banks wrong, the algorithm could pick the alternative merely because it was *less wrong*. This violated the prospective requirement to preserve old banks and abstain under uncertain third-state evidence. The original 4-noise results above remain the immutable first fixture scores.

The scoped correction adds a second gate to alternative-bank recall: its absolute observed-consequence error must be **less than the existing 0.9 threshold**, not merely at least 0.9 better than the current bank. This introduces **no retuning of the original success thresholds, no changed original fixture/noise values, no novel original data, no F57 seed consumption, and no new controller or FSA permit**. New adversarial test: after authentic source-free A/B learning, an unlabeled third consequence C(+3,−3) for two action pairs leaves both old bank checkpoints byte-unchanged, keeps active B, marks exactly four observed events `unresolved`, preserves all observed history and allows exact SHA-bound cold restoration. No third-world science claim.

**Final scoped source:** `research/itd02_two_bank_reversal_dev.py` Git blob `f231b57237f1276a02d7ca239e3887fea53c4bea`; focused tests Git blob `da3d008ee0ab170a3fd1e85471d7cdd4d5c6ea89`. Actual two-OS focused temporary-job execution: [run #43279464074](https://github.com/spoonman136668-ai/FORGE/actions/runs/43279464074), Linux job `131396564711` **7/7 PASS**, Windows job `131396565212` **7/7 PASS**, including third-mode negative, no FSA use. Crucially, all previously reported 4 fixture payoffs and 48-event cold continuations **remained exactly the same** on both operating systems. The temporary whole workflow is expected to have unrelated G145 altered-harness-scope failures; its aggregate success is **NOT** claimed.

Original byte-exact workflow restoration is mandatory and performed in the separate final commit. Qualification on that separate final exact source **must be verified again** with original native full Linux/Windows regression; the previous [8/8 PASS #43278829023](https://github.com/spoonman136668-ai/FORGE/actions/runs/43278829023) belongs to the prior pre-correction SHA `7028842d6f278665685e3ae845e743a9cbf70abf` and cannot substitute for final post-correction qualification.

**Final scientific classification unchanged:** two-bank candidate tied the strong Bayesian comparator at 72/72 on deliberately simple familiar synthetic effect-reversal grammar. No independent scientific gain, novel-family transfer, intervention-selected physical consequence, cognitive generality, RSI or deployment.
