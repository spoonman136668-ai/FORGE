# G107 — Authentic baseline identity report

**Checkpoint:** 2026-10-31  
**Protocol:** `G107_BASELINE_IDENTITY_GATE_20261031.md`  
**Status:** `BLOCKED_IDENTITY` — read-only evidence review complete; no benchmark executed.

## Evidence reviewed

- Candidate screen ledger: `docs/research/acc_g91_g106/SCREEN_DECISIONS_20261031.md`.
- Final candidate screening qualification: FORGE run #2735, source branch SHA `56dabd23d9de4cee23a2d9b22bcff21a0edf1474`, full Linux and Windows job conclusion SUCCESS. These are software qualification environments. Neither job emitted target-GPU telemetry or authenticated model execution.
- The G91–G106 original case receipts establish synthetic CPU or normalized analytical screens only. They do not provide a fixed TinyLlama checkpoint manifest, target GPU identity, CUDA/runtime identity or an authentic inference trace.

## Required identity inventory

| Identity item | Result | Reason |
|---|---|---|
| Original approved TinyLlama repo + immutable revision | UNVERIFIED | No authenticated checkpoint/revision source linked to this baseline gate |
| Config/tokenizer/shard SHA256 manifest | UNVERIFIED | No original checkpoint files or verified digests in current evidence |
| FORGE inference loader/decoder/backend source SHA | UNVERIFIED | Screening branch is not itself proof of the exact approved inference runtime |
| Python/framework/CUDA/attention backend versions | UNVERIFIED | Not captured from the actual target-GPU inference process |
| Actual GPU PCI identity, compute capability, driver and memory | UNVERIFIED | CI job identity does not establish a GPU-equipped target; no authenticated target-device readback |
| Fixed held-out prompts/token IDs and workload digest | UNVERIFIED | No approved immutable benchmark corpus manifest in this gate |
| Baseline TTFT/tokens/s/latency and memory telemetry | NOT RUN | Benchmark correctly stopped before model load/inference |
| Output parity/quality baseline | NOT RUN | No model execution performed |

## Decision

**G107 = BLOCKED_IDENTITY.** No model-first-use, GPU allocation, checkpoint download, benchmark, driver/runtime mutation, candidate integration, merge or promotion was performed. The available Linux/Windows CI qualification is sufficient to close the software-validation work for G91–G106, but not to establish an authentic inference baseline.

The precise remaining blocker is an authenticated, read-only manifest from the original approved inference checkpoint/runtime and proof that the existing authorized execution route can see the actual target GPU. The workflow and runner labels alone do not prove that. Do not create a new controller, route through CKB-plane, substitute CPU timing, or assume that a machine's advertised GPU is visible to the active runner.

## Next authorized step

Collect the immutable checkpoint/config/tokenizer/shard identities and the exact inference runtime revision from the existing original source of truth. Separately confirm target-GPU PCI/device/driver/runtime telemetry through the already-qualified authorized route. Reconcile these into a canonical manifest and repeat the read-only digest check. Only after that manifest passes should a separately preregistered authentic baseline benchmark be considered. Existing scientific acceptance thresholds remain unchanged.

No secrets, tokens, private prompt contents, personal paths or account credentials are retained here.
