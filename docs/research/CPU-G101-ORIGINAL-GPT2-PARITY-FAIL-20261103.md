# CPU G101 P2 — Authentic original GPT-2 correctness result (2026-11-03)

**Verification outcome: KV_BIT_EXACT=FAIL; GENERATED_TOKENS=PASS.**
Engineering execution of the original-model parity workflow **FAILED as designed**
on an actual floating-point KV mismatch. This is an authentic correctness gate,
not a runner failure, and no performance qualification or promotion is allowed.

## Immutable original evidence

- Source commit and frozen implementation: `02267960aa9f9944cb598c1f126f64439ef4a2f3`.
- Original-model execution trigger: `21298b9b08ac44002e739cb1d12884af562ff369`.
- Original-model run: https://github.com/spoonman136668-ai/FORGE/actions/runs/41733947792 .
- Source-admission job: **PASS**.
- Original-model parity job: **FAIL**, raised `G101_PREFIX_KV_NOT_BIT_EXACT`.
- Artifact: `cpu-g101-original-gpt2-parity-only`, ID `13278585512`.
- Artifact ZIP SHA-256: `c83ba468f6e660ddbcabfa9c945c7fa8d8efa0b1aec7a584f344c72ef9bdce04`.
- Qualified exact-source Linux/Windows regression: https://github.com/spoonman136668-ai/FORGE/actions/runs/41732579833 (both PASS).
- Temporary workflow push trigger removed in `7ff8bb21e23be79996ce9d88d1af2e58dc6cbc66`.
- Dataset SHA-256: `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`.
- Model weights SHA-256: `248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707`.
- Development ranks: 276–285 (previously used G100 development ranks);
  protected ranks 288–299 were **NOT** used.

## Measured result from raw run artifact

- Generated-token parity: **PASS**, 10 of 10 actual original-model requests.
- Prefix KV bit-exactness: **FAIL**, 0 of 10 prefix/suffix checks were exact.
  Each check compared 24 tensors (12 GPT-2 layers times K/V).
- Largest max-absolute KV difference: `1.52587890625e-05`.
  Per-check maxima ranged from `1.1444091796875e-05` to
  `1.52587890625e-05`.
- Model calls: 80 (10 requests times 8 model forwards); extra standalone
  prefix forwards in the *candidate request path* are zero.
- Cache: 7 misses, 7 admissions, 3 hits, 3 evictions.
  Peak logical resident KV bytes: 86,114,304 (at the frozen cap).
- Performance verdict: `NOT_EVALUATED`.
  Scientific acceptance: `NOT_GRANTED`; protected or production promotion: **false**.

## Interpretation and next bounded diagnostic

The KV mismatch is consistent with (but does not prove) floating-point
kernel/shape-dependent rounding between full-prompt and standalone-prefix
prefill. Generation parity on this limited development sample does not
supersede the strictly frozen KV-equality requirement.

**Next eligible research diagnostic:** compare per-layer prefix KV tensors
using exact equality, max absolute difference, number of differing elements,
and ULP-distance distributions; compare separate-prefix versus full-prompt
runs with identical CPU runtime, thread count, model, dtype and suffix lengths.
Add zero-suffix and short-suffix controls, and check whether mismatches
correlate with total sequence length or execution kernel. Use development
inputs already consumed, not protected ranks. Preserve all original raw
receipts and the authentic FAIL. No threshold relaxation, approximate
equivalence substitution, hidden forward computation, or timed G101 trial.

Only after discovering a mechanism that satisfies the strict original
bit-exact KV and token contract should a new frozen performance protocol
be considered. If exact KV cannot be achieved economically, retire this
exact-capture mechanism rather than changing the acceptance rule after
observing the failure.
