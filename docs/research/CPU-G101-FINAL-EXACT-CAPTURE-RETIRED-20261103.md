# CPU G101 — Final original-GPT2 exact-capture falsification receipt (2026-11-03)

**Frozen scientific decision: `RETIRE_G101_EXACT_CAPTURE`.** The final
SDPA-versus-eager experiment, all frozen source-admission gates and the
independent raw-data receipt verifier **PASS**. Neither attention backend
produces the strictly bit-identical prefix KV state required by this
mechanism. Generated tokens match on the bounded development diagnostic,
but that does not override the failed exact-KV acceptance condition.

## Pinned evidence and custody

- Original unmodified frozen final experiment source:
  `82448631ca25b25ce275d5d21f735791125af802`.
- Exact-head focused Linux/Windows qualification: [41735792143](https://github.com/spoonman136668-ai/FORGE/actions/runs/41735792143), **PASS/PASS**.
- Exact-head mandatory full Linux/Windows qualification: [41735798560](https://github.com/spoonman136668-ai/FORGE/actions/runs/41735798560), **PASS/PASS**.
- Real-model diagnostic: [41743988650](https://github.com/spoonman136668-ai/FORGE/actions/runs/41743988650), source-admission **PASS**, original-model execution **PASS** and independent receipt validation **PASS**.
- One-shot trigger SHA: `fa1633dab1497a53ba9f0ec6364022ccb36d0c17`; automatic trigger removed at `3218ea471f64859f8aadf62bf2ae391f911f113f`. The run checked out and executed the frozen source above, not the trigger commit.
- Archived artifact ID `13281579059`, `cpu-g101-final-original-gpt2-falsification`.
- Artifact ZIP SHA-256: `bf7c575ffb7800114c9c7c6b855cbb8b3983d07bc2a96f94cf615e54d386d242`.
- Original JSON `cpu_g101_final_diagnostic.json` SHA-256:
  `67bf123610ec1a188e48cd1ea55a7095ab8c942400b7e5f856a7c85de63016e0`.
- Original environment TXT SHA-256:
  `01024d732ef7738c2cfce6fc4c3a10e2d57e2a1834a4e2718b817f43b10ebdaa`.
- Pinned model weights SHA-256: `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Pinned dataset SHA-256: `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.

## Complete frozen diagnostic summary

| Original GPT-2 backend | SDPA | Eager |
| --- | ---: | ---: |
| Bit-exact prefix/suffix pairs | **0 / 10** | **0 / 10** |
| KV tensors evaluated | 240 | 240 |
| Total KV elements compared | 53,194,752 | 53,194,752 |
| Elements with differing bits | 22,948,863 | 22,937,904 |
| Largest absolute difference | 1.52587890625e-05 | 1.52587890625e-05 |
| Largest integer-ordered ULP distance | 1,782,153,216 | 1,777,336,320 |
| Original-model generated-token parity | **PASS** | **PASS** |
| Candidate served-path model forwards | 80 | 80 |
| Additional served-path prefix forwards | 0 | 0 |
| Cache hits / misses / admissions / evictions | 3 / 7 / 7 / 3 | 3 / 7 / 7 / 3 |
| Maximum logical resident prefix KV bytes | 86,114,304 | 86,114,304 |

The numerical differences are small in absolute magnitude but not
bit-identical; the very large maximum ULP distances can occur near zero
and must not be interpreted as equivalent absolute-magnitude errors.
Neither numerical tolerance nor a substitute criterion was introduced.

The frozen development cohort uses already-consumed ranks 276–285,
not protected first-use ranks 288–299. This experiment was diagnostic
only, with **no throughput, latency or energy performance conclusion**.
Independent receipt validator output:
`G101_FINAL_INDEPENDENT_RECEIPT=PASS RETIRE_G101_EXACT_CAPTURE`.

## Final research decision and handoff

The previously committed [frozen rule](CPU-G101-FINAL-FALSIFICATION-PREREG-20261103.md)
requires that either SDPA or eager produce all 10 bit-exact comparisons
while preserving all performance-independent correctness controls.
Both failed on real pinned original weights. Hence retire this **particular
full-prefill exact-KV extraction** mechanism as predeclared.

Do not patch this experiment to weaken byte-exactness, hide additional
prefix computation, rerun G101 with posthoc variants, or promote the
mechanism. Retain G97/G100 negative original-model results and all
original G101 receipts intact.

**Next independent research family (proposal, not executed):** Explore
eliminating per-request *deepcopy* of separately computed, already
bit-exact immutable prefix KV while retaining copy-on-write/isolation for
the appended decode states. This attacks a different cost center and
does not depend on extracting prefix KV from a full-prompt prefill.
Before any experiment, verify cache aliasing and mutation invariants
under the native GPT-2 cache implementation, account for transient
memory and full CPU/wall cost, use strong G96/G97/G100 controls,
preregister new development-only cohorts and thresholds, qualify exact
source on Linux/Windows, and preserve protected-data and owner
boundaries. No such new mechanism is accepted or deployed here.

**Final status:** G101 exact-capture **RETIRED**; generated-token parity
diagnostic **PASS**; strict KV identity **FAIL**; scientific acceptance
**NOT GRANTED**; production promotion **NOT AUTHORIZED**.
