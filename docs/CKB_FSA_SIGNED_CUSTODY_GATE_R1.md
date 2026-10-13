# FORGE two-lane CKB → FSA custody gate R1 (inactive)

**Purpose:** Compose the actual old CKB-plane irreversible S09–S14 first-use records with an independently signed release observation from the original Wingless/Yggdrasil lane custodian and a separate signed FORGE Scientific Authority (FSA) high-water witness. This is a **read-only consistency gate**; it is not scientific activation.

The new `cutovergate.Assess` demands all of the following before returning even an **audit candidate**:

- The existing CKB ledger directory is read-only, contains all six canonical permanently consumed S09–S14 first-use records, matches independently pinned SHA256 digests, and retains the exact S14→S09–S13 predecessor hash chain. **Missing S14 is unconditionally blocked as unknown, not assumed unused.**
- The previously implemented `lanetakeover.Preflight` verifies both original lane identities, exact source commits, queues and the old owner, with zero signed active leases or uncertain dispatches. Both lane release fingerprints are nonzero and distinct.
- One **new Ed25519-signed joint custody observation** binds the exact inventory SHA256, S14 ledger SHA256 and both signed lane-custody fingerprints to the same old authority and a fresh observation (maximum 300 seconds). Individually valid but unrelated or stale snapshots cannot be spliced together.
- `fsaremote.VerifyWitness` verifies a separate signed FSA high-water checkpoint against independently pinned archive ID, public signing key, owner epoch, physical binding digest and minimum monotonic witness revision; the old CKB collector, FSA witness, FSA authority and FORGE original-grant keys may not collapse into one signing role.
- A NEW dedicated local FORGE original-reservation store is independently read and must be empty and at the exact genesis head. An existing, corrupt or uncertain reservation blocks; it is never overwritten or reset.

Tests exercise a six-generation synthetic CKB first-use history, both independently signed existing-lane releases, signed joint read-only custody, signed FSA high-water and a clean genesis FORGE reservation store. Negative tests cover missing/changed S14, old active lease, queue substitution, forged join, stale observation, signer reuse, FSA witness rollback/forgery and existing FORGE reservations.

**Hard boundary:** Passing this source-only gate returns `INACTIVE_CUSTODY_CANDIDATE_NOT_AUTHORIZED`, `cutover_authorized=false`, `science_activated=false`, `original_replay_authorized=false`, and explicit unsatisfied conditions. Signed source assertions do **not** prove the old owner was actually revoked or that a live independent server retains monotonic state. The gate deliberately does not expose an authorization token, activate either lane, consume a cohort, execute a patch or dispatch a worker.

**Still required for real cutover:** verified CKB/GitHub issuer and original-run histories (including the previously ambiguous S14 attempt), independently measured live owner revocation and worker-side epoch fences, provisioned off-host linearizable FSA and witness services, qualified source and whole-tree regressions, original two-lane genuine unattended cycles, and explicit qualified cutover approval. KTRADE remains untouched and paper-only.
