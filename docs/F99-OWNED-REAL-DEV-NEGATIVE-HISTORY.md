# F99 — Authenticate original archive bytes and recover real train-only development negatives

**Purpose:** Close the previous F98 limitation: verify the **actual original ZIP bytes, exact embedded JSON and every frozen development row** of Wingless W-F10 and Yggdrasil Y-F9. Retain them as FORGE-owned, source-pinned historical negative observations that can inform *future development hypothesis selection*, not as independently accepted scientific originals.

## Actual original archive inputs

Directly downloaded from GitHub Actions in the preparation/qualification of this source:

| Lane | Source and run | Archive ZIP SHA-256 | Contained JSON SHA-256 |
|---|---|---|---|
| Wingless W-F10 | `fab5f094a29203a5ef1d63fb40225a3aa9a7e57f` / 38646170288 / artifact 11932322023 | `cf160c2abe1dcc32425f89eb445a20de47ba01c5b158e4fb9242507554dbaadf` | `f397e0f45b0f1664426bca7d5a196eacc5d131d417c9030cc276aa9342a15d92` |
| Yggdrasil Y-F9 | `714e10f9df0d036f66e4baea229470ed4fe86f04` / 38646109265 / artifact 11932008018 | `cc20faf2c31607ace820b2a9bd90d334b52902a2f776384f938a91884a99fb9e` | `669c3564d7715621e97aa345ee081912223a91c337a17bd3e7dc1c5e6f38f4af` |

ZIPs each contain precisely one bounded JSON source report with the registered development negative. Real observations, independently recomputed from all row-level predictions:
- **Wingless:** 96 depth counterfactual pairs (192 questions). Frozen depth-blind learned model solved **0/96 complete pairs**; the coded depth-aware control solved **96/96**. Fails because requested depth was not present in the learned model's frozen input interface.
- **Yggdrasil:** 192 typed-role counterfactual pairs (384 questions). Role-blind learned model solved **0/192 complete pairs**; typed-role coded control solved **192/192**. Fails because the learned model's state lacked role codes.

These two cohorts are strictly historical **development-only** records. Neither is an independent protected original; neither has independent source-birth custody, sealed first-use authorization or independently accepted scientific promotion.

## Concrete files and reproducible acceptance

`reference/research-intake/f99-authentic-development-negative-history.json` is a FORGE-owned, commit-pinned historical negative snapshot with exact original artifact and contained-byte digests, the original registered outcomes, and deterministic observed-only diagnostic vectors:
- Wingless `[96,96,96]`: [wrong complete pairs, coded control correct pairs, total pairs]
- Yggdrasil `[192,192,192]`: same fixed feature definition

These are **observed retrospective historical diagnostics**, NOT newly learned environment vectors, independently accepted policy-improvement data or native-cognition gains.

`nativeevidence/f99_real_archive.py` rehashes both GitHub ZIPs and their one permitted JSON member, verifies exact schemas/DEV/no-science flags, checks every frozen seed/family pairing and every paired prediction including strong coded control and shortcut baseline, independently recomputes score totals/false positives, and checks the negative verdict and snapshot vectors. `nativeevidence/test_f99_real_archive.py` exercises replay, omission, false labels, missing controls, spoofed scores, wrong source/malformed ZIP and authority drift.

FORGE's existing six-hour integrated GitHub workflow runs F99 source-only adversarial tests **mandatorily** and invokes real archive download/reaggregation **optionally**, alongside the separately quarantinable F98 historical-source observer. GitHub is the only network provider. If archived remote source is unavailable, F98/F99 admission is explicitly quarantined and the independently qualified native synthetic core remains healthy. No new workflow, scheduler, credentials or CKB-plane integration.

## Absolute scientific limits

No model inference, Codex, Work tasks, paid inference, original rerun, accepted-ref mutation, protected first-use or policy promotion. **No live GenEnv training is activated by this gate**. The owned negative snapshots are eligible for future **development-only planning** after the frozen feature mapping and scientific controls are independently qualified. The two old cohorts cannot be represented as novel independent validation or reused for later first-use.

Passing CI and seeing two real reaggregated negative records confirms source integrity and negative preservation only. It does not solve unattended GPT inference. The next scientific gate is to preregister and implement *substantively different* source- and role-aware mechanisms under fresh, separately frozen development conditions, retaining strong controls and distinct protected cohorts.
