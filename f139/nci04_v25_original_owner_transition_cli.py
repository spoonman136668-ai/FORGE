"""ONE-SHOT original Windows owner V20->V21 source transition CLI.

This is NOT another controller, scheduler, runner, model provider or poller.
Use only inside a separately reviewed original-owner guarded cutover after
task quiescence, complete cold backup, immutable protected release proof.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

from f139.local_controller import (
    Database, GitHub, SingleOwner, native_original_owner_profile,
    legacy_windows_task_disabled,
)
from f139.nci04_model_owner_bridge import inspect_policy, FORGE_REPO, POLICY_ISSUE
from f139.nci04_native_contract import canonical
from f139.nci04_v24_v20_renewable_readonly_preflight import (
    FROM_V20, SCHEMA as APPROVAL_SCHEMA, FIELDS as APPROVAL_FIELDS,
)
from f139.nci04_v25_v20_source_transition import (
    commit_original_v21, V21TransitionDenied,
)


def require(ok: bool, message: str):
    if not ok:
        raise V21TransitionDenied("F139_V25_CLI_" + message)


def _git(root: Path, *argv: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *argv],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, timeout=20, check=False)
    require(process.returncode == 0, "SOURCE_GIT_READ_DENIED")
    return process.stdout.decode("utf-8", "strict").strip()


def guarded_original_transition(db_path: Path, approval_path: Path) -> dict:
    """Fail closed until *actual* original disabled-task identity is proven."""
    require(os.name == "nt", "WINDOWS_ORIGINAL_OWNER_ONLY")
    require(isinstance(db_path, Path) and isinstance(approval_path, Path)
            and approval_path.is_file(), "EXPLICIT_APPROVAL_PATH_REQUIRED")
    raw = approval_path.read_bytes()
    require(0 < len(raw) <= 4096, "APPROVAL_BYTES_INVALID")
    approval = json.loads(raw)
    require(type(approval) is dict and set(approval) == APPROVAL_FIELDS
            and canonical(approval) == raw
            and approval["schema"] == APPROVAL_SCHEMA
            and approval["from_source_sha"] == FROM_V20,
            "APPROVAL_CANONICAL_V20_SCOPE_REQUIRED")
    root = Path(__file__).resolve().parent.parent
    target = approval["to_source_sha"]
    require(_git(root, "rev-parse", "HEAD") == target
            and _git(root, "status", "--porcelain", "--untracked-files=all") == "",
            "EXACT_CLEAN_INSTALLED_RELEASE_REQUIRED")

    # Same Windows SID, same DB and the same original *disabled* task route.
    # The quiesced original task cannot race the single event transition.
    native_original_owner_profile(db_path)
    legacy_windows_task_disabled()
    api = GitHub()
    require(api.protected_main() == target,
            "PROTECTED_MAIN_SOURCE_MOVED")
    api.legacy_dispatchers_disabled()
    policy = api.native_repo_get(
        "repos/" + FORGE_REPO + "/issues/" + str(POLICY_ISSUE))
    require(inspect_policy(policy, FROM_V20)["enabled"] is True,
            "EXISTING_ORIGINAL_FEED_POLICY_NOT_AUTHENTIC")
    release = api.native_repo_get(
        "repos/" + FORGE_REPO + "/branches/f139-owner-release-" + target)
    require(type(release) is dict
            and release.get("protected") is True
            and isinstance(release.get("commit"), dict)
            and release["commit"].get("sha") == target,
            "IMMUTABLE_ORIGINAL_RELEASE_REF_MISSING")

    db = Database(db_path)
    try:
        with SingleOwner(db_path.with_suffix(".lock")):
            report = commit_original_v21(
                db, approval,
                owner_witness=lambda: native_original_owner_profile(db_path))
            db.verify()
            require(db.meta()["source_sha"] == target,
                    "ORIGINAL_POST_TRANSITION_SOURCE_MISMATCH")
            return report
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--approval", required=True, type=Path)
    args = ap.parse_args(argv)
    outcome = guarded_original_transition(args.db, args.approval)
    print(canonical(outcome).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
