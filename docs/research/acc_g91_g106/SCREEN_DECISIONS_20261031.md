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
| G98 compressed KV low-rank subspace | NO-GO: rank 8 both ~1.37×, but worst IID output rel-L2 1.024; no rank meets error across regimes | `results/g98_linux_run2722.json`, 144 cases, run #2722 | Linux focused+full PASS; Windows pending |
| G99 INT8 with FP32 sparse outlier corrections | NO-GO: storage 0.254–0.301× FP32 but medians 0.129–0.195× and only K=8 accurate both regimes | `results/g99_linux_run2722.json`, 144 cases, run #2722 | Linux focused+full PASS; Windows pending |
| G100 predictive cold-KV page staging | PREREG + IMPLEMENTED, UNVERIFIED. Analytical cost model, no real GPU transfer | `../G100_KV_STAGING_PREREG_20261031.md`, `research/acc_g100/` | Dual-OS CI staged |
| G101–G106 | NOT EXECUTED | Original hypotheses in `../SCREENING_PREREG_20261031.md` | — |

**G95–G97 CI custody:** original research screen commit `dd95b85ad1b881063919385877c718f758640acd`, GitHub Actions run #2718 Linux job `124510489655`, all G95/G96/G97 focused steps PASS, all 24+48+48 cases recovered from job stdout and separately committed to the above individual receipts. Original GitHub run artifact `13039855039` digest `sha256:2cc7af92b88e788041df832754e01d4a70ec1266ec77c23096b53d0250364a1d`. Source stdout parsed and reserialized into GitHub JSON, not byte-exact raw log.

**CI defect and recovery:** previous run #2715 failed on *both* operating systems in the isolation gate, `FORGE_ISOLATION_GATE=BLOCKED GIT_NOT_QUALIFIED`; the verified cause was a single trailing-whitespace added line in G96 source, rejected by `git diff --check`. Exact source-only repair `dd95b85ad1b881063919385877c718f758640acd` restored isolation PASS on both OS in run #2718. The failed run never reached the G95/G96 screen, and does not count as a research negative. No safety gate was disabled or weakened.

**Admission rule:** all CPU screens are nonrepresentative synthetic controls, often with deliberately favorable structure. A mathematical certificate or optimized microkernel comparison is not an authentic TinyLlama/RTX throughput claim. NO-GO is local to frozen proxy rules, not universal impossibility of a mechanism. Keep research evidence in the repository; no model first-use, protected-main merge, promotion, paid API, controller/queue change, or scientific acceptance.

**G99 fixed design and execution custody (2026-10-31):** preregistered at `d49d5ce205918286ed54d6b3e72096d91050d256` before source; source at `a2604b6dd28613a9495078ac4976d7479248a260`; guards at `48545e077024514549dc8d4740b522c882c98b2c`; Linux/Windows CI with output capture at `c755c801476a8520ba2be7bcf540f58c7eb88dc6`. Frozen 144 cases, three outlier budgets, IID and injected-outlier regimes, 1e-2 per-case relative error, both-regime 1.15× median speed and <=0.65× FP32 weight-storage cutoff. Uncharged preprocessing and runtime allocations are explicitly caveated. A scheduled CI run is not a scientific performance result; G99 status is **UNVERIFIED** until source-matched outputs are collected.

**G98/G99 original Linux CI custody:** run #2722 `41192854398`, Linux job `124513179853`, source branch SHA `3dff673e176422c11dc95a877a43d694e0694b2d`, original GitHub Actions artifact `13039438005`, SHA256 `6330fbcf58aa2004685f1a5113e2f4c9bf136785e8721b6c9dd14dd697490865`. Both screens' 144/144 source stdout JSON cases were retrieved after Linux job completed, parsed, and committed to separate repository receipt files. The receipts are reserialized JSON, not byte-identical stdout. G98 G99 both **NO_GO_SYNTHETIC_SCREEN** under frozen rules; measured CPU results only, original GPU/LLM **NOT_RUN**. Windows and full qualification not inferred from Linux.

**G100:** Frozen analytic cost-model prereg at `2e753b036513f3032286c733f94d19a9bc85c3eb` before source `cf5625473f49a8e32b31413e36630326f01d44d5`, guards `edc7a4e4ba1cdbf9bf9a4c9f392aa33c4fe52684` and two OS CI steps `def1a15aa7e39aa54d8246357e3427d2ec029369`. Transfer/compute times are **hypothetical normalized units**. Twelve held-out sequence cases, no oracle, strict cache/transfer accounting. G100 result and qualification UNVERIFIED until the scheduled original CI actually runs.
