# ACC G60 — preregister real RTX 5070 Ti CUDA compatibility and authentic GPT-2 baseline

**Committed before runtime or benchmark code. No scientific promotion.** Previous real-hardware source [G59 issue #1259](https://github.com/spoonman136668-ai/FORGE/issues/1259) verifies dedicated `FORGE-CODEX-REMOTE` Windows runner RTX 5070 Ti Laptop 12,227 MiB total VRAM, NVIDIA driver 596.13. Its available VRAM is **time-dependent**; G60 must refuse non-NVIDIA/insufficient-memory or PyTorch CPU fallback. Separate F139 controller / protected main / paid API remain untouched.

## Bounded runtime execution

Use the **existing** isolated `[self-hosted, Windows, forge-codex-isolated]` runner. Job 30-minute hard timeout. Do not install global packages, modify PATH outside the job, schedule or build a controller, or touch workspace secrets. Create a venv in `$env:RUNNER_TEMP\acc-g60-venv`; install pinned `torch==2.8.0` from official CUDA 12.8 wheel index and exact `transformers==4.48.3`, `huggingface_hub==0.30.2`, `safetensors==0.5.3`, `tokenizers==0.21.1` from PyPI. All downloaded packages remain in ephemeral environment; `pip --no-cache-dir`. Finally delete G60 venv, model cache, and downloaded source folder. If cleanup fails, record failure; do not attempt global uninstall. No force or broad cleanup outside `RUNNER_TEMP`. Python interpreter and RAM/space checked before install. Should not use Codex or runner-owned authentication.

CUDA admission must verify `torch.cuda.is_available()`, `torch.version.cuda >= 12.8`, device capability `(12,0)`, actual NVIDIA name, free VRAM >= **5,000 MiB**, and successful synchronized 1024×1024 FP32 GPU matrix multiplication with device/CUDA checks. Record actual Torch version, CUDA runtime, driver, GPU memory allocated/peak. Failure to meet **any**: classify BLOCKED; do not silently use CPU.

## Public pretrained GPT-2 identity

Use independent earlier [G54 pinned authentic GPT-2 model](https://github.com/spoonman136668-ai/FORGE/pull/1250), `openai-community/gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`, `model.safetensors` SHA256 `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707` (548,105,171 bytes). No user tokens, no HF auth, no private files. Download manifest-listed config/tokenizer/weight files into a temp folder, compute each SHA, fail if weight/source mismatch, then load via `local_files_only=True, trust_remote_code=False`. GPT2-small **does not represent 8B long-context HBM behavior**; this is a CUDA pipeline proof and honest GPU latency baseline only.

## Predeclared benchmark

Measure plain FP32 pretrained GPT-2 with **standard `past_key_values` incremental decoding** (not uncached greedy), deterministic argmax decoding, full attention context 128 and 384 original text tokens, generation **32** continuation tokens each, batch=1. Publicly authored prompt repeated/truncated to the target token sizes; reject if context length <=32 or >1000. CPU same checkpoint and prompts as an informational reference (2 CPU threads), GPU:
- 2 untimed warmups per context
- 5 timed independent trials per context
- synchronize GPU before/after prefill and token-by-token decode; report prefill and continuation separately, full 32-token sequence time, median and individual timings; avoid any claimed end-to-end TTFT including tokenization or model load.
- identical greedy output tokens for CPU vs GPU **required**; logits allowed minor float differences but report max absolute first-token discrepancy, do not require bitwise GPU/CPU equality.
- report actual peak GPU VRAM allocation/reservation; report all execution/toolchain identity and required source hashes. Repetitions must agree on GPU, no cached-prefix cross-request reuse; context length 384 fits GPT2's 1024 capacity.

**Success criterion** = device GPU real computation PASS + pinned authentic weights PASS + 2/2 contexts ×5 trials valid, CPU/GPU output agreement, all positive timings. No novel accelerator superiority or model science claims. GPU/CPU ratios may be reported descriptively but not counted toward a candidate >1.15x novelty gate.

**Stop rule**: If dependencies cannot install, source unavailable, validation fails, or GPU unavailable: honest BLOCKED/FAIL with complete stderr, no synthetic CPU substitution. Do not modify F139, accepted science, trading or model-serving systems. Publication in an unmerged **DRAFT** research PR only, and durable findings in repo, not user library.