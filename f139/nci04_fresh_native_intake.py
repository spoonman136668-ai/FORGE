"""One-shot owner-bound Yggdrasil DEV issue staging for the F139 fresh epoch.

Source-only and intentionally NOT installed as a CLI or owner workflow.
One existing owner, one SQLite and one verified READY task; never dispatch,
rebind, reset, replay a historical issue or authorize scientific first use.
"""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import inspect_owner_issue
from f139.nci04_fresh_native_provider_issue import (
    FORGE, YGG, inspect_fresh_provider_issue,
)
from f139.nci04_fresh_yggdrasil_boundary import ACCEPTED, ACCEPTED_NATIVE_PATH
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256, audit_frozen_original_readonly,
)

KIND = "FRESH_NATIVE_DEVELOPMENT_ADMITTED"
SCHEMA = "forge.f139.fresh-native-development-intake.v1"
OWNER_WORKFLOW = ("spoonman136668-ai/FORGE/.github/workflows/"
                  "f139-fresh-original-owner-admission.yml@refs/heads/main")
OWNER_PREFIX = "F139-FRESH-DEV-ADMIT"
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
FIELDS = frozenset((
    "schema", "owner_run_id", "source_sha", "activation_sha256",
    "ticket", "lane", "issue_number", "issue_id", "issue_body_sha256",
    "native_intent_sha256", "qualification_key", "native_target_commit",
    "native_target_tree", "native_path", "before_sha256", "after_sha256",
    "native_intent_base64", "remote_issue_number_floor", "manifest_sha256",
    "scientific_first_use", "paid_model_calls", "worker_dispatch_authorized",
    "model_continuation_authorized",
))


class FreshIntakeDenied(ValueError):
    pass


def need(value: bool, why: str) -> None:
    if not value:
        raise FreshIntakeDenied("F139_FRESH_INTAKE_" + why)


def audit_admission_pair(db, activation: dict, tail: list) -> dict:
    """Validate the immutable admission/intake pair independently of later state."""
    need(len(tail) == 2 and tail[0]["seq"] >= 3
         and tail[0]["kind"] == KIND
         and tail[1]["seq"] == tail[0]["seq"] + 1
         and tail[1]["kind"] == "TASK_INTAKE",
         "UNEXPECTED_POSTACTIVATION_EVENTS")
    try:
        r = json.loads(tail[0]["payload"])
        companion = json.loads(tail[1]["payload"])
    except (ValueError, TypeError, UnicodeError) as exc:
        raise FreshIntakeDenied("F139_FRESH_INTAKE_BAD_EVENT_JSON") from exc
    m = db.meta()
    a = db.conn.execute("SELECT sha FROM events WHERE seq=2").fetchone()
    need(a is not None and type(r) is dict and set(r) == FIELDS
         and (tail[0]["seq"] != 3 or tail[0]["prior_sha"] == a["sha"])
         and tail[1]["prior_sha"] == tail[0]["sha"]
         and r["schema"] == SCHEMA
         and r["source_sha"] == activation["source_sha"]
         and r["owner_run_id"] == activation["owner_run_id"]
         and r["activation_sha256"] == a["sha"]
         and r["lane"] == "Yggdrasil"
         and type(r["issue_number"]) is int
         and r["issue_number"] > activation["remote_issue_number_floor"]
         and r["remote_issue_number_floor"] ==
             activation["remote_issue_number_floor"]
         and type(r["issue_id"]) is int and r["issue_id"] > 0
         and type(r["ticket"]) is str
         and re.fullmatch(r"f139-nci04-[a-z0-9-]{1,100}", r["ticket"]) is not None
         and r["scientific_first_use"] is False
         and type(r["paid_model_calls"]) is int and r["paid_model_calls"] == 0
         and r["worker_dispatch_authorized"] is False
         and r["model_continuation_authorized"] is False,
         "SOURCE_IDENTITY_OR_AUTHORITY_INVALID")
    need(all(type(r[k]) is str and SHA64.fullmatch(r[k]) is not None
             for k in ("issue_body_sha256", "native_intent_sha256",
                       "qualification_key", "before_sha256", "after_sha256",
                       "manifest_sha256"))
         and r["native_target_commit"] == ACCEPTED
         and type(r["native_target_tree"]) is str
         and SHA40.fullmatch(r["native_target_tree"]) is not None
         and r["native_path"] == ACCEPTED_NATIVE_PATH,
         "CANDIDATE_NOT_SOURCE_PINNED")
    unsigned = {k: v for k, v in r.items() if k != "manifest_sha256"}
    need(digest(canonical(unsigned)) == r["manifest_sha256"],
         "INTAKE_RECORD_DIGEST_INVALID")
    try:
        encoded = r["native_intent_base64"]
        need(type(encoded) is str and 0 < len(encoded) <= 60000,
             "INTENT_SIZE_INVALID")
        raw = base64.b64decode(encoded, validate=True)
        candidate = parse_intent(
            raw, protected_main=r["source_sha"],
            target_commit=ACCEPTED, target_tree_sha=r["native_target_tree"])
    except (ValueError, UnicodeError, TypeError) as exc:
        raise FreshIntakeDenied("F139_FRESH_INTAKE_INTENT_INVALID") from exc
    need(base64.b64encode(raw).decode("ascii") == encoded
         and digest(raw) == r["native_intent_sha256"]
         and candidate.lane == "Yggdrasil"
         and candidate.path == r["native_path"]
         and candidate.qualification_key == r["qualification_key"]
         and candidate.before_sha256 == r["before_sha256"]
         and candidate.after_sha256 == r["after_sha256"],
         "INTENT_SOURCE_BYTES_CHANGED")
    need(companion == {"ticket": r["ticket"], "lane": "Yggdrasil",
                       "manifest_sha": r["manifest_sha256"]},
         "TASK_INTAKE_EVENT_MISMATCH")
    return r


