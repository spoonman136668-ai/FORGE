"""Bounded single-shot G2 owner-source publisher, inert unless invoked.

G1 produces genuine finite native source bytes. G2 can publish a uniquely
identified, owner-authored, single-commit/single-source-file draft PR using
already-authorized GitHub credentials under the *same original F139 owner*.
There is no scheduler, background service, new queue or generic code executor.

This module NEVER self-activates, does not acquire credentials and is NOT
wired to live run_once. The production caller must separately attest the
original-owner SID, mutex, immutable SQLite history and current source.
Only externally injected read/write operations can modify GitHub.
"""
from __future__ import annotations

import base64
import hashlib
import re
from typing import Callable

from f139.nci04_autonomy_feed import (
    FORGE_REPO, POLICY_ISSUE, _candidate_from_pr, _decode_content,
    inspect_policy,
)
from f139.nci04_candidate_producer import (
    LANE, PATH, candidate_mechanism_identity, produce,
)
from f139.nci04_native_contract import REPOS, digest

SCHEMA = "forge.f139.g2.owner-draft-publisher.v1"
RECIPE_G1 = "g1-tier-local-pooling"
RECIPE_G3 = "g3-local-evidence-abstention"
SUPPORTED_RECIPES = frozenset({RECIPE_G1, RECIPE_G3})
BRANCH_PREFIX = "f139/auto-g2-ygg-"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class PublisherDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise PublisherDenied("F139_G2_" + reason)


def _sha1_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _verified_original(get: Callable[[str], object], *,
                       source_sha: str) -> None:
    need(callable(get) and isinstance(source_sha, str)
         and SHA40.fullmatch(source_sha) is not None,
         "ORIGINAL_SOURCE_ARGUMENT_INVALID")
    policy_raw = get(f"repos/{FORGE_REPO}/issues/{POLICY_ISSUE}")
    try:
        policy = inspect_policy(policy_raw, source_sha)
    except Exception as exc:
        raise PublisherDenied("F139_G2_OWNER_POLICY_INVALID") from exc
    need(policy["enabled"] is True, "FEEDER_DISABLED")
    branch = get(f"repos/{FORGE_REPO}/branches/main")
    need(isinstance(branch, dict) and branch.get("protected") is True
         and isinstance(branch.get("commit"), dict)
         and SHA40.fullmatch(str(branch["commit"].get("sha"))) is not None,
         "PROTECTED_CONTROLLER_SOURCE_DRIFT")
    protected=branch["commit"]["sha"]
    if protected != source_sha:
        from f139.nci04_source_continuity import (
            SourceContinuityDenied, prove_protected_research_only_advance)
        try:
            prove_protected_research_only_advance(
                get, deployed_source=source_sha,
                protected_source=protected)
        except SourceContinuityDenied as exc:
            raise PublisherDenied("F139_G2_PROTECTED_RUNTIME_SOURCE_DRIFT") from exc


