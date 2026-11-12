# ITD-02 original Gymnasium DEV action/reward smoke — executed source receipt and G145 correction

**Original runtime execution: PASS**. Exact FORGE parent candidate `30580883c37decb92b3edc6cb297dbe7f21964d2` (protocol-only ancestor `42b2b1820419bb7ee59f823dee92e55b2b08690b`, source Git blob `bdffca543aa042dbc7e5f1f638a8e24d30ff28fc`). Existing PR #1614, research branch only. Read-only, isolated GitHub-hosted original run [#42799563753](https://github.com/spoonman136668-ai/FORGE/actions/runs/42799563753), job `itd02_original_gymnasium_dev_smoke` **SUCCESS** (129773314060); original JSON [artifact](https://github.com/spoonman136668-ai/FORGE/actions/runs/42799563753/artifacts/13754869564), retained seven days. The original pinned upstream `Farama-Foundation/Gymnasium` commit was `e6be96abfb0a9df36da5e7884522c4f1f2432e53`, tree `0a6e6b8c16c9b039fad21128336cecf3a13e0877`; strict Git checkout integrity, four exact upstream file blobs, imported package provenance, public observation grammar and no post-termination action were verified in the original job. The Python runtime used selected exact dependency versions but no transitive wheel SHA lock: **dependency supply-chain hermeticity not proven**. No hidden simulator state, counterfactual, first-use or native learning was used.

## Executed physical simulator action/reward evidence (fresh independent deterministic replay)

| Original environment | Dev seed | Actual steps | Reward sum | Trace SHA256 | Episode ended |
|---|---:|---:|---:|---|---|
| CartPole-v1 | 547 | 14 | 14.0 | `6a089d4bf226a7b93b10adf03506886c5cf2940fd9904e0838c7d83d33dc70b6` | terminated |
| CartPole-v1 | 557 | 32 | 32.0 | `8c5dbafb25f3b556e269ee8824126566b3bacfff27561ee38b12cde4c878bc03` | truncated by DEV smoke cap, not upstream |
| MountainCar-v0 | 547 | 32 | -32.0 | `527ed416d719511d950381e442aa29d6a4063bbdb8f3b489a0489e4c48fd1b75` | truncated by DEV smoke cap, not upstream |
| MountainCar-v0 | 557 | 32 | -32.0 | `07ecbd36ab669ac71b90ad02126b87e6b7ce34d2f471de391d00ebe60c8edbc9` | truncated by DEV smoke cap, not upstream |

Each world/seed original trace was executed twice from fresh original instances and exactly matched. Canonical JSON report SHA256 (inside report) `a1a6d976a64c39227d239d70c1244321b049f6c3ef2ee39e064fd4221f89bd8b`, exported JSON file SHA256 `8618b588f707922e2cbccd349675394fd7ff8b69d23fd14976ec9e4fbbd4e3c6`; both were verified from downloaded original artifact after the job. Four original DEV traces; **not** evidence of successful model training, causal advancement, retention, transfer, independent science or live FORGE owner execution.

## Mandatory G145 scope correction (no weakening)

The temporary branch-only job was initially added to `.github/workflows/qualify.yml` on the Eureka draft to run this original smoke once. This **violated the existing G145 generic-source PR allowlist**, and the original run at head `30580883c37decb92b3edc6cb297dbe7f21964d2` correctly failed both Linux and Windows native jobs with `G145_GENERIC_PR_CHANGED_OR_UNRELATED_HARNESS`; Windows reports downstream `G148_COMPILED_INPUT_IDENTITY_FAILED`. This is an **engineering source-scope failure introduced by the temporary workflow change**, not F39's frozen scientific result nor the prior G141 timeout. The original smoke job itself passed.

**Corrective source action on this child commit:** restore `.github/workflows/qualify.yml` to its original exact Git blob `8b6710df902710d088fe9658da718d22244e5151` (the parent F39-approved workflow), preserving G145 guard unchanged. Keep the inert, exact original smoke implementation as source-only research evidence and this separate retrospective receipt. **No replacement workflow**, bypass, new PR, runner, scheduler, F139 owner/worker or additional original execution triggered beyond normal existing PR qualification. F39 SCIENCE stays `DEV_NO_GO 0/4`; original full regression qualification for corrected head must be checked separately and cannot be called PASS until final results.

**Disposition:** `ORIGINAL_ENV_DEV_SMOKE=PASS`, `PR_SOURCE_SCOPE_CORRECTION=PROPOSED_IN_THIS_COMMIT`, `INDEPENDENT_SCIENCE=NOT_RUN`, `FIRST_USE=NOT_CONSUMED`, `MERGE_DEPLOYMENT=INACTIVE`.
