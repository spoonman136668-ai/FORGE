# F139 scientific selection — source-only FSA handoff

FORGE's existing F139 Windows controller is the **only** scheduler. This patch
does not create an alternate controller or enable scientific execution.

\`fsaadmission.AssessSelectedArchived\` composes the already-existing independently
recovered FSA archive, frozen experiment / complete all-lane ledger check,
and a source-born experiment candidate carrying:
- a signed, domain-separated frozen hypothesis/protocol, strongest fully trained
  control and equal-training evidence digests, with complete native CPU,
  peak resident memory, and wall-time caps;
- a separate, independently signed source-birth witness for two unfamiliar
  source families, from an independently pinned distinct Ed25519 public key;
- matching lane, candidate, source/cohort and the ordering of freeze vs birth.

Every failure denies; passing means **preflight only**. Real pins must be
independently provisioned: keys included in experiment data are not keys.
Synthetic signatures in the regression tests establish only parser/verification
correctness, not independent authority or real source first-use.

Still separately required before any science work: authentic F139 23-event
custody witness and source transition; real independent frozen signer and
source-birth signer; independently authenticated no-prior-use global ledger,
and an **atomic externally accepted start receipt** before the existing
controller may dispatch once. The present F139 development worker must remain
development-only. No new scheduler, paid API, Cloudflare controller, or CKB
dependency.
