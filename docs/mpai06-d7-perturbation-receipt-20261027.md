# MP-AI06 D7 query perturbation — 2026-10-27

**Execution:** [FORGE original isolated Windows runner #40541161304](https://github.com/spoonman136668-ai/FORGE/actions/runs/40541161304), completed SUCCESS. Workflow commit `f3bb0532f5042aec4c217663b49bb8f1dcaf41fe`.

Source: Mind-Palace D7 branch at `536d451c0e585d22e09a2aadecf2a6cefba76402`. The genuine pinned read-only MemorySnapshot baseline and the exact proposed D7 `normalized_recall` were executed on the original Windows runner using an ephemeral read-only checkout, unchanged original corpus/records and budget profiles. No external inference, no memory writes and no production activation.

## Development-only measurements

Twelve previously exposed D3 answerability cases underwent three deterministic query renderings: original, lowercase and mechanical suffix/singularization replacements. These 36 **correlated, partly duplicate variants** are not 36 novel questions, hidden holdouts or independently unfamiliar families.

| Metric | Baseline | D7 |
|---|---:|---:|
| Target source ID in retrieved records | 27/36 | **33/36** |
| Previously successful retrievals lost under D7 | — | **0** |
| D7 per-profile context budgets honored | — | **36/36** |

Exact markers: `MPAI06_D7_PERTURB_VARIANTS=36`; `MPAI06_D7_PERTURB_BASELINE_HITS=27`; `MPAI06_D7_PERTURB_CANDIDATE_HITS=33`; `MPAI06_D7_PERTURB_BASELINE_LOSSES=0`; `MPAI06_D7_PERTURB_BUDGET_PASS=True`.

## Limits and decision

- The three transformations are near-duplicates and original cases were publicly exposed before the test. Treat this as robustness smoke testing only.
- Scoring measures whether the preregistered evidence record ID is returned, not whether a model reads it correctly; no measured actual inference tokens, answer quality, latency or cross-agent generalization.
- This extends the already measured D7 11/12 vs baseline 9/12 source evidence coverage but is **not** independent scientific confirmation.
- Prior exact-source focused qualification, full Windows regression, and null results are preserved.
- **Decision:** `DEVELOPMENT_PERTURBATION=PASS`; `ZERO_REGRESSIONS_ON_EXPOSED_CASES=PASS`; `REAL_MODEL_ANSWER_GAIN=NOT_TESTED`; `SCIENTIFIC_FIRST_USE=NOT_TESTED`; `ADMISSION=NOT_AUTHORIZED`. D7 remains opt-in, draft, unmerged and disabled for default readers.
