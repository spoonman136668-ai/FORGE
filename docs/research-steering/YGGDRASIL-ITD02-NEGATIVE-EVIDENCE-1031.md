# F139 Yggdrasil development evidence — #1031

**Status:** Source-bound advisory handoff awaiting owner-qualified consumption. No live intake change, science, or model promotion.

## Decision contract for next *eligible* Yggdrasil development candidate

When the existing original-owner F139 idle intake next considers a fully authenticated Yggdrasil development candidate, inspect the following negative and structural evidence **before making a model-development priority choice**:

- Issue: [FORGE #1031](https://github.com/spoonman136668-ai/FORGE/issues/1031)
- Yggdrasil candidate source: `a39171a76d0d7817e3563682bb139a9d7ecf37c4`, file `yggdrasil/itd02_local_ring_memory_dev.py`. This is **not** the active `LocalTaskRuntime`.
- Multi-seed acting EMA superiority: [run 40653820848](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/40653820848) (Windows and Linux).
- Negative-only retention-gate ablation looked better on the original synthetic maps: [run 40654459488](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/40654459488).
- Same ablation **failed to generalize** to unfamiliar public observation/action mappings: [run 40661084507](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/40661084507). Across twelve scenarios: original A/B/A reward [284,-554,240]; negative-only [286,-710,-190]; independent EMA [1718,1494,1476]. Reject generalized-benefit claim.
- Action-local feature collisions at initial gate parameters: [run 40661579545](https://github.com/spoonman136668-ai/Yggdrasil/actions/runs/40661579545). There are six exact pair collisions across three heads under tested two-hop history pulses; whether learning resolves them remains **unproven**.

## Decision required

**Prefer an existing, eligible source-authenticated proposal addressing trainable action-local observation identifiability and transfer** over another isolated reward-rate/gate-credit tweak, if such a proposal exists and satisfies the existing original-owner authentication and lane-fairness policies. Otherwise explicitly defer as **NO_ELIGIBLE_NATIVE_CANDIDATE** instead of fabricating a candidate or accepting a negative experiment.

Require the eventual decision witness to identify source commit/tree, owner candidate PR, this evidence document's exact Git blob and original run URLs, steering manifest identity, selected/deferred reasoning, and both Wingless/Yggdrasil lane budget outcomes. If a candidate is chosen, qualify in the existing native worker and compare against independently acting, equally informed conventional learners before any promotion.

## Operational guardrail

The existing live steering reader `f139/nci04_research_steering.py` uses a four-file exact Git blob manifest pinned at commit `2a3c9453ba36c983b7b1dee0bb6ab1371108141b`. **This new file is not in that manifest and cannot be assumed live-consumed.** A future owner-qualified source change must explicitly authenticate and consume this handoff at the existing eligible planning boundary; never silently repin that manifest or edit ledger custody. Policy #807 remains the owner authority for eligible intake, not this document.

No protected original-world replay, new controller/scheduler/queue, accepted-ref mutation, paid API, or scientific first-use. Preserve the negative results and keep scientific status **NO-GO**.
