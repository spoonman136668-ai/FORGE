# Hybrid research candidate contract — staged, inactive

This package prepares a *future* TTT-Hybrid-Lab research track in FORGE without
adding it to FORGE's existing two-lane scientific state machine, scheduler, or
authoritative execution path. It is a separately reviewed offline import format,
not a controller, worker, launcher, scientific registry activation, or evidence witness.

## Contract

`forge.hybrid.candidate-snapshot.v1` accepts at most 64 external candidate
identities from the exact `spoonman136668-ai/TTT-Hybrid-Lab` repository:

- experiment ID; PR number and matching canonical URL
- proposed head SHA and proposed frozen protocol SHA-256
- phase limited to `PROTOCOL_DESIGN` or `ENGINEERING_CANDIDATE`

Neither the source identity nor protocol bytes are authenticated by the
submitted metadata. All rows are explicitly `UNVERIFIED_NOT_SCIENTIFIC_EVIDENCE`,
and the output forbids any assertion of dispatch authorization, training
execution, scientific acceptance, or independently authenticated first-use.

## Offline use (not required to run for existing research)

```sh
go run ./cmd/forge-hybrid-advisory --snapshot /absolute/path/hybrid-candidates.json
```

The command reads exactly one ordinary, bounded local JSON file, rejects
symlinks and unknown input fields, and prints deterministic advisory JSON.
It does not fetch the private repository, open any credential, alter source
trees or durable journals, schedule tasks, dispatch a runner, write a file,
or change accepted scientific results.

## Prospective integration plan

1. Continue isolated S24 JEPA and S25 contradiction-gated TTT qualifications
   under TTT-Hybrid-Lab's own execution rights and first-use rules.
2. Add an authenticated, versioned source/protocol witness for hybrid candidate
   artifacts, with an independent immutable custody receipt. Keep source/data
   private to the authorized project; FORGE only needs permitted metadata.
3. Qualify a **prospective** third-lane scientific lifecycle migration. Do not
   reinterpret or rewrite any previously hashed two-lane records.
4. Test a disabled execution adapter against the existing hybrid runner and
   authorized FORGE owner, including no-replay fault injection, resource
   quotas, recovery, and absence of interference with Wingless/Yggdrasil.
5. Separately admit scientific first-use, then activate the hybrid lane only
   after exact-source final regression, independent evidence, and project
   authority checks. Activation is not part of this PR.

This staged development intentionally avoids introducing new scheduled tasks,
a new controller, an automatic cross-repository dependency, paid APIs, or
an immediate research cutover.
