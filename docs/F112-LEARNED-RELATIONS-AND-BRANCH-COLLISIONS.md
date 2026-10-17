# F112 — learned relational features and adversarial binding collisions

First F112 commit `1a790a03c03884ae909c530d27c07425bef51e3b` preregistered the mechanism families, new source-string encodings, public seed blocks, training budget, controls, Yggdrasil graph topology and authority denials before implementation. Parent F111 exact branch head `559f5979feea3b3e538de38c82b02db00d3ab37c`. Keep ancestor draft F99–F111 lineage intact.

## Motivation

F111 established that the existing F109 additive source-offset attention learned a *limited routing mapping* (39/144) that did not transfer to nonadditive public identifier tables; a simple full-information table lookup scored 144/144. The strict variable-binding structure remained tied with soft binding 144/144 on all F111 public conditions. Those negatives are preserved as mandatory authenticated F112 intake: current integrated-run F111 JSON and receipt must match the independent full re-evaluation of its upstream evidence and frozen results.

## Wingless

A trainable **six-weight relation-attention metric** works on public query and source code strings. Fixed engineered input features are normalized character-set overlap, aligned positions, common prefix, common suffix, length similarity and bigram Jaccard. It is a learned weighting of **engineered similarity features**, not a general-purpose learned character representation, and does not contain a hardcoded Boolean equality feature. It trains 100 differentiable BCE gradient updates on 96 fresh PUBLIC paired examples (seeds 68100–68131, three each). At prediction, it uses only string metadata to choose which **one** observation value to read.

Three independently frozen PUBLIC diagnostic identifier-encoding families—W112-A 68148–68195 (framed decimal), W112-B 68200–68247 (variable-length symbol codes), W112-C 68300–68347 (new alphanumeric prefixes)—change source strings, shuffle tags, and construct counterfactual signs in a test label separate from model input. No post-diagnostic training or cherry-picking.

Controls include a six-feature uniform metric with no learned weights, a separately trained 64-weight query-only attention, the original frozen 64-weight offset router, and a **perfect full-information source-ID exact lookup that also reads exactly one observation**. This exact table lookup is a strong control for whether the problem actually requires learning; performance at or below the lookup is *not superiority*. Full per-pair records are retained. The first three frozen thresholds require 75% paired accuracy each, 18 pooled net correct examples over the fixed metric, and 60% minimum group. Failed thresholds are valid negative outcomes, not engineering failures.

## Yggdrasil

A different 12-edge four-hop task generator freezes 48 test pairs each in Y112-A 68400–68447, Y112-B 68500–68547 and Y112-C 68600–68647. Each pair has **three** competing path candidates with identical four-hop typed roles leading to the same target; one valid variable path in positives and two invalid competing paths. Negative examples break exactly one main-path variable connection while keeping all roles/topology fixed. A separate exact oracle verifies the generated truth. The soft F103 model, F109 strict equality-gated variant using the same learned role weights, trained blind control and coded oracle all appear in the same paired outcomes. No model retraining on F112 diagnostics. Net hard-only advantage of 18/144 is required to claim **public** structural superiority.

## Explicit limits

F112 does not generate hypotheses with GPT, train a new general-purpose embedding model, demonstrate transfer to independent real-world scientific samples, qualify protected original experiments, or establish recursive self-improvement. All datasets and features are programmatically specified here, with fixed public research gates. The existing GitHub-hosted Ubuntu/Windows cycle produces SHA256 receipts and keeps negative results. No Codex, paid API, scheduler, Work task, Cloudflare/CKB-plane/Mind-Palace write, native scientific dispatch, accepted refs or optimizer promotion. Keep this PR draft/unmerged; successful PR test-merge CI is not literal direct branch-head qualification.
