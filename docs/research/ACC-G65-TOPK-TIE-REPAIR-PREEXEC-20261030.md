# ACC G65 — corrective tie-resolution amendment before revised executable

**Original G65 run retained unchanged:** [GitHub Actions #41045759070](https://github.com/spoonman136668-ai/FORGE/actions/runs/41045759070), source SHA `a531e5d259be6474c880f4d2e08af2910b2d00fc` completed SUCCESS. Original artifact #12971509270, ZIP SHA256 `93fa1cc001ad997319e9e2fc837248e54f7b383dc6299b3da65a1561ae0eb8f3`, raw `g65_result.json` SHA256 `16021ea6669cbd3205d958231dcb7f685c6a95974f0025415e4b2eac836f6738`. It verified original model, original G64 output hashes, exact same prompt, and three numerical replicas in each of three modes.

**Critically observed before this amendment:**
- Standard SDPA one-token-at-a-time cached mode: logits at IDs **7866 and 29871 are both exactly 10.671875 in FP16** in all three repeats (signed margin 0.0). Its `torch.topk` output listed 29871 before 7866, **but `torch.topk` has no argmax-equivalent stable ordering guarantee on ties.** Hence the original `cached_top1_ids=[29871,29871,29871]` produced by `topk` is **NOT** evidence that the actual next-token greedy `argmax` selects 29871. The original G64 baseline `model.generate` had instead selected 7866.
- Cached 48-token chunk and full no-cache 1584-token SDPA each favored 29871 by **0.0078125** FP16 in all three repeats, reproducing the G64 fresh full forward.
- This already proves calculation-path-dependent **logit margin**, but until canonical `argmax` is explicitly measured the cross-path greedy token agreement cannot be classified.
- Original G65 output `numeric_comparison.classification=G64_NUMERICAL_PATH_OBSERVATION_DRIFT` is **not accepted as an inference** from actual greedy argmax. Preserve its raw data; do not erase or silently change the first receipt.

## Bounded source repair, after amendment and before revised run

Retain ALL original G65 source/corpus/model hashes, exact 1536-token prompt IDs and 48 common prefix, source revision, FP16 dtype, hardware/driver and software, `use_cache` modes, 3 repeats, numerical computation and frozen no-promotion rule. Replace `summarize_logits` interpretation only:
1. Report **actual `int(logits.argmax())`** as `greedy_argmax_id`; this is the canonical greedy selection. `torch.topk(...,2)` is **descriptive only**, using keys `topk_first_id`, `topk_second_id`, and may order tied values differently. Also count `exact_max_tie_count` via `torch.count_nonzero(logits == logits.max())` and report `float32`-converted values for two disputed IDs. No arbitrary tie-break, tolerance, float precision, logit perturbation or threshold change.
2. Replicate same exact three-mode, three-repeat test from one pinned original model and source. Define `cached_full_argmax_split_reproduced` using true `greedy_argmax_id` (cached must 7866, full must 29871) and separately report whether chunked joins full. On any unexplained drift of original model/sequence, BLOCKED.
3. Add source tests for tie semantics where possible (explicit `torch.argmax` rather than `torch.topk` for selection); preserve previous 10 tests and the added regression.
4. One corrected source-push isolated 30-minute execution, no retuning, no broad dataset bench, no novel science claim. Regardless of revised outcome G63 remains **FAIL NO-GO**, PR remains draft/unmerged, no FORGE owner/controller/main or native model change.

**Scientific scope:** Even if argmax switches from 7866 under token-by-token cached mode to 29871 under chunked/full, that is evidence consistent with FP16 rounding and kernel-shape differences under tiny margin. It is not proof of a specific kernel bug or universal accuracy advantage. The next original method should either handle numerical ties/guardrails under independent quality criteria or be rejected; do not retroactively pass G63.
