# F139-G4 — Portable, GitHub-attested original-owner negative-evidence receipt

## Scope and incident

The original F139 owner at `FORGE-CODEX-REMOTE` authenticated issue #856
exactly once and retained its failed development outcome at event193, preserving
11 quarantines and 18 verified tasks. Initial read-only audit job #40082015017
failed due to copying SQLite outside the original negative-artifact custody
root, not because original evidence was corrupt. Corrected run #40083044533
succeeded and left the original database unchanged.

That audit cannot run on the second escalated runner because it requires
the original SID and local SQLite + historical ZIPs. Making a second machine
a controller or copying private SQLite custody to GitHub is forbidden.

## Proposed qualification boundary

- On the **original Windows runner only**, authenticate the exact installed
  F139 source, Windows task name, task SID, protected GitHub `main`, issue
  policy #807 and first-use controls. Open original SQLite as URI
  `mode=ro`, copy it to a new one-shot scratch database **in the original
  custody directory**, and run existing `Database.verify()` plus original
  `verify_native_activation()`. No original writer is stopped or touched.
- Extract only public event-chain headers (seq, previous SHA, SHA), one
  target original admission commitment, and the target original terminal
  quarantine/provider negative payload. Do not publish the live database,
  historical provider archive ZIPs, private keys, signatures, source bodies,
  or model input. Schema/digest are canonical and bounded.
- Sign the **exact JSON receipt bytes** using GitHub's OIDC/Sigstore
  `actions/attest@v4` provenance. Upload only the receipt as a short-lived
  artifact. GitHub attestation is **mandatory**: a self-asserted JSON digest
  or GitHub Actions artifact URL alone must never grant trust.
- On an **independent GitHub-hosted runner**, first verify the signed artifact
  with `gh attestation verify`, bound to this repository, precise signer
  workflow, source ref and immutable source digest. Then validate its
  canonical hash, ordered header links, target terminal payload hashes,
  original failure run + dual-OS jobs, and preserved negative counts.
- The portable verifier checks supplied chain continuity and the two
  disclosed terminal event hashes. It **cannot independently re-run the
  original raw filesystem custody check** from a metadata-only receipt; the
  signed original-owner build claim is its trust boundary. Do not overstate
  this as independent access to original ZIP bytes or as scientific review.
  A compromised original runner remains a trust risk.
- Entirely **development-only**. The read-only workflow is manually/branch
  qualified, not attached to the original controller's scheduler, no
  automatic event append, no GitHub issue transitions, no acceptance, no
  second controller, no paid API or live broker permission.

## Acceptance gates

1. Adversarial synthetic checks on both OSes: canonical JSON, duplicate
   keys, changed event header, stale source, forged negative payload,
   duplicate target, missing artifact, altered scientific authority.
2. Original owner-only receipt job **PASS**, original SQLite proven
   unchanged. Failure of custody validation must block attestation/upload.
3. GitHub OIDC/Sigstore attestation **PASS**, followed by independent
   hosted Ubuntu verifier **PASS**, without mounting the original database.
4. Prove a reused/stale receipt, changed signer, different workflow ref,
   digest alteration or removed provenance is refused. Do not test by
   mutating live SQLite.
5. One full protected-repo regression and source merge only if all gates
   pass. A future original owner snapshot cadence requires separate
   authorization and risk-bound qualification; this PR does not schedule it.

If attestation is unsupported in this repository's GitHub plan, **stop
closed**; do not silently substitute an unsigned issue comment.
