# AC-10 — Authentic upstream DTR packaging and development-interface preflight

**PRE-REGISTERED before any AC-10 upstream checkout, import attempt or environment episode.**  
**Status: SOURCE-ONLY EXACT-COMMIT COMPATIBILITY. No DTR episode is authorized/executed by this gate.**

## Exact upstream identity

CausalAILab/Causal-Gymnasium commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, tree `fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0`. Verify on every run with Git HEAD, tree and Git blob hashes before importing any package. Required original blobs:

- `causal_gym/envs/dtr.py`: `6af2371dce21804140ea141ccb7be14e003ba275`
- `causal_gym/envs/mdp.py`: `6264ec5450754c009e98c3e85f6d5927ece0a9ab`
- `causal_gym/core/pch.py`: `ff37780c6b791877c70583b8d5f699be7fcd8817`
- `LICENSE`: `993e3a4922f003dced0fd061735697c850ea7205`, Apache-2.0.
- `setup.py`: `31097c35f908e393bfd4763a298c1d5f4ab60600`.

**Engineering risk discovered:** Upstream `causal_gym/__init__.py` eagerly imports all `causal_gym.envs`, whose `__init__.py` eagerly imports over ten unrelated gym environments; `setup.py` declares broad `gymnasium[all]`, `box2d-py`, `highway-env`, pygame and other dependencies. Naïve `from causal_gym.envs.dtr import DTRPCH` may be unavailable on a clean minimal Python environment. Do not claim the original DTR is executable from an AST, a replayed fixture or an edited/stubbed fork. The bounded import check attempts the **unmodified original import** in a subprocess and records success or failure. A missing dependency is an honest packaging **BLOCKER**, not proof the causal mechanism fails.

## Hard source-public interface and prospective public development freeze

Only source-owned DTR `reset` and `do` are permissible for *later*, separately eligible source-public development. Its two native binary actions are at stages 0/1, with public initial `S1`, intermediate `S2`, then terminal binary reward. Source-owned `PCH` enforces task-specific permission checks; verify the actual task and permission on the unmodified runtime before actions. A prospective adapter may expose only:

`stage, observation, action, next_observation, reward, terminated, truncated, valid_actions`

Do **not** forward raw `info`, graph, `ctf_do`, environment object, latent confounder, SCM source, source-private labels or oracle data to learner, scorer or controls. Never infer availability of hidden future events. Package-level imports might legitimately initialize unrelated environments; such exposure must be isolated by process boundary, never by pretending that source code was imported faithfully.

**Proposed PUBLIC DEVELOPMENT seeds, held entirely unused by AC-10:**

- Smoke-only (permission-limited later): `759011, 759013`
- FIT proposed: `760000..760007`
- Public VALID reserved: `760100..760103`
- Public DEV reserved: `760200..760203`
- No scientific unknown-family, sealed CHECK or protected first-use seed is specified or made eligible here.
- At most two source-native actions per original DTR episode. All arms use equal public observation/action/reward access; any later comparison must prefreeze total matched FIT interactions and evaluate equally trained contextual/tabular and recurrent/episodic controls, with genuine unmodified DTR episodes and CPU, process RSS, wall, storage and checkpoint accounting. A source-native public development score remains **development-only**.

**AC-10 DOES NOT RUN THESE EPISODES.** It instead tests whether the exact external source is available and importable safely without changing it, preserving diagnostic failure. An unverified development owner/worker authorization or a missing native process adapter remains a hard stop before using seed `759011`.

## Qualification and stop rules

A narrowly scoped extension of `.github/workflows/forge-ac07-remaining-sourcefree.yml` uses GitHub-hosted Windows and Linux only, checks out the exact upstream commit into isolated `ac10_upstream`, runs `research/ac07_sourcefree/test_ac10_upstream_contract.py` against that checkout, and emits `ac10-report.json`. Tests must reject wrong commit, tree, any original blob drift, loss of permission methods, broad observation allowlist, seed overlap and positive scientific claims. No original source episodes, policy inference, training, model change, scientific FSA, source-birth signature or F139 controller/queue mutation. No new controller or separate scheduler; the workflow retains prior AC05/06/07 and AC08 regression.

The runtime import probe is an honest package-installation diagnostic **without installing upstream's heavyweight extras** and without using stubs. If it fails with `ModuleNotFoundError`, classify `UPSTREAM_IMPORT_BLOCKED`; do not claim a source-native pilot was performed or remove/upstream-edit dependencies to produce a green result. If it unexpectedly imports, that still qualifies **import only**, not public actions, W1 science, fitted model, or full-source packager.

**Admission disposition remains:** `ITD02_W1_SCIENTIFIC_ADMISSION=NO_GO_SOURCE_CUSTODY_UNPROVEN`. For a future actual public-development run, existing FORGE owner policy, original-source license and package integrity, safe isolated public-only adapter, and independently qualified existing native learner/checkpoint interface all need explicit source-bound clearance. Original sealed family birth/witness/high-water remains its own gate.

**Progress criterion:** AC-10 has established exact-source checkout compatibility and whether the original import is *runnable* without altering upstream. A blocked import is a completed **negative compatibility finding**, not technical permission to substitute a toy DTR. Next gate may qualify a full genuine upstream dependency environment on an isolated runner, without spending scientific first-use. No invented outputs or retroactive data sharing.

`AC10_FROZEN_SOURCE_COMMIT=c94e9a4cd3641588b6b8507e71ccee5c27032bdf`  
`AC10_UPSTREAM_DTR_EPISODES=0`  
`AC10_MODEL_TRAINED=FALSE`  
`AC10_NATIVE_MODEL_CHANGED=FALSE`  
`AC10_PROTECTED_SCIENCE=NO_GO`  
`AC10_NO_CKB_PLANE_OR_PAID_APIS=TRUE`
