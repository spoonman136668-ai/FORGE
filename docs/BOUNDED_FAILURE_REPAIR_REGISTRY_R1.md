# FORGE Bounded Failure & Repair Registry — R1

**Authority:** Evidence-only. Never an execution authorization, patch approval, scientific threshold decision, or license to waive controls.

Each incident is a versioned content-addressed JSON record. An exact advisory match requires repository, component, failure signature, applicability scope, and ordered preconditions, plus valid record hash and qualified status. Human- or separately-authorized agent-initiated repairs require independent provenance, bounded diff review, focused qualification, and final cross-platform integration regression. New incidents append new records; negative and failed repairs remain preserved, not overwritten. No replay of original scientific cohorts is authorized.

## Historical Linux public-isolation failure family

Observed in Actions:
- Failure **38307356790**: Public isolation rejected a newly introduced process-spawning supervisor and test. Narrow allowlist change qualified by **38307677046**, merged via PR #106.
- Failure **38308584693**: Existing standalone supervisor CLI integration test was outside the narrow allowlist. Policy change at **0e3c02f83ffa58a6918c932af0a1d5adf90305c9** passed Go tests but was not a fully qualified repair.
- Failure **38309699707**: Policy still expected two subprocess invocation files after a third crash regression was added. Exact inventory correction at **c8c1a350877e4248a0db819c2a06df7f450fac3f** passed **38310139710**, merged via PR #108.

**Reusable diagnosis:** If Go tests pass and Linux fails Public isolation, compare the actual process-invocation file inventory against the versioned CI restriction. The *repair is not* to remove isolation. Only explicitly justified synthetic-only file paths may be added, and a full regression must pass on the exact candidate SHA. Never auto-modify authority, scientific budgets, cohort ledgers, or operator controls.

**Provenance boundary:** These are source-control and Actions identifiers, not off-host signed scientific attestations. Re-query exact commits and checks before any reuse. The Go package does not provide authority to perform repairs or infer a missing original attempt is safe.
