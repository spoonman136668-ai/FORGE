# F139 RSI R7 — bounded read-only fresh-failure discovery (inactive)

**Base:** protected FORGE main \`e5522fc96efd17cba19ca8febad25f169920b292\`,
tree \`ea4149d1914782f51e6aacfef66b3da0dc8431f2\`.
**Authority:** no change to existing F139 owner, SQLite, native lanes, CI workflow,
task admission, research science, installed services, or independent projects.

## Gap closed

Merged R6 can authenticate and synthesize a source-only known SQLite
open-handle repair for a *caller-supplied* run/job/target. There was no bounded
fresh run discovery. R7 adds an inert, explicitly called read-only scanner
that uses the existing \`f139.local_controller.GitHub.get\` interface, never
a new token, controller, scheduler, queue, subprocess or GitHub write.

R7 checks at most two fixed pages (30 failures each), examines no more than
eight authenticated, first-attempt, owner-origin **main push** failures strictly
newer than both caller-supplied cutoffs, authenticates their one matching
failed Windows job, and reuses R6's exact Git blob + original job log checks
to synthesize a bounded source-only proposal. The target source path is
caller-selected from R6's tight allowlist; it is not guessed from logs.
Unrelated failure classes and consumed scopes are retained as negatives.
Duplicate runs, incomplete job pages, untrusted actor/fork/attempt,
ambiguous candidate jobs and coverage overruns **fail closed**.
No raw provider log is emitted by the scanner.

**Limitations:** the cutoffs and consumed-scope set are supplied by the
caller, not authenticated against original Windows owner SQLite in R7.
A two-page scan is never exhaustive. The source-only proposal does not
qualify repaired source, prove a new defect, grant owner eligibility, or
establish durable no-replay custody. The real F139 owner still permits
Wingless, Yggdrasil and Qualification, not FORGE-self. Historical R13 is
consumed and may only serve as a regression fixture, NEVER as fresh RSI.
No caller may infer admissibility or dispatch authority from a report.

## Acceptance

Original Linux+Windows F139, GenEnv, native owner, Go suite/race/vet/build
and isolation mandatory final regression at the **exact candidate SHA**.
The new offline tests exercise synthetic provider bytes only. After
engineering PASS the next non-replayed live action is an authorized original
owner custody+FORGE-self scope expansion, followed by a new authentic
failure, isolated candidate qualification and a frozen two-generation
strongest-baseline comparison per issue #1550.

ENGINEERING pending until exact-head qualification.
SCIENTIFIC RSI/learning/transfer unverified.
DEPLOYMENT inactive; zero owner, scientific first-use, paid API or runner effects.

## R9: authenticated main/push server-side failure selection

A read-only GitHub API measurement on November 8, 2026 found the generic
repository failed-run feed reporting **2,500** entries (the API's reported
count), while the same endpoint filtered with
`branch=main&event=push&status=failure` returned exactly **19** runs.
The prior R7 first two generic pages could contain only unrelated PR or
other-project failures and miss all 19 relevant main/push runs. This was a
discovery false-negative, not an owner or scientific failure.

R9 retains the original two-page/30-per-page/8-relevant-run bounds, original
R6 Git-blob/job/log checks, strict caller cutoffs, and all inactive flags.
It performs the main/push filtering on the provider itself and independently
rejects any returned run that is not a completed failed `main` push. This
check happens **before** evaluating the caller cutoff, preventing an
ignored-filter provider from hiding invalid older rows. No new writer,
controller, owner tick, automation, job retry, scheduler or scientific first
use is introduced. Remaining pre-R8 failed main pushes are **historical** and
must not be relabeled as newly discovered, unconsumed RSI improvements.

R9 is a discovery-correctness repair, not a demonstration of G1 or G2 benefit.
Source-only final qualification still requires full original Linux/Windows
regression and inactive owner-release continuity.
