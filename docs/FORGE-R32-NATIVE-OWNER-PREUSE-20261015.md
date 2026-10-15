# R32 — Native owner preuse adapter, from actual R31 scientific release points

**Classification:** qualified local source/first-use transport only. **NOT independent custody, science authorization, or a new original.**

R31 identified the actual local scientific release functions:

- Wingless: `scripts/Invoke-RepoLocalResearchCycle.ps1` invokes `Invoke-ResearchQualification.ps1`. The R31 preexecution observation is staged separately in [Wingless PR #241](https://github.com/spoonman136668-ai/Wingless/pull/241), not merged.
- Yggdrasil: `scripts/Invoke-RepoLocalResearchCycle.ps1` invokes the first `Invoke-ScientificRun`. R31 observes the real timing boundary in [Yggdrasil PR #235](https://github.com/spoonman136668-ai/Yggdrasil/pull/235), not merged.

R30 [FORGE PR #273](https://github.com/spoonman136668-ai/FORGE/pull/273) developed the source-level native function `originalclaim.ConsumeWithPredecision` and qualified it without starting a real scientific original.

## R32 code delta

R32 adds an actual **bounded native command-line entry point** at `cmd/forge-owner-preuse`. An already-authorized existing owner can call this executable with **three separate, externally supplied canonical signed-input files**:

`--claim`: exact `originalclaim.Claim` for one already frozen Wingless/Yggdrasil experiment, with owner epoch, source commit, worker, run and one-time original identity.

`--signed-predecision`: double-signed `originalclaim.SignedPredecision` for this exact experiment, policy, frozen four baseline SHA-256s, candidate set, selection probability, randomization-proof digest and nonzero decision sequence.

`--independent-pins`: independently sourced `originalclaim.PinnedTrust` containing the two immutable public keys and the exact policy/decision/source hashes. The proposed worker must **never** select these keys, supply this file as a trust root, or generate both keys.

`--journal-dir`, `--expected-lane`, `--expected-experiment`, `--expected-source-commit`: owner supplied exact immutable binding and a pre-existing durable local directory.

On valid owner- and witness-signed correspondence, the CLI calls R30's fsynced write-once predecision/claim sequence, reopens and verifies both, and emits an **explicitly non-authorizing result**. File absence, source or epoch drift, path aliases, untrusted signatures, symlinks, unknown fields, interruption and replay fail closed with no normal stdout. This executable does not generate private keys, create a journal, call the research worker, contact an API or select a policy.

**Warning:** the CLI's successful exit merely reports an authenticated **local record**. It does not check a separately operated current physical signer or distributed consumed-first-use CAS. A caller must never treat this result as science release approval or bypass the current independent source-birth/once-only gate.

## What is missing from existing active controller (not to be invented)

GitHub source inspection of current Wingless/Yggdrasil repository-local release scripts and their Actions workflows confirms **no provisioned owner + witness dual-signature source and no authenticated independent monotonic first-use token** is passed into the existing R31 release points. Existing Cloudflare D1 archives past research original ZIP bytes but has no independently proven CAS-based research-policy source-birth permit. R32 therefore does **not** insert a new call into the live controllers that would accidentally permit research on the strength of local trust files.

Before an authentic prospective R28P trial may execute, the current independent scientific owner must **really produce** frozen pre-outcome action probabilities and signed owner/witness decision evidence, obtain independently checked first-use monotonic CAS/high-water, and verify exact next original identity. Only then should R32's local recorder be installed in the existing active branch with a *separate externally verified release permit* in front of the worker. That operational gate cannot be declared closed by self-issued signatures or another synthetic CI run.

One final exact-head Linux and Windows regression, with Linux race/vet/build and native Windows vet/build, qualifies the source interface. No new controller/scheduler/FSA or paid API, Codex routine review, Cloudflare writes, original dispatch, or modifications to independent active research are part of this gate.
