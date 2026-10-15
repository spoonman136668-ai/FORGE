# FORGE R26 — pinned main-branch policy continuity (no new authority)

## What was actually authenticated
On 2026-10-15 the connected GitHub integration read native ruleset [#25031517](https://github.com/spoonman136668-ai/FORGE/rules/25031517) for `spoonman136668-ai/FORGE`, including **an explicitly empty `bypass_actors=[]` list** and `current_user_can_bypass=never`. The real resource has node identity `RRS_lACqUmVwb3NpdG9yec5UPTgWzgF9810` and GitHub-managed `updated_at=2026-10-13T17:08:13.052-04:00`. It targets `main`, enforces merge commits, stale-review dismissal, resolved threads, additional approval for unattributed changes, and exact required GitHub Actions Linux + Windows contexts (integration 15368). See the source-pinned constants in `scripts/fsa_policy_anchor_r26.py`.

## Smallest useful resolution
The already-protected default branch provides a GitHub-authenticated **source custody location** for this policy observation. R26 pins its identity, GitHub-managed last-update time, full readable rule parameters, and required checks. On each future read, any observed policy mutation must change the pinned GitHub server timestamp or policy parameters, and is classified as drift.

The GitHub Actions ephemeral token previously omitted the `bypass_actors` field. **A matching timestamp is continuity evidence; it is not fresh authentication of a hidden actor list and is not an independently signed attestation.** R26 reports `PinnedSourcePolicyUnchanged` separately from `BypassActorsFreshlyVisible` and `FullRulesetAuthenticated`. Hidden fields are never filled in, inferred empty, or elevated to complete authority. `MergeAuthorized=false` and `ScientificAuthority=false` regardless of outcome.

## Operational rollout
R26 uses the **existing** `forge-source-audit-r21-qualification.yml` test pathway, and adds the pinned continuity observation to the **existing** `scripts/fsa_source_audit.py` read-only output, without adding a controller, cron, workflow or credential. The R21 fail-closed bypass check is retained. Wrong policy identity, rule changes, or `updated_at` drift reject the source audit even if the Actions token redacts sensitive policy fields.

Focused tests include a full synthetic view, genuinely redacted actor fields, ruleset drift, changed checks, changed reviews, bypass introduction, and malformed data. The real hosted CI must independently read GitHub and report `R26_PINNED_POLICY_CONTINUITY=PASS_READONLY`, followed by Linux + Windows regression.

## What R26 does not do
No automatic merge, branch-rule write, new FSA controller, paid Codex review, new scientific first use, Wingless/Yggdrasil experiment, KTRADE operation, or Cloudflare work. The only path to atomic source promotion remains a separate exact-head GitHub merge call under independently accepted authority, with the real GitHub rules enforced server-side. R26 improves drift detection; it **does not by itself close the complete-authenticated-bypass-actor gate**.

This policy pin will need a refreshed authenticated observation and qualified source change if ruleset #25031517 legitimately changes. There is no hidden fallback.
