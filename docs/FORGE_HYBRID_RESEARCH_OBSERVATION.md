# Hybrid research observation — additive Phase A (advisory only)

The optional `--hybrid` input to existing `forge-research-observer` accepts a
locally supplied, pinned GitHub `workflow_runs` JSON snapshot for the independent
`TTT-Hybrid-Lab` research project. Both existing `--wingless` and
`--yggdrasil` inputs remain mandatory. Without `--hybrid`, the historical
two-lane output is unchanged.

## Example (paths supplied by the authorized operator)

```sh
go run ./cmd/forge-research-observer -wingless /absolute/w.json -yggdrasil /absolute/y.json -hybrid /absolute/h.json
```

The hybrid lane is represented only as `hybrid` in the metadata report.
No direct network reads from FORGE to the private hybrid repository are
introduced. No source code, secrets, model weights, research data, or runner
credentials are copied or fetched by this adapter. Private evidence should not
be committed to FORGE's public repository. A trusted caller must obtain and
verify any permitted snapshot separately.

The parser requires exact repository and run URL identity, canonical source
SHA, known workflow status, positive attempt IDs, and bounded input size.
Successful GitHub CI is always classified as
`UNVERIFIED_NOT_A_SCIENTIFIC_RESULT`. Neither historical completeness nor
scientific acceptance, original execution, dispatch authority, or protected-ref
changes may be inferred.

## Integration status and next gates

- **Implemented here:** optional read-only hybrid registration in the current
  research metadata observer, source-identity checks, negative controls and
  backward-compatible dual-lane output.
- **Not implemented:** auto-discovery, scheduled polling, persistent scientific
  state, new scientific lane in the immutable two-lane lifecycle, queue/runner
  dispatch, experiment training, checkpoint ingestion, model selection, merge,
  or scientific progression.
- **Next authorized engineering work:** version a prospective FORGE research
  lane registry and intake/evidence contract, independently qualify a compatible
  hybrid training runner, then test dispatch and recovery through existing
  *project-scoped* authority only. Preserve original Wingless/Yggdrasil records;
  do not rewrite historical ledgers or first-use identities.
- **Scientific gate:** preserve frozen S24/S25 protocols and all negative
  evidence. New first-use or heldout training needs separate original custody
  and permissions; this adapter does not grant them.

No extra controller, cross-project execution dependency, paid API, or automatic
research scheduling is introduced.
