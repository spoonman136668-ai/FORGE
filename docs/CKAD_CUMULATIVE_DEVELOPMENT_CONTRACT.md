# CKAD cumulative-training custody interface — FORGE development only

FORGE's role is to audit checkpoint lineage and resource limits for
CKAD-authored Yggdrasil training. This is neither a trainer nor a release
route. Yggdrasil/CKAD remains the scientific source owner.

Exact source baseline: Yggdrasil main `5e74f8db85b2f5839c42148c0dfba69a88b1a2c9`,
CKAD draft PR #1182 candidate `5df8dbf506027b914f66e19441376d1347a3e09d`
(tree `52e54277d155f8ab683ef34e02e4a0d599e54037`).

The existing CKAD component APIs `NativeContextBasis.checkpoint()`,
`NativePropertyKnowledge.checkpoint()`, and their restore methods already
yield native checkpoint bytes and hashes; this adapter handles supplied bytes
and requires exact identity, not an LLM-generated answer.

`plan_digest` freezes source SHA/tree, tokenless architecture, synthetic-only
evidence mode, seeds, curriculum stages, metric-control and split pins, and
per-stage resource budgets. `seal_stage` requires the *actual byte sequence*
at both ends of each stage and the evidence/control/evaluation receipts,
checks the input against the previous stage output, and returns an inert
SHA-chained audit record. `audit_chain` checks the full declared chain but
cannot prove that external checkpoint bytes were genuinely persisted or
trained; original CKAD custody must independently verify that.

All receipts set `scientific_pass=false`,
`training_executed_by_forge=false`, `development_custody_only=true`.
This code has no runner, network, provider, controller, scheduler, database
writer, promotion, source first-use, or training execution.

**Next experiment is CKAD-owned, NOT silently started by this contract:**
one source-qualified integrated trainer that continues the exact native
checkpoint across knowledge, causal-fit and contradiction/retention stages,
with frozen conventional and independent symbolic controls, cold restart,
unfamiliar transfer and whole-process cost. This schema is ready to
validate its handoff only when CKAD supplies authentic checkpoints and
approved original source admission.
