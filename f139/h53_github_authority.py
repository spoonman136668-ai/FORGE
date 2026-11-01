"""Read-only GitHub authority preflight for the H53 original-owner audit.

Invoked only by a separately approved one-shot audit. No credentials, POST,
controller actions or GitHub mutation. Every page and ruleset is bounded.
"""
from __future__ import annotations
import json
import urllib.request
from f139 import h53_audit_guards as guard

API = "https://api.github.com/repos/spoonman136668-ai/FORGE"

def read_json(url, opener=urllib.request.urlopen):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "FORGE-F139-H53-readonly-original-owner-preflight"})
    with opener(req, timeout=12) as response:
        guard.demand(response.status == 200, "GITHUB_READ_STATUS")
        return json.load(response)

def verify_authority(sha, read=read_json):
    guard.demand(len(sha) == 40 and all(c in "0123456789abcdef" for c in sha),
                 "AUDIT_SHA")
    rules = read(API + "/rulesets?includes_parents=true&targets=branch&per_page=100")
    guard.demand(isinstance(rules, list) and len(rules) < 100, "RULESET_INVENTORY")
    details = []
    for rule in rules:
        if rule.get("enforcement") == "active":
            rid = rule.get("id")
            guard.demand(type(rid) is int, "RULESET_ID")
            details.append(read(API + "/rulesets/" + str(rid)))
    guard.ruleset_guard(details)
    comments = []
    for page in range(1, 11):
        batch = read(API + "/issues/807/comments?per_page=100&page=" + str(page))
        guard.demand(isinstance(batch, list) and len(batch) <= 100, "APPROVAL_PAGE")
        comments.extend(batch)
        if len(batch) < 100:
            break
    else:
        guard.demand(False, "APPROVAL_PAGINATION")
    guard.approval_guard(comments, sha)
    return {"immutable_ref": guard.REF, "approved_audit_sha": sha,
            "ruleset_count": len(details), "approval_count": 1}

if __name__ == "__main__":
    import os
    print(json.dumps(verify_authority(os.environ["GITHUB_SHA"]), sort_keys=True))
