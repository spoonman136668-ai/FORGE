# G66 — Cross-gate evidence audit and production disposition (G54–G65)

**Classification:** Read-only historical receipt and source-provenance assessment. No model training, runtime activation, production inference, scientific first-use, controller/queue changes, merge, or acceptance authority. The existing experiment remains in draft PR #1250.

## Frozen input and verification

- Audit the **12 original authentic GPT-2 hosted-run artifact ZIPs**, one each G54–G65, with original GitHub Actions run URLs; independently verify each ZIP's SHA256, ZIP entry CRC, embedded result JSON's SHA256, original gate field, pretrained model revision and original pretrained weights SHA256. The exact original GPT-2 revision is `607a30d783dfa663caf39e06633721c8d4cfcd7e`, `model.safetensors` SHA256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Exception to preserve **literally**: the original G57 replay result embeds `gate: G51` because it reruns the frozen G51 benchmark. Label this run G57 with `embedded_receipt_gate: G51`; never rewrite the underlying evidence as if it claimed G57.
- Preserve authentic original CI/workflow URLs, source SHAs only when explicitly present in native receipt, all PASS/FAIL labels, each measured speedup, complete source ZIP/JSON digests and refusal of production promotion. Treat missing original receipt source SHA as missing, **never infer it from a branch**.
- G65 frozen authentic run #41045847620 measured **14/14 source controls PASS**, original greedy token parity PASS, prefill/decode overlap and freed-worker-slot execution verified; **performance FAIL**. Exact-head G65 full Linux and Windows run #41045855561 both **PASS** at `81c293922f3545f76368c66f6529d7442b3ff87d`. No branch change before this G66 contract was authored.

## Scientific disposition, not a new candidate

- G54/G55/G57 sequential cached GPT-2 prefix reuse showed positive frozen screens (~1.41×/~1.39×/~1.36×); G56 showed 0% reuse regression and G58/G59 show locality-dependent non-dominance. Keep distinctions among their different original workloads.
- G60/G61 authentic two-worker concurrent decoding **regressed** for high-reuse under serial coordinator prefill. G62 1.224× overlapped prefill screen used an extra producer worker (3 vs 2), so was not an equal-resource serving claim.
- G63 equal-resource screen **FAIL** on no-reuse and thrash controls, despite conditional high-reuse gains. G64 routing screen **FAIL** for high-reuse B3. G65 verified actual worker release, but its matched B3 high-reuse screen was 0.906662× vs no cache **FAIL**, and its B3 thrash result 0.977248× missed 0.98×.
- **Decision:** Preserve all improvements and negatives, reject cross-workload/concurrent production acceleration promotion, and record native Wingless/Yggdrasil transfer as **UNVERIFIED/NOT TESTED**. Do not pool incomparable medians or retrofit failed thresholds.
- **Next evidence boundary:** only an independently preregistered natural held-out concurrent serving study versus an optimized serving/batched baseline with equal CPU, memory, energy, token correctness and honest launch/queue costs could materially improve acceptance prospects; stop repeated synthetic scheduler tweaks until this route exists.

## Durable implementation and limitations

- `research/llm_g66/g66_verified_evidence.json` retains a compact machine-readable evidence index with 12 exact archive/JSON SHA256s, original URLs, model identity, selected original performance measurements, and protected negative acceptance decision.
- `research/llm_g66/g66_audit.py` checks that index **offline without contacting models, paid APIs, or controllers** and can **optionally** reverify every original archive byte-for-byte with `--archive-root <directory>`. If the original archives are not present, hosted source-only tests verify only the indexed values and invariants; they cannot claim independent archive-byte revalidation. This distinction is explicit.
- GitHub Actions artifact retention is finite. The digest+summary index and PR evidence comments do not replace every original uncompressed trial record. Do not claim an indefinite upstream signed artifact archive.
- The reproducible audit was first tested locally against all 12 original downloaded ZIPs and 10 unit tests, before GitHub publication. Any audit discrepancy is FAIL, not a reason to erase negative results.
- Keep PR #1250 **draft/unmerged**. Separately qualify full Linux/Windows source CI on resulting G66 SHA. No automatic FORGE research-ingestion/production activation.

**Scope frozen before adding G66 executable/manifest files.**
