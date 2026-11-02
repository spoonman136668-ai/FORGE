# G107 — Authentic TinyLlama/GPU baseline identity gate

**Purpose:** transition from synthetic candidate triage to a source-authenticated, repeatable model/hardware baseline. G107 is an **inventory and identity gate only**. It performs no checkpoint download, model load, GPU execution, runtime mutation, candidate promotion or accepted-baseline change.

## Why this gate is next

The G91–G106 screening slate has generated useful CPU proxy and analytical falsification evidence but no accepted GPU throughput improvement. Synthetic controls do not establish the workload distribution, kernel launch overhead, bandwidth pressure, attention backend behavior, KV residency or GPU arithmetic characteristics of an actual decoder. Further candidate work must be compared against a pinned original model and optimized authentic baseline, not against more invented proxies.

## Required provenance manifest

Before any inference benchmark is authorized, record and independently verify:

1. **Model identity:** exact model repository/owner, immutable revision/commit, configuration JSON SHA256, tokenizer files SHA256, every model shard filename/size/SHA256, dtype, quantization state and any adapters. Do not use a mutable `main`/latest pointer as the tested checkpoint identity. The exact existing approved checkpoint must be established from authoritative repository records, not inferred from its display name.
2. **Runtime identity:** FORGE repository branch+commit, clean-tree/diff status, source hashes for loader, decoder, cache, sampling and inference backend; exact Python/framework versions; backend selection (eager/SDPA/FlashAttention or other), CUDA/cuDNN/runtime and compiler versions; kernel package versions; deterministic flags and environment configuration. Record relevant dependencies and lockfile digest.
3. **Hardware identity:** actual host and GPU device model, PCI vendor/device identifiers, compute capability, device-memory total/available, driver version, CUDA visibility, power/clock policy and thermal state. A CI runner without the target GPU is not evidence of GPU qualification. Do not assume a runner label implies a GPU.
4. **Workload identity:** fixed, non-secret prompt corpus revision and SHA256; tokenizer revision; tokenized input ID hashes; context-length buckets and batch size; generation length; sampling/greedy settings; stop criteria; warmup count; repeat count; cache cold/warm state. Keep held-out prompts separate from calibration or tuning.
5. **Measurement identity:** time-to-first-token, steady-state tokens/s, full request latency distribution (not just one mean), peak and steady device memory, power/clock/temperature telemetry if available, CPU utilization and host-to-device transfer evidence. Preserve per-run raw measurements, not just summary statistics. Use alternating baseline/candidate ordering only after a candidate is separately preregistered; do not mix environment drift across arms.
6. **Correctness/quality:** exact greedy token parity against the original baseline for optimizations claiming exactness; otherwise a predeclared held-out quality/error criterion owned by the applicable scientific acceptance contract. Report outliers, crashes, OOMs and excluded runs explicitly. Never use the benchmark prompt corpus to calibrate the candidate and then call it held-out.

## G107 acceptance criteria

- **Identity completeness:** every required immutable hash/version/setting is present and read back from its original source. Missing identity => `BLOCKED_IDENTITY`, not PASS.
- **Reproducibility:** two independent manifest reads over the same clean state produce byte-identical canonical manifests. Unexplained host/runtime/model drift => re-inventory.
- **Isolation:** confirm the benchmark does not write to protected model files, accepted refs, live runtime state, broker/trading configuration, or other program controllers.
- **Target availability:** prove actual target GPU visibility through the existing authorized and qualified execution route. A GitHub Linux/Windows CPU runner, a developer machine with a different GPU, or a named runner label without device evidence is insufficient.
- **No performance threshold declared at this stage:** G107 does not assert a speedup. It establishes an immutable baseline and a traceable measurement path. Candidate-specific speed/quality cutoffs must be separately preregistered before candidate execution and remain subordinate to existing scientific criteria.

## Stop conditions and authority boundary

G107 may complete its read-only repository inventory using already authorized GitHub read operations. Stop before model download/load, local shell execution, GPU allocation, benchmark run, model first-use, runtime/driver configuration, candidate integration, merge or promotion. These actions require an existing qualified target-GPU route and applicable explicit authority. If no such route is verifiably available, report the precise missing piece rather than substitute a CPU runner or new controller. Mind-Palace context is advisory; it grants no execution or acceptance authority. CKB-plane is not a universal controller and is not a dependency for FORGE.

## Output

Repository-owned `docs/research/acc_g91_g106/G107_BASELINE_IDENTITY_REPORT.md` plus a canonical machine-readable manifest only after each field is verified. Record `PASS/FAIL/UNVERIFIED` separately per field with original source references. No secrets, tokens, personal paths or private prompt contents in durable evidence.

**Current initial status:** `UNVERIFIED`. No verified immutable target checkpoint + target-GPU manifest has been established in this gate. No authentic GPU benchmark is claimed.
