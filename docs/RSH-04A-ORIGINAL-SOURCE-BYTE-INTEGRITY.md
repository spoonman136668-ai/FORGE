# RSH-04A — exact original research source byte integrity

## Bounded change
RSH-03 qualifies an optional read-only FSA archive-head transport, but does not authenticate any original research bytes. RSH-04A introduces `researchfeed.ObserveOriginalIntegrity` and adversarial tests for **one selected immutable source** in the existing six-lane index. It does not modify the index, FSA, private archive, existing F139 feeder, or any scientific result.

The observer first strictly validates the entire proposed untrusted index. Before reading a source, its target entry must exactly match an externally supplied frozen `OriginalPin`: lane, research ID, approved repository, exact commit SHA, relative path, Git blob SHA-1 and byte SHA-256. An optional reported digest must also match. The injected source transport returns at most 1 MiB. The observer recomputes both the exact Git blob framing SHA-1 (`blob <size>\0<original bytes>`) and SHA-256. A mismatch, absent original, unexpected identity, malformed input, cancellation or failed transport denies the observation.

**Scope of success:** only `blob_integrity_verified=true`, advisory-only. All of `original_bytes_authenticated`, `external_signer_verified`, `original_first_use_cleared`, `scientific_accepted`, and `dispatch_authorized` stay false. A SHA match does not establish a genuine source: the separate read-only transport must independently prove the immutable commit/tree/path-to-blob binding and operator provenance. Synthetic tests demonstrate rejection behavior, not live external authentication. Neither the untrusted candidate nor Mind-Palace may supply the trusted pin.

## Qualification
Run existing exact-head hosted Linux and Windows `.github/workflows/qualify.yml` with repository full tests, race, vet, build and F139 controller checks; include focused `go test -count=1 ./researchfeed` and `go test -race -count=1 ./researchfeed`. All prior immutable foundations must match expected identity; do not skip final integration regression.

## Next factual source gate
Obtain an **actual** independently authenticated original source readback for one frozen research lane, including immutable commit/tree/path binding, external signer/source custody and consumed first-use history. Preserve positive, negative and invalid historical findings. If the trusted source or witness is unavailable, record `SOURCE_ORIGINAL_AUTHENTICATION_UNVERIFIED` rather than declaring science accepted. Keep F139 and FORGE operational authority exclusively with their existing owners. No controller, queue, scheduler, worker, paid API, broker, CKB-plane integration or protected acceptance path is added.
