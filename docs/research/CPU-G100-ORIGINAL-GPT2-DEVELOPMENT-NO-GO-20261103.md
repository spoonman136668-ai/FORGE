# CPU G100 — Original GPT-2 frozen development verdict (2026-11-03)

**Verdict: `DEVELOPMENT_NO_GO`.** Engineering execution and independent
receipt validation **PASS**. Protected first-use and production promotion
remain **NOT AUTHORIZED**.

## Immutable evidence

- Research implementation and experiment source:
  `d7134d1284d19ab94bd93b74972546630fda5736`.
- Original-model run: [41718728653](https://github.com/spoonman136668-ai/FORGE/actions/runs/41718728653).
  `source-admission` and `original-model-development` both **PASS**.
- Frozen source qualification: [41694699991](https://github.com/spoonman136668-ai/FORGE/actions/runs/41694699991), mandatory Linux and Windows **PASS**.
- Artifact: `cpu-g100-original-gpt2-development`, ID `13272418098`.
- Artifact ZIP SHA-256: `88256df94608e13129d6bde48ba6773e8c6e30bfcfb677c7af69070f2c47d6bc`.
- Result JSON SHA-256: `1693c04dcb4f87fcc17d6741c9745534df7f27da7cba270f8d01a1b55b40ea0b`.
- Frozen stream JSON SHA-256: `0e5e303bf7e05e196cb4e30ee171deb286075e13d5623a3f70781e81805677f3`.
- Environment TXT SHA-256: `aaa342d3c594c3e820cc493574c682d6d88813053dd2ecb7331667e85b11886e`.
- Model weights SHA-256: `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Dataset SHA-256: `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Actual frozen ranks: development 276–287. Protected ranks 288–299 **NOT EXECUTED**.
- Original-model run log explicitly reports
  `G100_DEVELOPMENT_ONLY=PASS DEVELOPMENT_NO_GO` and
  `G100_INDEPENDENT_RECEIPT_VALIDATION=PASS DEVELOPMENT_NO_GO`.

## Preregistered controls and results

Four traffic strata; each uses four paired repetitions of 48 requests.
Arms: no-cache, LRU, G97 overflow bypass, G100 deferred first-use.
Throughput speedup is versus no-cache; paired floor is the *minimum*
per-request ratio, not a median. Frozen requirements include throughput
`>=1.15x`, paired floor `>=0.90x`, p95 latency `<=1.10x`,
CPU `<=1.10x`, RSS `<=1.15x`, resident KV `<=86,114,304` bytes,
and strict G100 improvement over G97 on overflow.

| Traffic | G100 throughput | G100 minimum paired | G100 p95 latency ratio | G97 throughput | G100 verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| Round-robin | 1.67117x | 0.86031x | 0.93720x | 1.77914x | FAIL (paired floor) |
| Bursty | 1.62759x | 0.78086x | 1.01750x | 1.74433x | FAIL (paired floor) |
| Mixed | 1.66107x | 0.83678x | 1.00857x | 1.78495x | FAIL (paired floor) |
| Overflow | 1.09199x | 0.81655x | 1.07782x | 1.07635x | FAIL (throughput, paired floor) |

All four strata **FAIL** the minimum-paired-request constraint. Overflow
also **FAILS** the required 1.15x throughput threshold. The observed
overflow wall total was 105.560 s (G100) versus 107.188 s (G97) across
the four repetitions, a small within-run improvement that does not overcome
the frozen failure gates. Outside overflow, G100 throughput was *lower*
than G97 and LRU. In every stratum, the resident KV peak matched the
86,114,304-byte cap. Exact token parity was **PASS**.

**Interpretation:** Deferring first-use cache construction lowers cache
churn in overflow, but it does not solve the worst-request speed floor and
it sacrifices throughput on stable traffic. This is a **negative
development result**, not an accepted optimization. Do not tune the
frozen thresholds, infer held-out performance, or automatically trigger
another original-model run.

## Execution and governance boundaries

The workflow-only one-shot push at `535ec449c22bf6787e3a0cb0e6bd7d3abd21160e`
ran the frozen implementation at `d7134d12...`. The temporary push
trigger was removed at `93fbd31df6f77066837d21c808ce03272ed656d4`;
the workflow blob was restored byte-for-byte to
`fbe39099b0e34f5dd00cbf1229105f1fddaff349`.
The default branch contains only the separately qualified manual
workflow registration from PR #1429; no research optimization has been
merged into production.

**Next research boundary:** archive G100 as NO_GO; compare the
existing G96/G97/G100 development failures to identify a new causal
mechanism that directly addresses per-request latency, preregister a
*new* development cohort and negative controls before executing it,
and require ordinary qualification and separate scientific custody.
No held-out or production action is justified by these results.
