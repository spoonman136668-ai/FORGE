# ACC G91–G106: screening decisions and qualification evidence

**Research-only ledger; not a claim of GPU/model speedup, integration or scientific acceptance.** GPU LLM-bottleneck track, separate from the original GPT-2 CPU line and G79–G90 PR #1326. Existing FORGE authority/approval boundaries unchanged.

| Screen | Linux initial decision | Grounded evidence | Windows qualification |
|---|---|---|---|
| G91 certified vocabulary | NO-GO, IID 0.240× / clustered 4.680× | `results/g91_linux_run2705.json`, run #2705 | focused PASS; dual-OS PASS |
| G92 synthetic self-sketch microtrees | ANALYTIC FEASIBILITY ONLY, width 4 47/48 analytically infeasible | `results/g92_linux_run2707.json`, run #2707 | focused PASS; dual-OS PASS |
| G93 SwiGLU negative-tail pruning | NO-GO, all frozen thresholds fail | `results/g93_linux_run2709.json`, run #2709 | focused PASS; dual-OS PASS |
| G94 exact activation delta projection | NO-GO, IID 0.075× / sparse 0.845× Linux; IID 0.042× / sparse 0.979× Windows | `results/g94_linux_run2712.json` and `results/g94_windows_run2712.json`, run #2712 | focused PASS; full dual-OS PASS |
| G95 RoPE strict identity reuse | NO-GO, context drift 0.958× / identical 1.810× Linux | `results/g95_linux_run2718.json`, run #2718 | PENDING as of archival; do not claim PASS |
| G96 mathematically certified attention blocks | NO-GO, IID 0.079× / clustered 0.679× Linux | `results/g96_linux_run2718.json`, run #2718 | PENDING as of archival |
| G97 conservative head contribution pruning | NO-GO, normal 0.308× / favorable 0.442× Linux | `results/g97_linux_run2718.json`, run #2718 | PENDING as of archival |
| G98 compressed KV low-rank subspace | PREREG + IMPLEMENTED, UNVERIFIED | `../G98_KV_SUBSPACE_PREREG_20261031.md` and `../../../../research/acc_g98/` | New CI queued by this ledger commit |
| G99 INT8 with FP32 sparse outlier corrections | PREREG + IMPLEMENTED; NO NUMERIC RESULTS | `../G99_OUTLIER_MIXED_PRECISION_PREREG_20261031.md` and `research/acc_g99/` | Linux/Windows CI qualification now scheduled |
| G100–G106 | NOT EXECUTED | Original hypotheses in `../SCREENING_PREREG_20261031.md` | — |

**G95–G97 CI custody:** original research screen commit `dd95b85ad1b881063919385877c718f758640acd`, GitHub Actions run #2718 Linux job `124510489655`, all G95/G96/G97 focused steps PASS, all 24+48+48 cases recovered from job stdout and separately committed to the above individual receipts. Original GitHub run artifact `13039855039` digest `sha256:2cc7af92b88e788041df832754e01d4a70ec1266ec77c23096b53d0250364a1d`. Source stdout parsed and reserialized into GitHub JSON, not byte-exact raw log.

**CI defect and recovery:** previous run #2715 failed on *both* operating systems in the isolation gate, `FORGE_ISOLATION_GATE=BLOCKED GIT_NOT_QUALIFIED`; the verified cause was a single trailing-whitespace added line in G96 source, rejected by `git diff --check`. Exact source-only repair `dd95b85ad1b881063919385877c718f758640acd` restored isolation PASS on both OS in run #2718. The failed run never reached the G95/G96 screen, and does not count as a research negative. No safety gate was disabled or weakened.

**Admission rule:** all CPU screens are nonrepresentative synthetic controls, often with deliberately favorable structure. A mathematical certificate or optimized microkernel comparison is not an authentic TinyLlama/RTX throughput claim. NO-GO is local to frozen proxy rules, not universal impossibility of a mechanism. Keep research evidence in the repository; no model first-use, protected-main merge, promotion, paid API, controller/queue change, or scientific acceptance.

**G99 fixed design and execution custody (2026-10-31):** preregistered at `d49d5ce205918286ed54d6b3e72096d91050d256` before source; source at `a2604b6dd28613a9495078ac4976d7479248a260`; guards at `48545e077024514549dc8d4740b522c882c98b2c`; Linux/Windows CI with output capture at `c755c801476a8520ba2be7bcf540f58c7eb88dc6`. Frozen 144 cases, three outlier budgets, IID and injected-outlier regimes, 1e-2 per-case relative error, both-regime 1.15× median speed and <=0.65× FP32 weight-storage cutoff. Uncharged preprocessing and runtime allocations are explicitly caveated. A scheduled CI run is not a scientific performance result; G99 status is **UNVERIFIED** until source-matched outputs are collected.
