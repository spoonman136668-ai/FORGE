# CPU G96 original GPT-2 development artifact receipt — 2026-10-31

**Status:** DEVELOPMENT ENGINEERING PASS; SCIENTIFIC ACCEPTANCE NOT GRANTED; NO PRODUCTION INTEGRATION.

- GitHub Actions run: https://github.com/spoonman136668-ai/FORGE/actions/runs/41232592023
- Source commit: `e6b7b5243873b9eb82b400e2c52c0676711fe905`
- Jobs: source-admission PASS; original-model-development PASS
- Artifact ID: `13054712436`, name `cpu-g96-original-gpt2-development`
- Original downloaded artifact ZIP SHA-256: `63b7f9168cf15b392f32714278ce0380be6594ef21a4accb913b30bfb16ba4ac`
- Original result JSON SHA-256: `903e90752df2b258b9795e1b28ec8d355abb1f048e13cbc7ec776e663b9dd22e` (500114 bytes)
- Original environment TXT SHA-256: `99a1cfd1f16a8ee6418e48d563802c29e9d04afe6de627eab48bd78ab98d3f34` (3728 bytes)
- Phase: DEVELOPMENT_ONLY; GSM8K ranked cohort 276–287; heldout_executed=false.
- Pinned GPT-2 model and dataset identity verified by runner; exact-token parity PASS for all executed arms.
- Development cost calibration: median prefix prefill `607914073 ns`; median KV clone `5755155 ns`; expected reuses `2`. **Not frozen as final candidate selection.**
- Development stratum wall times (seconds), ordered baseline / LRU / second-use / frequency / cost-aware:
  - Round-robin: 42.649 / 20.734 / 22.632 / 22.665 / 23.025
  - Bursty: 42.308 / 20.875 / 22.928 / 22.774 / 22.598
  - Overflow: 42.449 / 47.236 / 46.393 / 46.415 / 46.223
  - Mixed: 42.497 / 21.093 / 23.193 / 23.229 / 23.067
- **Methodology gap:** the development script executed one 48-request cycle per stratum rather than the preregistered four paired repetitions; this is exploratory development evidence, **not** frozen-criteria qualification. The overflow traffic has zero cache hits for all policies, and cached arms are slower than uncached. Do not extrapolate aggregate speedups or advance to heldout.
- The result and environment originals remain in GitHub Actions artifact storage (30-day retention), **not** committed as full raw files in this repository. This receipt anchors their byte identities. Preserve the originals durably before expiry if required by the evidence contract.
- Next: correct the development measurement harness to four independent paired repetitions per stratum, enforce all frozen metrics and exact cohort/stream identity, rerun development, then freeze policy/calibration and publish a replacement qualified receipt. Protected heldout and promotion remain blocked.
