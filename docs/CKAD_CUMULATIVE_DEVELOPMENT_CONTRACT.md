# CKAD cumulative-training custody interface — FORGE development only

FORGE's role is to audit checkpoint lineage and resource limits for
CKAD-authored Yggdrasil training. This is neither a trainer nor a release
route. Yggdrasil/CKAD remains the scientific source owner.

Exact source baseline: Yggdrasil main `5e74f8db85b2f5839c42148c0dfba69a88b1a2c9`,
CKAD13 integrated draft PR #1207 candidate `8eb49bdb8f6d6886d05d6e3e67c0994aa6ebac2e`
(tree `2786140a50ec26a025760f771aeeb82573c10dd3`).

The CKAD13 owner provides one integrated `NativeCumulativeLearner.checkpoint()`/
`restore()` format spanning A-F. FORGE accepts its supplied raw byte
identity, not separate incompatible component checkpoints or language-model
predictions. Source-bound results remain development evidence only.

`plan_digest` freezes source SHA/tree, tokenless architecture, synthetic-only
evidence mode, seeds, curriculum stages, metric-control and split pins, and
per-stage resource budgets. `seal_stage` requires the *actual byte sequence*
at both ends of each stage and the evidence/control/evaluation receipts,
checks the input against the previous stage output, and returns an inert
SHA-chained audit record. `audit_chain` checks the full declared chain and accepts an optional
`expected_head_receipt_sha256` from independent CKAD custody. Without that
external head pin, a deliberately substituted *terminal* output hash cannot
be distinguished from a genuine state by digest chaining alone. It cannot
prove external checkpoint bytes were persisted or actually trained; original
CKAD custody must independently verify those facts.

All receipts set `scientific_pass=false`,
`training_executed_by_forge=false`, `development_custody_only=true`.
This code has no runner, network, provider, controller, scheduler, database
writer, promotion, source first-use, or training execution.

**Next experiment is CKAD-owned, NOT silently started by this contract:**
qualification of the existing CKAD13 integrated A-F trainer on exact source,
then independently authorized new original-source scientific exposure and
matched controls. No FORGE action may create a new scientific training run. This schema is ready to
validate its handoff only when CKAD supplies authentic checkpoints and
approved original source admission.
