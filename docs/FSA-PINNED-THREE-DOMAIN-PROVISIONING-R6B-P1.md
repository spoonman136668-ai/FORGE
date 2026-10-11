# FORGE FSA R6B-P1: externally pinned three-domain provisioning descriptors

Parent: exact qualified R6A draft source commit `185ceeb6304a48fbf96947e3c346c7d120553fdc`.

This **source-only prerequisite** introduces `fsaprovision`, which checks canonical, content-addressed provisioning descriptors signed by three distinct **externally pinned** Ed25519 attestors for authority, witness and monotonic floor. No server, cloud resource, certificate, key or runtime is created.

The verifier requires:

1. An immutable bundle SHA-256 and archive/binding/epoch identity, all obtained **independently of the untrusted bundle**.
2. Separate pinned signing public keys for authority, witness and floor; signatures have an explicit domain separator and role identity.
3. Exactly three statements that claim nonoverlapping host, storage, failure-domain and service-SPKI identities, with independently referenced external evidence digests.
4. Exact canonical JSON at the input boundary, including rejection of unknown/duplicate fields, alternate encodings and trailing input.
5. No local inference of trusted keys, automatic retry, state mutation, scientific acceptance or new scheduler.

**A signed claim is not physical proof.** Different IDs, keys, hashes, and declarations do not establish that machines, regions, cloud accounts, power supplies, retention mechanisms or attestor custody are actually independent. The external evidence hashes are pointers for separate inspection, not a cryptographic proof that their underlying evidence is true. An operator-pinned bundle hash must not be generated from an attacker-supplied bundle at admission time. This package deliberately returns `ValidatedDescriptor`, never an authorization to deploy, operate, repair, or accept a scientific result.

Source qualification: identical immutable commit on hosted Linux (full tests, race, vet, build, public isolation) and native Windows (tests, vet, build), with adversarial cases including collocated claims signed by legitimate but separate keys, identity drift, forgery, signer substitution and noncanonical input.

Remaining physical R6B requirements: independently provisioned, custody-attested authority host, witness host and off-host rollback-resistant floor, distinct failure domains verified by a separate audit, power-loss and partition injection, host replacement, immutable external evidence retention and independent end-to-end trial. CKB-plane remains the sole active execution/orchestration and acceptance authority. Keep this draft inactive; **do not merge or cut over based on source CI**.
