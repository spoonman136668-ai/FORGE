#!/usr/bin/env python3
"""R26 source-pinned read-only GitHub ruleset continuity witness.

The GitHub connected identity observed the full ruleset with zero bypass
actors on 2026-10-15. The Actions token has redacted those actors. This
verifier pins the independent observation to source and checks ALL readable
policy fields and the server-maintained updated_at for subsequent drift.

It never treats hidden bypass actors as freshly authenticated, nor grants
merge authority or scientific authority.
"""
import json
from datetime import datetime, timezone

REPO = "spoonman136668-ai/FORGE"
RULESET = 25031517
NODE = "RRS_lACqUmVwb3NpdG9yec5UPTgWzgF9810"
UPDATED_AT = "2026-10-13T17:08:13.052-04:00"
SOURCE = "CONNECTED_GITHUB_APP_READ_2026-10-15"
REVIEW_PARAMETERS = {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews_on_push": True,
    "required_reviewers": [],
    "require_code_owner_review": False,
    "require_last_push_approval": False,
    "required_review_thread_resolution": True,
    "require_extra_approval_for_unattributed_changes": True,
    "allowed_merge_methods": ["merge"],
}
STATUS_PARAMETERS = {
    "strict_required_status_checks_policy": True,
    "do_not_enforce_on_create": False,
    "required_status_checks": [
        {"context": "linux", "integration_id": 15368},
        {"context": "windows", "integration_id": 15368},
    ],
}


