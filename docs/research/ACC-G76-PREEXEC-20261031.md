# ACC G76 — source-pinned authentic RTX CPU/CUDA timeline capture

**PRE-EXECUTION FREEZE, 2026-10-31.** The existing G76 helper is an offline scaffold. This protocol freezes one bounded profiler-only execution before modifying its executable or adding a GPU workflow. No performance/candidate hypothesis is admitted by this gate.

## Why G76 is needed

Prior G61–G75 measured model-level timing and isolated several shape-sensitive numerical differences, but no authenticated Chrome trace has quantified the mix of CPU operators, CUDA runtime launch/API events and GPU kernels for the original FP16 inference path. Category counts are not launch-overhead fractions: the trace can support event classification and later correlation, not a speedup claim by itself.

## Immutable model, corpus and host

- Model: Apache-2.0 `TinyLlama/TinyLlama-1.1B-Chat-v1.0`, revision `c13e4efb205d7a8e5d13c088aa10a9dabac9b96a`; original `model.safetensors` exactly 2,200,119,864 bytes, SHA256 `6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933`. Load original FP16, no training, no quantization, no model compilation.
- Text source: GITenberg `GITenberg/Pride-and-Prejudice_1342`, immutable commit `81db45c9c48c592f0b77f01fc59e677ad0a5634e`, `1342.txt`, Git blob SHA1 `0a7d439c2f34b0dfacb88b7116429a9575b5735c`, expected size 717,602 bytes. Verify canonical Git blob before decoding. Never upload or store corpus text in the artifact.
- Fixed contexts only: character offsets `24576` -> 512 tokens and `98304` -> 1,536 tokens. Tokenize each following 30,000-character source slice using the pinned model tokenizer, `add_special_tokens=False`, then take exactly the first frozen context length. Require exact lengths; never move an offset or replace a short segment after observing output. These passages are already exposed by G74 and are used **only for profiling instrumentation**, not independent first-use/generalization or a candidate acceptance set.
- Model/hardware runtime: existing `FORGE-CODEX-REMOTE` Windows runner labels `[self-hosted, Windows, forge-codex-isolated]`; NVIDIA RTX 5070 Ti Laptop GPU, compute capability sm_120; torch `2.8.0+cu128`, CUDA 12.8, transformers `4.52.3`, huggingface_hub `0.30.2`, safetensors `0.5.3`, tokenizers `0.21.1`. Verify actual CUDA matmul, actual CUDA device and real SDPA dispatch using `aten::scaled_dot_product_attention`; refuse CPU fallback.
- Verify live free VRAM before load (minimum 7,000 MiB) and record GPU, driver, free/total memory. The previous historical free-memory value is not reused as a live guarantee.

## Frozen capture procedure

For each of the two fixed prompts, in fixed order 512 then 1536:
1. Run one unprofiled, synchronized original FP16 SDPA `model.generate` warmup with `do_sample=False`, `num_beams=1`, `use_cache=True`, exactly 64 generated tokens, EOS disabled as in earlier ACC runs. Record the generated 64-token ID SHA256 as the expected result.
2. Run exactly one same-setting generation under PyTorch `torch.profiler.profile(activities=[CPU, CUDA], record_shapes=False, profile_memory=False, with_stack=False)`; synchronize the GPU before and after. Require all 64 generated token IDs to match the warmup exactly.
3. Export the original Chrome trace and record its raw byte SHA256, trace event count, counts of complete CPU-op, CUDA-runtime/API and GPU-kernel events, the presence of actual `aten::scaled_dot_product_attention`, model/source/prompt/runtime identity and cleanup result. Do not infer launch overhead from category counts. Do not enable stack traces, tensor values, shapes, memory snapshots or private text capture.
4. Run only one profiled generation per context (2 total); no timing comparison, no candidate, no dtype comparison, no tuning, no repeated sampling. Profile trace perturbation makes elapsed time descriptive only; no performance threshold is applied.

## Frozen acceptance and reporting

- **Evidence complete** only if both contexts have verified source/model identities, the real RTX/CUDA/SDPA path, exact 64-token profile/warmup parity, nonempty valid Chrome traces and hashes, and successful deletion of the disposable environment/cache/text.
- **Profiler instrumentation PASS** only if both traces contain nonzero CPU events, CUDA runtime/API events, and GPU kernel events, with `aten::scaled_dot_product_attention` observed on the actual GPU model forward.
- Any missing category, no SDPA op, token drift, invalid/empty trace, identity drift, insufficient free VRAM or cleanup failure is **BLOCKED/FAIL**, not a zero-overhead result.
- Always report `launch_overhead_fraction=UNMEASURED`, `speedup=UNMEASURED`, `cuda_graph_speedup=UNMEASURED`, and `scientific_acceptance=NOT_GRANTED`. A follow-on study must correlate individual CUDA API launch events with GPU kernel activity, separate device execution from CPU enqueue gaps, validate profiler perturbation, and use a separately preregistered before/after intervention. No 1.15× removable fraction is inferred from a trace count.

## Bounded execution and custody

One source-push workflow on the existing isolated self-hosted Windows RTX runner; 30-minute timeout; share non-cancelling GPU concurrency group `forge-acc-g73-original-rtx-precision` with existing G73/G74 family to prevent overlapping runs. Disposable venv, HF cache, and corpus go only under `RUNNER_TEMP`, with collision checks and always-run cleanup. Upload only the two Chrome traces, numeric JSON summaries, and pinned package freeze; 30-day artifact retention. No secrets, raw text, weights, hidden activations, prompt text, private files or personal paths in artifacts.

No new runner/controller/scheduler, no CKB-plane dependency, no global runtime installation, no production model changes, no F139/autonomy or Wingless/Yggdrasil modification, no protected-main writes, no model promotion, no accepted-ref change, no paid API, and no scientific first-use/acceptance. This is a bounded diagnostic read-only workflow; a green job is **not** an acceleration pass.