def audit_one_ready_tail(db, activation: dict, tail: list) -> dict:
    """Historical inert READY contract stays exact; never grants dispatch."""
    r = audit_admission_pair(db, activation, tail)
    m = db.meta()
    need(tail[0]["seq"] == 3 and m["head_seq"] == 4
         and m["head_hash"] == tail[1]["sha"],
         "UNEXPECTED_POSTACTIVATION_EVENTS")
    tasks = list(db.conn.execute("SELECT * FROM tasks"))
    need(len(tasks) == 1 and tasks[0]["ticket"] == r["ticket"]
         and tasks[0]["source_sha"] == r["source_sha"]
         and tasks[0]["lane"] == "Yggdrasil"
         and tasks[0]["stage"] == "READY"
         and tasks[0]["manifest_sha"] == r["manifest_sha256"]
         and tasks[0]["started_at"] is None
         and tasks[0]["run_id"] is None,
         "TASK_NOT_SINGLE_READY_AND_UNDISPATCHED")
    return r


def _authenticate_disabled_owner_host(old: Path, source: str,
                                      number: int, run_id: int) -> None:
    """Require genuine original owner host, comment, SID and disabled task."""
    from f139.nci04_fresh_activation_writer import _WINDOWS_READONLY_PROBE
    repo = "spoonman136668-ai/FORGE"
    need(os.name == "nt" and sys.platform == "win32"
         and os.environ.get("RUNNER_NAME") == "FORGE-CODEX-REMOTE"
         and os.environ.get("GITHUB_REPOSITORY") == repo
         and os.environ.get("GITHUB_REF") == "refs/heads/main"
         and os.environ.get("GITHUB_ACTOR") == "spoonman136668-ai"
         and os.environ.get("GITHUB_EVENT_NAME") == "issue_comment"
         and os.environ.get("GITHUB_WORKFLOW_REF") == OWNER_WORKFLOW
         and os.environ.get("GITHUB_SHA") == source
         and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
         and os.environ.get("GITHUB_RUN_ID", "").isdigit()
         and int(os.environ["GITHUB_RUN_ID"]) > run_id
         and not os.environ.get("OPENAI_API_KEY"),
         "AUTHENTICATED_ORIGINAL_OWNER_WORKFLOW_REQUIRED")
    home = os.environ.get("LOCALAPPDATA", "")
    need(bool(home) and old.resolve() ==
         (Path(home) / "FORGE-F139" / "state.sqlite").resolve(),
         "ORIGINAL_DATABASE_PATH_INVALID")
    file = Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    need(file.is_file() and not file.is_symlink()
         and 0 < file.stat().st_size <= 64000, "OWNER_EVENT_MISSING")
    try:
        event = json.loads(file.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise FreshIntakeDenied("F139_FRESH_INTAKE_OWNER_EVENT_JSON") from exc
    comment = event.get("comment", {})
    need(event.get("action") == "created"
         and event.get("repository", {}).get("full_name") == repo
         and event.get("issue", {}).get("number") == 1830
         and event.get("issue", {}).get("state") == "open"
         and event.get("issue", {}).get("user", {}).get("login") == "spoonman136668-ai"
         and event.get("sender", {}).get("login") == "spoonman136668-ai"
         and type(comment.get("id")) is int and comment["id"] > 0
         and comment.get("url") ==
             f"https://api.github.com/repos/{repo}/issues/comments/{comment['id']}"
         and comment.get("user", {}).get("login") == "spoonman136668-ai"
         and comment.get("body") == f"{OWNER_PREFIX} {source} {number}",
         "EXACT_SOURCE_BOUND_OWNER_COMMENT_REQUIRED")
    pwsh = shutil.which("powershell.exe")
    need(pwsh is not None, "ORIGINAL_WINDOWS_POWERSHELL_REQUIRED")
    try:
        result = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command",
             _WINDOWS_READONLY_PROBE.replace("__FROZEN_SOURCE__", SOURCE)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30, check=False,
            env={**os.environ, "F139_FRESH_ORIGINAL_DB": str(old)})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FreshIntakeDenied("F139_FRESH_INTAKE_OWNER_PROBE_FAILED") from exc
    need(result.returncode == 0 and result.stdout.strip() ==
         b"F139_FRESH_ORIGINAL_WINDOWS_TASK_DISABLED=PASS",
         "ORIGINAL_OWNER_NOT_QUIESCED")


