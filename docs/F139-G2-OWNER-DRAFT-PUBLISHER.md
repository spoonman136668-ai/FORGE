# F139 G2 — Original-owner bounded source publisher (inactive)

## Purpose and authenticated starting point

G1's genuine first source-generated draft Yggdrasil [PR #488](https://github.com/spoonman136668-ai/Yggdrasil/pull/488) was consumed by the pre-existing source-pinned F139 feeder as [issue #840](https://github.com/spoonman136668-ai/FORGE/issues/840). Both original provider OS jobs in [run #40052020867](https://github.com/spoonman136668-ai/FORGE/actions/runs/40052020867) failed the frozen native development code test. The original Windows task independently verified the immutable result in [audit #40054119829](https://github.com/spoonman136668-ai/FORGE/actions/runs/40054119829): owner ledger event 176 `NATIVE_FAILED_PROVIDER_CUSTODY`, event 177 `ATTEMPT_QUARANTINED`, ten quarantined tasks, eighteen verified tasks, no replay, unchanged original SQLite during audit.

The valid engineering result is that the existing F139 controller autonomously admitted, dispatched and reconciled genuine generated native source. The native mechanism itself is a retained development **negative**, NOT a scientific improvement.

## G2 source-only capability

`f139.nci04_candidate_publisher` implements a deliberate, one-shot authenticated **draft PR publisher**, reusing the existing G1 finite source recipe. It has no automatic invocation or GitHub credential acquisition. Its only network-dependent behavior comes from caller-injected, separately authorized `get` and `write` callbacks. No new scheduler, controller, issue queue, machine registration, model service or paid API.

A separate original-owner invocation must own the Windows task identity/lock, verify original immutable history and provide read/write GitHub credentials already qualified for this owner. G2 itself never claims those conditions have been satisfied.

Mandatory guards BEFORE any write:

- Original protected FORGE `main`, exact source policy #807, enabled F139 existing feeder.
- Real, independently authenticated Yggdrasil parent commit/tree and original source blob bytes.
- Prospectively supplied consumed-mechanism and candidate-history identities from the original owner, rejecting the prior #840 candidate.
- Pre-existing deterministic branch and PR identity absent; reject incomplete PR history.
- Generated source genuinely differs from original and is bounded to one allowlisted original native file.

Qualified actions, only if separately invoked by the existing authorized owner:

1. Create exactly one deterministic new branch at the verified parent commit.
2. Commit only generated source bytes to `yggdrasil/public_causal_cells.py`; check exact Git blob SHA.
3. Independently GET-verify one commit and one modified file, then POST one **draft** owner-authored `F139 autonomy DEV:` PR.
4. Re-read the PR as GitHub owner identity and run the **unchanged F139 feeder's** byte-level `_candidate_from_pr` authenticator before reporting publication successful.

Ambiguous POST/PATCH/PUT outcomes are never automatically replayed; a partial branch creation remains intact for bounded manual custody/reconciliation. G2 has **no** automatic PR merge, native execution dispatch, accepted-ref mutation, or first-use permission.

## Not yet operational

This is a development branch only; it does **not** install a writer in the live owner tick. It cannot generate new research proposals after the one finite source recipe is exhausted. The G1 mechanism has already been attempted as #840 and MUST NOT be emitted again. A future qualified activation must supply materially new, independently sourced structural hypotheses, frozen advisory decisions where genuinely available, exact original-owner credential custody, a bounded stop rule, full Linux/Windows regression, protected merge and another safe one-owner source transition.

Passing mock-host tests proves a safe one-shot code-writer interface and failure boundaries. It does not prove *autonomous ongoing* research, actual owner-authored G2 publication, scientific transfer, or 2 experiments per 10 minutes.
