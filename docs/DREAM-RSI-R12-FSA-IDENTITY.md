# FORGE Dream-RSI R12 — FSA-side protected GitHub identity registration

**Status:** source-qualified FSA-side verification logic, not a deployed FSA. No scientific dispatch, keys, cloud infrastructure or new scheduler.

R11 genuinely verified a GitHub-issued OIDC token, but did so **on the untrusted GitHub-hosted worker itself**. R12 makes the security boundary explicit: only an FSA-owned process, whose registration is protected and immutable before seeing a runner's JWT, can validate a token for eligibility consideration. The worker may provide an OIDC JWT, but **may never provide its own trusted registration, pinned hash, or JWKS**.

## Source-only implementation

- `fsaidentity.Registration` is the *FSA-controlled* exact expected GitHub workflow run ID, source commit, original workflow path, authorized repo+numeric identity, branch, event, first-attempt, Wingless/Yggdrasil lane, cohort digest, frozen prewake and run-claim digest, archive epoch and audience. Its canonical complete SHA is required out of independent FSA protected state. The registration is not a signing authority or grant.
- `fsaidentity.Verify` validates a GitHub-signed JWT against RSA SHA-256 with a single matching issuer key ID, exact JWT issuer, expected **production-issuer-only** audience `forge-fsa-issuer-authorization-v1` (explicitly different from R11's shadow audience), repository name/ID/owner, public visibility, hosted runner, workflow/ref/subject, event, exact source commit, the FSA-recorded GitHub run ID, first attempt, and expiration. It refuses mismatched, stale, manipulated or duplicate signing keys, algorithms and tokens.
- `fsaidentity.VerifyLive` fetches GitHub's current RSA signing keys over OS-validated HTTPS from the *hardcoded* GitHub JWKS URL, disallows redirects, bounds payload and timing, and invokes `Verify`. There is no caller-supplied production JWKS URL, no JWT logging/storage and no process-wide key cache. `FetchGitHubKeys` is separately testable using an injected authority-owned HTTP client, but production uses `NewGitHubClient`.
- A positive verification returns `FSA_SIDE_CRYPTOGRAPHIC_REVIEW_ONLY`, with `GitHubOIDCVerified=true`. Crucially `ProtectedFSARegistrationObserved`, `FSAIndependentlyDeployed`, `FSAFirstUseConsumed`, `FSADispatchLeaseConsumed`, `ScienceDispatchAuthorized`, `ScientificOriginalExecuted`, `AcceptedScientificResult` remain **false**. The verifier cannot query protected external state to prove who supplied the registration; that ownership must be established by actual FSA deployment and custody, not test-fixture values.
- This code has **no HTTP server, signer, worker, FSA CAS, new GitHub Actions scheduler, or original science**. It does not grant GitHub OIDC permission to science on its own. The production-only audience must not be minted for shadow CI and no live token with that audience is requested here.

## Qualification

Source parent is exact R11 `88478a45745f6a8164d7a4d89eb090b2e853f7a8`. Exactly four additive paths (`fsaidentity/verify.go`, `fsaidentity/verify_test.go`, this document and a dedicated hosted qualification workflow).

Native hosted Windows and Linux require focused RSA/JWKS/repository/subject/workflow/attempt/expiry/registration pin tampering tests, one full FORGE regression, vet/build, Linux race, and a separate GitHub-hosted no-trusted-registration fail-closed probe. The positive signature tests use *ephemeral generated RSA test keys*, never the real FSA or a scientific original. R11 alone remains the evidence that real GitHub-issued OIDC works on hosted compute; R12 only proves the FSA-side verifier contract with synthetic tokens.

## Remaining genuine operational blocker

Provision an **independently controlled FSA runtime** with operator-approved signing credentials, protected externally anchored registration, monotonic first-use and separate dispatch CAS, authentic JWKS retrieval and an authenticated channel to the worker; perform network partition/power/rollback/fault qualification. The remote FSA must itself see the raw short-lived GitHub JWT securely, confirm its run registration, retain only policy-safe audit metadata, atomically commit the lease and make the original separately eligible. No GitHub-hosted worker may issue an FSA grant to itself.

R12 does not solve independently protected infrastructure by running code in the public repository. The real FSA physical gate [#20](https://github.com/spoonman136668-ai/FORGE/issues/20) remains open; Dream-RSI scientific succession [#25](https://github.com/spoonman136668-ai/FORGE/issues/25) remains unactivated. F1/F2 remain consumed; neither Wingless/Yggdrasil nor KTRADE/CKB-plane is changed.