def publisher_preflight(get: Callable[[str], object], *,
                        source_sha: str, parent_commit: str,
                        historical_sha256: str,
                        consumed_mechanisms: set[str],
                        existing_candidate_identities: set[str],
                        recipe: str = RECIPE_G1) -> dict:
    """Authenticate available source and reject repeats BEFORE any write.

    Returns a *non-authorizing* bounded plan, containing actual source bytes.
    History and candidate consumption sets MUST be obtained from original
    owner ledger; this function does not sign a scientific history claim.
    """
    _verified_original(get, source_sha=source_sha)
    need(isinstance(parent_commit, str)
         and SHA40.fullmatch(parent_commit) is not None
         and isinstance(historical_sha256, str)
         and SHA64.fullmatch(historical_sha256) is not None
         and isinstance(consumed_mechanisms, set)
         and isinstance(existing_candidate_identities, set)
         and all(isinstance(v, str) and SHA64.fullmatch(v)
                 for v in consumed_mechanisms | existing_candidate_identities),
         "HISTORICAL_SOURCE_OR_DEDUP_INVALID")
    need(recipe in SUPPORTED_RECIPES, "UNKNOWN_RECIPE_DENIED")
    if recipe == RECIPE_G1:
        need(candidate_mechanism_identity() not in consumed_mechanisms,
             "PREVIOUSLY_CONSUMED_MECHANISM_NO_REPLAY")
    else:
        # The original G1 negative must remain in the witnessed history.
        # A G3 proposal is never permitted to erase the failed G1 outcome.
        from f139.nci04_candidate_producer_g3 import mechanism_identity
        need(candidate_mechanism_identity() in consumed_mechanisms,
             "G1_NEGATIVE_HISTORY_NOT_RETAINED")
        need(mechanism_identity() not in consumed_mechanisms,
             "PREVIOUSLY_CONSUMED_MECHANISM_NO_REPLAY")
    repo = REPOS[LANE][0]
    parent = get(f"repos/{repo}/git/commits/{parent_commit}")
    need(isinstance(parent, dict) and parent.get("sha") == parent_commit
         and isinstance(parent.get("tree"), dict)
         and isinstance(parent["tree"].get("sha"), str)
         and SHA40.fullmatch(parent["tree"]["sha"]),
         "PARENT_COMMIT_TREE_INVALID")
    blob_doc = get(f"repos/{repo}/contents/{PATH}?ref={parent_commit}")
    try:
        before, before_blob = _decode_content(blob_doc)
    except Exception as exc:
        raise PublisherDenied("F139_G2_BEFORE_SOURCE_BYTES_UNVERIFIED") from exc
    if recipe == RECIPE_G3:
        from f139.nci04_candidate_producer_g3 import produce_g3
        generated = produce_g3(
            lane=LANE, path=PATH, parent_commit=parent_commit,
            original=before, original_sha256=digest(before),
            history_sha256=historical_sha256,
            consumed_mechanisms=consumed_mechanisms,
            consumed_candidates=existing_candidate_identities,
            scientific_first_use=False)
    else:
        generated = produce(
            lane=LANE, path=PATH, parent_commit=parent_commit,
            before_bytes=before, pinned_before_sha256=digest(before),
            history_sha256=historical_sha256,
            consumed_mechanism_sha256=consumed_mechanisms,
            scientific_first_use=False)
    need(generated["candidate_identity"] not in existing_candidate_identities,
         "PREVIOUS_CANDIDATE_IDENTITY_NO_REPLAY")
    suffix = generated["record"]["mechanism_sha256"][:12] + "-" + parent_commit[:12]
    branch_name = BRANCH_PREFIX + suffix
    refs = get(f"repos/{repo}/git/matching-refs/heads/{branch_name}")
    need(isinstance(refs, list) and len(refs) == 0,
         "SOURCE_BRANCH_EXISTS_OR_UNVERIFIED")
    prs = get(f"repos/{repo}/pulls?state=all&per_page=100&page=1")
    need(isinstance(prs, list) and len(prs) < 100,
         "PR_HISTORY_INCOMPLETE")
    for pr in prs:
        need(not (isinstance(pr, dict) and
                  isinstance(pr.get("head"), dict)
                  and pr["head"].get("ref") == branch_name),
             "PR_ALREADY_PUBLISHED")
    return {
        "schema": SCHEMA,
        "recipe": recipe,
        "lane": LANE, "repository": repo, "path": PATH,
        "branch": branch_name, "source_sha": source_sha,
        "parent_commit": parent_commit, "parent_tree": parent["tree"]["sha"],
        "before_blob": before_blob, "after_blob": _sha1_blob(generated["source"]),
        "candidate_identity": generated["candidate_identity"],
        "candidate_source": generated["source"],
        "source_sha256": generated["record"]["after_sha256"],
        "history_sha256": historical_sha256,
        "mechanism_sha256": generated["record"]["mechanism_sha256"],
        "pr_title": generated["pr_title"],
        "no_scientific_acceptance": True,
        "advisory_record_not_fabricated": True,
        "writes_authorized": False,
    }


