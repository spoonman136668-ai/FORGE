# F111-O — frozen source-native double-dot two-role hypothesis, not graph semantics

Parent exact qualified F110-O draft PR #409 head `fc21398dd7765be9d001279bba4db614c73f37c7`; GitHub Actions #39020870703 passed Ubuntu and Windows. F110 source-only TRAIN results before design: 20,358 original questions, 37,306 parse annotations. F109 accepted 25,498 flat single dotted predicate labels. 11,807 original F109 rejects each had interior `..` (502 distinct source strings); one lacked dot. F110 leading-dot alternative admitted zero. F109/F110 production policies SHALL remain unchanged.

**This is the FIRST F111 commit before inspecting the original TRAIN strings via F111 or implementing this new hypothesis.**

## One preselected hypothesis and zero semantic inference

The original source `InferentialChain` is an opaque annotated STRING. The hypothesis is that precisely **one** internal double-dot `..` may delimit **two** Freebase predicate names, each independently matching F109's unchanged frozen dotted-predicate syntax `[A-Za-z_][A-Za-z0-9_]*(?:[.][A-Za-z_][A-Za-z0-9_]*)+`. This establishes **lexical compatibility only**, not actual graph path composition, direction, entity linking, model prediction or scientific validity.

For each original source value in the frozen original F110 `interior_repeated_dot` subgroup:
1. Source must be printable ASCII, 1–512 UTF-8 bytes, with exactly **one** occurrence of literal `..`, not beginning or ending in a dot. Split exactly once into left and right, preserving every byte, case and punctuation, no trimming.
2. Accept as **one two-predicate *lexical tuple*** IFF **both** sides each match the F109 full strict source predicate regex unchanged. Return `candidate_two_roles_lexically_admitted` with the original two source strings internal to ephemeral runtime only.
3. Otherwise return exclusive refusal: `multiple_double_dot_delimiters`, `left_predicate_invalid`, `right_predicate_invalid`, `both_predicates_invalid`, or `unsupported_other_source_label`. The original F109 25,498 accepted and its one no-dot failure are never changed by this candidate.
4. No graph direction is annotated by the source text. Record `direction_unknown` for every lexical pair. **Forbid** assignment of forward, reverse, inverse or an edge order from string punctuation alone. Inability to establish direction blocks actual source graph Resolve.
5. No answer, source annotation MID, original question, original role value or per-parse identity is used for acceptance or leaked to artifact. Source TRAIN labels are developer annotations; never treat them as question-predicted typed paths or a scientific model improvement.

## Complete source and score controls

Immutable upstream `kelvin-jiang/FreebaseQA` commit `d16aae5149aaa25e43ff2a7bd00a06f280ca19b9`, original TRAIN `FreebaseQA-train.json` Git blob `24dc4b13a9c4a0ad734732db094c124d086b7d67`, exact bytes 23,888,089, full 20,358 unique question IDs/37,306 parse objects. Only the TRAIN Git object may be read. DEV `2e16ac381efb7b9e362cbf9bd0cee90006244ea8` and EVAL `d7d06ae721aedca26a0838d0113cddc1aa6774a8` Git identities checked as **metadata only**, with both original JSON files absent from sparse checkout and not decoded, sampled or scored.

Count exact frozen 25,498 F109 single-role acceptances, exactly 11,807 original interior-double-dot labels and the one nondotted refusal. Exclusively classify all 11,807 by the categories above. Publish only counts and distinct original chain **cardinalities**, no source strings, per-question outputs, MIDs, answer annotations, candidate details or label hashes. Source JSON decoder transiently materializes TRAIN answer objects, but no nested answer field is accessed or interpreted. No original DEV/EVAL question content read or scored. No synthetic gold witness and no accepted benchmark claim.

## Original Freebase graph remains unqualified

Publisher README describes approx. 2.2GB Freebase extract ZIP / 16M entities / 182M triples, out-of-repo and beyond F100 MetaQA budget. Reuse F110's hard-denied `evaluate_manifest` source custody contract, including checks on original archive/extracted checksums, whole-corpus count, license, decompression and disk-backed streaming design and independently separated evaluator. Do not download, sample, or treat a fabricated manifest as verified. **Real graph query count remains 0**, role prediction count 0 and no QA accuracy. The original MetaQA graph and F104 policy remain intact.

## Acceptance and authority

GitHub-hosted exact-head Ubuntu+Windows pinned external original TRAIN sparse checkout, synthetic adversarial lexical and no-direction and source-denial tests, all 37,306 original annotations, source-authentic Git SHA checks, SHA256 evidence manifests, one complete Go test/vet/build on each OS, independently compared exact-head evidence. No scheduler, Codex, paid inference, CKB-plane coupling, Cloudflare write, accepted ref mutation, protected scientific dispatch, Dream-RSI/Pareto activation or ThetaEvolve accepted learning. Draft/unmerged. First-use and independent scientific generalization NOT QUALIFIED.

**Disposition**: `PUBLIC_FREEBASE_TRAIN_DOUBLE_DOT_TWO_ROLE_LEXICAL_DIAGNOSTIC`, not verified 2-hop graph syntax or qualified scientific progress. Next gate must separately obtain independent graph source and direction semantics and an independently custodied untouched eval protocol; do not use public QA source labels as predictions.
