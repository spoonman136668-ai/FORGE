# Prospective three-lane FORGE scientific lifecycle — inactive

This is a pure, offline **preview** in a new package; it is **not** a
migration of the two-lane scientific journal or an activated third lane.

- Verify the original Wingless/Yggdrasil v1 journal and match the exact
  existing journal head before constructing any new preview.
- Bind the prospective Hybrid-only event chain to a domain-separated digest
  of the complete, unmodified v1 journal and head.
- Allow only OBSERVED, PROTOCOL_FROZEN, ENGINEERING_CHECKED and BLOCKED
  shadow states; never QUALIFIED, AUTHORIZED, EXECUTING or SCIENTIFIC_PASS.
- Reject stale/tampered v1 history, duplicate starts, changed frozen protocol,
  unknown/cross-lane events, altered hashes, and attempted post-block replay.
- Preserve old v1 journal bytes and hash semantics. A pure read-only
  preview cannot become durable first-use custody or execution authority.

The API does not touch files, network, tokens, queues, owners, controllers,
workers, scientific data, checkpoints or scheduled tasks. It is independent
of hybrid observation PR #1560 and candidate snapshot PR #1561.

## Next separate qualification

Authenticate Hybrid experiment protocol and result provenance without pulling
private model data into FORGE. Qualify the already existing hybrid runner
behind a *disabled* adapter, with no-replay fault injection and fair resource
limits. Run full exact-candidate Linux/Windows regression before any proposed
integration, then separately verify existing project-scoped first-use and
execution authority. No research activation is requested in this PR.
