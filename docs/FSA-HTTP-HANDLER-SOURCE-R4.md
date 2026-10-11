# FORGE FSA handler seam — source-only qualification

This draft adds inactive HTTP handlers for the existing FORGE FSA authority and witness protocol. It does not start a server or create credentials.

The authority handler requires an injected checkpoint backend plus independent verification interfaces for archive-instance binding and signed scientific transition admission before attempting one compare-and-swap. The witness handler requires an injected read-only signed high-water source. Both handlers require directly verified TLS 1.3 client certificates and exact peer SPKI identity.

Focused tests cover authentication refusal, strict request routes, single transition, conflicting replay, ambiguous commit, untrusted transition, witness outage, and signature rejection. These tests are synthetic and do not establish physical host separation or long-lived trust retention.

Activation blockers remain: independently provisioned services, independent key custody and physical archive binding, durability across power failure and host replacement, monotonic witness retention, and full end-to-end unattended qualification. The existing CKB-plane research controller remains unchanged. Do not merge or activate this draft solely from source CI.

The draft PR targets main for public GitHub Actions qualification of the complete identical source tree; R4's bounded delta is the three paths relative to the exact qualified PR #14 head. Neither parent PR nor this dependent draft may be merged or activated based on synthetic source tests alone.
