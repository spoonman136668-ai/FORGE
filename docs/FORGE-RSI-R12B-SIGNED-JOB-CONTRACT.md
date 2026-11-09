# FORGE RSI R12-B — credentialed source-bound one-job contract (inactive)

## Exact baseline and scope

Protected main `8ebabd68557516af080ad1f62520c834b0cf9c31`
and tree `7e4df6c0856b14e5a89fc19158505c862596a9cf`.
Pure signing and credentialed verification in one additive source file,
one additive negative-test file, and this contract. No existing owner,
worker, workflow, scheduler, ticket, Git ref, research lane, or
scientific-first-use code changes.

## New engineering invariant

R12-A's cold original-ledger binding is now carried into a domain-separated
HMAC development job *format* that fixes one original reservation,
source/target hashes, one GitHub run ID, one job ID, first attempt,
protected-main source/tree, repository, existing workflow name and OS.
A credentialed validation function checks the real R12-A cold owner
binding again, and compares all authenticated workflow fields and HMAC
in constant time. It explicitly returns all operational/scientific
authorization fields **false**. No key goes into a credential-free worker.

This is a verifiable, source-only preparatory contract, not an original-owner
issuance. The `_development_signature` method is a pure cryptographic
primitive for development testing, NOT a replacement for the original
owner signer. F139's live HMAC ticket signer rejects FORGE-self and
the existing worker never accepts this new envelope.

## Remaining execution boundary

A separately qualified original Windows owner must atomically record a
lifetime-one R12-B *issuance/spend* event in its existing SQLite ledger,
authenticate exactly one original workflow run and job, then issue the
signed claim. The credential-free existing worker must check an independently
authenticated, one-use authorization result and execute only fixed
source/staged qualification commands. Independently verify original
terminal receipts, cold restart, crash/replay rejection, complete Linux
and Windows regression, and no protected source/holdout effects.

Until the spend+credential-free worker+terminal path exists, all
R12-B job admissions remain denied. A fixture-generated HMAC or green CI
does not prove a genuine original-owner signature, job dispatch or RSI.

## Release criterion

Mandatory original complete Linux/Windows regression and build on
candidate exact SHA. Source-only merge is permitted once CI passes, but
never enables unattended original-owner execution or declares RSI.
