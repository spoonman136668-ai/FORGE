# G103 original GPT-2 structural-sharing diagnostic — NO_GO

**Original-model engineering: PASS. Frozen research verdict: `STRUCTURAL_NO_GO_DIAGNOSTIC`.** No production or protected held-out evaluation was performed.

## Provenance and execution

- Frozen P1 source SHA `2a6ab9ff82eb8f200a0eeeaba53d033a6b829a07`.
- Focused Linux/Windows PASS: [41752321420](https://github.com/spoonman136668-ai/FORGE/actions/runs/41752321420).
- Mandatory full Linux/Windows PASS: [41752328124](https://github.com/spoonman136668-ai/FORGE/actions/runs/41752328124).
- One-shot real original-model run [41755243212](https://github.com/spoonman136668-ai/FORGE/actions/runs/41755243212): source admission PASS, original-model measurement PASS, independent JSON invariant/decision verifier PASS.
- Original run trigger `a539af42427c457f049f4748b3484d3f560c04db`; push trigger disabled via `5f26a5eae7a6de5549b0f07c227e27d9126b424c`.
- Saved artifact ID `13288665226`: `cpu-g103-original-gpt2-structural`.
- ZIP SHA-256 `36ea7d16dfec8ae6e3bc39d4cd4c0eb224b8bfb3b43f2b7501dfae06804fc6fa`.
- Raw receipt SHA-256 `c9f680ccf8a15400ad3c89f97ec5b158242f0d34fe991147efeefdc6efbd0a21`.
- Environment artifact SHA-256 `f9b4da9b4bf8764af620d8d15b9676eec020b8d74c0a6def13a7cf2f214335ea`.
- Original GPT-2 weights SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Eight real original GPT-2 forward passes; three groups: identical prefix duplicate, distinct related one-token variants, unrelated original G95 templates. No question dataset was loaded.

## Frozen original-model measurements

Bytes, inclusive of modeled block payloads, block metadata, all manifest references, and per-state hashes for each structural arm.

| Group | Raw | Standalone zlib-6 | Fixed 256-byte block sharing | Adaptive 64/256/512-byte block sharing |
| --- | ---: | ---: | ---: | ---: |
| Identical | 39,075,840 | 36,262,590 | 29,917,504 | 28,896,008 |
| Related | 58,613,760 | 54,393,684 | 74,933,280 | 73,132,784 |
| Unrelated | 63,037,440 | 58,496,959 | 83,520,288 | 81,895,039 |

All three groups and both sharing modes recovered every exact FP32 KV state and passed identity validation. Original authentic per-state bytes and prefix lengths were recorded.

Related-prefix adaptive sharing was only **2.40%** smaller than fixed-block sharing, but **34.45% larger** than the independent zlib-6 control and **24.77% larger** than raw. The frozen rule required adaptive sharing to be at least 10% smaller than *all* three comparison methods for **distinct related prefixes**. It failed.

### Time and metadata

- Related group adaptive build wall: `11,855,667,271 ns` (~11.86 s), fixed build wall `309,405,478 ns` (~0.31 s); **not** an end-to-end inference benchmark.
- Related adaptive pool: `195,506` unique blocks and `206,764` manifest references; modeled metadata `17,745,008` bytes.
- Related fixed pool: `216,024` unique blocks, `228,960` references; modeled metadata `19,631,136` bytes.
- Process RSS is sampled, not a measured full transient peak. Python object allocator and transient buffering overhead were *not* included in the modeled storage totals; adding them is not expected to rescue an arm already exceeding raw and compressed controls.
- Both sharing methods beat independent zlib only on the duplicate-prefix positive control. This is not novel cross-prefix discovery.

## Decision

`STRUCTURAL_NO_GO_DIAGNOSTIC` is an authentic negative result. Retire this specific fixed/adaptive exact-identity block partitioning representation. Do not tune chunk sizes after viewing results or claim that duplicate-only reuse generalizes to distinct prefixes. No protected cohort, model/runtime integration, or scientific promotion.

**Recommended distinct next research step (not yet executed):** Return to causal computational bottlenecks rather than further granularity in KV byte storage; measure original GPT-2 profiler attribution under an explicitly frozen CPU workload, then choose a truly differentiated compute-side mechanism with a conventional control and end-to-end criteria. Avoid relabeling known deduplication/compression as novelty.

**Disposition:** source admission PASS; infrastructure PASS; strict reassembly PASS; scientific storage NO_GO; runtime performance NOT EVALUATED; held-out untouched; production unchanged.
