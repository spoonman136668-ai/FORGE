# MP-AI05 — matched legacy versus tiered retrieval, 2026-10-27

## Verification

Real FORGE isolated Windows runner, same pinned private Mind-Palace corpus SHA `7ad7230a82e3c748aa5336b7288ad2b45d42630c`, same frozen 18-case fixture. The comparative workflow uses source-original `tools/context-pack.ps1` with seven records maximum and candidate `tools/context-pack-tiered.ps1` with five PRIMARY records plus mandatory governance. The candidate's real `model_context` and the legacy record statements are counted in UTF-8 bytes. Private source cloned only inside runner scratch and deleted; no private records were exported; no model inference.

- Successful original real-corpus retrieval contract qualification: [run #40501678821](https://github.com/spoonman136668-ai/FORGE/actions/runs/40501678821). Tiered contract: 18/18 cases, PRIMARY precision 91.3043%, required-fact coverage 100% **across PRIMARY and SUPPORT**, combined relevance recall 100% **across PRIMARY and SUPPORT**, proxy context savings 85.8086% relative to the benchmark's larger candidate set. These metrics are not from the paired legacy comparison.
- First paired run [#40506779037](https://github.com/spoonman136668-ai/FORGE/actions/runs/40506779037) exposed invalid zero-byte tiered accounting and is **not** authoritative for byte comparisons.
- Corrected paired run: [#40506908983](https://github.com/spoonman136668-ai/FORGE/actions/runs/40506908983) PASS, source workflow commit `2f665660a24ec93f908df7195fd14f9f878db1f5`.

## Corrected comparable paired metrics

| Metric | Legacy | Tiered default |
|---|---:|---:|
| Cases evaluated | 18 | 18 |
| Required fact IDs present | 19/20 | 20/20 |
| Relevant IDs present | 30/41 | 30/41 |
| Forbidden IDs returned | 0 | 0 |
| Records selected (including governance) | 126 | 128 |
| Model-facing UTF-8 statement bytes | 36,528 | 34,060 |

Tiered saves **2,468 bytes (6.76%)** of model-facing statement content and recovers one additional required fact in these 18 frozen cases. This is a **paired retrieval-context benefit**, not a measured response-token or answer-quality benefit. Context byte totals are not exact model token counts. The two implementations have different ranking and governance inclusion rules; this is a practical product-baseline comparison, not an isolated mechanism ablation. The test fixture is existing, not newly independent held-out scientific evidence.

## Boundary

`PAIRED_CORPUS_RETRIEVAL=PASS`; `REQUIRED_FACT_COVERAGE=20/20_VS_19/20`; `MODEL_CONTEXT_BYTES=34060_VS_36528`; `REAL_MODEL_CALLS=0`; `UNFAMILIAR_TRANSFER=NOT_TESTED`; `SCIENTIFIC_ACCEPTANCE=NOT_TESTED`.

Keep both the prior positive synthetic mechanism result and equal-context null experiment as historical records. Do not promote based only on this benchmark; next material gate is a bounded, authorized actual-answer comparison with source-grounded adjudication. No accepted `.ice` change and no new credentials/controller.
