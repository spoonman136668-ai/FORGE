# FORGE R13 — bounded Promptbreeder-style lineage (source-only)

Starting source identity: FORGE `22a67191b9b5e13c02ce943b31d1fc8369eba8b7` (R12). This batch addresses one previously PARTIAL enhancement without claiming autonomous scientific mutation, real result validation, deployment, or authority.

## Implemented

- `promptlineage.Generate` accepts one independently content-pinned, frozen plan per Wingless/Yggdrasil lane, including exact source SHA, generation, base prompt, fixed vocabulary, ordered operators, and a hard global cap of 32 mutations.
- Only two predefined operators (single-token replacement from the frozen vocabulary, or an adjacent swap) are permitted. Deterministic replay emits content-addressed parent/child lineage with all candidates labeled `UNTESTED`. No selection on sealed outcomes, learned prompt evolution, paid model call, runtime launch, self-dispatch, scientific acceptance, or budget expansion exists.
- Negative tests fail closed on source/pin drift, duplicate candidates, illegal operators/vocabulary, identity collision, missing bounds, and no-op mutation.
- Full Linux/Windows tests/vet/build and Linux race tests are required at the exact PR SHA before source inclusion. This is a small *implementation foundation*, not a qualified autonomous Promptbreeder experiment.

## Remaining to actually mark enhancements ready

1. Authenticate historical train-only candidate outcomes/propensities and link this source-only lineage to the strictly bounded screening portfolio without consuming protected heldouts.
2. Design/independently validate ThetaEvolve adaptation and DGM/GenEnv environment novelty using frozen budgets, matched controls, and separated cohorts; neither is being represented as active by R13.
3. Qualify independent FSA original-birth and first-use signing roots, complete CKB S14 custody, external monotonic CAS/owner revocation, real worker side-effect fencing and crash recovery. No R13 source artifact grants any of these.
4. Complete two independently accepted real generations for **each** lane, then the continuous unattended soak with verifiable successor handoff and zero duplicate originals.
5. Protect critical branches and acceptance surfaces from unqualified merges. Current public `main` was reported unprotected in GitHub branch metadata; source CI alone cannot replace protection and independent trust.

**Authority stays unchanged:** no original science, CKB accepted-ref mutation, autonomous runner or scheduler, deployment, production, credentials or broker actions. Existing Wingless and Yggdrasil work continues independently.
