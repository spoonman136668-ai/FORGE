"""Fail-Closed Automated Draft-PR Self-Improvement Proposer for FORGE F139 (Gate 19).

Converts a verified, strictly improving `SelfImprovementBundle` (from
`f139/nci04_self_improvement_loop.py`) into an auditable Draft Pull Request
payload for `spoonman136668-ai/FORGE`.

Hard boundaries:
- ONLY accepts bundles with `qualified_count >= 1`, `selected_meta_delta > 0`,
  `live_controller_mutated: False`, `requires_human_or_ci_merge: True`,
  `paid_model_calls == 0`, `auto_promote_checkpoint: False`, and valid
  `bundle_sha256`.
- Target file MUST be in `SELF_IMPROVABLE_MODULES` and MUST NOT match any
  protected kernel/controller/workflow prefix.
- Strictly enforces `draft: True` and `auto_merge: False` — FORGE may propose
  self-upgrades as Draft PRs, NEVER merge itself or mutate protected `main`.
"""
from __future__ import annotations

import json
import urllib.request

from f139.nci04_native_contract import canonical, digest
from f139.nci04_self_improvement import (
    PROTECTED_KERNEL_PREFIXES, SELF_IMPROVABLE_MODULES,
)
from f139.nci04_self_improvement_loop import BUNDLE_SCHEMA

PROPOSAL_PR_SCHEMA = "forge.f139.self-improvement-draft-pr.v1"
FORGE_REPO = "spoonman136668-ai/FORGE"


class SelfPRProposerDenied(ValueError):
    """Fail-closed denial for unqualified, tampered, or unsafe self-PR bundles."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise SelfPRProposerDenied("F139_SELF_PR_" + reason)


def build_draft_pr_payload(bundle: dict, *, base_branch: str = "main") -> dict:
    """Validate a sealed SelfImprovementBundle and build a Draft PR payload."""
    need(type(bundle) is dict and bundle.get("schema") == BUNDLE_SCHEMA, "BUNDLE_SCHEMA_INVALID")
    sig = bundle.get("bundle_sha256")
    unsigned = {k: v for k, v in bundle.items() if k != "bundle_sha256"}
    need(digest(canonical(unsigned)) == sig, "BUNDLE_DIGEST_MISMATCH")

    target = bundle.get("target_rel_path")
    need(type(target) is str and target in SELF_IMPROVABLE_MODULES, "TARGET_NOT_ALLOWLISTED")
    for prefix in PROTECTED_KERNEL_PREFIXES:
        need(not target.startswith(prefix), "PROTECTED_KERNEL_TARGET_DENIED")

    need(bundle.get("qualified_count", 0) >= 1
         and type(bundle.get("selected_candidate_id")) is str
         and type(bundle.get("selected_meta_delta")) in (int, float)
         and float(bundle["selected_meta_delta"]) > 0.0
         and type(bundle.get("selected_after_sha256")) is str
         and len(bundle["selected_after_sha256"]) == 64,
         "NO_STRICTLY_IMPROVING_CANDIDATE")

    need(bundle.get("live_controller_mutated") is False
         and bundle.get("requires_human_or_ci_merge") is True
         and bundle.get("paid_model_calls") == 0
         and bundle.get("auto_promote_checkpoint") is False
         and bundle.get("scientific_first_use") is False,
         "SAFETY_CONTRACT_VIOLATION")

    need(base_branch == "main", "ONLY_MAIN_BASE_ALLOWED")
    cid = bundle["selected_candidate_id"]
    delta = bundle["selected_meta_delta"]
    after_short = bundle["selected_after_sha256"][:12]
    head_branch = f"forge-self-improve/{cid}-{after_short}"

    title = f"FORGE self-improvement draft: {cid} on {target} (meta Δ +{delta})"
    body = (
        f"Automated **Draft PR** proposed by FORGE fail-closed self-improvement loop.\n\n"
        f"- **Cycle ID:** `{bundle['cycle_id']}`\n"
        f"- **Target Module:** `{target}` (allowlisted research module)\n"
        f"- **Selected Candidate:** `{cid}` (`after_sha256`: `{bundle['selected_after_sha256']}`)\n"
        f"- **Downstream Meta-Benchmark Gain:** `+{delta}`\n"
        f"- **Bundle Digest:** `{sig}`\n"
        f"- **Safety Contract:** `draft: true`, `auto_merge: false`, `live_controller_mutated: false`, "
        f"`paid_model_calls: 0`, `auto_promote_checkpoint: false`, `scientific_first_use: false`.\n\n"
        f"Requires full 12/12 CI pass and human/owner merge approval."
    )

    payload = {
        "schema": PROPOSAL_PR_SCHEMA,
        "repo": FORGE_REPO,
        "base": base_branch,
        "head": head_branch,
        "title": title,
        "body": body,
        "draft": True,
        "auto_merge": False,
        "target_rel_path": target,
        "selected_candidate_id": cid,
        "selected_after_sha256": bundle["selected_after_sha256"],
        "bundle_sha256": sig,
    }
    payload["proposal_pr_sha256"] = digest(canonical(payload))
    return payload


def submit_draft_pr_via_api(
    pr_payload: dict, *, token: str, opener=urllib.request.urlopen
) -> dict:
    """Submit a validated Draft PR payload to GitHub API (strictly `draft: true`)."""
    need(type(pr_payload) is dict and pr_payload.get("schema") == PROPOSAL_PR_SCHEMA,
         "PR_PAYLOAD_SCHEMA_INVALID")
    need(pr_payload.get("draft") is True and pr_payload.get("auto_merge") is False,
         "MUST_BE_DRAFT_AND_NO_AUTO_MERGE")
    need(type(token) is str and len(token) >= 20, "TOKEN_INVALID")

    api_body = {
        "title": pr_payload["title"],
        "head": pr_payload["head"],
        "base": pr_payload["base"],
        "body": pr_payload["body"],
        "draft": True,
    }
    req = urllib.request.Request(
        f"https://api.github.com/repos/{FORGE_REPO}/pulls",
        data=json.dumps(api_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Mozilla/5.0 (compatible; Google-Agent; +https://developers.google.com/crawling/docs/crawlers-fetchers/google-agent)",
        },
        method="POST",
    )
    with opener(req, timeout=20) as resp:
        created = json.loads(resp.read().decode("utf-8"))
    need(created.get("draft") is True, "PROVIDER_DID_NOT_CREATE_DRAFT")
    return {
        "number": created["number"],
        "html_url": created["html_url"],
        "draft": True,
        "auto_merge": False,
    }
