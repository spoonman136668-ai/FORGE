# CPU G96 — deterministic cohort and traffic manifest contract

Parent preregistration: `856da2432ef4163938711bcb6b0369fbfab2ccbd`. This contract is frozen before any G96 original-model measurements. No development or held-out results have been inspected.

- Original data: pinned `openai/grade-school-math` GSM8K source, revision `3101c7d5072418e28b9008a6636bde82a006892c`, raw SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Original model: pinned GPT-2 revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, FP32 original weights SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Rank construction: identical to G95 `rank_original`, `SHA256(SEED + UTF8(question))` sorted ascending with source-row tie break, deduplicating exact questions; freeze G95 `SEED` constant by source blob `b401c86e4dff2f25eb995a47ba58884838f232eb`. Reject source, raw file or rank contract drift.
- Development/calibration cohort: ranks **276–287** inclusive (12 unique original questions).
- Final held-out cohort: ranks **288–299** inclusive (12 unique original questions). Do not inspect outputs, tune thresholds or select policy on this cohort. Reject any intersection with G68 [0,11], G70 [12,23], G95 [264,275], and any other previously screened exact question hashes found in repo evidence. If additional prior screened ranks overlap, fail admission and re-preregister before seeing outcomes.
- Four distinct G95 instruction-prefix texts, unchanged tokenizer and exact-key semantics. Three questions per prefix; eight greedy generated tokens/request; four paired repetitions.
- Traffic strata (each repeated 4×): (a) round-robin 4-prefix, (b) contiguous 4-request bursts by prefix, (c) working-set overflow with eight distinct prefix keys derived by deterministic duplication of the four original prefix texts with a fixed, preregistered marker suffix, (d) deterministic mixed locality with prefix index sequence seeded by `SHA256("CPU_G96_TRAFFIC_20261031")`. All arms use identical streams. Each stratum has 48 requests per repetition, four repetitions, and fixed sequence digest emitted before running the first arm.
- Freeze the exact byte sequences of overflow-prefix markers and mixed-locality generator implementation in source and focused tests before final original-model execution; changing them after results invalidates qualification.
- Policies: no cache, capacity-four LRU, admit-on-second-use, bounded frequency-aware, cost-aware admission; fixed 4-entry and 86,114,304-byte resident KV ceilings. Track all cache bookkeeping and request-copy overhead.
- Run the development/calibration cohort before final held-out. Lock any cost calibration using development data only, commit its values and immutable receipt, and require a fresh exact-head source-admission run before the held-out benchmark.
- Held-out acceptance: all frozen G95 criteria, per stratum, with no aggregate-only exemption, no waiver of worst paired speedup, and exact token parity.
- Mandatory final Linux and Windows regression and immutable repository receipt. No production or scientific acceptance.
