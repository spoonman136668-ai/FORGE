# G62 — Practical navigation closure on the qualified G61 atlas

Scope: FORGE runner-private offline source viewer only. No research execution, FSA admission, controller or trading runtime changes.

## Reproduced limitation

The merged G61 HTML rendered only the first 200 search results, with no pagination or load-more control. With 783 source files and thousands of declarations, operators could not browse beyond the first 200 without knowing a search term. Selecting an indexed file also failed to offer a local path to its indexed declarations.

## Bounded repair

- Reuse the qualified immutable G61 JSON and ICE unchanged; alter only the generated runner-private HTML script.
- Add explicit 200-at-a-time progressive disclosure and accurate filtered result counts.
- Add Browse this file's declarations, filtering by exact file path. This is same-file declaration navigation, not a compiler-qualified dependency edge.
- Preserve pinned source URLs, source confidence, textContent escaping, no network or storage, and no runtime or scientific authority.

## Qualification

The existing G29 source atlas workflow runs focused Go evidence-preservation tests and a hermetic Node JavaScript-interaction test against generated HTML on Linux and Windows. The JavaScript test executes the actual viewer code with a minimal DOM shim; it does not claim genuine Chromium acceptance.

Standing protected-branch Linux and Windows regression checks remain required. Exact G61 source identity is pinned at 07b585dde1e9ea88bf4d768b46412ee77673b140, with 747 reused, 16 modified and 20 new indexable files. No atlas rebuild, additional controller or research runner allocation.

No compiler or runtime call confidence is inferred from lexical file-to-symbol navigation. Any unrelated source/branch drift must be reconciled before integration.
