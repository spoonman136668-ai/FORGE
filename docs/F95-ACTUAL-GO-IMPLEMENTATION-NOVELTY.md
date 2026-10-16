# F95 — verifiable implementation artifacts for optimizer novelty proposals

**Scope:** FORGE research-optimizer mechanism engineering only. Autonomy, first-use research execution, owner/witness authority and Cloudflare deployment remain with FORGE Gate Advancement. **No CKB-plane integration.** Mind-Palace is the optional pinned, read-only advisory source.

## Correcting the F94 gap

F94's `promptlineage` and `genenv` generators produce **UNTESTED** candidate lineages. F94's structural-manifest screen rejects superficial claims, but an arbitrary 64-hex digest does **not** prove any code exists. F95 closes part of this gap by checking *actual Go source bytes and syntax-tree differences* in a checked-out, exact-commit Git worktree. It does not convert source novelty into an accepted scientific result.

## Actual new implementation and test conditions

The F95 candidate adds `noveltymechanisms/`:

- `f95_representation.go`: typed relation-edge memory, preserving the distinction between entity identities and named roles. Unlike the pre-existing `genenv` environment-vector representation, it can express explicit compositional paths.
- `f95_consumer.go`: bounded sequential role-composition retrieval with ambiguity retained rather than resolving to the first plausible endpoint. This is different code from the pre-existing Promptbreeder-style word-mutation consumer.
- `f95_environment_test.go`: actual executable four-hop relationship composition, role-swap and distractor controls, ambiguous multi-answer refusal, and adversarial malformed-input/budget checks. These are **source-level research-condition fixtures**, not independent original scientific experiments or sealed holdouts.

The novel candidate has no claim to being learned yet: it is a bounded algorithmic prototype designed to expose whether later substantive hypothesis tests can beat task controls. It is not installed into Wingless or Yggdrasil.

## Binding actual code rather than trusting a manifest

`optimizerstages/f95_real_source_novelty.go` validates every representation/consumer/test-condition claimed SHA-256 against actual Go source bytes, parses them with the Go syntax parser, and requires distinct AST-shape fingerprints (ignoring cosmetic identifier names, literal value substitutions, whitespace and comments). It also binds this F95 candidate to its required real Go entrypoints. AST-shape changes are a **necessary source-level condition**, not a proof of semantic or scientific novelty.

`AuditF95LinkedGeneratorSource` recomputes the **entire F94 Promptbreeder + DGM/GenEnv frozen candidate population**, rejects cherry-picked or relabeled lineage, then verifies the selected candidate's source bytes. This is tested against bounded synthetic lineage fixtures, **not** claimed as real owner-independent generation evidence.

`cmd/f95audit` adds authenticated **local Git object readback** to the hosted qualification: it checks the exact protected F94 base `dce583ff9e1be25effe2d7c1988a92c0ede6780e` is an ancestor, reads original `genenv` and `promptlineage` blobs at that SHA, and reads the new implementation files at the exact checked-out PR SHA. These are true Git object bytes, not caller-provided strings. The readback emits a SHA-256-verified JSON artifact. This CLI uses a synthetic/unwitnessed source-only generator candidate identifier and does not establish independent F94 preregistration or science custody. The artifact is not a long-term archive; GitHub Actions artifact retention is finite.

F95's anti-falsification tests include mismatched claimed SHA values, changed bytes, malformed Go, role swaps, unchanged implementation, missing executable test cases, cosmetic-only identifier/comment changes and incomplete F94 generator populations. **Source changes alone never establish predictive generalization or scientific acceptance.**

## Qualification and unambiguous disposition

The GitHub-hosted F95 workflow runs the real-code tests, F94 lineage/source checks, full Go tests/vet/build, and emits exact Git-source readback evidence; normal protected Linux/Windows qualification remains mandatory for merge.

**Always false/denied:** independently accepted new mechanisms, source-independent frozen prospective experiment outcomes, causal improvement, scientific original first-use, Dream-RSI/Pareto promotion, ThetaEvolve accepted-result training, controller cutover and accepted scientific ref mutation. No worker or Cloudflare writes occur.

**Next optimizer-only direction:** independently engineer and compare at least one further genuinely different mechanism under **new, frozen, independently witnessed research conditions** and accepted baselines, without leaking sealed evaluation or confusing code novelty with scientific achievement.