def stage_one_fresh_development_issue(fresh: Database, original: Database,
                                      *, issue_number: int, get) -> dict:
    """Stage one issue only after authentic old task release; no dispatch."""
    from f139.nci04_fresh_native_owner_route import (
        inspect_staged_fresh_native_mode, _sealed_json,
    )
    from f139.nci04_fresh_native_activation import audit_fresh_native_activation
    need(type(fresh) is Database and type(original) is Database
         and getattr(original, "_readonly_opened", False) is True
         and original.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and original.conn.total_changes == 0 and callable(get)
         and type(issue_number) is int and issue_number > 0,
         "OWNER_DATABASE_OR_PROVIDER_ARGUMENT_INVALID")
    old, path = original.filename.resolve(), fresh.filename.resolve()
    need(old.name == "state.sqlite" and old.parent.name == "FORGE-F139"
         and path.parent.parent == old.parent
         and SingleOwner.held(old.with_suffix(".lock")) is True
         and SingleOwner.held(path.with_suffix(".lock")) is True,
         "ORIGINAL_AND_FRESH_MUTEX_REQUIRED")
    stage = inspect_staged_fresh_native_mode(fresh, path)
    need(stage is not None
         and stage["disposition"] == "FRESH_ACTIVATION_RECORDED_DISPATCH_BLOCKED"
         and not stage["fresh_work_admitted"], "FRESH_STAGE_ALREADY_CONSUMED")
    activation = audit_fresh_native_activation(fresh)
    source = activation["source_sha"]
    need(issue_number > activation["remote_issue_number_floor"],
         "ISSUE_MUST_FOLLOW_CUTOVER_FLOOR")
    _authenticate_disabled_owner_host(
        old, source, issue_number, activation["owner_run_id"])
    original.verify()
    before = audit_frozen_original_readonly(original)
    need(before["source_sha"] == SOURCE
         and before["head_seq"] == HEAD_SEQ
         and before["head_sha256"] == HEAD_SHA256,
         "ORIGINAL_CUSTODY_MOVED")
    folder = path.parent
    floor, _ = _sealed_json(folder / "remote-issue-cutover-floor.json")
    consumed, _ = _sealed_json(folder / "consumed-development-identities.json")
    lineage, _ = _sealed_json(folder / "yggdrasil-research-lineage.json")
    proof = inspect_fresh_provider_issue(
        activation=activation, remote_floor=floor, consumed=consumed,
        yggdrasil_boundary=lineage, issue_number=issue_number, get=get)
    need(proof["source_sha"] == source and proof["issue_number"] == issue_number
         and proof["accepted_yggdrasil_source_sha"] == ACCEPTED
         and proof["worker_dispatch_authorized"] is False
         and proof["issue_admission_authorized"] is False,
         "PROVIDER_PREFLIGHT_INVALID")
    issue = get(FORGE + "/issues/" + str(issue_number))
    identity = get(YGG + "/git/commits/" + ACCEPTED)
    need(type(identity) is dict and identity.get("sha") == ACCEPTED
         and type(identity.get("tree")) is dict
         and type(identity["tree"].get("sha")) is str
         and SHA40.fullmatch(identity["tree"]["sha"]) is not None,
         "ACCEPTED_YGGDRASIL_TREE_DRIFT")
    native = inspect_owner_issue(
        issue, protected_main=source, authenticated_target_commit=ACCEPTED,
        authenticated_target_tree=identity["tree"]["sha"])
    need(native.number == issue_number and native.issue_id == proof["issue_id"]
         and native.ticket == proof["ticket"] and native.lane == "Yggdrasil"
         and native.issue_body_sha256 == proof["issue_body_sha256"]
         and native.native_intent_sha256 == proof["native_intent_sha256"]
         and native.candidate.target_commit == ACCEPTED
         and native.candidate.path == ACCEPTED_NATIVE_PATH,
         "ISSUE_CHANGED_AFTER_PROVIDER_PREFLIGHT")
    head = fresh.conn.execute("SELECT sha FROM events WHERE seq=2").fetchone()
    need(head is not None, "ACTIVATION_NOT_RECORDED")
    record = {
        "schema": SCHEMA, "owner_run_id": activation["owner_run_id"],
        "source_sha": source, "activation_sha256": head["sha"],
        "ticket": native.ticket, "lane": "Yggdrasil",
        "issue_number": native.number, "issue_id": native.issue_id,
        "issue_body_sha256": native.issue_body_sha256,
        "native_intent_sha256": native.native_intent_sha256,
        "qualification_key": native.qualification_key,
        "native_target_commit": native.candidate.target_commit,
        "native_target_tree": native.candidate.target_tree_sha,
        "native_path": native.candidate.path,
        "before_sha256": native.candidate.before_sha256,
        "after_sha256": native.candidate.after_sha256,
        "native_intent_base64":
            base64.b64encode(native.intent_raw).decode("ascii"),
        "remote_issue_number_floor": activation["remote_issue_number_floor"],
        "scientific_first_use": False, "paid_model_calls": 0,
        "worker_dispatch_authorized": False,
        "model_continuation_authorized": False,
    }
    record["manifest_sha256"] = digest(canonical(record))
    need(set(record) == FIELDS, "INTAKE_RECORD_FIELDS_INVALID")
    with fresh.transaction():
        _authenticate_disabled_owner_host(
            old, source, issue_number, activation["owner_run_id"])
        need(original.conn.total_changes == 0
             and audit_frozen_original_readonly(original) == before
             and fresh.meta()["head_seq"] == 2
             and not fresh.conn.execute("SELECT 1 FROM tasks LIMIT 1").fetchone(),
             "OWNER_OR_FRESH_HEAD_MOVED")
        fresh.event(KIND, record)
        fresh.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
            "VALUES(?,?,?,'READY',?)",
            (native.ticket, "Yggdrasil", source, record["manifest_sha256"]))
        fresh.event("TASK_INTAKE", {
            "ticket": native.ticket, "lane": "Yggdrasil",
            "manifest_sha": record["manifest_sha256"],
        })
        fresh.verify()
        need(audit_frozen_original_readonly(original) == before,
             "ORIGINAL_MUTATED_DURING_INTAKE")
    final = inspect_staged_fresh_native_mode(fresh, path)
    need(final["disposition"] ==
         "FRESH_DEVELOPMENT_INTAKE_READY_DISPATCH_BLOCKED"
         and final["fresh_work_admitted"]
         and not final["worker_dispatched"],
         "READY_INTAKE_DISPATCH_FENCE_INVALID")
    return {
        "schema": SCHEMA, "source_sha": source, "ticket": native.ticket,
        "issue_number": issue_number, "head_seq": fresh.meta()["head_seq"],
        "head_sha256": fresh.meta()["head_hash"],
        "original_mutations": 0, "task_rebound": False,
        "worker_dispatched": False, "scientific_first_use": False,
        "paid_model_calls": 0, "model_continuation_authorized": False,
    }
