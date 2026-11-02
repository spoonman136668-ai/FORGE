# G107 — Authentic model and GPU baseline identity report

**Checkpoint:** 2026-10-31  
**Status:** `BLOCKED_MODEL_IDENTITY` — target GPU and one-shot CUDA execution path are verified; approved model/checkpoint and authentic inference runtime identity remain unverified. No model inference or training benchmark was executed.

## Verified target GPU and qualified route — corrected prior finding

The prior report said no target-GPU route had been established. That statement was incomplete and is superseded by the original G59/G60 source evidence.

### G59 — actual hardware observation

FORGE issue [#1259](https://github.com/spoonman136668-ai/FORGE/issues/1259) records original read-only capability run [#41030389354](https://github.com/spoonman136668-ai/FORGE/actions/runs/41030389354). The existing self-hosted Windows `FORGE-CODEX-REMOTE` runner with labels `[self-hosted, Windows, forge-codex-isolated]` exposed:

- NVIDIA GeForce RTX 5070 Ti Laptop GPU; one device.
- 12,227 MiB total VRAM and 11,812 MiB free at the observation (ephemeral).
- NVIDIA driver 596.13.
- At that time, no globally installed/importable PyTorch CUDA runtime and no `llama-bench` on PATH.

Corrected workflow commit `acfe588425351848942097d258842e47fe811f80`, artifact ID `12966370600`, ZIP SHA256 `c6d368b70e6697e4ec699c7943100401214eed5fcea17688e3ed6351b564bac2`. Structured source record: `docs/research/ACC-G59-GPU-CAPABILITY-20261030.json`, commit `a4f67b3fd4936cc83fd1b9fb1cff57350fd55293`, blob `569bed3450a80f454b9c846040153299c6ee1c50`.

### G60/G61 — actual CUDA runtime admission

G60 used the same dedicated runner and a one-shot workflow on isolated branch `research/acc-g60-cuda-runtime-20261030`:

- Source commit `34cff5dff81407688e010f9abff0f33a253cf655`; workflow blob `5d4248029f4478b51ca8f9296d94de6792ceb1e8`.
- Original job [#124205236235](https://github.com/spoonman136668-ai/FORGE/actions/runs/41097033533/job/124205236235) in run [#41097033533](https://github.com/spoonman136668-ai/FORGE/actions/runs/41097033533) completed SUCCESS.
- It created a temporary virtual environment under `RUNNER_TEMP`, installed `torch==2.8.0` from the official CUDA 12.8 wheel index, and confirmed `torch 2.8.0+cu128`, CUDA 12.8, CUDA availability, device compute capability `sm_120`, and an actual CUDA-resident matrix multiplication.
- The measured one-shot 1024×1024 FP32 GPU matmul wall time was 113.323 ms; result checksum 268,522,304; maximum allocated VRAM 24,248,320 bytes. This is a runtime smoke test, **not** a model throughput benchmark.
- The workflow's `finally` block removes the temporary virtual environment. It did not establish a persistent global PyTorch runtime; it did not install `llama.cpp`, `llama-bench`, or model files.
- Original artifact ID `12995299765`, GitHub digest and independently downloaded ZIP SHA256 both `c0f4fee1d06a566e01dc4529ff7f031a89a3b0a22c5b15337f89afc6d2eab5e4`. The artifact JSON records `authentic_model_loaded=false` and `scientific_acceptance=NOT_GRANTED`.
- The G61 readback comment on issue #1259 confirms the original G60 run's PASS without repeating hardware execution.

Structured combined receipt: `G107_GPU_RUNTIME_ADMISSION_20261030.json` in this directory, committed in the current branch. It preserves both G59 and G60 immutable provenance.

**Revised gate state:** target GPU identity **PASS**; existing dedicated runner visibility **PASS**; isolated CUDA 12.8 runtime admission and real GPU matmul **PASS**. This corrects the earlier generic G107 statement that GPU route was unverified. The only thing established here is that this specific one-shot CUDA test worked on that runner at that time.

## Remaining approved-model identity inventory

| Identity item | Result | Evidence / reason |
|---|---|---|
| Approved causal-LM model repository and immutable revision | **UNVERIFIED** | G59 recommends choosing and pinning an approved open-weight model; it does not nominate or authorize a specific checkpoint |
| TinyLlama checkpoint identity (if TinyLlama remains the intended baseline) | **UNVERIFIED** | No source-bound model ID/revision found in the inspected records; do not infer a revision from the model family name |
| Model config, tokenizer, all weight-shard names/sizes/SHA256 | **UNVERIFIED** | G59/G60 did not download, load, or hash model files |
| Model license/usage rights and permitted checkpoint source | **UNVERIFIED** | No approved model-specific rights record tied to the target checkpoint |
| Persistent inference runtime/loader/decoder/cache/sampling source SHA | **UNVERIFIED** | G60 validated a temporary PyTorch CUDA runtime only; it did not establish a persistent inference stack |
| Persistent optimized inference backend and versions (llama.cpp CUDA, Transformers/SDPA, etc.) | **UNVERIFIED** | `llama-bench` was absent at G59; G60 did not install or test an inference backend |
| Target-device identity, driver, VRAM, compute capability | **PASS — historical readback** | G59/G60 original artifacts; live VRAM free space is not guaranteed and must be reread before a later benchmark |
| Existing qualified route capable of real GPU compute | **PASS — one-shot admission** | Existing `FORGE-CODEX-REMOTE` self-hosted Windows runner, G59/G60 source and immutable artifacts |
| Fixed held-out prompt/token-ID corpus digest and generation settings | **UNVERIFIED** | No approved model-specific inference workload manifest |
| End-to-end TTFT, steady-state tokens/s, latency distribution and memory | **NOT RUN** | No authentic model loaded |
| Model output parity/quality baseline | **NOT RUN** | No inference performed |

## Other relevant source checked

G58 draft PR [#1257](https://github.com/spoonman136668-ai/FORGE/pull/1257) identifies a pinned public-domain *Alice's Adventures in Wonderland* training corpus and a small four-layer scratch model. That is a distinct scratch-training experiment; it is not a pretrained TinyLlama checkpoint and cannot be substituted for the approved inference baseline.

Repository-scoped code-index searches across FORGE, forge-knowledge, rbackup, Qualification-Forge and ckb for `TinyLlama`, `model.safetensors`, `huggingface`, `nvidia-smi`, and `CUDA_VISIBLE_DEVICES` returned zero indexed code results. This does not inspect unindexed files, release assets, external registries, local model caches, encrypted backup contents, or runner-host directories. No local files, credentials, caches or secrets were inspected.

Mind-Palace was retrieved read-only at pinned commit `84ad556910c869afa2f171673d5a5b4041a4a9b4`; v2 bootstrap/catalog schemas and matching `source.records_sha256` were verified. Relevant FORGE advisory records include `decision/forge-cloudflare-reuse-autonomy-priority-20261015`, `decision/forge-dream-rsi-fsa-execution-partition-20261011`, `decision/forge-e2e-cutover-proof-gate-20261011`, and `decision/forge-portfolio-methods-preservation-20261012`. They reinforce that actual first-use, source custody, frozen scientific controls and separate acceptance remain mandatory. They grant no execution authority.

## Decision and next gate

**G107 = `BLOCKED_MODEL_IDENTITY`, not GPU-access-blocked.**

The next gate is to obtain or select an **explicitly approved** immutable causal-LM checkpoint and a matching evaluation corpus. Then perform read-only identity capture: model repository and commit, config/tokenizer/shard hashes, license, exact inference backend and source/dependency identity, fixed held-out token IDs, context/batch/generation settings and quality criterion. After that, separately qualify a persistent optimized inference backend in an isolated temporary environment on the already verified runner, reread live VRAM and device/driver state, and preregister the first authentic baseline measurement.

Do not silently choose a Hugging Face repo/revision, download weights, load a model, install a persistent runtime, or claim first-use/benchmark success before the model identity, rights, resource budget, and applicable authorization are established. No controller, protected-main, accepted-ref, CKB-plane, production or scientific acceptance change is made here.

**Plain English:** We have the GPU and proved CUDA compute works on the existing FORGE runner. We still do not know which exact approved model checkpoint and tokenizer should be benchmarked. That is now the sole primary blocker for starting the authentic model baseline.
