# G85 final evidence qualification trigger — 2026-10-31

This record requests the existing exact-receipt Linux and Windows regression workflow to validate the already-committed native ARM64 experiment receipt. It does not modify or reinterpret measurement data.

- Original ARM64 workflow run: `41204709461`, terminal workflow success.
- Frozen preregistration: `275284b5c2fffd8031fe2caaa570793e3fe6941a`.
- Original-model result branch HEAD: `ca7f5f4300a6e05ff9fa42e9edd5be5d15297a24`.
- Raw result blob: `3f9ee2d07fc6cfe27d869c20b3bae95c026a7fc0`.
- Raw result SHA-256: `4ab290bd0c603a0717624347a206076bd851fb99c7ef8648660db9e8469c88dd`.
- Native architecture verified as `aarch64`; original model/data identity, 180/180 exact-output responses and 1,440 output tokens PASS.

Frozen decision is **TRANSFER_FAIL**: uniform2 median speedup was **1.061656× vs uniform1** (below 1.35×) and **0.972751× vs uniform3** (below 1.05×; three threads were faster). The paired-minimum, p95, sampled RSS and process CPU limits passed. Do not retune, and do not treat this as model acceptance or intelligence transfer.

This trigger exists solely to run the required exact-receipt custody, unchanged G70 baseline, F139/isolation and full Linux/Windows source qualification. Scientific/model acceptance remains NOT_GRANTED.