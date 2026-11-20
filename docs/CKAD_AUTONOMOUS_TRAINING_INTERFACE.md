# FORGE specified-training campaigns — development source contract

A FORGE operator may specify a bounded, immutable **Yggdrasil/CKAD** native
cumulative-learning campaign and ask the **existing** FORGE-F139-UnifiedController
to prepare its next stage. This extends PR #1808's native checkpoint-custody
interface; it does **not** create a scheduler, controller, queue or an alternate
Yggdrasil scientific owner.

The ckad_campaign_request.validate_campaign function checks the exact owner
scope, source SHA/tree, tokenless composite learner, frozen seeds/preregistration/
splits/controls, per-stage and total CPU, observation and intervention budgets,
source mode and prohibited authority flags. It accepts **only previously
consumed development fixtures**. A different source, live scientific first-use,
paid models, promotion or owner release requires independent source-owner
qualification and an explicit separately authenticated contract.

next_stage re-audits the full composite checkpoint chain, requires a
**separately held** terminal-receipt SHA-256 after each completed stage, and
returns exactly one source-bound *proposal*. The proposal includes the owner
source, native candidate SHA/tree, stage index, checkpoint SHA, predecessor
receipt, component and stage budget. No action executes. The proposal always
sets dispatch_authorized=false and training_execution_authorized=false.
It returns ALL_REQUESTED_STAGES_SEALED at the declared stage cap and never
silently starts a new campaign.

seal_owner_result verifies the proposal is unchanged and calls the existing
CKAD byte-level custody validator; it does **not** create learned state or
measure intelligence. Future integration must use **the existing F139 owner
lock, ledger and authorized worker route** and obtain independent Yggdrasil
scientific-owner permission and persisted raw checkpoints. A self-reported
receipt head is not independent authentication. Unknown effects must remain
held rather than replayed. Negative results, frozen baselines, actual resource
receipts, and retained older capabilities must survive continuation.

## Qualification and activation boundary

This is a **development integration contract**, not live autonomous training.
Only source-specific regression and negative controls may qualify this PR.
No original owner source install, task change, GitHub training workflow
trigger, worker allocation, privileged source access, scientific first-use,
model promotion or accepted-ref change is authorized by this contract.
Yggdrasil PR #1207 is a draft and its latest learner head differs from the
original fixed CKAD13 source pin in PR #1808. Rebind and qualify an exact
native checkpoint interface before authorizing execution. Engineering PASS
is not SCIENTIFIC_PASS. A genuine live campaign must independently verify
CKAD's own source, admission, stage execution, stored checkpoints, cold
continuation, retention, unfamiliar transfer, matched controls, and cost.
