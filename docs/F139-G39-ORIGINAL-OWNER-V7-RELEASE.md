# F139 G39 — one-time original owner V7 source cutover

## Why G39 is required

The qualified G30–G38 V2 worker/receipt code in PR #959 is not installed
in the original owner source. Original protected main is
b2079282fed03df2203807de09b4f3e82bdfe05a, the one-shot V6 transition.
The original G19 release and V6 transition cannot be reused as a second
release: doing so would deny source custody and could strand the owner.

G39 introduces exactly ONE new V7 transition, cryptographically chained
to the immutable original V6 source-transition event and existing negative
ticket seal. It accepts no prior source replay, fresh scheduler or controller,
or source with waiting or inflight old work.

## Actual original-owner release

After G39 has been independently qualified and merged into protected main,
an authenticated comment on original owner issue #807 by the owner GitHub
account can trigger the ONE existing original Windows runner:

    F139-V7-OWNER-CUTOVER <exact-current-protected-main-SHA>

The issue_comment workflow requires this exact syntax and account, original
issue number, original runner machine, administrator/SID, protected main
commit and exact old installed original task source. It refuses second
GitHub attempts and any missing original 300s task.

A preflight snapshots the exact live SQLite head, V6 seal and all historical
negatives. The original task is disabled and quiesced; a fresh read must
hash-match the previous snapshot. The same directory gets an SQLite API
backup. Only then does it fetch the specific protected main commit into
the original worktree, execute the new V7 migration through the EXISTING
SingleOwner lock, verify its new event, and explicitly activate native
development for that distinct source. Finally it re-enables the SAME task.

Failures before the V7 event attempt bounded old-source rollback. Failures
after the irreversible V7 event leave the original task stopped for an
owner-only recovery — NEVER switch SQLite or events backward automatically.

## V2 authority and scientific limitations

A V7 release by itself does not grant a scientific result or authorize
arbitrary work. The original run_once will consider new V2 development
only when the real original V7 transition AND an independent native
activation event both exist for the currently installed source. It must
still authenticate each fresh V2 candidate and G36 exclusive claim,
run the G13 frozen original, and verify G35/G38 provider custody before
recording VERIFIED/QUARANTINED.

No old G1/G3/#907 run is replayed. No live broker, new controller,
scheduler, queue, paid API or scientific FSA first-use is enabled.
The G29 experimental candidate PR is independent and not yet a genuine
new signed original-owner development issue. The final autonomy acceptance
still requires fresh original admission, unattended one-shot POST,
durable original terminal and unattended successor on the 300s cadence.

No cutover happens merely because a draft PR exists or its unit tests pass.
