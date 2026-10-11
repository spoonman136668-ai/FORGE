# FORGE Dream-RSI R11 — Actual GitHub-hosted workload identity, without FSA activation

**Status:** source-only, non-authorizing provenance audit. This qualification uses a real GitHub-issued, ephemeral OIDC JWT on a live hosted runner, not an invented/mock GitHub token. No FSA signing/first-use rights or scientific originals.

## Why R11 exists

R10 separated independently issued pre-run intent from GitHub's subsequently assigned run ID. The remaining identity boundary requires the FSA to authenticate a hosted run without trusting a worker's environment variables. GitHub publishes an OIDC issuer at https://token.actions.githubusercontent.com/.well-known/openid-configuration and RS256 JWKS endpoint. This change provides a narrow **client-side cryptographic implementation** and a genuine token exercise to validate the claim format/source binding. The same verification must ultimately be performed **in the independent FSA**, with FSA-supplied allowed claim values, instead of trusting an in-process runner's report.

## Security design and actual token test

- New `oidcaudit` Go package verifies JWT header `RS256` (no insecure alg), matches a specific key ID in a bounded HTTPS-fetched GitHub JWKS, verifies RSA-SHA256 signature, checks token validity times and a dedicated audience `forge-r11-provenance-audit-non-authorizing`.
- Independently pinned FORGE repository ID **1413298198**, owner ID **253477821**, repository name and visibility; the exact proposal branch and R11 workflow file; triggering event `push`, repository source commit `sha`, GitHub `run_id`, first `run_attempt`, and `runner_environment=github-hosted`. The raw token and bearer request credential are never echoed, persisted, uploaded or cached in artifacts.
- `cmd/forge-oidc-audit` uses GitHub's documented `ACTIONS_ID_TOKEN_REQUEST_URL` and `ACTIONS_ID_TOKEN_REQUEST_TOKEN`, requests exactly the isolated audit audience, downloads the issuer's JWKS by TLS from the *hardcoded* well-known address, and verifies the signed claims. Output is only a minimal non-authorizing JSON receipt.
- Dedicated qualification workflow gives `id-token: write` to **one audited job only**, `contents: read` globally and elsewhere. This permission is only the ability to request a temporary OIDC JWT; it does not grant scientific FSA, storage, GitHub repository write, accepted reference or cloud credentials.
- Two independent hosted source-qualification jobs (Linux + Windows), exact R10 SHA/five-file diff, focused adversarial RSA/key/issuer/audience/run/lane/cross-workflow/expiry tests, one full FORGE Go regression, vet/build, Linux race; then a **real** hosted OIDC credential acquisition/signature verification job and a separate hosted reconciliation job. Only a seven-day **non-secret receipt** is transferred. Never upload JWT, JWKS signing key, tokens or sealed science.
- If OIDC cannot be requested, GitHub's signature is unavailable/invalid, GitHub claims have shifted from the preregistered expectation, or the run/source identity mismatches, the hosted audit fails closed and cannot start or dispatch any science.

## Not authority

The output `forge.oidc.provenance-audit.v1` sets actual signature validation and exact GitHub source context booleans, but **independently witnessed by FSA, physical custody, dispatch authorized, accepted science, and original experiment executed are all FALSE**. GitHub OIDC alone does not sign frozen hypotheses, grant first-use, consume protected dispatch state, verify independent scientific evidence, or protect accepted refs.

The distinct, protected FSA must itself verify OIDC using a credential that cannot be replaced by a self-reported worker, bind it to an independently frozen R10 wake/run claim, reconcile its own durable one-shot dispatch/high-water, and authorize a specific already preregistered cohort. None of those independent operations are installed here. The R11 shadow audience must NEVER be accepted by a future FSA for scientific execution. F1/F2 remain consumed. Dedicated long-lived compute servers remain unnecessary for basic bounded hosted jobs (R8).

## Acceptance and limitation

Native Windows/Linux source and one full regression + Linux race, actual GitHub JWT RS256 signature, issuer/audience/repository/source/run identity, isolated id-token scope and non-sensitive independent receipt reconciliation must all pass before R11 is source qualified. R11 makes a materially new operational claim compared with R10: **real GitHub-hosted token provenance has been verified**, not that the independent FORGE Scientific Authority has been qualified or deployed.

The FSA external physical signing/monotonic floor/witness custody gate [#20](https://github.com/spoonman136668-ai/FORGE/issues/20) and scientific optimizer integration [#25](https://github.com/spoonman136668-ai/FORGE/issues/25) remain open. No GITHUB_TOKEN workflow dispatch, scientific original, production cutover, new scheduler, KTRADE or CKB-plane modifications occur in the R11 proposal. All stacked proposals remain draft and unmerged until separately accepted.
