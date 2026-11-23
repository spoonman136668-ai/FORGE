# FORGE native model-free proposal/evaluation continuity — source-only

## Objective

Connect the existing bounded **Promptbreeder-style `promptlineage.Generate`** and **DGM/GenEnv `genenv.Generate`** generators to **`optimizerstages.ScreenF94`** and **`optimizerstages.AssessActivation`** as a single repeatable dual-lane GitHub-native workflow step. Reuse the existing scheduled `forge-integrated-synthetic-cycle.yml`; **no second scheduler, runner registration, FSA, cloud service or paid model provider**.

## What actually runs

On the existing six-hour Linux and Windows disposable hosted runs, `cmd/forge-model-free-loop --synthetic-only --source-ref $GITHUB_SHA`:

1. Creates two independent in-source **synthetic** frozen fixture lineages, one per program. These are NOT authenticated Wingless/Yggdrasil scientific histories; placeholder source identities and synthetic negative/invalid/mixed records deliberately prove the boundary.
2. Regenerates each complete two-prompt + two-environment proposal population rather than accepting an arbitrarily favorable subset.
3. Applies F94's frozen source and training-history constraints and bounded structural advisory screening; then applies the current `AssessActivation` authority-denial policy.
4. Refuses missing candidates, missing controls, relabeled negatives, drifted frozen plans, candidate collisions across lanes, or promotion/first-use authority flags.
5. Runs twice against the **same protected source commit**, requires byte-identical JSON, verifies the GitHub checkout identity, and attaches `forge-model-free-advisory.json` plus its SHA-256 manifest to the already-existing synthetic workflow artifacts.

No network call, model call, Codex, private source download, Cloudflare write, GitHub write, accepted reference mutation, source implementation generation, new experiment or scientific original occurs in this new CLI. Production original execution, sealed evaluation and research-policy promotion remain explicitly false.

## Meaning of passing qualification

Passing establishes only that the **model-free native source components are wired and can operate unattended** under a reproducible, finite, source-only synthetic contract. The inputs are not real accepted research histories and the output is not a new hypothesis, learned mechanism, scientific discovery or independently witnessed outcome. Repeating the same frozen cohort on later schedules creates reproducibility evidence, **not new scientific progress**.

The new source-only connectivity must never be used to claim the user's desired continuously self-generating GPT research loop has been achieved. That separate objective still requires an actually accessible no-paid-API, no-Codex model execution path and independent FORGE-native scientific first-use authorization.

## Constraints and gate

No CKB-plane runtime or repository dependency. Mind-Palace remains optional read-only advice. The existing Wingless and Yggdrasil Codex-free research launchers stay unchanged. An exact-head successful Linux/Windows regression, focused adversarial tests and at least one genuine scheduled/manual *post-merge* integrated artifact are required before reporting that even this source-only scheduled bridge is operational. Fail closed on any identity or permission drift.