class PolicyDenied(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise PolicyDenied(reason)


# These FORGE-scoped immutable owner/audit ref rulesets are disjoint from
# refs/heads/main. Unexpected ids, names, scopes or activation fail closed.
# Their separate owner permissions are NOT vouched for by this FSA witness.
AUXILIARY_RULESET_SCOPES = {
    26049392: ("FORGE F139 immutable owner release refs",
               "refs/heads/f139-owner-release-*"),
    26293659: ("FORGE H53 original-owner immutable audit ref",
               "refs/heads/audit/f139-v26-h53-original-successor-ro-once-20261031"),
    26304983: ("audit/f139-v26-h53b-original-successor-ro-once-20261101",
               "refs/heads/audit/f139-v26-h53b-original-successor-ro-once-20261101"),
    26305401: ("audit/f139-v26-h53c-original-successor-ro-once-20261101",
               "refs/heads/audit/f139-v26-h53c-original-successor-ro-once-20261101"),
    26313891: ("audit/f139-v26-h53d-original-successor-ro-once-20261101",
               "refs/heads/audit/f139-v26-h53d-original-successor-ro-once-20261101"),
    26253679: ("audit/f139-v26-i1290-original-ro-terminal-20261031",
               "refs/heads/audit/f139-v26-i1290-original-ro-terminal-20261031"),
}


def verify_ruleset_inventory(api, listing):
    """Bound and verify the actual main ruleset plus reviewed disjoint refs.

    This is not permission to merge. A new scope, changed owner/audit ref
    identity, unknown ruleset, or branch pattern affecting main is denied.
    """
    need(isinstance(listing, list) and 1 <= len(listing) <= 20,
         "RULESET_INVENTORY_OR_ACTIVATION_DRIFT")
    identities = set()
    for item in listing:
        need(isinstance(item, dict) and type(item.get("id")) is int
             and item["id"] not in identities
             and item.get("enforcement") == "active",
             "RULESET_INVENTORY_OR_ACTIVATION_DRIFT")
        identity = item["id"]
        identities.add(identity)
        if identity == RULESET:
            continue
        need(identity in AUXILIARY_RULESET_SCOPES,
             "RULESET_INVENTORY_OR_ACTIVATION_DRIFT")
        expected_name, expected_ref = AUXILIARY_RULESET_SCOPES[identity]
        detail = api.get(f"/rulesets/{identity}")
        need(isinstance(detail, dict) and detail.get("id") == identity
             and detail.get("name") == expected_name
             and detail.get("source") == REPO
             and detail.get("enforcement") == "active"
             and detail.get("target") == "branch"
             and detail.get("conditions") == {
                 "ref_name": {"exclude": [], "include": [expected_ref]}},
             "AUXILIARY_RULESET_SCOPE_OR_IDENTITY_DRIFT")
        # Bypass actors for a different ref never authenticate main's policy.
        # They are deliberately not used as an acceptance or owner-control
        # signal; only exact disjoint branch scope is relevant here.
    need(RULESET in identities, "RULESET_INVENTORY_OR_ACTIVATION_DRIFT")


def observe(api):
    """Return read-only evidence. Hidden actor metadata is NEVER presumed empty."""
    result = {
        "Schema": "forge.source-policy-anchor.r26.readonly.v1",
        "Source": SOURCE,
        "RulesetID": RULESET,
        "PinnedUpdatedAt": UPDATED_AT,
        "PinnedSourcePolicyUnchanged": False,
        "BypassActorsFreshlyVisible": False,
        "CallerBypassFreshlyVisible": False,
        "FullRulesetAuthenticated": False,
        "MergeAuthorized": False,
        "ScientificAuthority": False,
        "Reason": "NOT_CHECKED",
    }
    try:
        listing = api.get("/rulesets?includes_parents=true")
        verify_ruleset_inventory(api, listing)
        r = api.get(f"/rulesets/{RULESET}")
        result["ObservedUpdatedAt"] = r.get("updated_at")
        need(isinstance(r, dict) and r.get("id") == RULESET
             and r.get("node_id") == NODE and r.get("source") == REPO
             and r.get("name") == "FORGE main qualified-source only"
             and r.get("target") == "branch"
             and r.get("enforcement") == "active"
             and r.get("conditions") == {"ref_name": {
                 "exclude": [], "include": ["refs/heads/main"]}},
             "RULESET_IDENTITY_OR_SCOPE_DRIFT")
        # GitHub updates this server-maintained timestamp when the ruleset
        # changes. That is a continuity check, not a signed third-party
        # attestation or a proof of hidden fields.
        # GitHub returns the same timestamp in different equivalent time
        # zones to different authenticated callers. Compare the *instant*
        # with full fractional-second precision; never truncate or allow a
        # tolerance for an actual ruleset mutation.
        def instant(raw):
            need(isinstance(raw, str) and raw, "RULESET_TIMESTAMP_UNAVAILABLE")
            try:
                value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                need(value.tzinfo is not None, "RULESET_TIMESTAMP_TIMEZONE_MISSING")
                return value.astimezone(timezone.utc)
            except ValueError as error:
                raise PolicyDenied("RULESET_TIMESTAMP_MALFORMED") from error
        need(instant(r.get("updated_at")) == instant(UPDATED_AT),
             "RULESET_UPDATED_AFTER_AUTHENTICATED_OBSERVATION")
        rules = r.get("rules")
        need(isinstance(rules, list) and len(rules) == 4
             and all(isinstance(x, dict) for x in rules),
             "RULESET_RULES_MALFORMED")
        mapping = {item.get("type"): item for item in rules}
        need(len(mapping) == 4 and set(mapping) == {
            "deletion", "non_fast_forward", "pull_request",
            "required_status_checks"}, "RULESET_RULE_TYPES_DRIFT")
        need(mapping["deletion"] == {"type": "deletion"}
             and mapping["non_fast_forward"] == {"type": "non_fast_forward"}
             and mapping["pull_request"] == {
                 "type": "pull_request", "parameters": REVIEW_PARAMETERS}
             and mapping["required_status_checks"] == {
                 "type": "required_status_checks",
                 "parameters": STATUS_PARAMETERS},
             "RULESET_RULE_PARAMETERS_DRIFT")
        result["PinnedSourcePolicyUnchanged"] = True
        # The fields may be filtered according to the caller credential.
        # Visibility and value are separate, explicit facts.
        if "bypass_actors" in r:
            need(isinstance(r["bypass_actors"], list) and
                 r["bypass_actors"] == [],
                 "RULESET_BYPASS_ACTORS_CHANGED")
            result["BypassActorsFreshlyVisible"] = True
        if "current_user_can_bypass" in r:
            need(r["current_user_can_bypass"] == "never",
                 "RULESET_CALLER_BYPASS_CHANGED")
            result["CallerBypassFreshlyVisible"] = True
        if (result["BypassActorsFreshlyVisible"]
                and result["CallerBypassFreshlyVisible"]):
            result["FullRulesetAuthenticated"] = True
            result["Reason"] = "FRESH_POLICY_VISIBLE_READ_ONLY_NO_MERGE_AUTHORITY"
        else:
            result["Reason"] = "PINNED_POLICY_STABLE_REDACTED_ACTORS_NO_AUTHORITY"
    except (PolicyDenied, KeyError, TypeError, ValueError) as e:
        result["Reason"] = str(e) if isinstance(e, PolicyDenied) else \
            "GITHUB_POLICY_EVIDENCE_MALFORMED"
    return result


if __name__ == "__main__":
    from fsa_source_audit import GitHub
    print(json.dumps(observe(GitHub()), sort_keys=True, separators=(",", ":")))
