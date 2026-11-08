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
