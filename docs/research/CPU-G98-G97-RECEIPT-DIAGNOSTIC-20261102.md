# G98 frozen G97 receipt diagnostic — development only

- Qualified diagnostic source: `75d1e0efcb7bb077d96d67ccf67339cd4bea87aa`.
- Focused Linux/Windows PASS: [41537138376](https://github.com/spoonman136668-ai/FORGE/actions/runs/41537138376).
- Mandatory original Linux/Windows full regression PASS: [41537145437](https://github.com/spoonman136668-ai/FORGE/actions/runs/41537145437).
- Original G97 model development source: `64e27188ed1c3e61980bc2c16f96a97c4ac2b73c`; [run 41523296068 attempt 2](https://github.com/spoonman136668-ai/FORGE/actions/runs/41523296068).
- Frozen artifact: [artifact 13182614903](https://github.com/spoonman136668-ai/FORGE/actions/runs/41523296068/artifacts/13182614903), archive SHA256 `576b4d0da61749a76c68dff2c4801f292f0fce3d2277509a8febf33355aab70f`.
- G97 decision: **DEVELOPMENT_NO_GO**. No protected held-out execution, acceptance or promotion.

## Observed cache events per 48-request repetition

| Traffic | Hits | Admissions | Bypasses | First bypass index |
|---|---:|---:|---:|---:|
| round_robin | 44 | 4 | 0 | none |
| bursty | 44 | 4 | 0 | none |
| mixed | 44 | 4 | 0 | none |
| overflow | 12 | 16 | 20 | 16 |

All four repetitions exhibit the same event counts. The diagnostic distinguishes observed request-wall and clone timings only. Separate prefix-prefill, KV construction, admission-decision, decode, fallback, and transition timings are **UNOBSERVED**. No causal attribution to admission overhead is established.

## Reproduction and integrity

Download the original G97 artifact from the linked GitHub Actions run and verify its ZIP SHA256. Extract `cpu_g97_development_result.json`. From the qualified G98 source, run:

```bash
python research/cpu_g97/g98_receipt_diagnostic.py cpu_g97_development_result.json cpu_g98_diagnostic_receipt.json
```

The script rejects non-development receipts, unqualified engineering/correctness, protected-cohort flags, wrong request counts and mispaired request identities. It produces a deterministic JSON receipt with the original G97 source and stream hash. Preserve the generated JSON unchanged with its SHA256 if archiving it separately.

This record preserves observations and qualification provenance only. It does **not** modify frozen G97 thresholds or declare a scientific candidate. Any future G98 instrumentation/measurement is a new development-only experiment requiring its own exact-head qualification.
