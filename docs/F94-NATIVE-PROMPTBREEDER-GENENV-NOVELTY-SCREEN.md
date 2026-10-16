# F94 — FORGE-native Promptbreeder and DGM/GenEnv structural novelty intake

**Ownership:** This workstream improves FORGE optimizer proposal screening. Controller autonomy, scientific-first-use custody, deployment, research execution and Cloudflare remain in the separate FORGE Gate Advancement track. **No CKB-plane interaction is authorized.** Mind-Palace is pinned/read-only advisory context only.

## Existing generators reused, not duplicated

- `promptlineage.Generate` creates bounded Promptbreeder-style **word-level prompt variations**, from a source-and-budget-frozen lineage plan. Such a variant alone cannot demonstrate a new algorithmic or scientific mechanism.
- `genenv.Generate` creates bounded DGM/GenEnv-style environment-vector variations based on an exact frozen training-history digest. Negative, invalid and mixed historical training records remain differentiated; *distance from history is not scientific novelty*.

**F94 connects their actual outputs** in `optimizerstages.ScreenF94`, regenerating both complete candidate populations rather than accepting caller-supplied candidate digests as proof. The lane, source, epoch, frozen generator plans, training-history identity, test protocol and control hashes must agree. Both Wingless and Yggdrasil may independently prepare source-only novelty proposals without waiting for the other lane.

## Screening contracts

F94 preregisters one frozen structural parent with separately named *representation*, *consumer*, and *test-environment* artifact digests, an immutable test protocol, independently supplied frozen pin and distinct negative controls. Every generator candidate must be linked once to an **unverified future implementation claim** naming three resulting artifact SHA-256 digests. To be structurally interesting at the manifest level, at least **two of three** resulting artifact SHA values must differ from the parent; two proposals cannot share the same full structural fingerprint.

The entire bounded output population must be screened: the user cannot submit only a favorable-looking subset after examining candidates, duplicate candidates, relabel a Promptbreeder output as DGM/GenEnv, reuse an identical mechanism fingerprint or lower minimum historical distance without changing the source-pinned freeze. Each resulting **UNTESTED** structural claim is converted into FORGE's existing `StructuralMechanismProposal` and validated by the existing F88 `AssessActivation` advisory gate, with no prospective trials or accepted results supplied.

**Crucial limitation:** A SHA-256-like value in a manifest does not establish that the corresponding new code exists, compiles, changes actual behavior, uses an original test environment, or constitutes a new scientific mechanism. F94 never claims these facts. A genuinely implementation-backed next gate must independently fetch pinned code and sealed, protocol-controlled evaluation tasks before first scientific use; it cannot use fabricated files, tests or an assertive status string to skip the owner and witness process.

## Fail-closed boundaries

F94 rejects: changed/wrong independent pins, wrong lane/epoch/source, source/history drift, missing/replayed generator candidate, fewer than two changed structural dimensions, duplicate structural fingerprints, invalid/out-of-budget plans, unqualified training history or too-small environment novelty, self-selected candidate subsets, forged positive outcomes and any attempt to turn an advisory proposal into a controller permission.

**All outputs explicitly remain false** for independent implementation validation, genuine mechanism novelty, sealed holdout consumption, scientific acceptance, Dream/Pareto policy promotion, ThetaEvolve accepted-result learning, scientific original dispatch and accepted-ref mutation. Negative historical records never become positive optimizer training labels.

## Verification and next work

GitHub-hosted F94 CI checks exact-source qualification against the **genuine F93 source-only GitHub run** [#38966044988](https://github.com/spoonman136668-ai/FORGE/actions/runs/38966044988), then performs focused adversarial integration tests, all five optimizer packages, full Go tests/vet/build and normal Linux/Windows protected checks. It does not treat CI as independent prospective science custody.

**Next optimizer direction:** Under authentic FORGE-native source control, qualify specific implementation diffs and independent *novel conditions* behind the strongest nonexecuting proposal families. Prefer mechanism-level changes rather than cosmetic prompt tweaks; keep frozen controls, diversity, negative preservation, and the separately governed scientific first-use gate.
