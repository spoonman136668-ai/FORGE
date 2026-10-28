# AC-14 — Authentic OGBench package compatibility and source-public DTR smoke

**Pre-registration; engineering-only, no original scientific first-use.** Existing branch/PR: [FORGE #1062](https://github.com/spoonman136668-ai/FORGE/pull/1062). AC-13 qualified Linux/Windows with original pinned PyTorch CPU wheels at exact source `7bfcdc62b858a358282ed1708535266c67ce452f`; both original DTR imports failed next with precisely `ModuleNotFoundError: No module named 'ogbench'`.

## Source and dependency identity

- Upstream original source: `CausalAILab/Causal-Gymnasium` commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, tree `fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0`, canonical committed DTR SHA-256 `e31eff82f862355057653d150967bb44a5ed57a6acaad57f7ecf2a551f6c6811`.
- Only new candidate top-level package: **official PyPI `ogbench==1.2.1`**, exact published wheel `ogbench-1.2.1-py3-none-any.whl`, SHA-256 `597ac2207935e4edc46de5d5742e940a753f2329e18612e9cfe7f9e857435f83`, **8,940,331 bytes**, published 2026-01-14. Verified against immutable version-specific official JSON endpoint `https://pypi.org/pypi/ogbench/1.2.1/json` before any install. The PyPI record lists `mujoco>=3.1.6`, `dm_control>=1.0.20`, `gymnasium[mujoco]` and other packages **only under optional `train`/`dev` extras**; do **not** install those extras or GPU training packages.
- Pin the entire OGBench wheel bytes, not only a human-readable version. Install the authenticated downloaded file into the *existing AC-11→13 ephemeral venv*, allowing genuine wheel-only runtime dependencies but no source-code build, stub, editing source checkout or alternative causal environment.
- Preflight strictly requires AC-13's source-bound report with pinned original SHA and tree, both actual CPU wheels' verified official hashes, successful real CPU installation, and exact missing `ogbench` in the subsequent original DTR import. If any precondition changes, **hard stop** before installation.

## Source/runtime controls

1. Use installed Python 3.11, real original package and legitimate public dependency resolver. Record official PyPI JSON wheel SHA, downloaded wheel bytes/hash, package install exit code/time and complete environment freeze SHA/package count. No privileged original-state/SCM inspection by model.
2. Attempt original `from causal_gym.envs.dtr import DTRPCH,DTRSCM`. Report exact missing-module token, incompatible API or other class if blocked; no speculative fix/next package installation. An import PASS is **not** a learned-model or two-stage environment PASS.
3. Only on genuine import PASS, run existing `ac11._SMOKE_CHILD` in an isolated subprocess with exactly two **public-development smoke seeds `759011,759013`**, two predetermined actions `0,1` each, original `Task(learning_regime=do)`, denial of forbidden `ctf_do`, stage/observation/action/reward/terminal whitelist. Original `info`, `env`, latent `u`, graph, source/CF and any privileged state never cross into learner-visible report.
4. The FIT `760000..760007`, VALID `760100..760103`, DEV `760200..760203`, sealed CHECK and unfamiliar-family source identities remain unused. No native Wingless/Yggdrasil model fitted, trained, changed, compared, evaluated or scientifically admitted. Any attempted failed smoke reports action/episode counts **unknown**, never 0. Only a fully validated two-episode result can claim 2 episodes/4 actions. No source-birth signatures or FORGE policy/queue writes.

## Qualification limits and budget

Reuse the existing narrow [AC-07 source-free workflow](https://github.com/spoonman136668-ai/FORGE/blob/research/ac07-remaining-originals-sourcefree-20261028/.github/workflows/forge-ac07-remaining-sourcefree.yml) with its source-bound AC-05–13 regressions, plus AC-14 guard tests on GitHub-hosted Linux/Windows. Limit official wheel metadata read and wheel download to **120 seconds**, wheel-only install/dependencies **180 seconds**, import **40 seconds**, two public smoke episodes **45 seconds**. Preserve archived JSON and frozen dependency inventory even on packaging-blocked outcomes. A failed install is **BLOCKED, not candidate science FAIL**. If the package requires a platform-only dependency that cannot be installed from genuine wheels in budget, retain the failure and do not build an untrusted fork.

**Explicit stop:** Source-public compatibility is not independently witnessed original ITD-02 W1 scientific source birth/first-use; an imported and successfully smoked original DTR still has no claim to native architecture improvement. No new controller, recurring scheduler, F139 intake/queue, CKB-plane, paid APIs or protected-main mutation.

`AC14_OGBENCH_PIN=1.2.1`  
`AC14_WHEEL_SHA256=597ac2207935e4edc46de5d5742e940a753f2329e18612e9cfe7f9e857435f83`  
`AC14_SOURCE_OWNED_PUBLIC_ONLY=TRUE`  
`AC14_SCIENTIFIC_FIRST_USE=FALSE`  
`AC14_NATIVE_MODEL_OR_CONTROLLER_CHANGED=FALSE`