def publish_single_draft(
    get: Callable[[str], object],
    write: Callable[[str, str, dict], object], plan: dict, *,
    owner_witness: Callable[[], bool],
    consumed_mechanisms: set[str],
    existing_candidate_identities: set[str],
) -> dict:
    """One deliberate source commit + owner draft PR; no retries on uncertainty.

    A separately qualified original-owner invocation must supply the owner
    witness; never call on a generic GitHub Actions runner. On partial network
    failure, keep the new source ref for bounded operator reconciliation and
    do NOT resend writes automatically.
    """
    need(callable(get) and callable(write) and callable(owner_witness)
         and owner_witness() is True and isinstance(plan, dict)
         and plan.get("schema") == SCHEMA
         and plan.get("recipe") in SUPPORTED_RECIPES
         and plan.get("lane") == LANE
         and plan.get("path") == PATH and plan.get("repository") == REPOS[LANE][0]
         and plan.get("writes_authorized") is False
         and plan.get("no_scientific_acceptance") is True
         and plan.get("advisory_record_not_fabricated") is True,
         "OWNER_WRITER_NOT_QUALIFIED")
    fresh = publisher_preflight(
        get, source_sha=plan["source_sha"],
        parent_commit=plan["parent_commit"],
        historical_sha256=plan["history_sha256"],
        consumed_mechanisms=consumed_mechanisms,
        existing_candidate_identities=existing_candidate_identities,
        recipe=plan["recipe"])
    # Verify the *same* historical consumed set under the owner lock again.
    # A negative from #840 must never be republished by clearing history.
    need(all(fresh[k] == plan[k] for k in fresh),
         "PLAN_MOVED_BETWEEN_PREFLIGHT_AND_WRITE")
    repo = plan["repository"]
    branch = plan["branch"]
    ref = "refs/heads/" + branch
    created = write("POST", f"repos/{repo}/git/refs", {
        "ref": ref, "sha": plan["parent_commit"]})
    need(isinstance(created, dict) and created.get("ref") == ref
         and isinstance(created.get("object"), dict)
         and created["object"].get("sha") == plan["parent_commit"],
         "CREATE_REF_NOT_AUTHENTICATED_NO_RETRY")
    changed = write("PUT", f"repos/{repo}/contents/{PATH}", {
        "message": "F139 G2 DEV: bounded source-only public causal mechanism",
        "content": base64.b64encode(plan["candidate_source"]).decode("ascii"),
        "sha": plan["before_blob"], "branch": branch,
    })
    need(isinstance(changed, dict)
         and isinstance(changed.get("content"), dict)
         and changed["content"].get("sha") == plan["after_blob"]
         and isinstance(changed.get("commit"), dict)
         and isinstance(changed["commit"].get("sha"), str)
         and SHA40.fullmatch(changed["commit"]["sha"]) is not None,
         "SOURCE_COMMIT_NOT_AUTHENTICATED_NO_RETRY")
    head = changed["commit"]["sha"]
    delta = get(f"repos/{repo}/compare/{plan['parent_commit']}...{head}")
    files = delta.get("files") if isinstance(delta, dict) else None
    need(delta.get("ahead_by") == 1 and delta.get("total_commits") == 1
         and isinstance(files, list) and len(files) == 1
         and files[0].get("filename") == PATH
         and files[0].get("status") == "modified"
         and files[0].get("sha") == plan["after_blob"],
         "NOT_ONE_SOURCE_COMMIT_NO_PR")
    hypothesis = (
        "This G3 hypothesis abstains until three genuine local observations "
        "per action; it never pools evidence across contexts and may slow "
        "exploration. "
        if plan["recipe"] == RECIPE_G3 else
        "Public causal tier-local pooling is an untested mechanism; "
        "unfamiliar transfer and confounding remain unverified. "
    )
    pr = write("POST", f"repos/{repo}/pulls", {
        "title": plan["pr_title"],
        "head": branch, "base": "main", "draft": True,
        "body": (
            "Development-only source proposal created by the original "
            "FORGE G2 bounded publisher. " + hypothesis +
            "No independent advisory Decision has been "
            "issued. No scientific first-use, accepted-ref mutation, "
            "paid API, or additional controller authorization. "
            "The existing F139 feeder must independently verify every "
            "Git commit/tree/blob before admitting an issue."),
    })
    need(isinstance(pr, dict) and type(pr.get("number")) is int
         and pr["number"] > 0, "PR_RESPONSE_UNVERIFIED_NO_RETRY")
    verified = get(f"repos/{repo}/pulls/{pr['number']}")
    need(isinstance(verified, dict) and verified.get("state") == "open"
         and verified.get("draft") is True
         and verified.get("title") == plan["pr_title"]
         and verified.get("head", {}).get("sha") == head
         and verified.get("user", {}).get("login") == "spoonman136668-ai"
         and verified.get("author_association") == "OWNER",
         "OWNER_DRAFT_PR_NOT_VERIFIED")
    from f139.nci04_autonomy_feed import NativeFeedDenied
    try:
        candidate = _candidate_from_pr(
            get, lane=LANE, pr=verified, source_sha=plan["source_sha"])
    except NativeFeedDenied as exc:
        raise PublisherDenied("F139_G2_NATIVE_PR_NOT_INTAKE_QUALIFIED") from exc
    need(candidate["candidate_identity"] == plan["candidate_identity"],
         "SOURCE_CANDIDATE_IDENTITY_DRIFT")
    return {
        "schema": SCHEMA, "pr_number": pr["number"], "head_commit": head,
        "candidate_identity": candidate["candidate_identity"],
        "authentic_single_commit_owner_draft": True,
        "source_qualified_for_existing_feeder": True,
        "scientific_first_use": False,
        "worker_dispatched": False, "controller_mutated": False,
    }
