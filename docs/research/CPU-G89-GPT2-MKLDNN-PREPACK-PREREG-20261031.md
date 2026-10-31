# CPU GPT-2 G89 — explicit oneDNN prepacked dense projections after exact Conv1D conversion

**Prospective preregistration — 2026-10-31.** This contract is committed before G89 executable source, tests, workflow or model measurement. CPU LLM evaluation only; separate from GPU ACC, FORGE controller/autonomy and native Wingless/Yggdrasil research.

## Motivation and distinct hypothesis

G88 established that toggling `torch.backends.mkldnn.enabled` did not provide an observable oneDNN execution-path distinction for this original GPT-2 implementation. Its run was blocked before timing. It did not test explicit MKLDNN prepacked linear modules.

The original Hugging Face GPT-2 uses custom `Conv1D` projection modules whose stored weight orientation is `[in_features, out_features]`. PyTorch 2.5.1's `torch.utils.mkldnn.to_mkldnn` explicitly converts standard `nn.Linear` and convolution modules, not this custom GPT-2 `Conv1D` type. G89 therefore tests a representation-preserving adapter: replace each original GPT-2 `Conv1D` projection with a mathematically equivalent `nn.Linear` (transpose the stored weight into Linear's `[out_features, in_features]` orientation, copy bias unchanged), then explicitly convert supported Linear modules using the pinned `torch.utils.mkldnn.to_mkldnn` FP32 path.

Hypothesis: real oneDNN `aten::mkldnn_linear` dispatch across the original GPT-2 dense projections can improve end-to-end cached CPU decoding enough to pay for the conversion/prepacking cost, while retaining exact greedy token outputs.

This is a different intervention from G88's Boolean MKLDNN toggle and G87's Inductor graph compilation. No quantization, model training, approximation, changed tokenizer, changed sampling, synthetic kernel benchmark or alternate weight file is permitted.

## Immutable identity and evaluation cohort

- Exact qualified CPU baseline: G70 commit `20a540d0241519e2e9d90ace868ffd6db60bd065`; all G54–G70 source files must remain byte-identical.
- Original pretrained `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`; safetensors SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Original MIT GSM8K test source commit `3101c7d5072418e28b9008a6636bde82a006892c`; raw dataset SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Exact G82/G86/G87/G88 SHA-rank protocol and seed `G68-GPT2-HELDOUT-20261030:`. Select ranks **192–203 inclusive** (12 unique source questions) after G87 168–179 and G88 180–191. Verify G68 and G70 partition contracts and all earlier selected rank intervals are disjoint. No cohort replacement, prompt reuse or post-result reselection.
- Preserve G55 original prompt prefix, first 64 question token IDs (`add_special_tokens=False`), unchanged FP32 pretrained values, cached greedy decoding, and exactly eight new tokens.
- Verify the original `Conv1D` layer weight/bias values against the converted `nn.Linear` representation exactly (transpose is a layout operation, not a numerical transform); verify every converted module's dense logical weight/bias equals the corresponding original. No parameter training, calibration or weight mutation.

## Runtime and matched experiment

- Native `ubuntu-24.04` x86_64 CPU; Python 3.11; PyTorch `2.5.1+cpu`; Transformers `4.48.3`; huggingface-hub `0.30.2`; safetensors `0.5.3`; tokenizers `0.21.1`; psutil `7.1.3`. Verify package versions, `torch.version.cuda is None`, `torch.backends.mkldnn.is_available()`, `pip check`.
- Same fixed affinity of three logical CPUs for both arms; PyTorch intra-op threads=2 and inter-op threads=1, set and read back. No GPU.
- Arm A: original pretrained model, original custom `Conv1D` projections, ordinary FP32 CPU execution.
- Arm B: independent copy of the same original pretrained model; replace each original GPT-2 `Conv1D` with an `nn.Linear` that implements the exact same affine map; verify full logical weight/bias equivalence; prepack those linears through `torch.utils.mkldnn.to_mkldnn(model, dtype=torch.float32)`. This explicit conversion, not a global MKLDNN flag, is the candidate intervention.
- Measure all model layers and attention paths. Candidate must dispatch real `aten::mkldnn_linear` events during authentic full-request warmup and profiling. Baseline must dispatch zero `aten::mkldnn_linear` events. Capture `torch.profiler` CPU event keys/counts (not only a config flag) and freeze them in the receipt. Candidate must execute oneDNN prepacked linears for the original GPT-2 projection paths; missing or ambiguous dispatch is `BLOCKED_IMPLEMENTATION`.
- Warm both arms identically outside timed requests. Candidate conversion/prepacking wall time and parameter preparation time are measured separately and fully included in amortization. Do not hide or discard it.
- Two primary arms: `original_conv1d2` and `mkldnn_prepacked_linear2`. Both use same model outputs, request tensors, KV-cache semantics, greedy argmax and eight-token response. Rotate paired order deterministically.
- Exactly 12 original prompts × 4 paired repetitions × 2 arms = **96 authentic full responses, 768 generated tokens and 48 paired records**. Require token-ID equality for all eight positions in every pair/repetition. No outlier deletion.
- Record model/data/source identities, converted layer inventory, original and converted parameter hash receipts, profiler operator names/counts, exact thread/affinity settings, conversion/prepack time, per-request wall/process CPU timings, sampled RSS, output/input hashes, per-pair records and environment manifest.
- Report warmed median, p95, worst paired ratio, sampled RSS and total process CPU. Charge the entire one-time conversion/prepack cost; report break-even full responses and 1,000-response total time ratio.

## Frozen acceptance

`MKLDNN_PREPACK_PASS` requires every condition:

1. Exact immutable model/dataset/source identities, disjoint ranks 192–203, native CPU runtime, fixed three-core affinity and all 48 paired records.
2. Every original GPT-2 `Conv1D` projection is represented by an exactly equivalent Linear affine map before MKLDNN conversion; original versus converted logical weight/bias values are exactly equal.
3. Actual candidate `aten::mkldnn_linear` profiler execution events > 0 and baseline `aten::mkldnn_linear` events = 0 on authentic GPT-2 full requests.
4. All 96 responses and all 768 tokens have exact greedy token parity.
5. Warmed median full-response speedup >= **1.15×**.
6. Minimum individual paired speedup >= **0.90×**.
7. Candidate p95 latency / baseline p95 <= **1.10×**.
8. Sampled maximum RSS ratio <= **1.10×**.
9. Total process CPU ratio <= **1.25×**.
10. One-time conversion/prepack <= **300 seconds**, break-even <= **1,000** full responses, and 1,000-response total wall-time ratio including conversion <= **0.95×**.

Any speed/resource/horizon miss is `MKLDNN_PREPACK_NO_GO`. Token mismatch is `FAIL_EXACTNESS`. Unverifiable layer conversion, missing/ambiguous actual MKLDNN Linear dispatch, runtime/source drift or incomplete trials is `BLOCKED_IMPLEMENTATION` or `BLOCKED_ENV`; no latency result may be claimed. No post-result threshold/arm/cohort changes.

## Interpretation and authority

A pass establishes only exact-output explicit oneDNN FP32 dense-projection prepacking for this pinned GPT-2 CPU workload/runtime/host. It does not establish other models, Windows/ARM transfer, production serving, energy, cognitive capability, native Wingless/Yggdrasil performance, scientific/model acceptance or general intelligence.

Keep DRAFT/UNMERGED. Preserve G71–G88 evidence and original G70 sources unchanged. No protected-main changes, deployment, controller/queue changes, paid APIs, broker activity, model training, promotion, GPU or Wingless/Yggdrasil source changes are authorized.
