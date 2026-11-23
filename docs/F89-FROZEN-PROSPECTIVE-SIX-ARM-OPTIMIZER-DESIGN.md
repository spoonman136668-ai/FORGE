# F89 — frozen unbiased six-arm research-selection experiment design

**Workstream:** Optimizers only. FORGE Gate Advancement independently owns autonomy, controller/runner operation, one-shot scientific first-use, recovery and deployment.

**Parent:** F88 `f0f431c3d30519dd638746e7ec274d64f859c712` integrated source, plus four existing FORGE-native policy-control identities. The earlier source-only F61P/F62P drafts provide the six-arm uniform-randomization rationale, but this gate isolates that logic under the merged `optimizerstages` namespace rather than importing outdated controller/Cloudflare branches.

### Controlled comparison design

For each research lane, freeze four distinct selection controls plus Dream-RSI and Shinka/Pareto policy hashes; also freeze exact prospective source identity, preregistration, public candidate slate, source family and budget before outcome access. Exactly one six-way policy-arm choice is drawn from caller-provided 64-bit bytes; reject draws 2^64-4 through 2^64-1, so each arm has **exact probability 1/6**, without rounding to basis points. Preserve the raw draw, exact chosen arm and a content-addressed source-only record.

**This is the probability of a research-selection POLICY ARM, not the probability of an ACTION given a selected policy.** Do not substitute it into existing Dream-RSI action-propensity estimators. Randomness/clock independence and real owner first-use are not established by drawing bytes in a Go unit test. Future genuine research-owner services must independently witness pre-outcome assignment, commit first-use, and record every outcome before any causal training or promotion.

Adversarial guards fail closed on reused policy hashes, changed freeze/source, biased tail draws, forged owner/witness flags, rounded propensities, altered assignment choices, duplicate slate/source across Wingless/Yggdrasil, and shared random draws. Both lanes can prepare source-only designs separately; no new scientific original is launched.

F89 does **not** perform causal estimation, prospective scientific experiments, optimizer policy promotion, ThetaEvolve accepted training or source/archive deployment. Promptbreeder and DGM/GenEnv remain independent untested novelty-proposal avenues from F88.

### Qualification and stopping rule

GitHub-hosted focused tests and full Go regression; protected branch policy Linux and Windows checks must pass on exact PR head. The operator's no-CKB policy is enforced by existing isolationguard. All FORGE autonomy changes remain in the separate advancement thread.

**No live activation until** independent preregistration, real owner-side witnessed pre-outcome assignment, once-only original first-use, complete outcomes, frozen causal review and independently accepted scientific gains are present. The presence of F89 source code or a successful CI job cannot supply those missing facts.
