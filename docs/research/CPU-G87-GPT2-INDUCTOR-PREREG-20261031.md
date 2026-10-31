# CPU GPT-2 G87 — fullgraph Inductor compilation versus eager CPU execution

**Prospective preregistration — 2026-10-31.** This file is committed before the G87 executable, tests, workflow, or new-cohort benchmark. Research-only CPU LLM evaluation; separate from RTX GPU ACC, FORGE autonomy/controller, and native Wingless/Yggdrasil research.

## Hypothesis

Test whether compiling the unchanged original pretrained GPT-2 forward path with PyTorch 2.5.1 CPU Inductor (`torch.compile`, backend `inductor`, `fullgraph=True`, `dynamic=True`, mode `default`) reduces full-request latency versus eager execution at a fixed two-thread budget, without changing a single generated token.

This is distinct from G86's eager-versus-SDPA backend selection. It tests graph capture and CPU code generation, not a new attention backend, new weights, quantization, altered decoding, or a synthetic kernel.

## Immutable baseline, checkpoint, and disjoint evaluation cohort

- Qualified CPU research base: G70 commit `20a540d0241519e2e9d90ace868ffd6db60bd065`. G54-G70 sources remain immutable.
- Original pretrained `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`; safetensors SHA-256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Original MIT GSM8K test source commit `3101c7d5072418e28b9008a6636bde82a006892c`; raw SHA-256 `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Use the exact G82/G86 hash-ranking algorithm and seed `G68-GPT2-HELDOUT-20261030:`. Select original rows at ranks **168–179 inclusive** (12 distinct questions), after the G86 ranks 156–167. Verify the exact G68/G70 partition records and disjointness; no prompt reuse, synthetic substitution, or post-measurement cohort changes.
- Retain original G55 shared prefix and first 64 original GPT-2 question token IDs (`add_special_tokens=False`). Original full-FP32 model, original greedy decoding, original 8 new tokens. No training, weights changes, cache reuse across prompts, tokenizer changes, quantization, speculation or altered output policy.

## Runtime and paired design

- Native `ubuntu-24.04` x86_64 Linux; Python 3.11; PyTorch `2.5.1+cpu`; Transformers `4.48.3`; huggingface-hub `0.30.2`; safetensors `0.5.3`; tokenizers `0.21.1`; psutil `7.1.3`. Verify exact versions, `torch.version.cuda is None`, and `pip check`.
- Pin all arms to the same three logical CPU cores; set/read back PyTorch inter-op threads = 1. Primary eager and compiled arms both use intra-op threads = 2. Charge `torch.set_num_threads(2)` to each timed request.
- Load one source-verified original FP32 GPT-2 instance for eager and an independently loaded weight-identical instance for compiled inference. Verify exact parameter equality and source-file SHA/manifest equality.
- Candidate is `torch.compile(model, backend=counted_inductor, fullgraph=True, dynamic=True, mode="default")`, where `counted_inductor` delegates to the pinned PyTorch Inductor backend while counting graph compilations. Fullgraph capture must not silently graph-break to eager. Require a bounded number of compiled graphs (at most four over the frozen cohort/decoding shapes); reject unexplained recompilation, fallback, backend drift, or eager execution inside the compiled candidate as `BLOCKED_IMPLEMENTATION`.
- Primary arms: original `eager2` and original `inductor2`; same weights, tokenizer, prompt IDs, sampling policy, cache behavior, thread affinity, and exact eight-token response length. Rotate arm order per prompt/repetition.
- 12 prompts × 4 paired repetitions × 2 arms = **96 authentic full responses and 768 generated tokens**, 48 paired records. Every candidate response must exactly match its same-prompt eager baseline and remain identical across its own repetitions. No outlier exclusion.
- Record source and prompt hashes, original token IDs only via output hashes and mismatch indices, wall and process-CPU time, sampled RSS, graph compile count, graph-break count, compile startup time, warmup time, and per-request latencies. No generated prose in artifacts.
- Measure one-time compile/setup cost separately from warmed request latency. Charge the entire observed first compile to amortization; do not discard it or describe warm-only throughput as end-to-end improvement. Report the break-even response count and total wall-time ratio at exactly **1,000 responses** using frozen eager and compiled medians.

## Frozen acceptance

`INDUCTOR_PASS` requires **all** of the following:

1. Exact G70/prereg/source/model/dataset identity, native CPU runtime, fixed affinity, complete ranks 168–179 and 48 paired trials.
2. Actual Inductor compilation with `fullgraph=True`, no graph breaks/fallback, at most four compiled graphs, no weight or tokenizer changes.
3. Exact greedy token parity for all 96 original responses and all 768 generated tokens.
4. Median warmed full-request speedup of `inductor2` versus `eager2` >= **1.15×**.
5. Minimum individual paired eager2/inductor2 speed ratio >= **0.90×**.
6. p95 compiled/eager latency ratio <= **1.10×**.
7. Sampled maximum RSS compiled/eager ratio <= **1.10×**.
8. Total process CPU time compiled/eager ratio <= **1.25×**.
9. Compile startup <= **300 seconds**, and compile-cost break-even <= **1,000 full responses**. The 1,000-response total-time ratio, including startup, must be <= **0.95×** (at least 5% aggregate savings).

Any threshold miss is `INDUCTOR_NO_GO`. Output mismatch is `FAIL_EXACTNESS`. Compilation fallback, unsupported graph, more than four graphs, runtime/source drift, or incomplete cohort is `BLOCKED_IMPLEMENTATION` or `BLOCKED_ENV`; it is never silently counted as a candidate speedup. No threshold, model, prompt, arm, or horizon changes after first measurement.

## Interpretation and authority

A pass would establish only an exact-output, compiled-execution benefit for this pinned GPT-2 CPU runtime, Linux host, fixed CPU budget, and small original question cohort. It does not establish Windows/ARM transfer, another model family, production serving throughput, energy efficiency, training-held-out generalization, cognition, intelligence, native Wingless/Yggdrasil capability, or scientific/model acceptance.

Keep DRAFT/UNMERGED regardless of result. Preserve all prior G71–G86 negative and positive records unchanged. No protected-main change, model promotion, deployment, controller/queue mutation, paid API, broker, GPU run, or Wingless/Yggdrasil source mutation is authorized by this research preregistration.
