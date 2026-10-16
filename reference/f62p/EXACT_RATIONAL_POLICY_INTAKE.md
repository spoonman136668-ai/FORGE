# F62P — exact rational policy-arm prospective intake (source-only)

Exact parent: F61P \`e80ac19569bc9294005696b7bb2c92793aea03c5\`. This branch fixes the F61P **evaluator compatibility seam** without changing either the frozen Dream-RSI implementation or the independent owner/custody authority.

- A randomized **policy-arm** has precisely \`P(arm)=1/6\`, recorded as numerator=1, denominator=6. Integer 1666/1667 basis points are wrong; never round them.
- A randomized **research action** chosen *by a policy* has a different logging propensity. The existing \`dreamrsi.Evaluate\` algorithm consumes research-action basis points and **must not** be invoked on six-arm policy-allocation evidence or have its meaning changed.
- \`PreviewF62PExactPolicyArms\` consumes bounded F61P prepared-source structs plus source-only proposed trial outcomes. It validates each content-addressed assignment, monotone local sequence, no repeat assignment/source receipt, lane and public-source-family/compute-budget consistency; refuses a pilot larger than 12 assignments per lane; and computes arithmetic as reduced exact rationals (\`math/big.Rat\`) only when *all* proposed outcomes are known. This is purely a testable statistical adapter, not an externally audited trial.
- A missing outcome is never counted as a negative or zero reward. Missing outcomes suppress all calculated IPS statistics; no cross-lane pooling, no source-family/budget drift, no fake first-use flags, no repeated trial identities. Tests include negative and indeterminate original outcomes.
- The score scale in this preview mirrors the *legacy illustrative* \`SUPPORTED=3, MIXED=1, else=0\`. It is **not** an accepted scientific utility or quality-per-compute claim; only independent preregistration and owner results could set true outcome/utility definitions.
- Every output unconditionally reports \`independent_owner_witness_authenticated=false\`, \`genuine_firstuse_established=false\`, \`causal_comparison_authorized=false\`, and \`optimizer_activation_authorized=false\`. Pseudo-SHA / synthetic local testing cannot change those values.

## Operational owner first-use gate still open

Authentic prospective scientific activation requires the existing owner to produce and independently verify: genuine Dream/Pareto policy nominees and signed disjoint training/validation data, a future public slate/family/equal-budget commitment, a non-cherry-picked externally witnessed pre-outcome six-arm assignment, monotonically registered/atomic one-use first-use source, an authorized original, actual independently accepted outcomes including negatives/missingness, and independent causal comparisons against the four frozen controls per lane. Historical GitHub observation, local hashes and green CI never replace those records.

The F58 pilot cap remains **12 future independently witnessed selections per lane**; confirmatory qualification requires at least **72 per lane**, ESS >= 8 per policy, appropriate randomization and multiple-comparison audits. The F62P source preview deliberately does not run a genuine pilot or claim readiness for confirmatory science.

Keep this PR **DRAFT** until authentic existing-owner first-use and independently assessed prospective evidence. No new controller, scheduler, signer, Cloudflare/D1 or CKB mutation, paid model API, automated Codex PR review, KTRADE operation, or Wingless/Yggdrasil interruption.
