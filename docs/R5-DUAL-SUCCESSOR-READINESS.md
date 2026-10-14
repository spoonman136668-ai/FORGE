# R5 — Two-lane signed-parent successor-readiness seam

**Purpose:** Link FORGE's already-present scientific review, historical-policy replay, diverse candidate selection and next-hypothesis cursor, without adding another authority, worker, scheduler, cloud bill or manual classification bypass.

## Reused primitives

- `classification.AssessSuccessor`: exact Ed25519-signed independent parent classification **and** the terminal Classified event in a verified hash-chained `researchstate` journal.
- `evoportfolio.PlanAfterReplay`: independently pinned training-only historical policy and frozen diverse portfolio. Report validation/holdout utility but do not train or select on holdout.
- `evoportfolio.NextAdvisory`: deterministic first eligible candidate from the frozen finalist order.
- `classification.PlanDualReadiness`: one pure call for Wingless and Yggdrasil with independent source identities and no shared candidate source SHA.

**Scientific invariants:** Classifications NEGATIVE and INCONCLUSIVE are eligible to *propose* a fresh, separately qualified successor. INVALID stays blocked in its lane without stopping the other's advisory progress. Source crossing, wrong signing key, missing journal classification, changed frozen portfolio and invalid historical outcome fail closed.

**Optimization:** The selected ranking policy is based on training only; the diverse finalist portfolio and compute budget stay frozen. Explicit train/validation leakage tests ensure changed heldout outcomes cannot retroactively change the selected training policy. The two lanes do not share parent source identities or selected candidate source SHA.

**Operating state:** This is an adapter, not evidence that genuine first-use source custody or new automatic experiments have occurred. All positive tests use synthetic signatures, local append-only journals and frozen unit fixtures. No authentic independent reviewer signing keys or source/custody receipts are committed. No live inputs are automatically fetched because the hourly read-only metadata observer cannot authenticate scientific classification.

**Next real gate:** Deliver independently authenticated parent classifications and journal checkpoints through the **existing** owner-approved scientific intake, then prepare a frozen candidate/continuation record. Scientific execution remains under the existing narrowly scoped once-only authority, with zero new FSA controllers. Cloudflare archival integration uses the previously provisioned setup only when correct access, quota, restore identity and off-host control are independently verified.

**No new recurring workflow:** The existing `forge-integrated-synthetic-cycle.yml` already runs Linux/Windows every six hours. It now runs the classification/readiness and researchstate regressions in that same qualification job.

This is a bounded autonomy-and-optimization **engineering** gate. It is not a declaration of production autonomous research or scientific improvement.
