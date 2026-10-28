# AC-11 — Exact upstream DTR dependency and public-smoke **result**

**2026-10-28 status:** `AUTHENTIC_DEPENDENCIES_INSTALLED_BOTH_OS`; `ORIGINAL_DTR_IMPORT_BLOCKED_BOTH_OS`; `PUBLIC_DTR_SMOKE_NOT_EXECUTED`; `SCIENTIFIC_ADMISSION_NO_GO`. This is a useful **packaging negative**, not a failure of candidate intelligence or a source-native experiment success.

## Exact reproducible custody

- Original upstream `CausalAILab/Causal-Gymnasium` Git SHA `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, original tree `fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0`, original committed DTR blob SHA-256 `e31eff82f862355057653d150967bb44a5ed57a6acaad57f7ecf2a551f6c6811`. All five AC-10 Git blob pins are verified by the AC-11 source contract on both OSes.
- FORGE AC-11 actual executable/test and workflow commit: `ea62801aefdd031fb7764da8c2d7516315ce991a`, existing open draft [PR #1062](https://github.com/spoonman136668-ai/FORGE/pull/1062), stacked on AC-06 #1061. Reuses existing read-only GitHub-hosted Linux/Windows qualification. No new scheduler/controller, protected main, model or scientific first-use authority.
- Exact Linux/Windows **PR run**: [#40786044538](https://github.com/spoonman136668-ai/FORGE/actions/runs/40786044538), both jobs **SUCCESS** for *development qualification and evidence preservation*, **not** actual native DTR execution. Exact-source push run [#40786035656](https://github.com/spoonman136668-ai/FORGE/actions/runs/40786035656) also passed.
- Source-only inherited AC-02/03/05/06/07/08 checks and AC-10 contract checks remained active. AC-11 8 anti-leak, permission, seed and no-science unit tests passed, but these tests use validator fixtures solely to test failure rejection; no fixture is counted as a source-owned DTR episode.

## Authentic upstream packaging experiment

The AC-11 driver created an ephemeral Python 3.11 venv on each existing GitHub-hosted OS. It successfully ran `python -m pip install <verified original upstream checkout>` with all dependencies declared by **unmodified** `setup.py`. No fake package, generated consequence source or altered `causal_gym` files.

| Parameter | Linux | Windows |
| --- | ---: | ---: |
| Upstream `setup.py` install | **Success**, exit 0 | **Success**, exit 0 |
| Install wall time | 156.65 s | 221.22 s |
| Exact `pip freeze` entries | 96 | 78 |
| Unmodified original `from causal_gym.envs.dtr import DTRPCH,DTRSCM` | **BLOCKED** | **BLOCKED** |
| Failure classification | `UPSTREAM_MODULE_NOT_FOUND` | `UPSTREAM_MODULE_NOT_FOUND` |
| Source-owned public smoke episodes | **0** (not attempted) | **0** (not attempted) |
| Source-native model trained | No | No |
| Original scientific first-use | No | No |

GitHub Actions evidence artifacts from the PR run: Linux ID `12858629830`, ZIP SHA-256 `0802271984dd408368d681f977bd29b27ed7a4faa28c5ca17446533285a5f7ba`, report SHA-256 `fd7968d0cd95425ee404eb8e35923ab388a18eca718c5b5b9a146d777883c79b`, freeze SHA-256 `9886aa449794fc950ddd907b6238b25efc943cfe78e0d0b7cfb39bc5f8603861`; Windows ID `12859661574`, ZIP SHA-256 `91be36146001e8bd3f6e43ffea1b7752f6c2a9cba344c53eeed806302cd4d863`, report SHA-256 `e6bdd5a286c318b6e1d4e5a6041c73a14cd991ba02050f12011fea1759d91e17`, freeze SHA-256 `780a6cdaaadd7c60354e2a2eb511afb56d52462faf3d7d6f30ffcff10299da3a`. These artifacts preserve all diagnostic flags and exact source identity; **not** science results.

## Root cause investigation: what is supported and what remains uncertain

The original upstream package `causal_gym/__init__.py` eagerly imports every `causal_gym.envs` module before `causal_gym.envs.dtr` can be reached. In the pinned original `causal_gym/envs/__init__.py`, `windy_minigrid.py` is imported first and directly requires `minigrid`; `mnist.py` also imports `torchvision` and `torch`; the `antmaze` family requires `ogbench`. **All three `minigrid`, `torchvision`, `ogbench` are absent from the Linux installed freeze**, and at least `minigrid` and `torchvision` are also absent from Windows. These are source-visible *undeclared direct-import dependencies*. `setup.py` contains heavyweight `gymnasium[all]`, but does not independently list those packages.

The authenticated AC-11 report records only the error **class** `ModuleNotFoundError`, not the specific missing module token; accordingly **`minigrid` is the earliest likely blocker based on static import order, but first thrown module is NOT independently verified from a traceback**. Do not silently overstate that root-cause identity. Current installed `gymnasium` version on Linux was `1.4.0`, despite original minimal spec `>=0.29.1`; compatibility of this API with upstream PCH has not yet been exercised. Installing the original setup successfully was therefore **insufficient** to run DTR unchanged. No error from DTR's action–consequence dynamics has been observed.

## Evidence-preserving next engineering action, without invented science

The next bounded **public development** packaging gate may add **genuine missing upstream-import dependencies** to the isolated venv, with exactly pinned package versions and a sanitized diagnostic of the first actual `ModuleNotFoundError`, while leaving the original upstream Git tree/blobs unchanged. Never install an edited/stubbed replacement of `DTRPCH`, replace the package initializer, or claim that separately executing a copied DTR equation represents upstream source-native behavior. The test must continue to gate any real episodes on a successful original import plus original `Task(learning_regime=do)` permission denial of `ctf_do`, and expose only public observation/action/reward fields from a separate process.

Source-native two-stage public smoke remains **NOT_RUN**; the reserved FIT/VALID/DEV seeds remain entirely unused. No comparison to trained native Wingless/Yggdrasil or conventional controls exists. Source-birth witness and independent scientific first-use remain **NO_GO** irrespective of future packaging repair. FORGE issue #857 is unchanged; active autonomous development and existing owner release policy are not touched.

`AC11_AUTHENTIC_ORIGINAL_SETUP_INSTALL=PASS_BOTH_OS`  
`AC11_GENUINE_IMPORT=BLOCKED_MISSING_MODULE_BOTH_OS`  
`AC11_REAL_PUBLIC_DTR_ACTIONS=ZERO`  
`AC11_QUALIFIED_SCIENTIFIC_RESULT=NONE`  
`AC11_SOURCE_FIRST_USE=FALSE`  
`AC11_NATIVE_MODEL_OR_CONTROLLER_MUTATION=FALSE`
