# ACC G62 — preregistered authentic optimized-SDPA prompt-lookup speculation screen

**PREEXEC FREEZE, BEFORE ANY G62 EXECUTABLE.** Preserve G61 final authentic TinyLlama-1.1B paired optimized-attention baseline at commit `e6cac6b2eb7438d1331bae2ef0dd42f1316cb059` / [draft PR #1261](https://github.com/spoonman136668-ai/FORGE/pull/1261). The G62 test is a different mechanism from attention: n-gram **prompt-lookup speculative generation** implemented in the upstream Hugging Face generation interface. This is **well-established prior art**, not a new LLM technique. [HF documentation](https://huggingface.co/docs/transformers/v4.52.2/generation_strategies) and [NVIDIA TensorRT-LLM speculative guidance](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/features/speculative-decoding.md) both document prompt lookup / n-gram-based drafting.

## Authentic model and optimized comparator

- Same original pinned Apache-2.0 model as G61: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`, Git `c13e4efb205d7a8e5d13c088aa10a9dabac9b96a`; exact `model.safetensors` **2,200,119,864 bytes**, SHA256 **`6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933`**, fail closed if missing or mismatched.
- Actual RTX 5070 Ti Laptop GPU, CUDA sm120, Torch `2.8.0+cu128`, Transformers `4.52.3`; FP16 model, `attn_implementation="sdpa"`, verify true `aten::scaled_dot_product_attention` execution on CUDA via PyTorch profiler. Require >=7,000 MiB currently free; actual real CUDA matmul. No CPU fallback.
- **Baseline:** standard `model.generate(do_sample=False, num_beams=1, use_cache=True)` with real SDPA. **Candidate:** same `model.generate()` with `prompt_lookup_num_tokens=5, max_matching_ngram_size=3`. Identical inference model, same input token IDs, 64 new greedy tokens, same config, EOS disabled (`eos_token_id=-1`) to force 64 full tokens. Both live on actual GPU, not a CPU strawman; do not compare candidate to separate G61 `manual cached decode` implementation or eager backend. No separate model/draft checkpoint/training.

## Frozen workload, repeat schedule, outputs

Six cases from **three preauthored workload families × two fixed prefix sizes (512,1536)**. Model context 2048, all 1536+64 fit; fail if prompt tokenization yields fewer than 1536 tokens. Families:
1. `structured`: recurring table-like logs with repeated `item, status, sector, amount` fields, followed by a completion cue; likely to benefit from prompt lookup.
2. `grounded`: repetitive plain-English source report snippets and a request to continue an excerpt; may partially reuse prompt material.
3. `freeform`: independently phrased prose and generic explanatory continuation; weak lookup control.

Use deterministic fixed source strings in code, not G61 measured prompt texts or dynamic prompt selection. For each case: two warmups per backend, **five paired full `generate()` measurements**, alternating baseline/candidate order AB/BA. GPU-synchronize before and after **each** call; record total generation wall from first model call to final generated token, excluding venv/model loading and initial tokenization, including internal n-gram lookup and verification overhead. Record all individual GPU timings and peak allocated/reserved VRAM, and model forward-call count per arm as an explanatory operational measure.

**Correctness hard gate:** All 6×5 pairs produce **bitwise identical 64 continuation token IDs**, same prompt and generation settings, must not end before 64 tokens. On mismatch the case is **FAIL**, no claimed speedup. If prompt lookup is disabled or silently ignored, record `candidate_forward_calls` versus baseline, do not imply speculation worked from the flag alone. If actual PyTorch SDPA operator or model hash fails, classify BLOCKED.

**Engineering screen threshold predeclared:** `GO_NARROW_ENGINEERING` only if both `structured` context sizes have **>=1.15× paired median baseline/candidate**, **geometric mean speedup across ALL SIX cases >=1.00×**, no correctness failure, and peak GPU memory <=1.10× baseline (using peak allocated/reserved reporting). Otherwise `NO_GO`. This result is **never original science** (existing prior art) and **never production speedup** (not vLLM/llama.cpp optimized serving).

## Isolation / resource limits

Run once from an isolated source-push GitHub Actions workflow on existing `[self-hosted, Windows, forge-codex-isolated]` runner, **30-minute timeout**; install pinned packages in disposable `RUNNER_TEMP` venv, public model in disposable HF cache, no global packages, no CKB-plane, no paid endpoints, no access to secrets or runtime owner state. Always remove all G62-specific temp paths even on failure; artifact only raw receipts, environment, no model or private files; retention 30 days. Preserve final concise evidence within this isolated unmerged draft PR. Operator authority to modify protected main, FORGE F139, native Wingless/Yggdrasil, model promotion or existing scientific acceptance is **NOT GRANTED**.

**Prior-work caveat:** G54 on GPT-2 confirmed known prefix caching 1.41× versus deliberately uncached requests; it did NOT use optimized SDPA generation. G62 must explicitly count both normal SDPA baseline and prompt lookup candidate under matched API and cache behavior, to avoid repeating that easy baseline mistake. Speculative methods are expected to vary strongly with prompt overlap.