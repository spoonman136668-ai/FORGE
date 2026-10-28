"""F139 native workstation controller. One owner, SQLite, GitHub as a worker only.

This controller NEVER authorizes scientific originals, optimizer promotion, or
GitHub protected-ref mutation. The workflow it can call is fixed in source.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import zipfile

REPO = "spoonman136668-ai/FORGE"
WORKFLOW = "forge-f139-development-worker.yml"
SCHEMA = "forge.f139.windows-controller.v1"
ZERO = "0" * 64
SHA = re.compile(r"[a-f0-9]{40}\Z")
TICKET = re.compile(r"f139-[a-z0-9][a-z0-9-]{2,47}\Z")
LANES = {"Wingless", "Yggdrasil", "Qualification"}
ALLOWED_STAGES = {"READY", "START_RISK", "WAIT_PROVIDER", "VERIFIED", "QUARANTINED"}
LIMIT_PER_DAY = 288  # Sustained two developments per ten minutes, 24/7 capacity.
MAX_ZIP_BYTES = 2_000_000
MAX_RECEIPT_BYTES = 8192
D2K_WORK_LABEL = "f139-development-eligible"
D2K_KIND = "go-package-test-diagnostic"
D2K_ALLOWED_PACKAGES = ("./planner", "./dreamrsi", "./optimizerstages")
D2K_MAX_DAILY = 4
D2K_MAX_TOTAL = 80
D2K_OWNER = "spoonman136668-ai"


# D2J is a single bounded, source-bound development-only succession tranche.
# Do not infer a science grant or evergreen self-authority from these two tickets.
D2J_FROZEN_ORIGINALS = {
    "f139-d2c-qualification-659bb1f4d751": ("Qualification", 39178196331),
    "f139-d2c-wingless-659bb1f4d751": ("Wingless", 39178299792),
}
D2J_TRANCHE = (("Wingless", "wingless"), ("Yggdrasil", "yggdrasil"))



class F139Error(RuntimeError):
    pass


def require(condition: bool, message: str):
    if not condition:
        raise F139Error("F139_" + message)


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def d2j_plan(source_sha: str, previous_head_sha256: str) -> dict:
    """Source-frozen one-shot development plan; no user-provided code or science."""
    require(isinstance(source_sha, str) and SHA.fullmatch(source_sha) is not None
            and isinstance(previous_head_sha256, str)
            and re.fullmatch(r"[a-f0-9]{64}", previous_head_sha256) is not None,
            "D2J_PLAN_IDENTITY_INVALID")
    return {
        "schema": "forge.f139.d2j-once-only-succession.v1",
        "source_sha": source_sha,
        "prior_event_head_sha256": previous_head_sha256,
        "tasks": [
            {"ticket":"f139-d2j-" + label + "-" + source_sha[:12],
             "lane": lane, "source_sha": source_sha}
            for lane, label in D2J_TRANCHE
        ],
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "max_new_development_tickets": 2,
    }


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"), "PROVIDER_TIMESTAMP_INVALID")
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise F139Error("F139_PROVIDER_TIMESTAMP_INVALID") from exc
    require(result.tzinfo is not None, "PROVIDER_TIMESTAMP_INVALID")
    return result


class SingleOwner:
    """Kernel-released process lock, held during each reconciliation tick."""
    _held_paths = set()

    @classmethod
    def held(cls, path: Path) -> bool:
        return str(Path(path).resolve()) in cls._held_paths

    def __init__(self, path: Path):
        self.path = Path(path)
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.fd.seek(0)
                if self.fd.read(1) == b"":
                    self.fd.seek(0)
                    self.fd.write(b"L")
                    self.fd.flush()
                self.fd.seek(0)
                msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.fd.close()
            self.fd = None
            raise F139Error("F139_CONTROLLER_ALREADY_RUNNING") from exc
        self._held_paths.add(str(self.path.resolve()))
        return self

    def __exit__(self, *_):
        self._held_paths.discard(str(self.path.resolve()))
        if self.fd:
            if os.name == "nt":
                import msvcrt
                self.fd.seek(0)
                msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd.fileno(), fcntl.LOCK_UN)
            self.fd.close()
            self.fd = None


def v17_original_model_history_valid(counts: dict) -> bool:
    """Bound live V16 model custody without pretending the first UTC day froze.

    A subsequent original 300-second owner tick may consume another free
    request after midnight. The original hash-chain verifier authenticates
    each preceding attempt, scope, unique lane/day and no-replay semantics.
    This source transition freezes their exact history digest; it does not
    need to guess the number of later immutable attempts at release build.
    """
    if type(counts) is not dict or set(counts) != {
            "G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED",
            "MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED",
            "FREE_REASONER_ATTEMPTED"}:
        return False
    if any(type(n) is not int or n < 0 for n in counts.values()):
        return False
    g3a, g3b = counts["G3_DRAFT_ATTEMPTED"], counts["G3_DRAFT_AUTHENTICATED"]
    model_a = counts["MODEL_DRAFT_ATTEMPTED"]
    model_b = counts["MODEL_DRAFT_AUTHENTICATED"]
    free_a = counts["FREE_REASONER_ATTEMPTED"]
    return (g3a == g3b == 1
            and 2 <= free_a <= 8
            and 3 <= model_b <= model_a <= free_a + 1)


class Database:
    def __init__(self, filename: Path):
        self.filename = Path(filename)
        require(self.filename.is_file(), "DATABASE_MISSING_NO_AUTOINIT")
        self.conn = sqlite3.connect(str(self.filename), isolation_level=None, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=10000")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.verify()

    @classmethod
    def initialize(cls, filename: Path, source_sha: str):
        require(isinstance(source_sha, str) and SHA.fullmatch(source_sha), "SOURCE_SHA_INVALID")
        filename = Path(filename)
        require(not filename.exists(), "DATABASE_ALREADY_EXISTS_NO_RESET")
        filename.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(filename), isolation_level=None, timeout=10)
        try:
            conn.executescript(Path(__file__).with_name("local_schema.sql").read_text())
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("INSERT INTO meta(id,schema,source_sha,epoch,enabled,legacy_suspended,day,starts,head_seq,head_hash) VALUES(1,?,?,1,0,0,'1970-01-01',0,0,?)",
                         (SCHEMA, source_sha, ZERO))
        finally:
            conn.close()
        return cls(filename)

    def dual_native_schema(self):
        row=self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND name='only_one_active_f139_task'").fetchone()
        expected=("CREATE UNIQUE INDEX only_one_active_f139_task "
                  "ON tasks((1)) WHERE stage IN ('START_RISK','WAIT_PROVIDER') "
                  "AND ticket NOT LIKE 'f139-nci04-%'")
        trigger=self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' "
            "AND name='guard_two_native_active'").fetchone()
        return row is not None and row["sql"] == expected and trigger is not None

    def enable_native_two_slots(self):
        """EXPLICIT owner-only index migration, never on startup/read/status.

        Protected original event history survives unchanged; new event binds the
        one-time SQLite index change and preserves the full SHA event chain.
        """
        self.verify()
        meta=self.meta()
        require(meta["enabled"]==1 and meta["legacy_suspended"]==1
                and not self.actives() and self.ready() is None,
                "TWO_SLOT_OWNER_MIGRATION_NOT_IDLE")
        if self.dual_native_schema():
            return False
        old=("CREATE UNIQUE INDEX only_one_active_f139_task "
             "ON tasks((1)) WHERE stage IN ('START_RISK','WAIT_PROVIDER')")
        row=self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND name='only_one_active_f139_task'").fetchone()
        require(row is not None and row["sql"]==old,
                "ORIGINAL_SQLITE_INDEX_IDENTITY_DRIFT")
        with self.transaction():
            self.conn.execute("DROP INDEX only_one_active_f139_task")
            self.conn.execute(
                "CREATE UNIQUE INDEX only_one_active_f139_task ON tasks((1)) "
                "WHERE stage IN ('START_RISK','WAIT_PROVIDER') "
                "AND ticket NOT LIKE 'f139-nci04-%'")
            self.conn.execute(
                "CREATE TRIGGER guard_two_native_active BEFORE UPDATE OF stage "
                "ON tasks WHEN NEW.stage IN ('START_RISK','WAIT_PROVIDER') BEGIN "
                "SELECT CASE WHEN "
                "(SELECT COUNT(*) FROM tasks WHERE stage IN "
                "('START_RISK','WAIT_PROVIDER') AND ticket<>NEW.ticket) >= 2 "
                "OR (NEW.ticket NOT LIKE 'f139-nci04-%' AND EXISTS "
                "(SELECT 1 FROM tasks WHERE stage IN "
                "('START_RISK','WAIT_PROVIDER') AND ticket<>NEW.ticket)) "
                "OR (NEW.ticket LIKE 'f139-nci04-%' AND EXISTS "
                "(SELECT 1 FROM tasks WHERE stage IN "
                "('START_RISK','WAIT_PROVIDER') AND ticket<>NEW.ticket "
                "AND ticket NOT LIKE 'f139-nci04-%')) "
                "THEN RAISE(ABORT,'F139_TWO_ACTIVE_PROVIDER_LIMIT') END; END")
            self.event("NATIVE_TWO_SLOT_SCHEMA_ADMITTED",{
                "schema":"forge.f139.native-two-slot-owner-migration.v1",
                "source_sha":meta["source_sha"],
                "prior_event_head_sha256":meta["head_hash"],
                "scientific_first_use":False})
            require(self.dual_native_schema(),
                    "NATIVE_TWO_SLOT_INDEX_MIGRATION_INVALID")
            self.verify()
        return True

    def close(self):
        self.conn.close()

    def meta(self):
        row = self.conn.execute("SELECT * FROM meta WHERE id=1").fetchone()
        require(row is not None and row["schema"] == SCHEMA and SHA.fullmatch(row["source_sha"]) is not None
                and row["epoch"] > 0 and row["enabled"] in (0,1) and row["legacy_suspended"] in (0,1)
                and row["starts"] >= 0 and row["head_seq"] >= 0
                and re.fullmatch(r"[a-f0-9]{64}", row["head_hash"]), "METADATA_CORRUPT")
        return dict(row)

    def verified_native_provider_failures(self, *, through_seq=None):
        """Identify durable failed provider starts; no external API, no replay.

        through_seq scopes evidence to custody that existed before a historical
        source-transition event, so later negatives cannot retroactively change
        an already sealed transition's ticket set.

        This augments, never replaces, the two sealed original negatives.
        Only original-owner event records with an exact observed terminal
        provider attempt and adjacent quarantine event qualify.
        """
        accepted = {}
        require(through_seq is None or
                type(through_seq) is int and through_seq>0,
                "PROVIDER_NEGATIVE_CUSTODY_CUTOFF_INVALID")
        for event in self.conn.execute(
                "SELECT seq,sha,payload FROM events "
                "WHERE kind='NATIVE_FAILED_PROVIDER_CUSTODY' ORDER BY seq"):
            if through_seq is not None and event["seq"]>=through_seq:
                continue
            doc = json.loads(event["payload"])
            base_fields={"schema","ticket","run_id","source_sha",
                         "provider_sha256","provider","scientific_first_use"}
            late=doc.get("schema")=="forge.f139.owner-native-provider-negative.v2"
            require(isinstance(doc,dict)
                    and set(doc)==(base_fields|{
                        "quarantine_event_seq","quarantine_event_sha256"}
                        if late else base_fields)
                    and doc.get("schema") in {
                        "forge.f139.owner-native-provider-negative.v1",
                        "forge.f139.owner-native-provider-negative.v2"}
                    and doc["scientific_first_use"] is False,
                    "PROVIDER_NEGATIVE_CUSTODY_FIELDS_DRIFT")
            ticket=doc["ticket"]
            report=doc["provider"]
            require(isinstance(ticket,str)
                    and ticket.startswith("f139-nci04-")
                    and TICKET.fullmatch(ticket) is not None
                    and ticket not in accepted
                    and isinstance(doc["source_sha"],str)
                    and SHA.fullmatch(doc["source_sha"]) is not None
                    and type(doc["run_id"]) is int and doc["run_id"]>0
                    and isinstance(report,dict)
                    and set(report)=={
                        "ticket","run_id","source_sha","jobs","artifact_ids",
                        "provider_terminal","scientific_first_use"}
                    and report["ticket"]==ticket
                    and report["run_id"]==doc["run_id"]
                    and report["source_sha"]==doc["source_sha"]
                    and report["provider_terminal"]=="FAILURE_NO_REPLAY"
                    and report["scientific_first_use"] is False
                    and doc["provider_sha256"]==hash_bytes(canonical(report)),
                    "PROVIDER_NEGATIVE_CUSTODY_DIGEST_OR_TICKET")
            jobs=report["jobs"]
            require(isinstance(jobs,dict)
                    and set(jobs)=={"windows-latest","ubuntu-latest"}
                    and any(jobs[name].get("conclusion")=="failure"
                            for name in jobs)
                    and all(isinstance(jobs[name],dict)
                            and set(jobs[name])=={"job_id","conclusion"}
                            and type(jobs[name]["job_id"]) is int
                            and jobs[name]["job_id"]>0
                            and jobs[name]["conclusion"] in ("success","failure")
                            for name in jobs)
                    and isinstance(report["artifact_ids"],list)
                    and all(type(x) is int and x>0
                            for x in report["artifact_ids"])
                    and report["artifact_ids"]==sorted(set(report["artifact_ids"])),
                    "PROVIDER_NEGATIVE_OS_OR_ARTIFACT_INVALID")
            row=self.conn.execute(
                "SELECT stage,source_sha,run_id,evidence_dir,evidence_sha,"
                "quarantine_reason FROM tasks WHERE ticket=?",
                (ticket,)).fetchone()
            require(row is not None and row["stage"]=="QUARANTINED"
                    and row["source_sha"]==doc["source_sha"]
                    and row["run_id"] is None and not row["evidence_dir"]
                    and row["evidence_sha"] is None
                    and row["quarantine_reason"]=="FAILED_OR_CANCELLED_NO_REPLAY",
                    "PROVIDER_NEGATIVE_NOT_ORIGINAL_QUARANTINE")
            if doc["schema"]=="forge.f139.owner-native-provider-negative.v1":
                following=self.conn.execute(
                    "SELECT kind,payload FROM events WHERE seq=?",
                    (event["seq"]+1,)).fetchone()
                require(following is not None
                        and following["kind"]=="ATTEMPT_QUARANTINED"
                        and json.loads(following["payload"])=={
                            "ticket":ticket,
                            "reason":"FAILED_OR_CANCELLED_NO_REPLAY"},
                        "PROVIDER_NEGATIVE_NOT_ORIGINAL_QUARANTINE")
            else:
                require(doc["schema"]=="forge.f139.owner-native-provider-negative.v2"
                        and type(doc.get("quarantine_event_seq")) is int
                        and doc["quarantine_event_seq"]>0
                        and isinstance(doc.get("quarantine_event_sha256"),str)
                        and re.fullmatch(r"[a-f0-9]{64}",
                                         doc["quarantine_event_sha256"]) is not None,
                        "PROVIDER_LATE_CUSTODY_FIELDS_INVALID")
                q=self.conn.execute(
                    "SELECT seq,sha,kind,payload FROM events WHERE seq=?",
                    (doc["quarantine_event_seq"],)).fetchone()
                require(q is not None and q["seq"]<event["seq"]
                        and q["sha"]==doc["quarantine_event_sha256"]
                        and q["kind"]=="ATTEMPT_QUARANTINED"
                        and json.loads(q["payload"])=={
                            "ticket":ticket,
                            "reason":"FAILED_OR_CANCELLED_NO_REPLAY"},
                        "PROVIDER_LATE_CUSTODY_QUARANTINE_DRIFT")
            accepted[ticket]=(doc["source_sha"],event["sha"])
        return accepted

    def verify(self):
        meta = self.meta()
        head, count = ZERO, 0
        source_transitions = []
        free_reasoner_scopes = set()
        free_reasoner_days = {}
        free_reasoner_day_lanes = set()
        last_free_reasoner_day = ""
        for row in self.conn.execute("SELECT * FROM events ORDER BY seq"):
            count += 1
            require(row["seq"] == count and row["prior_sha"] == head, "EVIDENCE_CHAIN_DISCONTINUITY")
            doc = json.loads(row["payload"])
            require(canonical(doc).decode() == row["payload"], "NONCANONICAL_EVENT")
            entry = {"seq": count, "prior_sha": head, "kind": row["kind"], "payload": doc}
            head = hash_bytes(canonical(entry))
            require(head == row["sha"], "EVIDENCE_CHAIN_TAMPERED")
            if row["kind"] == "FREE_REASONER_ATTEMPTED":
                from f139.nci04_native_contract import model_source_path_allowed
                # The external model never becomes a signer or original owner.
                # Every API POST has one pre-committed no-retry event; reject
                # source drift, altered request scope, duplicate request, and
                # excessive attempts even after a cold restart.
                expected_fields = {
                    "schema", "source_sha", "model", "scope_sha256",
                    "original_feedback_sha256", "lane", "target_commit",
                    "path", "utc_day", "prior_event_head_sha256",
                    "remote_request_retry_authorized", "paid_model_calls",
                    "scientific_first_use",
                }
                active_source = (source_transitions[-1]["to_source_sha"]
                                 if source_transitions else meta["source_sha"])
                require(type(doc) is dict and set(doc) == expected_fields
                        and doc["schema"] ==
                            "forge.f139.owner-free-reasoner-attempt.v1"
                        and doc["model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"
                        and isinstance(doc["source_sha"], str)
                        and SHA.fullmatch(doc["source_sha"]) is not None
                        and doc["source_sha"] == active_source
                        and isinstance(doc["target_commit"], str)
                        and SHA.fullmatch(doc["target_commit"]) is not None
                        and isinstance(doc["scope_sha256"], str)
                        and re.fullmatch(r"[a-f0-9]{64}", doc["scope_sha256"])
                        and isinstance(doc["original_feedback_sha256"], str)
                        and re.fullmatch(r"[a-f0-9]{64}",
                                         doc["original_feedback_sha256"])
                        and doc["lane"] in ("Wingless", "Yggdrasil")
                        and isinstance(doc["path"], str)
                        and re.fullmatch(
                            r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}",
                            doc["path"]) is not None
                        and all(part not in ("", ".", "..")
                                for part in doc["path"].split("/"))
                        and model_source_path_allowed(doc["lane"], doc["path"])
                        and isinstance(doc["utc_day"], str)
                        and re.fullmatch(r"\d{4}-\d{2}-\d{2}",
                                         doc["utc_day"]) is not None
                        and doc["prior_event_head_sha256"] == row["prior_sha"]
                        and doc["remote_request_retry_authorized"] is False
                        and type(doc["paid_model_calls"]) is int
                        and doc["paid_model_calls"] == 0
                        and doc["scientific_first_use"] is False,
                        "FREE_REASONER_ORIGINAL_ATTEMPT_CUSTODY_DRIFT")
                require(doc["scope_sha256"] not in free_reasoner_scopes
                        and len(free_reasoner_scopes) < 8
                        and doc["utc_day"] >= last_free_reasoner_day
                        and free_reasoner_days.get(doc["utc_day"], 0) < 2
                        and (doc["utc_day"], doc["lane"]) not in free_reasoner_day_lanes,
                        "FREE_REASONER_ORIGINAL_SCOPE_REPLAY_OR_BUDGET")
                free_reasoner_scopes.add(doc["scope_sha256"])
                free_reasoner_days[doc["utc_day"]] = (
                    free_reasoner_days.get(doc["utc_day"], 0) + 1)
                free_reasoner_day_lanes.add((doc["utc_day"], doc["lane"]))
                last_free_reasoner_day = doc["utc_day"]
            if row["kind"] == "NATIVE_TWO_SLOT_SCHEMA_ADMITTED":
                require(isinstance(doc,dict) and set(doc)=={
                    "schema","source_sha","prior_event_head_sha256",
                    "scientific_first_use"} and doc["schema"]==
                    "forge.f139.native-two-slot-owner-migration.v1"
                    and doc["source_sha"]==(
                        source_transitions[-1]["to_source_sha"] if source_transitions
                        else meta["source_sha"])
                    and doc["prior_event_head_sha256"]==row["prior_sha"]
                    and doc["scientific_first_use"] is False,
                    "TWO_SLOT_MIGRATION_EVENT_DRIFT")
                require(self.dual_native_schema(),"TWO_SLOT_INDEX_MISSING")
            if row["kind"] == "DEVELOPMENT_WORK_ADMITTED":
                require(isinstance(doc, dict) and set(doc) == {
                    "schema", "source_sha", "ticket", "issue_number", "issue_id",
                    "lane", "kind", "target_package", "body_sha256", "manifest_sha256",
                    "prior_event_head_sha256", "scientific_first_use",
                    "admitted_day"},
                    "D2K_ADMISSION_FIELDS")
                require(doc["schema"] == "forge.f139.d2k.issue-work.v1"
                        and SHA.fullmatch(doc["source_sha"]) is not None
                        and doc["issue_number"] > 0 and type(doc["issue_number"]) is int
                        and doc["issue_id"] > 0 and type(doc["issue_id"]) is int
                        and doc["ticket"] == "f139-d2k-i" +
                            str(doc["issue_number"]) + "-" + doc["source_sha"][:12] +
                            "-" + doc["body_sha256"][:8]
                        and doc["lane"] in LANES and doc["kind"] == D2K_KIND
                        and doc["target_package"] in D2K_ALLOWED_PACKAGES
                        and re.fullmatch(r"[a-f0-9]{64}", doc["body_sha256"]) is not None
                        and re.fullmatch(r"[a-f0-9]{64}", doc["manifest_sha256"]) is not None
                        and doc["prior_event_head_sha256"] == row["prior_sha"]
                        and doc["scientific_first_use"] is False
                        and isinstance(doc["admitted_day"],str)
                        and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
                                         doc["admitted_day"]) is not None,
                        "D2K_ADMISSION_INVALID")
                task = self.conn.execute(
                    "SELECT lane,source_sha,manifest_sha FROM tasks WHERE ticket=?",
                    (doc["ticket"],)).fetchone()
                require(task is not None and task["lane"] == doc["lane"]
                        and task["source_sha"] == doc["source_sha"]
                        and task["manifest_sha"] == doc["manifest_sha256"],
                        "D2K_ADMISSION_TASK_DRIFT")
                digest = hash_bytes(canonical({
                    "schema":doc["schema"], "source_sha":doc["source_sha"],
                    "ticket":doc["ticket"], "issue_number":doc["issue_number"],
                    "issue_id":doc["issue_id"], "lane":doc["lane"],
                    "kind":doc["kind"], "target_package":doc["target_package"],
                    "body_sha256":doc["body_sha256"],
                    "prior_event_head_sha256":doc["prior_event_head_sha256"],
                    "admitted_day":doc["admitted_day"],
                    "scientific_first_use":False,
                }))
                require(digest == doc["manifest_sha256"],"D2K_MANIFEST_DIGEST_DRIFT")
            if row["kind"] == "UNATTENDED_SUCCESSION_ADMITTED":
                require(isinstance(doc, dict) and set(doc) == {
                    "schema", "source_sha", "prior_event_head_sha256",
                    "manifest_sha256", "tickets", "new_dispatches",
                    "scientific_first_use"}, "D2J_ADMISSION_FIELDS_INVALID")
                require(doc["schema"] == "forge.f139.d2j-once-only-succession.v1"
                        and SHA.fullmatch(doc["source_sha"]) is not None
                        and doc["prior_event_head_sha256"] == row["prior_sha"]
                        and re.fullmatch(r"[a-f0-9]{64}",doc["manifest_sha256"]) is not None
                        and isinstance(doc["tickets"], list) and len(doc["tickets"]) == 2
                        and doc["tickets"] == [
                            "f139-d2j-" + lane + "-" + doc["source_sha"][:12]
                            for _,lane in D2J_TRANCHE]
                        and doc["new_dispatches"] == 0
                        and doc["scientific_first_use"] is False,
                        "D2J_ADMISSION_INVALID")
                require(row["seq"] == 15 and len(source_transitions) == 3
                        and source_transitions[-1]["to_source_sha"] == doc["source_sha"]
                        and source_transitions[-1]["verified_historical_tasks"] == 2,
                        "D2J_ADMISSION_HISTORY_INVALID")
                expected_plan = d2j_plan(doc["source_sha"],row["prior_sha"])
                require(doc["manifest_sha256"] == hash_bytes(canonical(expected_plan))
                        and doc["tickets"] == [item["ticket"] for item in expected_plan["tasks"]],
                        "D2J_ADMISSION_MANIFEST_CHANGED")
                for item in expected_plan["tasks"]:
                    task = self.conn.execute(
                        "SELECT lane,source_sha,manifest_sha FROM tasks WHERE ticket=?",
                        (item["ticket"],)).fetchone()
                    require(task is not None
                            and task["lane"] == item["lane"]
                            and task["source_sha"] == item["source_sha"]
                            and task["manifest_sha"] == doc["manifest_sha256"],
                            "D2J_ADMISSION_TASK_RECORD_CHANGED")
            if row["kind"] == "SOURCE_TRANSITION_ADMITTED":
                base_fields = {
                    "schema", "from_source_sha", "to_source_sha", "prior_event_head_sha256",
                    "verified_historical_tasks", "new_dispatches", "scientific_first_use"}
                is_v1 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v1"
                         and set(doc) == base_fields)
                is_v2 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v2"
                         and set(doc) == base_fields | {"custodied_negative_tasks"})
                is_v3 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v3"
                         and set(doc) == base_fields | {
                             "custodied_negative_tasks", "custodied_negative_tickets"})
                is_v4 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v4"
                         and set(doc) == base_fields | {
                             "custodied_negative_tasks", "custodied_negative_tickets",
                             "provider_failures_sha256"})
                is_v5 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v5"
                         and set(doc) == base_fields | {
                             "custodied_negative_tasks", "custodied_negative_tickets",
                             "provider_failures_sha256", "v4_terminal_event_sha256"})
                is_v6 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v6"
                         and set(doc) == base_fields | {
                             "custodied_negative_tasks", "custodied_negative_tickets",
                             "provider_failures_sha256", "v5_terminal_event_sha256",
                             "v2_receipt_authorized"})
                is_v7 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v7"
                         and set(doc) == base_fields | {
                             "custodied_negative_tasks", "custodied_negative_tickets",
                             "provider_failures_sha256", "v6_terminal_event_sha256",
                             "v2_receipt_authorized"})
                is_v8 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v8"
                         and set(doc) == base_fields | {
                             "custodied_negative_tasks", "custodied_negative_tickets",
                             "provider_failures_sha256", "v7_terminal_event_sha256",
                             "prepost_negative_event_sha256", "v2_receipt_authorized"})
                is_v9 = (isinstance(doc, dict)
                         and doc.get("schema") == "forge.f139.source-transition.v9"
                         and set(doc) == base_fields | {
                             "custodied_negative_tasks", "custodied_negative_tickets",
                             "provider_failures_sha256", "v8_terminal_event_sha256",
                             "v2_receipt_authorized"})
                is_v10 = (isinstance(doc, dict)
                          and doc.get("schema") == "forge.f139.source-transition.v10"
                          and set(doc) == base_fields | {
                              "custodied_negative_tasks", "custodied_negative_tickets",
                              "provider_failures_sha256", "v9_terminal_event_sha256",
                              "v2_receipt_authorized"})
                is_v11 = (isinstance(doc, dict)
                          and doc.get("schema") == "forge.f139.source-transition.v11"
                          and set(doc) == base_fields | {
                              "custodied_negative_tasks", "custodied_negative_tickets",
                              "provider_failures_sha256", "v10_terminal_event_sha256",
                              "g54_ambiguous_start_event_sha256", "v2_receipt_authorized"})
                is_v12 = (isinstance(doc, dict)
                          and doc.get("schema") == "forge.f139.source-transition.v12"
                          and set(doc) == base_fields | {
                              "custodied_negative_tasks", "custodied_negative_tickets",
                              "provider_failures_sha256", "v11_terminal_event_sha256",
                              "g54_ambiguous_start_event_sha256", "g3_draft_history_sha256",
                              "v2_receipt_authorized"})
                is_v13 = (isinstance(doc, dict)
                          and doc.get("schema") == "forge.f139.source-transition.v13"
                          and set(doc) == base_fields | {
                              "custodied_negative_tasks", "custodied_negative_tickets",
                              "provider_failures_sha256", "v12_terminal_event_sha256",
                              "terminal_tasks_sha256", "model_history_sha256",
                              "v2_receipt_authorized"})
                is_v14 = (isinstance(doc, dict)
                          and doc.get("schema") == "forge.f139.source-transition.v14"
                          and set(doc) == base_fields | {
                              "custodied_negative_tasks", "custodied_negative_tickets",
                              "provider_failures_sha256", "v13_terminal_event_sha256",
                              "terminal_tasks_sha256", "model_history_sha256",
                              "v2_receipt_authorized"})
                is_v15 = (isinstance(doc, dict)
                          and doc.get("schema") == "forge.f139.source-transition.v15"
                          and set(doc) == base_fields | {
                              "custodied_negative_tasks", "custodied_negative_tickets",
                              "provider_failures_sha256", "v14_terminal_event_sha256",
                              "terminal_tasks_sha256", "model_history_sha256",
                              "v2_receipt_authorized"})
                is_v16 = (isinstance(doc, dict)
                          and doc.get("schema") == "forge.f139.source-transition.v16"
                          and set(doc) == base_fields | {
                              "custodied_negative_tasks", "custodied_negative_tickets",
                              "provider_failures_sha256", "v15_terminal_event_sha256",
                              "terminal_tasks_sha256", "model_history_sha256",
                              "v2_receipt_authorized"})
                is_v17 = (isinstance(doc, dict)
                          and doc.get("schema") == "forge.f139.source-transition.v17"
                          and set(doc) == base_fields | {
                              "custodied_negative_tasks", "custodied_negative_tickets",
                              "provider_failures_sha256", "v16_terminal_event_sha256",
                              "terminal_tasks_sha256", "model_history_sha256",
                              "v2_receipt_authorized"})
                require(is_v1 or is_v2 or is_v3 or is_v4 or is_v5 or is_v6 or is_v7 or is_v8 or is_v9 or is_v10 or is_v11 or is_v12 or is_v13 or is_v14 or is_v15 or is_v16 or is_v17,
                        "SOURCE_TRANSITION_EVENT_FIELDS")
                require((is_v1
                         or is_v2 and type(doc["custodied_negative_tasks"]) is int
                         and doc["custodied_negative_tasks"] == 1
                         or is_v3 and type(doc["custodied_negative_tasks"]) is int
                         and doc["custodied_negative_tasks"] == 2
                         or (is_v4 or is_v5 or is_v6 or is_v7 or is_v8 or is_v9 or is_v10 or is_v11 or is_v12 or is_v13 or is_v14 or is_v15 or is_v16 or is_v17)
                         and type(doc["custodied_negative_tasks"]) is int
                         and 3 <= doc["custodied_negative_tasks"] <= 100)
                        and isinstance(doc["from_source_sha"], str)
                        and SHA.fullmatch(doc["from_source_sha"])
                        and isinstance(doc["to_source_sha"], str)
                        and SHA.fullmatch(doc["to_source_sha"])
                        and doc["from_source_sha"] != doc["to_source_sha"]
                        and doc["prior_event_head_sha256"] == row["prior_sha"]
                        and type(doc["verified_historical_tasks"]) is int
                        and doc["verified_historical_tasks"] > 0
                        and type(doc["new_dispatches"]) is int
                        and doc["new_dispatches"] == 0
                        and doc["scientific_first_use"] is False,
                        "SOURCE_TRANSITION_EVENT_INVALID")
                if is_v3:
                    from f139.nci04_negative_owner_store import TICKET as NEGATIVE_696
                    from f139.nci04_split_negative_owner_store import (
                        TICKET as NEGATIVE_706, SOURCE as SOURCE_706, KIND as SECOND_KIND)
                    second = self.conn.execute(
                        "SELECT seq,sha FROM events WHERE kind=?", (SECOND_KIND,)).fetchall()
                    previous_v3 = [
                        t for t in source_transitions
                        if t["schema"] == "forge.f139.source-transition.v3"]
                    require(len(second) == 1 and second[0]["seq"] == 56
                            and doc["custodied_negative_tickets"] ==
                                [NEGATIVE_696, NEGATIVE_706],
                            "SOURCE_TRANSITION_V3_IDENTITY_DRIFT")
                    if not previous_v3:
                        # Original source transition remains exactly event 57.
                        require(row["seq"] == 57
                                and second[0]["sha"] == row["prior_sha"]
                                and doc["from_source_sha"] == SOURCE_706,
                                "SOURCE_TRANSITION_V3_ORIGINAL_DRIFT")
                    else:
                        # Only later manually approved transitions may retain
                        # both immutable negatives, never a second custody event.
                        require(row["seq"] > 57
                                and source_transitions[-1]["schema"] ==
                                    "forge.f139.source-transition.v3"
                                and doc["from_source_sha"] ==
                                    source_transitions[-1]["to_source_sha"]
                                and doc["to_source_sha"] not in {
                                    value for t in source_transitions
                                    for value in (t["from_source_sha"],
                                                  t["to_source_sha"])},
                                "SOURCE_TRANSITION_V3_SUCCESSOR_DRIFT")
                if is_v4 or is_v5 or is_v6 or is_v7 or is_v8:
                    from f139.nci04_negative_owner_store import TICKET as FIRST
                    from f139.nci04_split_negative_owner_store import TICKET as SECOND
                    provider_failures=self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST,
                        SOURCE_V7, CLAIM_SEQ)
                    prepost = verify_g49_custody(self)
                    expected=sorted({FIRST,SECOND}|set(provider_failures)
                                    | ({PREPOST} if is_v8 else set()))
                    require(len(provider_failures)>=1
                            and doc["custodied_negative_tickets"]==expected
                            and doc["custodied_negative_tasks"]==len(expected)
                            and doc["provider_failures_sha256"]==hash_bytes(
                                canonical([{"ticket":t,"source_sha":provider_failures[t][0],
                                            "event_sha":provider_failures[t][1]}
                                           for t in sorted(provider_failures)]))
                            and source_transitions
                            and source_transitions[-1]["schema"] in (
                                "forge.f139.source-transition.v3",
                                "forge.f139.source-transition.v4",
                                "forge.f139.source-transition.v5",
                                "forge.f139.source-transition.v6",
                                "forge.f139.source-transition.v7")
                            and doc["from_source_sha"]==
                                source_transitions[-1]["to_source_sha"]
                            and doc["to_source_sha"] not in {
                                sha for t in source_transitions
                                for sha in (t["from_source_sha"],t["to_source_sha"])},
                            "SOURCE_TRANSITION_V4_PROVIDER_CUSTODY_INVALID")
                    if is_v5:
                        sealed_v4 = [
                            r for r in self.conn.execute(
                                "SELECT seq,sha,payload FROM events "
                                "WHERE kind='SOURCE_TRANSITION_ADMITTED' "
                                "AND seq<? ORDER BY seq",(row["seq"],))
                            if json.loads(r["payload"])["schema"] ==
                                "forge.f139.source-transition.v4"]
                        prior_v5 = [
                            t for t in source_transitions if t["schema"] ==
                                "forge.f139.source-transition.v5"]
                        require(len(sealed_v4)==10
                                and len(prior_v5)<4
                                and source_transitions[-1]["schema"] in (
                                    "forge.f139.source-transition.v4",
                                    "forge.f139.source-transition.v5")
                                and isinstance(doc["v4_terminal_event_sha256"],str)
                                and doc["v4_terminal_event_sha256"] ==
                                    sealed_v4[-1]["sha"],
                                "SOURCE_TRANSITION_V5_V4_SEAL_INVALID")
                    if is_v6:
                        sealed_v5 = [
                            r for r in self.conn.execute(
                                "SELECT seq,sha,payload FROM events "
                                "WHERE kind='SOURCE_TRANSITION_ADMITTED' "
                                "AND seq<? ORDER BY seq",(row["seq"],))
                            if json.loads(r["payload"])["schema"] ==
                                "forge.f139.source-transition.v5"]
                        prior_v6 = [
                            t for t in source_transitions if t["schema"] ==
                                "forge.f139.source-transition.v6"]
                        require(len(sealed_v5)==4 and not prior_v6
                                and source_transitions[-1]["schema"] ==
                                    "forge.f139.source-transition.v5"
                                and doc["v5_terminal_event_sha256"] ==
                                    sealed_v5[-1]["sha"]
                                and doc["v2_receipt_authorized"] is False,
                                "SOURCE_TRANSITION_V6_V5_SEAL_OR_AUTHORITY_INVALID")
                    if is_v7:
                        sealed_v6 = [
                            r for r in self.conn.execute(
                                "SELECT sha,payload FROM events "
                                "WHERE kind='SOURCE_TRANSITION_ADMITTED' "
                                "AND seq<? ORDER BY seq",(row["seq"],))
                            if json.loads(r["payload"])["schema"] ==
                                "forge.f139.source-transition.v6"]
                        prior_v7 = [
                            t for t in source_transitions if t["schema"] ==
                                "forge.f139.source-transition.v7"]
                        require(len(sealed_v6) == 1 and not prior_v7
                                and source_transitions[-1]["schema"] ==
                                    "forge.f139.source-transition.v6"
                                and doc["from_source_sha"] ==
                                    "b2079282fed03df2203807de09b4f3e82bdfe05a"
                                and doc["v6_terminal_event_sha256"] ==
                                    sealed_v6[-1]["sha"]
                                and doc["v2_receipt_authorized"] is False,
                                "SOURCE_TRANSITION_V7_ORIGINAL_SEAL_DRIFT")
                    if is_v8:
                        from f139.nci04_g49_prepost_negative import (
                            verify_g49_custody, SOURCE_V7, CLAIM_SEQ)
                        prepost_rows=list(self.conn.execute(
                            "SELECT seq,sha,payload FROM events WHERE "
                            "kind='NATIVE_PREDISPATCH_NEGATIVE_CUSTODY' "
                            "AND seq<? ORDER BY seq", (row["seq"],)))
                        v7_rows=[
                            t for t in self.conn.execute(
                                "SELECT sha,payload FROM events "
                                "WHERE kind='SOURCE_TRANSITION_ADMITTED' "
                                "AND seq<? ORDER BY seq", (row["seq"],))
                            if json.loads(t["payload"])["schema"]==
                                "forge.f139.source-transition.v7"]
                        prior_v8=[t for t in source_transitions if
                            t["schema"]=="forge.f139.source-transition.v8"]
                        require(verify_g49_custody(self) and len(prepost_rows)==1
                                and prepost_rows[0]["seq"]==CLAIM_SEQ+2
                                and doc["prepost_negative_event_sha256"]==
                                    prepost_rows[0]["sha"]
                                and len(v7_rows)==1 and not prior_v8
                                and source_transitions[-1]["schema"]==
                                    "forge.f139.source-transition.v7"
                                and doc["v7_terminal_event_sha256"]==
                                    v7_rows[0]["sha"]
                                and doc["from_source_sha"]==SOURCE_V7
                                and doc["v2_receipt_authorized"] is False,
                                "SOURCE_TRANSITION_V8_ORIGINAL_CUSTODY_DRIFT")
                if is_v9:
                    v8_rows = [
                        t for t in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(t["payload"])["schema"] ==
                            "forge.f139.source-transition.v8"]
                    previous_v9 = [t for t in source_transitions
                                   if t["schema"] == "forge.f139.source-transition.v9"]
                    from f139.nci04_g49_prepost_negative import verify_g49_custody
                    require(len(v8_rows) == 1 and not previous_v9
                            and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v8"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v8_terminal_event_sha256"] == v8_rows[0]["sha"]
                            and doc["v2_receipt_authorized"] is False
                            and verify_g49_custody(self),
                            "SOURCE_TRANSITION_V9_ORIGINAL_CUSTODY_DRIFT")
                if is_v10:
                    v9_rows = [
                        t for t in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(t["payload"])["schema"] ==
                            "forge.f139.source-transition.v9"]
                    from f139.nci04_negative_owner_store import (
                        verify_original_negative_custody, TICKET as FIRST)
                    from f139.nci04_split_negative_owner_store import (
                        verify_second_negative_custody, TICKET as SECOND)
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST)
                    provider_failures = self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    expected = sorted({FIRST, SECOND, PREPOST} |
                                      set(provider_failures))
                    require(len(v9_rows) == 1 and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v9"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v9_terminal_event_sha256"] == v9_rows[0]["sha"]
                            and doc["v2_receipt_authorized"] is False
                            and len(provider_failures) >= 1
                            and verify_original_negative_custody(self)
                            and verify_second_negative_custody(self)
                            and verify_g49_custody(self)
                            and doc["custodied_negative_tickets"] == expected
                            and doc["custodied_negative_tasks"] == len(expected)
                            and doc["provider_failures_sha256"] == hash_bytes(
                                canonical([{"ticket": ticket,
                                            "source_sha": provider_failures[ticket][0],
                                            "event_sha": provider_failures[ticket][1]}
                                           for ticket in sorted(provider_failures)])),
                            "SOURCE_TRANSITION_V10_ORIGINAL_CUSTODY_DRIFT")
                if is_v11:
                    from f139.nci04_g54_ambiguous_start_custody import (
                        verified_g54_ambiguous_start)
                    from f139.nci04_negative_owner_store import (
                        verify_original_negative_custody, TICKET as FIRST)
                    from f139.nci04_split_negative_owner_store import (
                        verify_second_negative_custody, TICKET as SECOND)
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST)
                    terminal_v10 = [
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(r["payload"]).get("schema") ==
                            "forge.f139.source-transition.v10"]
                    g54 = g54_original_canonical(
                        self, through_seq=row["seq"])
                    previous_provider = self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} |
                                      set(previous_provider))
                    require(len(terminal_v10)==1 and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v10"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v10_terminal_event_sha256"] ==
                                terminal_v10[0]["sha"]
                            and doc["g54_ambiguous_start_event_sha256"] ==
                                g54["quarantine_event_sha256"]
                            and doc["v2_receipt_authorized"] is False
                            and doc["verified_historical_tasks"] >= 21
                            and verify_original_negative_custody(self)
                            and verify_second_negative_custody(self)
                            and verify_g49_custody(self)
                            and doc["custodied_negative_tasks"] == len(expected)
                            and doc["custodied_negative_tickets"] == expected
                            and doc["provider_failures_sha256"] == hash_bytes(
                                canonical([{"ticket": ticket,
                                            "source_sha": previous_provider[ticket][0],
                                            "event_sha": previous_provider[ticket][1]}
                                           for ticket in sorted(previous_provider)])),
                            "SOURCE_TRANSITION_V11_ORIGINAL_CUSTODY_DRIFT")
                if is_v12:
                    from f139.nci04_negative_owner_store import (
                        verify_original_negative_custody, TICKET as FIRST)
                    from f139.nci04_split_negative_owner_store import (
                        verify_second_negative_custody, TICKET as SECOND)
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST)
                    v11_rows = [
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(r["payload"]).get("schema") ==
                           "forge.f139.source-transition.v11"]
                    g54 = g54_original_canonical(self, through_seq=row["seq"])
                    providers = self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} |
                                      set(providers))
                    g3_rows = list(self.conn.execute(
                        "SELECT kind,sha FROM events WHERE kind IN "
                        "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED') "
                        "AND seq<? ORDER BY seq", (row["seq"],)))
                    g3 = [{"kind":r["kind"],"sha":r["sha"]} for r in g3_rows]
                    require(len(v11_rows)==1 and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v11"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v11_terminal_event_sha256"] == v11_rows[0]["sha"]
                            and doc["g54_ambiguous_start_event_sha256"] ==
                                g54["quarantine_event_sha256"]
                            and doc["g3_draft_history_sha256"] ==
                                hash_bytes(canonical(g3))
                            and sum(r["kind"]=="G3_DRAFT_ATTEMPTED" for r in g3_rows)==1
                            and sum(r["kind"]=="G3_DRAFT_AUTHENTICATED" for r in g3_rows)<=1
                            and doc["v2_receipt_authorized"] is False
                            and doc["verified_historical_tasks"] >= 21
                            and verify_original_negative_custody(self)
                            and verify_second_negative_custody(self)
                            and verify_g49_custody(self)
                            and doc["custodied_negative_tasks"] == len(expected)
                            and doc["custodied_negative_tickets"] == expected
                            and doc["provider_failures_sha256"] == hash_bytes(
                                canonical([{"ticket":t,"source_sha":providers[t][0],
                                            "event_sha":providers[t][1]}
                                           for t in sorted(providers)])),
                            "SOURCE_TRANSITION_V12_ORIGINAL_CUSTODY_DRIFT")
                if is_v13:
                    from f139.nci04_negative_owner_store import (
                        verify_original_negative_custody, TICKET as FIRST)
                    from f139.nci04_split_negative_owner_store import (
                        verify_second_negative_custody, TICKET as SECOND)
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST)
                    v12_rows = [
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(r["payload"]).get("schema") ==
                           "forge.f139.source-transition.v12"]
                    providers = self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    g54 = g54_original_canonical(self, through_seq=row["seq"])
                    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} |
                                      set(providers))
                    prior_sources = {value for tr in source_transitions
                                     for value in (tr["from_source_sha"],
                                                   tr["to_source_sha"])}
                    frozen_tasks = [dict(task) for task in self.conn.execute(
                        "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                        "FROM tasks ORDER BY ticket")
                        if task["source_sha"] in prior_sources]
                    frozen_model = [dict(evt) for evt in self.conn.execute(
                        "SELECT kind,sha FROM events WHERE kind IN "
                        "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                        "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                        "'FREE_REASONER_ATTEMPTED') AND seq<? ORDER BY seq",
                        (row["seq"],))]
                    kinds = {name: sum(evt["kind"] == name for evt in frozen_model)
                             for name in ("G3_DRAFT_ATTEMPTED",
                                          "G3_DRAFT_AUTHENTICATED",
                                          "MODEL_DRAFT_ATTEMPTED",
                                          "MODEL_DRAFT_AUTHENTICATED",
                                          "FREE_REASONER_ATTEMPTED")}
                    require(len(v12_rows) == 1 and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v12"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v12_terminal_event_sha256"] == v12_rows[0]["sha"]
                            and doc["terminal_tasks_sha256"] ==
                                hash_bytes(canonical(frozen_tasks))
                            and doc["model_history_sha256"] ==
                                hash_bytes(canonical(frozen_model))
                            and len([t for t in frozen_tasks
                                     if t["stage"] == "VERIFIED"]) >= 22
                            and all(t["stage"] in ("VERIFIED", "QUARANTINED")
                                    for t in frozen_tasks)
                            and all(kinds[name] == 1 for name in (
                                "G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED",
                                "MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED"))
                            and kinds["FREE_REASONER_ATTEMPTED"] == 0
                            and doc["verified_historical_tasks"] >= 22
                            and doc["custodied_negative_tickets"] == expected
                            and doc["custodied_negative_tasks"] == len(expected)
                            and doc["provider_failures_sha256"] == hash_bytes(
                                canonical([{"ticket": t,
                                            "source_sha": providers[t][0],
                                            "event_sha": providers[t][1]}
                                           for t in sorted(providers)]))
                            and doc["v2_receipt_authorized"] is False
                            and verify_original_negative_custody(self)
                            and verify_second_negative_custody(self)
                            and verify_g49_custody(self),
                            "SOURCE_TRANSITION_V13_ORIGINAL_CUSTODY_DRIFT")
                if is_v14:
                    from f139.nci04_negative_owner_store import (
                        verify_original_negative_custody, TICKET as FIRST)
                    from f139.nci04_split_negative_owner_store import (
                        verify_second_negative_custody, TICKET as SECOND)
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST)
                    v13_rows = [
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(r["payload"]).get("schema") ==
                           "forge.f139.source-transition.v13"]
                    providers = self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    g54 = g54_original_canonical(self, through_seq=row["seq"])
                    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} |
                                      set(providers))
                    prior_sources = {value for tr in source_transitions
                                     for value in (tr["from_source_sha"],
                                                   tr["to_source_sha"])}
                    frozen_tasks = [dict(task) for task in self.conn.execute(
                        "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                        "FROM tasks ORDER BY ticket")
                        if task["source_sha"] in prior_sources]
                    frozen_model = [dict(evt) for evt in self.conn.execute(
                        "SELECT kind,sha FROM events WHERE kind IN "
                        "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                        "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                        "'FREE_REASONER_ATTEMPTED') AND seq<? ORDER BY seq",
                        (row["seq"],))]
                    kinds = {name: sum(evt["kind"] == name for evt in frozen_model)
                             for name in ("G3_DRAFT_ATTEMPTED",
                                          "G3_DRAFT_AUTHENTICATED",
                                          "MODEL_DRAFT_ATTEMPTED",
                                          "MODEL_DRAFT_AUTHENTICATED",
                                          "FREE_REASONER_ATTEMPTED")}
                    require(len(v13_rows) == 1 and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v13"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v13_terminal_event_sha256"] == v13_rows[0]["sha"]
                            and doc["terminal_tasks_sha256"] ==
                                hash_bytes(canonical(frozen_tasks))
                            and doc["model_history_sha256"] ==
                                hash_bytes(canonical(frozen_model))
                            and len([t for t in frozen_tasks
                                     if t["stage"] == "VERIFIED"]) >= 22
                            and all(t["stage"] in ("VERIFIED", "QUARANTINED")
                                    for t in frozen_tasks)
                            and kinds["G3_DRAFT_ATTEMPTED"] == 1
                            and kinds["G3_DRAFT_AUTHENTICATED"] == 1
                            and kinds["MODEL_DRAFT_ATTEMPTED"] == 2
                            and kinds["MODEL_DRAFT_AUTHENTICATED"] == 2
                            and kinds["FREE_REASONER_ATTEMPTED"] == 1
                            and doc["verified_historical_tasks"] >= 22
                            and doc["custodied_negative_tickets"] == expected
                            and doc["custodied_negative_tasks"] == len(expected)
                            and doc["provider_failures_sha256"] == hash_bytes(
                                canonical([{"ticket": t,
                                            "source_sha": providers[t][0],
                                            "event_sha": providers[t][1]}
                                           for t in sorted(providers)]))
                            and doc["v2_receipt_authorized"] is False
                            and verify_original_negative_custody(self)
                            and verify_second_negative_custody(self)
                            and verify_g49_custody(self),
                            "SOURCE_TRANSITION_V14_ORIGINAL_CUSTODY_DRIFT")
                if is_v15:
                    from f139.nci04_negative_owner_store import (
                        verify_original_negative_custody, TICKET as FIRST)
                    from f139.nci04_split_negative_owner_store import (
                        verify_second_negative_custody, TICKET as SECOND)
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST)
                    v14_rows = [
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(r["payload"]).get("schema") ==
                           "forge.f139.source-transition.v14"]
                    providers = self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    g54 = g54_original_canonical(self, through_seq=row["seq"])
                    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} |
                                      set(providers))
                    prior_sources = {value for tr in source_transitions
                                     for value in (tr["from_source_sha"],
                                                   tr["to_source_sha"])}
                    frozen_tasks = [dict(task) for task in self.conn.execute(
                        "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                        "FROM tasks ORDER BY ticket")
                        if task["source_sha"] in prior_sources]
                    frozen_model = [dict(evt) for evt in self.conn.execute(
                        "SELECT kind,sha FROM events WHERE kind IN "
                        "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                        "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                        "'FREE_REASONER_ATTEMPTED') AND seq<? ORDER BY seq",
                        (row["seq"],))]
                    kinds = {name: sum(evt["kind"] == name for evt in frozen_model)
                             for name in ("G3_DRAFT_ATTEMPTED",
                                          "G3_DRAFT_AUTHENTICATED",
                                          "MODEL_DRAFT_ATTEMPTED",
                                          "MODEL_DRAFT_AUTHENTICATED",
                                          "FREE_REASONER_ATTEMPTED")}
                    require(len(v14_rows) == 1 and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v14"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v14_terminal_event_sha256"] == v14_rows[0]["sha"]
                            and doc["terminal_tasks_sha256"] ==
                                hash_bytes(canonical(frozen_tasks))
                            and doc["model_history_sha256"] ==
                                hash_bytes(canonical(frozen_model))
                            and len([t for t in frozen_tasks
                                     if t["stage"] == "VERIFIED"]) >= 22
                            and all(t["stage"] in ("VERIFIED", "QUARANTINED")
                                    for t in frozen_tasks)
                            and kinds["G3_DRAFT_ATTEMPTED"] == 1
                            and kinds["G3_DRAFT_AUTHENTICATED"] == 1
                            and kinds["MODEL_DRAFT_ATTEMPTED"] == 2
                            and kinds["MODEL_DRAFT_AUTHENTICATED"] == 2
                            and kinds["FREE_REASONER_ATTEMPTED"] == 1
                            and doc["verified_historical_tasks"] >= 22
                            and doc["custodied_negative_tickets"] == expected
                            and doc["custodied_negative_tasks"] == len(expected)
                            and doc["provider_failures_sha256"] == hash_bytes(
                                canonical([{"ticket": t,
                                            "source_sha": providers[t][0],
                                            "event_sha": providers[t][1]}
                                           for t in sorted(providers)]))
                            and doc["v2_receipt_authorized"] is False
                            and verify_original_negative_custody(self)
                            and verify_second_negative_custody(self)
                            and verify_g49_custody(self),
                            "SOURCE_TRANSITION_V15_ORIGINAL_CUSTODY_DRIFT")
                if is_v16:
                    from f139.nci04_negative_owner_store import (
                        verify_original_negative_custody, TICKET as FIRST)
                    from f139.nci04_split_negative_owner_store import (
                        verify_second_negative_custody, TICKET as SECOND)
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST)
                    v15_rows = [
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(r["payload"]).get("schema") ==
                           "forge.f139.source-transition.v15"]
                    providers = self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    g54 = g54_original_canonical(self, through_seq=row["seq"])
                    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} |
                                      set(providers))
                    prior_sources = {value for tr in source_transitions
                                     for value in (tr["from_source_sha"],
                                                   tr["to_source_sha"])}
                    frozen_tasks = [dict(task) for task in self.conn.execute(
                        "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                        "FROM tasks ORDER BY ticket")
                        if task["source_sha"] in prior_sources]
                    frozen_model = [dict(evt) for evt in self.conn.execute(
                        "SELECT kind,sha FROM events WHERE kind IN "
                        "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                        "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                        "'FREE_REASONER_ATTEMPTED') AND seq<? ORDER BY seq",
                        (row["seq"],))]
                    kinds = {name: sum(evt["kind"] == name for evt in frozen_model)
                             for name in ("G3_DRAFT_ATTEMPTED",
                                          "G3_DRAFT_AUTHENTICATED",
                                          "MODEL_DRAFT_ATTEMPTED",
                                          "MODEL_DRAFT_AUTHENTICATED",
                                          "FREE_REASONER_ATTEMPTED")}
                    require(len(v15_rows) == 1 and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v15"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v15_terminal_event_sha256"] == v15_rows[0]["sha"]
                            and doc["terminal_tasks_sha256"] ==
                                hash_bytes(canonical(frozen_tasks))
                            and doc["model_history_sha256"] ==
                                hash_bytes(canonical(frozen_model))
                            and len([t for t in frozen_tasks
                                     if t["stage"] == "VERIFIED"]) >= 22
                            and all(t["stage"] in ("VERIFIED", "QUARANTINED")
                                    for t in frozen_tasks)
                            and kinds["G3_DRAFT_ATTEMPTED"] == 1
                            and kinds["G3_DRAFT_AUTHENTICATED"] == 1
                            and kinds["MODEL_DRAFT_ATTEMPTED"] == 2
                            and kinds["MODEL_DRAFT_AUTHENTICATED"] == 2
                            and kinds["FREE_REASONER_ATTEMPTED"] == 1
                            and doc["verified_historical_tasks"] >= 22
                            and doc["custodied_negative_tickets"] == expected
                            and doc["custodied_negative_tasks"] == len(expected)
                            and doc["provider_failures_sha256"] == hash_bytes(
                                canonical([{"ticket": t,
                                            "source_sha": providers[t][0],
                                            "event_sha": providers[t][1]}
                                           for t in sorted(providers)]))
                            and doc["v2_receipt_authorized"] is False
                            and verify_original_negative_custody(self)
                            and verify_second_negative_custody(self)
                            and verify_g49_custody(self),
                            "SOURCE_TRANSITION_V16_ORIGINAL_CUSTODY_DRIFT")
                if is_v17:
                    from f139.nci04_negative_owner_store import (
                        verify_original_negative_custody, TICKET as FIRST)
                    from f139.nci04_split_negative_owner_store import (
                        verify_second_negative_custody, TICKET as SECOND)
                    from f139.nci04_g49_prepost_negative import (
                        verify_g49_custody, TICKET as PREPOST)
                    v16_rows = [
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' AND seq<? "
                            "ORDER BY seq", (row["seq"],))
                        if json.loads(r["payload"]).get("schema") ==
                           "forge.f139.source-transition.v16"]
                    providers = self.verified_native_provider_failures(
                        through_seq=row["seq"])
                    g54 = g54_original_canonical(self, through_seq=row["seq"])
                    expected = sorted({FIRST, SECOND, PREPOST, g54["ticket"]} |
                                      set(providers))
                    prior_sources = {value for tr in source_transitions
                                     for value in (tr["from_source_sha"],
                                                   tr["to_source_sha"])}
                    frozen_tasks = [dict(task) for task in self.conn.execute(
                        "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                        "FROM tasks ORDER BY ticket")
                        if task["source_sha"] in prior_sources]
                    frozen_model = [dict(evt) for evt in self.conn.execute(
                        "SELECT kind,sha FROM events WHERE kind IN "
                        "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                        "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                        "'FREE_REASONER_ATTEMPTED') AND seq<? ORDER BY seq",
                        (row["seq"],))]
                    kinds = {name: sum(evt["kind"] == name for evt in frozen_model)
                             for name in ("G3_DRAFT_ATTEMPTED",
                                          "G3_DRAFT_AUTHENTICATED",
                                          "MODEL_DRAFT_ATTEMPTED",
                                          "MODEL_DRAFT_AUTHENTICATED",
                                          "FREE_REASONER_ATTEMPTED")}
                    require(len(v16_rows) == 1 and source_transitions
                            and source_transitions[-1]["schema"] ==
                                "forge.f139.source-transition.v16"
                            and doc["from_source_sha"] ==
                                source_transitions[-1]["to_source_sha"]
                            and doc["v16_terminal_event_sha256"] == v16_rows[0]["sha"]
                            and doc["terminal_tasks_sha256"] ==
                                hash_bytes(canonical(frozen_tasks))
                            and doc["model_history_sha256"] ==
                                hash_bytes(canonical(frozen_model))
                            and len([t for t in frozen_tasks
                                     if t["stage"] == "VERIFIED"]) >= 24
                            and all(t["stage"] in ("VERIFIED", "QUARANTINED")
                                    for t in frozen_tasks)
                            and v17_original_model_history_valid(kinds)
                            and doc["verified_historical_tasks"] >= 24
                            and doc["custodied_negative_tickets"] == expected
                            and doc["custodied_negative_tasks"] == len(expected)
                            and doc["provider_failures_sha256"] == hash_bytes(
                                canonical([{"ticket": t,
                                            "source_sha": providers[t][0],
                                            "event_sha": providers[t][1]}
                                           for t in sorted(providers)]))
                            and doc["v2_receipt_authorized"] is False
                            and verify_original_negative_custody(self)
                            and verify_second_negative_custody(self)
                            and verify_g49_custody(self),
                            "SOURCE_TRANSITION_V17_ORIGINAL_CUSTODY_DRIFT")
                source_transitions.append(doc)
        require(meta["head_seq"] == count and meta["head_hash"] == head, "EVIDENCE_HEAD_ROLLBACK")
        historical_sources = set()
        if source_transitions:
            for index, transition in enumerate(source_transitions):
                if index:
                    require(transition["from_source_sha"] == source_transitions[index-1]["to_source_sha"],
                            "SOURCE_TRANSITION_CHAIN_INVALID")
                historical_sources.add(transition["from_source_sha"])
            require(source_transitions[-1]["to_source_sha"] == meta["source_sha"],
                    "SOURCE_TRANSITION_HEAD_INVALID")
        from f139.nci04_negative_owner_store import (
            verify_original_negative_custody, TICKET as ORIGINAL_NEGATIVE_TICKET,
            SOURCE_SHA as ORIGINAL_NEGATIVE_SOURCE)
        from f139.nci04_split_negative_owner_store import (
            verify_second_negative_custody, TICKET as SECOND_NEGATIVE_TICKET,
            SOURCE as SECOND_NEGATIVE_SOURCE)
        certified_negative = verify_original_negative_custody(self)
        certified_second = verify_second_negative_custody(self)
        negative_v2 = [
            t for t in source_transitions if t["schema"] == "forge.f139.source-transition.v2"]
        negative_v3 = [
            t for t in source_transitions if t["schema"] == "forge.f139.source-transition.v3"]
        negative_v4 = [
            t for t in source_transitions if t["schema"] == "forge.f139.source-transition.v4"]
        negative_v5 = [
            t for t in source_transitions if t["schema"] == "forge.f139.source-transition.v5"]
        negative_v6 = [
            t for t in source_transitions if t["schema"] == "forge.f139.source-transition.v6"]
        negative_v7 = [
            t for t in source_transitions if t["schema"] == "forge.f139.source-transition.v7"]
        negative_v8 = [
            t for t in source_transitions if t["schema"] == "forge.f139.source-transition.v8"]
        negative_v11 = [
            t for t in source_transitions if t["schema"] == "forge.f139.source-transition.v11"]
        require(len(negative_v11) <= 1, "V11_SOURCE_TRANSITION_DUPLICATED")
        # A special original owner quarantine does not have a provider run.
        # It cannot be misclassified as a failed-provider receipt or erased.
        g54_custody = g54_original_canonical(self) if negative_v11 else None
        from f139.nci04_g49_prepost_negative import (
            verify_g49_custody, TICKET as PREPOST, SOURCE_V7)
        prepost_verified = verify_g49_custody(self)
        verified_provider_negatives=self.verified_native_provider_failures()
        negative_transitions = (negative_v2 + negative_v3 + negative_v4 +
                                negative_v5 + negative_v6 + negative_v7 + negative_v8)
        require(len(negative_transitions) <= 37
                and len(negative_v3) <= 10 and len(negative_v4) <= 10
                and len(negative_v5) <= 4 and len(negative_v6) <= 1
                and len(negative_v7) <= 1 and len(negative_v8) <= 1 and
                (not negative_v5 or len(negative_v4)==10) and
                (not negative_v6 or len(negative_v5)==4) and
                (not negative_v8 or len(negative_v7)==1 and prepost_verified),
                "NEGATIVE_TRANSITION_BUDGET_EXHAUSTED")
        require(not negative_v3 or certified_negative and certified_second,
                "SECOND_NEGATIVE_CUSTODY_MISSING")
        for row in self.conn.execute("SELECT ticket,lane,source_sha,stage,run_id,evidence_dir,evidence_sha FROM tasks"):
            prior_verified = (
                row["source_sha"] in historical_sources and
                row["stage"] == "VERIFIED" and
                isinstance(row["run_id"], int) and row["run_id"] > 0 and
                isinstance(row["evidence_dir"], str) and bool(row["evidence_dir"]) and
                isinstance(row["evidence_sha"], str) and
                re.fullmatch(r"[a-f0-9]{64}", row["evidence_sha"]) is not None)
            prior_certified_negative = (
                certified_negative and bool(negative_transitions)
                and row["ticket"] == ORIGINAL_NEGATIVE_TICKET
                and row["source_sha"] == ORIGINAL_NEGATIVE_SOURCE
                and row["source_sha"] in historical_sources
                and row["stage"] == "QUARANTINED" and row["run_id"] is None
                and row["evidence_sha"] is None and not row["evidence_dir"])
            prior_certified_second = (
                certified_second and bool(negative_v3)
                and row["ticket"] == SECOND_NEGATIVE_TICKET
                and row["source_sha"] == SECOND_NEGATIVE_SOURCE
                and row["source_sha"] in historical_sources
                and row["stage"] == "QUARANTINED" and row["run_id"] is None
                and row["evidence_sha"] is None and not row["evidence_dir"])
            prior_provider_failure = (
                bool(negative_v4 or negative_v5 or negative_v6) and row["ticket"] in verified_provider_negatives
                and verified_provider_negatives[row["ticket"]][0]==row["source_sha"]
                and row["source_sha"] in historical_sources
                and row["stage"]=="QUARANTINED" and row["run_id"] is None
                and row["evidence_sha"] is None and not row["evidence_dir"])
            prior_prepost_negative = (
                bool(negative_v8) and prepost_verified
                and row["ticket"] == PREPOST and row["source_sha"] == SOURCE_V7
                and row["source_sha"] in historical_sources
                and row["stage"] == "QUARANTINED" and row["run_id"] is None
                and row["evidence_sha"] is None and not row["evidence_dir"])
            prior_g54_ambiguous = (
                g54_custody is not None
                and row["ticket"] == g54_custody["ticket"]
                and row["source_sha"] == g54_custody["source_sha"]
                and row["source_sha"] in historical_sources
                and row["stage"] == "QUARANTINED"
                and row["run_id"] is None
                and row["evidence_sha"] is None
                and not row["evidence_dir"])
            historical = (prior_verified or prior_certified_negative
                          or prior_certified_second or prior_provider_failure
                          or prior_prepost_negative or prior_g54_ambiguous)
            require(TICKET.fullmatch(row["ticket"]) and row["lane"] in LANES and
                    (row["source_sha"] == meta["source_sha"] or historical) and
                    row["stage"] in ALLOWED_STAGES,
                    "TASK_STATE_CORRUPT")
            require(row["run_id"] is None or (isinstance(row["run_id"], int) and row["run_id"]>0),
                    "TASK_RUN_ID_INVALID")
        if source_transitions:
            admitted=sum(1 for row in self.conn.execute("SELECT source_sha,stage FROM tasks")
                         if row["source_sha"] in historical_sources and row["stage"] == "VERIFIED")
            require(admitted >= source_transitions[-1]["verified_historical_tasks"],
                    "SOURCE_TRANSITION_HISTORIC_COUNT_INVALID")
            if negative_v2:
                require(certified_negative
                        and negative_v2[0]["from_source_sha"] == ORIGINAL_NEGATIVE_SOURCE
                        and all(t["custodied_negative_tasks"] == 1 for t in negative_v2),
                        "CUSTODIED_NEGATIVE_TRANSITION_DRIFT")
            if negative_v3:
                require(certified_second and certified_negative
                        and negative_v3[0]["from_source_sha"] == SECOND_NEGATIVE_SOURCE
                        and all(
                            t["custodied_negative_tasks"] == 2
                            and t["custodied_negative_tickets"] ==
                                [ORIGINAL_NEGATIVE_TICKET, SECOND_NEGATIVE_TICKET]
                            for t in negative_v3),
                        "SECOND_NEGATIVE_TRANSITION_DRIFT")
        # NCI04 admission is additive; historic F139/D2K event semantics stay
        # exact. Check native admission against the original SHA-linked SQLite
        # chain, preventing cross-kind issue replay and fabricated task records.
        from f139.nci04_owner_ledger import audit_native_events
        audit_native_events(self)
        # Every original cold read now rechecks G38 provider ZIP bytes,
        # evidence manifests, and terminal/quarantine states. No ledger
        # migration or controller fork is needed.
        from f139.nci04_g38_owner_terminal import verify_g38_custody
        verify_g38_custody(self)
        from f139.nci04_g49_prepost_negative import verify_g49_custody
        verify_g49_custody(self)
        active_rows = self.actives()
        require(len(active_rows) <= (2 if self.dual_native_schema() else 1)
                and (len(active_rows)<=1 or all(
                    r["ticket"].startswith("f139-nci04-") for r in active_rows)),
                "MULTIPLE_ACTIVE_PROVIDER_DISPATCHES")
        # V19 is verify-only at this gate. The original V17/V18 tick path
        # cannot emit a renewal event or invoke any provider. When a future
        # separately qualified original-owner cutover enables the event,
        # every cold reopen validates it against the full existing SHA chain,
        # authentic native terminal and spent free-model history.
        from f139.nci04_v19_original_attempt_schema import (
            audit_v19_original_request_events)
        audit_v19_original_request_events(self)
        # A future original-owner handoff is independently cold-verified as
        # exactly one source-bound, no-retry pre-transport spend; V17/V18
        # histories with no such event retain their original semantics.
        from f139.nci04_v19_original_one_post_handoff import (
            audit_v19_post_handoff_events)
        audit_v19_post_handoff_events(self)
        # V19 proposed one-shot transport is never in the original tick. A
        # separately held original owner may only send after a committed
        # terminal+intent+handoff+send-attempt chain, cold verified here.
        from f139.nci04_v19_original_one_shot_free_send import (
            audit_v19_send_events)
        audit_v19_send_events(self)

    @contextlib.contextmanager
    def transaction(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    def event(self, kind: str, payload: dict):
        # Only the two qualified G3 publication custody kinds contain digits.
        # Keep the legacy event grammar unchanged for all other events.
        require(re.fullmatch(r"[A-Z_]{3,48}", kind) is not None
                or kind in {"G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED"},
                "INVALID_EVENT_KIND")
        meta = self.meta()
        seq = meta["head_seq"]+1
        entry = {"seq":seq,"prior_sha":meta["head_hash"],"kind":kind,"payload":payload}
        digest = hash_bytes(canonical(entry))
        self.conn.execute("INSERT INTO events(seq,kind,payload,prior_sha,sha) VALUES(?,?,?,?,?)",
                          (seq,kind,canonical(payload).decode(),meta["head_hash"],digest))
        self.conn.execute("UPDATE meta SET head_seq=?,head_hash=? WHERE id=1",(seq,digest))

    def enable(self, *, legacy_suspended: bool):
        require(legacy_suspended, "LEGACY_DISPATCH_OWNER_STILL_ACTIVE")
        with self.transaction():
            self.conn.execute("UPDATE meta SET enabled=1,legacy_suspended=1 WHERE id=1")
            self.event("CUTOVER_ACTIVATED",{"source_sha":self.meta()["source_sha"]})

    def transition_source(self, new_source_sha: str, *,
                          allow_certified_negative: bool = False,
                          allow_v6: bool = False,
                          allow_v7: bool = False,
                          allow_v8: bool = False,
                          allow_v9: bool = False,
                          allow_v10: bool = False,
                          allow_v11: bool = False,
                          allow_v12: bool = False,
                          allow_v13: bool = False,
                          allow_v14: bool = False,
                          allow_v15: bool = False,
                          allow_v16: bool = False,
                          allow_v17: bool = False):
        """Admit v1 zero, v2 single, or bounded v3 double-negative transitions."""
        require(isinstance(new_source_sha, str) and SHA.fullmatch(new_source_sha),
                "SOURCE_TRANSITION_NEW_SHA_INVALID")
        from f139.nci04_negative_owner_store import (
            SOURCE_SHA as SOURCE_696, TICKET as NEGATIVE_696,
            verify_original_negative_custody)
        from f139.nci04_split_negative_owner_store import (
            SOURCE as SOURCE_706, TICKET as NEGATIVE_706,
            verify_second_negative_custody)
        recognized = {NEGATIVE_696: SOURCE_696, NEGATIVE_706: SOURCE_706}
        provider_failures=self.verified_native_provider_failures()
        recognized.update({ticket:source for ticket,(source,_) in provider_failures.items()})
        from f139.nci04_g49_prepost_negative import (
            verify_g49_custody, TICKET as PREPOST, SOURCE_V7)
        prepost = verify_g49_custody(self)
        if prepost:
            recognized[PREPOST] = SOURCE_V7
        if allow_v11 or allow_v12 or allow_v13 or allow_v14 or allow_v15 or allow_v16 or allow_v17:
            from f139.nci04_g54_ambiguous_start_custody import (
                verified_g54_ambiguous_start)
            frozen_ambiguous=g54_original_canonical(self)
            recognized[frozen_ambiguous["ticket"]]=frozen_ambiguous["source_sha"]
        with self.transaction():
            self.verify()
            meta = self.meta()
            require(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
                    and new_source_sha != meta["source_sha"],
                    "SOURCE_TRANSITION_OWNER_OR_IDENTITY_INVALID")
            tasks = list(self.conn.execute("SELECT * FROM tasks"))
            certified, verified = [], []
            for row in tasks:
                if (row["stage"] == "VERIFIED"
                    and type(row["run_id"]) is int and row["run_id"] > 0
                    and isinstance(row["evidence_sha"], str)
                    and re.fullmatch(r"[a-f0-9]{64}",row["evidence_sha"])
                    and row["evidence_dir"]):
                    verified.append(row)
                elif (allow_certified_negative and row["stage"] == "QUARANTINED"
                      and row["ticket"] in recognized
                      and row["source_sha"] == recognized[row["ticket"]]
                      and row["run_id"] is None and row["evidence_sha"] is None
                      and not row["evidence_dir"]):
                    certified.append(row)
                else:
                    raise F139Error("F139_SOURCE_TRANSITION_UNVERIFIED_OR_PENDING_TASK")
            require(bool(tasks) and len(verified) + len(certified) == len(tasks),
                    "SOURCE_TRANSITION_UNVERIFIED_OR_PENDING_TASK")
            tickets = {r["ticket"] for r in certified}
            schema = "forge.f139.source-transition.v1"
            if len(certified) == 1:
                transitions = [
                    parsed for parsed in (
                        json.loads(t["payload"]) for t in self.conn.execute(
                            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'")
                    ) if parsed["schema"] == "forge.f139.source-transition.v2"]
                require(tickets == {NEGATIVE_696}
                        and verify_original_negative_custody(self)
                        and (meta["source_sha"] == SOURCE_696
                             and meta["head_seq"] == 48 and not transitions
                             or meta["source_sha"] != SOURCE_696
                             and len(transitions) >= 1
                             and transitions[0]["from_source_sha"] == SOURCE_696),
                        "SOURCE_TRANSITION_NEGATIVE_NOT_CUSTODIED")
                schema = "forge.f139.source-transition.v2"
            elif len(certified) == 2:
                transitions = [
                    json.loads(r["payload"]) for r in self.conn.execute(
                        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'")]
                previous_v3 = [
                    t for t in transitions
                    if t["schema"] == "forge.f139.source-transition.v3"]
                original_boundary = (
                    meta["source_sha"] == SOURCE_706
                    and meta["head_seq"] == 56
                    and not previous_v3)
                from f139.nci04_owner_ledger import verify_native_activation
                successor_boundary = (
                    bool(previous_v3)
                    and len(previous_v3) < 10
                    and transitions[-1]["schema"] ==
                        "forge.f139.source-transition.v3"
                    and meta["source_sha"] == previous_v3[-1]["to_source_sha"]
                    and verify_native_activation(self)
                    and new_source_sha not in {
                        value for t in transitions
                        for value in (t["from_source_sha"], t["to_source_sha"])})
                require(tickets == {NEGATIVE_696, NEGATIVE_706}
                        and (original_boundary or successor_boundary)
                        and verify_original_negative_custody(self)
                        and verify_second_negative_custody(self)
                        and any(t["schema"] == "forge.f139.source-transition.v2"
                                and t["from_source_sha"] == SOURCE_696 for t in transitions)
                        and self.active() is None and self.ready() is None,
                        "SOURCE_TRANSITION_TWO_NEGATIVES_NOT_CUSTODIED")
                schema = "forge.f139.source-transition.v3"
            elif len(certified)>=3:
                from f139.nci04_owner_ledger import verify_native_activation
                events=[
                    json.loads(r["payload"]) for r in self.conn.execute(
                        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'")]
                require(tickets==set(recognized)
                        and len(provider_failures)>=1
                        and verify_original_negative_custody(self)
                        and verify_second_negative_custody(self)
                        and events and events[-1]["schema"] in (
                            "forge.f139.source-transition.v16",
                            "forge.f139.source-transition.v15",
                            "forge.f139.source-transition.v14",
                            "forge.f139.source-transition.v13",
                            "forge.f139.source-transition.v12",
                            "forge.f139.source-transition.v11",
                            "forge.f139.source-transition.v10",
                            "forge.f139.source-transition.v9",
                            "forge.f139.source-transition.v8",
                            "forge.f139.source-transition.v3",
                            "forge.f139.source-transition.v4",
                            "forge.f139.source-transition.v5",
                            "forge.f139.source-transition.v6",
                            "forge.f139.source-transition.v7")
                        and (verify_native_activation(self)
                             or (events[-1]["schema"] in
                                     ("forge.f139.source-transition.v4",
                                      "forge.f139.source-transition.v5",
                                      "forge.f139.source-transition.v6",
                                      "forge.f139.source-transition.v7")
                                 and self.conn.execute(
                                     "SELECT kind FROM events ORDER BY seq DESC LIMIT 1"
                                 ).fetchone()["kind"]=="SOURCE_TRANSITION_ADMITTED"
                                 and not self.conn.execute(
                                     "SELECT 1 FROM tasks WHERE source_sha=? LIMIT 1",
                                     (meta["source_sha"],)).fetchone()))
                        and events[-1]["to_source_sha"]==meta["source_sha"]
                        and new_source_sha not in {
                            sha for e in events
                            for sha in (e["from_source_sha"],e["to_source_sha"])}
                        and self.active() is None and self.ready() is None,
                        "SOURCE_TRANSITION_V4_NEGATIVES_NOT_CUSTODIED")
                prev_v4=[e for e in events if e["schema"]==
                         "forge.f139.source-transition.v4"]
                prev_v5=[e for e in events if e["schema"]==
                         "forge.f139.source-transition.v5"]
                prev_v6=[e for e in events if e["schema"]==
                         "forge.f139.source-transition.v6"]
                prev_v7=[e for e in events if e["schema"]==
                         "forge.f139.source-transition.v7"]
                prev_v8=[e for e in events if e["schema"]==
                         "forge.f139.source-transition.v8"]
                prev_v9=[e for e in events if e["schema"]==
                         "forge.f139.source-transition.v9"]
                prev_v10=[e for e in events if e["schema"]==
                          "forge.f139.source-transition.v10"]
                prev_v11=[e for e in events if e["schema"]==
                          "forge.f139.source-transition.v11"]
                prev_v12=[e for e in events if e["schema"]==
                          "forge.f139.source-transition.v12"]
                prev_v13=[e for e in events if e["schema"]==
                          "forge.f139.source-transition.v13"]
                prev_v14=[e for e in events if e["schema"]==
                          "forge.f139.source-transition.v14"]
                prev_v15=[e for e in events if e["schema"]==
                          "forge.f139.source-transition.v15"]
                prev_v16=[e for e in events if e["schema"]==
                          "forge.f139.source-transition.v16"]
                if prev_v16:
                    require(allow_v17 is True and len(prev_v16)==1
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v16"
                            and meta["source_sha"] == prev_v16[0]["to_source_sha"]
                            and verify_native_activation(self)
                            and self.active() is None and self.ready() is None,
                            "SOURCE_TRANSITION_V17_ORIGINAL_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v17"
                elif prev_v15:
                    require(allow_v16 is True and len(prev_v15)==1
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v15"
                            and meta["source_sha"] == prev_v15[0]["to_source_sha"]
                            and verify_native_activation(self)
                            and self.active() is None and self.ready() is None,
                            "SOURCE_TRANSITION_V16_ORIGINAL_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v16"
                elif prev_v14:
                    require(allow_v15 is True and len(prev_v14)==1
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v14"
                            and meta["source_sha"] == prev_v14[0]["to_source_sha"]
                            and verify_native_activation(self)
                            and self.active() is None and self.ready() is None,
                            "SOURCE_TRANSITION_V15_ORIGINAL_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v15"
                elif prev_v13:
                    require(allow_v14 is True and len(prev_v13)==1
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v13"
                            and meta["source_sha"] == prev_v13[0]["to_source_sha"]
                            and verify_native_activation(self)
                            and self.active() is None and self.ready() is None,
                            "SOURCE_TRANSITION_V14_ORIGINAL_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v14"
                elif prev_v12:
                    from f139.nci04_owner_ledger import verify_native_activation
                    require(allow_v13 is True and len(prev_v12)==1
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v12"
                            and meta["source_sha"] == prev_v12[0]["to_source_sha"]
                            and verify_native_activation(self)
                            and self.active() is None and self.ready() is None,
                            "SOURCE_TRANSITION_V13_ORIGINAL_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v13"
                elif prev_v11:
                    from f139.nci04_owner_ledger import verify_native_activation
                    require(allow_v12 is True and len(prev_v11)==1
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v11"
                            and meta["source_sha"] == prev_v11[0]["to_source_sha"]
                            and verify_native_activation(self)
                            and self.active() is None and self.ready() is None,
                            "SOURCE_TRANSITION_V12_ORIGINAL_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v12"
                elif prev_v10:
                    from f139.nci04_owner_ledger import verify_native_activation
                    require(allow_v11 is True and len(prev_v10)==1
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v10"
                            and meta["source_sha"]==
                                prev_v10[0]["to_source_sha"]
                            and verify_native_activation(self)
                            and self.active() is None and self.ready() is None,
                            "SOURCE_TRANSITION_V11_ORIGINAL_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v11"
                elif prev_v9:
                    from f139.nci04_owner_ledger import verify_native_activation
                    require(allow_v10 is True and len(prev_v9)==1
                            and events[-1]["schema"] ==
                                "forge.f139.source-transition.v9"
                            and meta["source_sha"] ==
                                prev_v9[0]["to_source_sha"]
                            and verify_native_activation(self) and prepost
                            and self.active() is None and self.ready() is None,
                            "SOURCE_TRANSITION_V10_SUCCESSOR_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v10"
                elif prev_v8:
                    from f139.nci04_owner_ledger import verify_native_activation
                    require(allow_v9 is True and len(prev_v8)==1
                            and events[-1]["schema"] ==
                                "forge.f139.source-transition.v8"
                            and meta["source_sha"] ==
                                prev_v8[0]["to_source_sha"]
                            and verify_native_activation(self) and prepost,
                            "SOURCE_TRANSITION_V9_ONE_SHOT_CUSTODY_REQUIRED")
                    schema="forge.f139.source-transition.v9"
                elif (len(prev_v4)==10 and len(prev_v5)==4
                        and len(prev_v6)==1 and len(prev_v7)==1):
                    require(allow_v8 is True and not prev_v8 and prepost
                            and events[-1]["schema"] ==
                                "forge.f139.source-transition.v7"
                            and meta["source_sha"] == SOURCE_V7,
                            "SOURCE_TRANSITION_V8_ONE_SHOT_PREPOST_REQUIRED")
                    schema="forge.f139.source-transition.v8"
                elif len(prev_v4)==10 and len(prev_v5)==4 and len(prev_v6)==1:
                    require(allow_v7 is True and not prev_v7
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v6"
                            and meta["source_sha"] ==
                                "b2079282fed03df2203807de09b4f3e82bdfe05a",
                            "SOURCE_TRANSITION_V7_ONE_SHOT_ORIGINAL_SOURCE_DENIED")
                    schema="forge.f139.source-transition.v7"
                elif len(prev_v4)==10 and len(prev_v5)==4:
                    require(allow_v6 is True,
                            "SOURCE_TRANSITION_V5_BOUNDED_CAPACITY_EXHAUSTED")
                    require(not prev_v6
                            and events[-1]["schema"]==
                                "forge.f139.source-transition.v5",
                            "SOURCE_TRANSITION_V6_BOUNDED_CAPACITY_EXHAUSTED")
                    schema="forge.f139.source-transition.v6"
                elif len(prev_v4)==10:
                    require(len(prev_v5)<4 and not prev_v6,
                            "SOURCE_TRANSITION_V5_BOUNDED_CAPACITY_EXHAUSTED")
                    schema="forge.f139.source-transition.v5"
                else:
                    require(len(prev_v4)<10 and not prev_v5,
                            "SOURCE_TRANSITION_V4_HISTORY_INVALID")
                    schema="forge.f139.source-transition.v4"
            else:
                require(not allow_certified_negative and not certified,
                        "SOURCE_TRANSITION_NEGATIVE_NOT_PRESENT")
            prior = meta["head_hash"]
            self.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", (new_source_sha,))
            event = {
                "schema": schema,
                "from_source_sha": meta["source_sha"],
                "to_source_sha": new_source_sha,
                "prior_event_head_sha256": prior,
                "verified_historical_tasks": len(verified),
                "new_dispatches": 0,
                "scientific_first_use": False,
            }
            if schema != "forge.f139.source-transition.v1":
                event["custodied_negative_tasks"] = len(certified)
            if schema == "forge.f139.source-transition.v3":
                event["custodied_negative_tickets"] = [NEGATIVE_696, NEGATIVE_706]
            elif schema in ("forge.f139.source-transition.v4",
                            "forge.f139.source-transition.v5",
                            "forge.f139.source-transition.v6",
                            "forge.f139.source-transition.v7",
                            "forge.f139.source-transition.v8",
                            "forge.f139.source-transition.v9",
                            "forge.f139.source-transition.v10",
                            "forge.f139.source-transition.v11",
                            "forge.f139.source-transition.v12",
                            "forge.f139.source-transition.v13",
                            "forge.f139.source-transition.v14",
                            "forge.f139.source-transition.v15",
                            "forge.f139.source-transition.v16",
                            "forge.f139.source-transition.v17"):
                event["custodied_negative_tickets"] = sorted(tickets)
                event["provider_failures_sha256"]=hash_bytes(
                    canonical([{"ticket":t,"source_sha":provider_failures[t][0],
                                "event_sha":provider_failures[t][1]}
                               for t in sorted(provider_failures)]))
                if schema == "forge.f139.source-transition.v5":
                    v4_rows=[
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                        if json.loads(r["payload"])["schema"] ==
                            "forge.f139.source-transition.v4"]
                    require(len(v4_rows)==10,
                            "SOURCE_TRANSITION_V5_V4_SEAL_MISSING")
                    event["v4_terminal_event_sha256"]=v4_rows[-1]["sha"]
                if schema == "forge.f139.source-transition.v6":
                    v5_rows=[
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                        if json.loads(r["payload"])["schema"] ==
                            "forge.f139.source-transition.v5"]
                    require(len(v5_rows)==4,
                            "SOURCE_TRANSITION_V6_V5_SEAL_MISSING")
                    event["v5_terminal_event_sha256"]=v5_rows[-1]["sha"]
                    # Migrating original code never implicitly enables V2
                    # receipt claims. Separate signed worker approval is required.
                    event["v2_receipt_authorized"]=False
                if schema == "forge.f139.source-transition.v7":
                    v6_rows=[
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                        if json.loads(r["payload"])["schema"] ==
                            "forge.f139.source-transition.v6"]
                    require(len(v6_rows)==1,
                            "SOURCE_TRANSITION_V7_V6_SEAL_MISSING")
                    event["v6_terminal_event_sha256"]=v6_rows[-1]["sha"]
                    event["v2_receipt_authorized"]=False
                if schema == "forge.f139.source-transition.v8":
                    v7_rows=[
                        r for r in self.conn.execute(
                            "SELECT sha,payload FROM events "
                            "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                        if json.loads(r["payload"])["schema"] ==
                            "forge.f139.source-transition.v7"]
                    custody=self.conn.execute(
                        "SELECT seq,sha FROM events "
                        "WHERE kind='NATIVE_PREDISPATCH_NEGATIVE_CUSTODY'"
                    ).fetchall()
                    require(len(v7_rows)==1 and len(custody)==1
                            and custody[0]["seq"]==227,
                            "SOURCE_TRANSITION_V8_SEALS_MISSING")
                    event["v7_terminal_event_sha256"]=v7_rows[0]["sha"]
                    event["prepost_negative_event_sha256"]=custody[0]["sha"]
                    event["v2_receipt_authorized"]=False
            if schema == "forge.f139.source-transition.v9":
                v8_rows=[
                    r for r in self.conn.execute(
                        "SELECT sha,payload FROM events "
                        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"])["schema"] ==
                        "forge.f139.source-transition.v8"]
                require(len(v8_rows)==1,
                        "SOURCE_TRANSITION_V9_V8_SEAL_MISSING")
                event["v8_terminal_event_sha256"]=v8_rows[0]["sha"]
                event["v2_receipt_authorized"]=False
            if schema == "forge.f139.source-transition.v10":
                v9_rows=[
                    r for r in self.conn.execute(
                        "SELECT sha,payload FROM events "
                        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"])["schema"] ==
                        "forge.f139.source-transition.v9"]
                require(len(v9_rows)==1,
                        "SOURCE_TRANSITION_V10_V9_SEAL_MISSING")
                event["v9_terminal_event_sha256"]=v9_rows[0]["sha"]
                event["v2_receipt_authorized"]=False
            if schema == "forge.f139.source-transition.v11":
                v10_rows=[
                    r for r in self.conn.execute(
                        "SELECT sha,payload FROM events "
                        "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"])["schema"] ==
                       "forge.f139.source-transition.v10"]
                require(len(v10_rows)==1,
                        "SOURCE_TRANSITION_V11_V10_SEAL_MISSING")
                from f139.nci04_g54_ambiguous_start_custody import (
                    verified_g54_ambiguous_start)
                g54=g54_original_canonical(self)
                event["v10_terminal_event_sha256"]=v10_rows[0]["sha"]
                event["g54_ambiguous_start_event_sha256"]=g54["quarantine_event_sha256"]
                event["v2_receipt_authorized"]=False
            if schema == "forge.f139.source-transition.v12":
                rows = [r for r in self.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"]).get("schema") ==
                       "forge.f139.source-transition.v11"]
                require(len(rows)==1,"SOURCE_TRANSITION_V12_V11_SEAL_MISSING")
                g54=g54_original_canonical(self)
                g3=list(self.conn.execute(
                    "SELECT kind,sha FROM events WHERE kind IN "
                    "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED') "
                    "ORDER BY seq"))
                require(sum(r["kind"]=="G3_DRAFT_ATTEMPTED" for r in g3)==1,
                        "SOURCE_TRANSITION_V12_G3_HISTORY_DRIFT")
                event["v11_terminal_event_sha256"]=rows[0]["sha"]
                event["g54_ambiguous_start_event_sha256"]=g54["quarantine_event_sha256"]
                event["g3_draft_history_sha256"]=hash_bytes(canonical(
                    [{"kind":r["kind"],"sha":r["sha"]} for r in g3]))
                event["v2_receipt_authorized"]=False
            if schema == "forge.f139.source-transition.v13":
                prior_rows = [r for r in self.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"]).get("schema") ==
                       "forge.f139.source-transition.v12"]
                require(len(prior_rows) == 1,
                        "SOURCE_TRANSITION_V13_V12_SEAL_MISSING")
                model = [dict(r) for r in self.conn.execute(
                    "SELECT kind,sha FROM events WHERE kind IN "
                    "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                    "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                    "'FREE_REASONER_ATTEMPTED') ORDER BY seq")]
                kinds = {name: sum(r["kind"] == name for r in model)
                         for name in ("G3_DRAFT_ATTEMPTED",
                                      "G3_DRAFT_AUTHENTICATED",
                                      "MODEL_DRAFT_ATTEMPTED",
                                      "MODEL_DRAFT_AUTHENTICATED",
                                      "FREE_REASONER_ATTEMPTED")}
                require(all(kinds[k] == 1 for k in (
                    "G3_DRAFT_ATTEMPTED", "G3_DRAFT_AUTHENTICATED",
                    "MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED"))
                    and kinds["FREE_REASONER_ATTEMPTED"] == 0,
                    "SOURCE_TRANSITION_V13_MODEL_HISTORY_DRIFT")
                frozen = [dict(r) for r in self.conn.execute(
                    "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                    "FROM tasks ORDER BY ticket")]
                event["v12_terminal_event_sha256"] = prior_rows[0]["sha"]
                event["terminal_tasks_sha256"] = hash_bytes(canonical(frozen))
                event["model_history_sha256"] = hash_bytes(canonical(model))
                event["v2_receipt_authorized"] = False
            if schema == "forge.f139.source-transition.v14":
                prior_rows = [r for r in self.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"]).get("schema") ==
                       "forge.f139.source-transition.v13"]
                require(len(prior_rows) == 1,
                        "SOURCE_TRANSITION_V14_V13_SEAL_MISSING")
                model = [dict(r) for r in self.conn.execute(
                    "SELECT kind,sha FROM events WHERE kind IN "
                    "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                    "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                    "'FREE_REASONER_ATTEMPTED') ORDER BY seq")]
                kinds = {name: sum(r["kind"] == name for r in model)
                         for name in ("G3_DRAFT_ATTEMPTED",
                                      "G3_DRAFT_AUTHENTICATED",
                                      "MODEL_DRAFT_ATTEMPTED",
                                      "MODEL_DRAFT_AUTHENTICATED",
                                      "FREE_REASONER_ATTEMPTED")}
                require(kinds["G3_DRAFT_ATTEMPTED"] == 1
                        and kinds["G3_DRAFT_AUTHENTICATED"] == 1
                        and kinds["MODEL_DRAFT_ATTEMPTED"] == 2
                        and kinds["MODEL_DRAFT_AUTHENTICATED"] == 2
                        and kinds["FREE_REASONER_ATTEMPTED"] == 1,
                        "SOURCE_TRANSITION_V14_MODEL_HISTORY_DRIFT")
                frozen = [dict(r) for r in self.conn.execute(
                    "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                    "FROM tasks ORDER BY ticket")]
                event["v13_terminal_event_sha256"] = prior_rows[0]["sha"]
                event["terminal_tasks_sha256"] = hash_bytes(canonical(frozen))
                event["model_history_sha256"] = hash_bytes(canonical(model))
                event["v2_receipt_authorized"] = False
            if schema == "forge.f139.source-transition.v15":
                prior_rows = [r for r in self.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"]).get("schema") ==
                       "forge.f139.source-transition.v14"]
                require(len(prior_rows) == 1,
                        "SOURCE_TRANSITION_V15_V14_SEAL_MISSING")
                model = [dict(r) for r in self.conn.execute(
                    "SELECT kind,sha FROM events WHERE kind IN "
                    "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                    "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                    "'FREE_REASONER_ATTEMPTED') ORDER BY seq")]
                kinds = {name: sum(r["kind"] == name for r in model)
                         for name in ("G3_DRAFT_ATTEMPTED",
                                      "G3_DRAFT_AUTHENTICATED",
                                      "MODEL_DRAFT_ATTEMPTED",
                                      "MODEL_DRAFT_AUTHENTICATED",
                                      "FREE_REASONER_ATTEMPTED")}
                require(kinds["G3_DRAFT_ATTEMPTED"] == 1
                        and kinds["G3_DRAFT_AUTHENTICATED"] == 1
                        and kinds["MODEL_DRAFT_ATTEMPTED"] == 2
                        and kinds["MODEL_DRAFT_AUTHENTICATED"] == 2
                        and kinds["FREE_REASONER_ATTEMPTED"] == 1,
                        "SOURCE_TRANSITION_V15_MODEL_HISTORY_DRIFT")
                frozen = [dict(r) for r in self.conn.execute(
                    "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                    "FROM tasks ORDER BY ticket")]
                event["v14_terminal_event_sha256"] = prior_rows[0]["sha"]
                event["terminal_tasks_sha256"] = hash_bytes(canonical(frozen))
                event["model_history_sha256"] = hash_bytes(canonical(model))
                event["v2_receipt_authorized"] = False
            if schema == "forge.f139.source-transition.v16":
                prior_rows = [r for r in self.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"]).get("schema") ==
                       "forge.f139.source-transition.v15"]
                require(len(prior_rows) == 1,
                        "SOURCE_TRANSITION_V16_V15_SEAL_MISSING")
                model = [dict(r) for r in self.conn.execute(
                    "SELECT kind,sha FROM events WHERE kind IN "
                    "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                    "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                    "'FREE_REASONER_ATTEMPTED') ORDER BY seq")]
                kinds = {name: sum(r["kind"] == name for r in model)
                         for name in ("G3_DRAFT_ATTEMPTED",
                                      "G3_DRAFT_AUTHENTICATED",
                                      "MODEL_DRAFT_ATTEMPTED",
                                      "MODEL_DRAFT_AUTHENTICATED",
                                      "FREE_REASONER_ATTEMPTED")}
                require(kinds["G3_DRAFT_ATTEMPTED"] == 1
                        and kinds["G3_DRAFT_AUTHENTICATED"] == 1
                        and kinds["MODEL_DRAFT_ATTEMPTED"] == 2
                        and kinds["MODEL_DRAFT_AUTHENTICATED"] == 2
                        and kinds["FREE_REASONER_ATTEMPTED"] == 1,
                        "SOURCE_TRANSITION_V16_MODEL_HISTORY_DRIFT")
                frozen = [dict(r) for r in self.conn.execute(
                    "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                    "FROM tasks ORDER BY ticket")]
                event["v15_terminal_event_sha256"] = prior_rows[0]["sha"]
                event["terminal_tasks_sha256"] = hash_bytes(canonical(frozen))
                event["model_history_sha256"] = hash_bytes(canonical(model))
                event["v2_receipt_authorized"] = False
            if schema == "forge.f139.source-transition.v17":
                prior_rows = [r for r in self.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                    if json.loads(r["payload"]).get("schema") ==
                       "forge.f139.source-transition.v16"]
                require(len(prior_rows) == 1,
                        "SOURCE_TRANSITION_V17_V16_SEAL_MISSING")
                model = [dict(r) for r in self.conn.execute(
                    "SELECT kind,sha FROM events WHERE kind IN "
                    "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED',"
                    "'MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED',"
                    "'FREE_REASONER_ATTEMPTED') ORDER BY seq")]
                kinds = {name: sum(r["kind"] == name for r in model)
                         for name in ("G3_DRAFT_ATTEMPTED",
                                      "G3_DRAFT_AUTHENTICATED",
                                      "MODEL_DRAFT_ATTEMPTED",
                                      "MODEL_DRAFT_AUTHENTICATED",
                                      "FREE_REASONER_ATTEMPTED")}
                require(v17_original_model_history_valid(kinds),
                        "SOURCE_TRANSITION_V17_MODEL_HISTORY_DRIFT")
                frozen = [dict(r) for r in self.conn.execute(
                    "SELECT ticket,stage,run_id,evidence_sha,source_sha "
                    "FROM tasks ORDER BY ticket")]
                event["v16_terminal_event_sha256"] = prior_rows[0]["sha"]
                event["terminal_tasks_sha256"] = hash_bytes(canonical(frozen))
                event["model_history_sha256"] = hash_bytes(canonical(model))
                event["v2_receipt_authorized"] = False
            self.event("SOURCE_TRANSITION_ADMITTED", event)
            self.verify()

    def enqueue(self, tasks: list[dict], freeze_sha: str):
        require(re.fullmatch(r"[a-f0-9]{64}",freeze_sha) is not None, "MANIFEST_HASH_UNQUALIFIED")
        meta=self.meta()
        require(meta["enabled"]==0 and isinstance(tasks,list) and 1<=len(tasks)<=100,"QUEUE_MANIFEST_LOCKED")
        seen=set()
        with self.transaction():
            for item in tasks:
                require(isinstance(item,dict) and set(item)=={"ticket","lane","source_sha"},"TASK_FIELDS_UNQUALIFIED")
                ticket,lane,source=item["ticket"],item["lane"],item["source_sha"]
                require(isinstance(ticket,str) and TICKET.fullmatch(ticket) and ticket not in seen and lane in LANES
                        and source==meta["source_sha"],"TASK_UNQUALIFIED_OR_DUPLICATE")
                seen.add(ticket)
                self.conn.execute("INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,'READY',?)",
                                  (ticket,lane,source,freeze_sha))
                self.event("TASK_INTAKE",{"ticket":ticket,"lane":lane,"manifest_sha":freeze_sha})

    def admit_d2j_succession(self):
        """One source-frozen two-ticket tranche after the authentic D2I history.

        This is a finite development successor, NOT a general science originator
        or permission to enroll tasks from untrusted GitHub issues.
        Caller must hold SingleOwner and verify protected main before invoking.
        """
        with self.transaction():
            self.verify()
            meta = self.meta()
            if meta["head_seq"] != 14:
                return False
            require(meta["enabled"] == 1 and meta["legacy_suspended"] == 1,
                    "D2J_OWNER_NOT_ENABLED")
            history = list(self.conn.execute("SELECT kind FROM events ORDER BY seq"))
            require(len(history) == 14 and
                    [row["kind"] for row in history[9:11]] ==
                    ["QUARANTINE_ORIGINAL_RECONCILED"] * 2 and
                    [row["kind"] for row in history[11:14]] ==
                    ["SOURCE_TRANSITION_ADMITTED"] * 3,
                    "D2J_FROZEN_EVENT_HISTORY_DRIFT")
            original = {row["ticket"]: dict(row) for row in
                        self.conn.execute("SELECT * FROM tasks")}
            require(set(original) == set(D2J_FROZEN_ORIGINALS),
                    "D2J_FROZEN_TASK_SET_DRIFT")
            for ticket, (lane, run_id) in D2J_FROZEN_ORIGINALS.items():
                row = original[ticket]
                require(row["lane"] == lane and row["stage"] == "VERIFIED"
                        and row["run_id"] == run_id
                        and row["source_sha"] != meta["source_sha"]
                        and row["evidence_dir"] and row["evidence_sha"]
                        and row["quarantine_reason"] == "PROVIDER_SOURCE_EVENT_SPOOFED",
                        "D2J_ORIGINAL_CUSTODY_NOT_QUALIFIED")
            manifest = d2j_plan(meta["source_sha"], meta["head_hash"])
            tickets = [item["ticket"] for item in manifest["tasks"]]
            digest = hash_bytes(canonical(manifest))
            self.event("UNATTENDED_SUCCESSION_ADMITTED", {
                "schema": manifest["schema"], "source_sha":meta["source_sha"],
                "prior_event_head_sha256": meta["head_hash"],
                "manifest_sha256": digest, "tickets": tickets,
                "new_dispatches": 0, "scientific_first_use": False,
            })
            for item in manifest["tasks"]:
                self.conn.execute(
                    "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
                    "VALUES(?,?,?,'READY',?)",
                    (item["ticket"],item["lane"],item["source_sha"],digest))
                self.event("TASK_INTAKE", {
                    "ticket": item["ticket"], "lane":item["lane"],"manifest_sha":digest})
            self.verify()
            return True

    def admit_d2k_issue(self, issue: dict):
        """Atomic issue-bound work intake: never interpret free-form issue text."""
        self.verify()
        meta = self.meta()
        require(meta["enabled"] == 1 and meta["legacy_suspended"] == 1,
                "D2K_OWNER_NOT_ACTIVE")
        # This source extension may run only after the original D2C and
        # successful D2J local four-receipt custody, never on an empty DB.
        verified = {
            row["ticket"]:row for row in self.conn.execute(
                "SELECT ticket,stage,run_id,evidence_sha FROM tasks")
        }
        authenticated = {
            name: row for name,row in verified.items()
            if name.startswith("f139-d2j-") or name.startswith("f139-d2c-")
        }
        require(meta["head_seq"] >= 23
                and len(authenticated) == 4
                and all(t["stage"]=="VERIFIED" and t["run_id"] is not None
                        and t["evidence_sha"] is not None
                        for t in authenticated.values())
                and sum(name.startswith("f139-d2j-") for name in authenticated) == 2
                and sum(name.startswith("f139-d2c-") for name in authenticated) == 2,
                "D2K_AUTHENTIC_SUCCESSION_REQUIRED")
        require(isinstance(issue, dict) and set(issue) == {
                    "ticket", "issue_number", "issue_id", "source_sha",
                    "lane", "kind", "target_package", "body_sha256"
                } and issue["source_sha"] == meta["source_sha"]
                and issue["lane"] in LANES and issue["kind"] == D2K_KIND
                and issue["target_package"] in D2K_ALLOWED_PACKAGES,
                "D2K_ISSUE_IDENTITY_INVALID")
        ticket = issue["ticket"]
        require(isinstance(ticket, str) and TICKET.fullmatch(ticket)
                and ticket == "f139-d2k-i" + str(issue["issue_number"]) + "-" +
                  meta["source_sha"][:12] + "-" + issue["body_sha256"][:8], "D2K_TICKET_IDENTITY_INVALID")
        with self.transaction():
            self.verify()
            require(self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
                    < D2K_MAX_TOTAL, "D2K_WORK_TOTAL_LIMIT")
            today = utc_now()[:10]
            rows = self.conn.execute(
                "SELECT payload FROM events WHERE kind='DEVELOPMENT_WORK_ADMITTED'")
            admitted_today = sum(
                json.loads(row["payload"])["admitted_day"] == today
                for row in rows)
            require(admitted_today < D2K_MAX_DAILY,"D2K_DAILY_ADMISSION_LIMIT")
            exists = self.conn.execute("SELECT 1 FROM tasks WHERE ticket=?",
                                       (ticket,)).fetchone()
            already_admitted = any(
                json.loads(row["payload"])["issue_id"] == issue["issue_id"]
                or json.loads(row["payload"])["issue_number"] == issue["issue_number"]
                for row in self.conn.execute(
                    "SELECT payload FROM events WHERE kind='DEVELOPMENT_WORK_ADMITTED'")
            )
            if exists is not None or already_admitted:
                return False
            require(self.active() is None and self.ready() is None,
                    "D2K_PENDING_WORK_NOT_EMPTY")
            prior = meta["head_hash"]
            manifest = {
                "schema":"forge.f139.d2k.issue-work.v1",
                "source_sha":meta["source_sha"], "ticket":ticket,
                "issue_number":issue["issue_number"], "issue_id":issue["issue_id"],
                "lane":issue["lane"], "kind":issue["kind"],
                "target_package":issue["target_package"],
                "body_sha256":issue["body_sha256"],
                "prior_event_head_sha256":prior,
                "admitted_day":today, "scientific_first_use":False,
            }
            digest = hash_bytes(canonical(manifest))
            self.event("DEVELOPMENT_WORK_ADMITTED", {
                **manifest, "manifest_sha256":digest
            })
            self.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) "
                "VALUES(?,?,?,'READY',?)",
                (ticket,issue["lane"],meta["source_sha"],digest))
            self.event("TASK_INTAKE", {
                "ticket":ticket,"lane":issue["lane"],"manifest_sha":digest})
            self.verify()
            return True

    def d2k_fields(self, ticket: str):
        """Recover worker identity only from the immutable, verified admission event."""
        if not ticket.startswith("f139-d2k-"):
            return None
        rows = [json.loads(row["payload"]) for row in self.conn.execute(
            "SELECT payload FROM events WHERE kind='DEVELOPMENT_WORK_ADMITTED'")]
        matches = [r for r in rows if r.get("ticket")==ticket]
        require(len(matches)==1, "D2K_ADMISSION_RECORD_MISSING_OR_DUPLICATE")
        r=matches[0]
        require(r["kind"]==D2K_KIND and r["target_package"] in D2K_ALLOWED_PACKAGES,
                "D2K_ADMISSION_KIND_DRIFT")
        return {"issue_number":str(r["issue_number"]), "issue_id":str(r["issue_id"]),
                "body_sha256":r["body_sha256"],"target_package":r["target_package"]}

    def actives(self):
        # Multiple provider tickets, ONE original owner mutex and SQLite log.
        return list(self.conn.execute(
            "SELECT * FROM tasks WHERE stage IN ('START_RISK','WAIT_PROVIDER') "
            "ORDER BY started_at,ticket LIMIT 3"))

    def active(self):
        return self.actives()[0] if self.actives() else None

    def ready(self):
        return self.conn.execute("SELECT * FROM tasks WHERE stage='READY' ORDER BY ticket LIMIT 1").fetchone()

    def claim(self, ticket: str, now: str):
        day = now[:10]
        with self.transaction():
            m = self.meta()
            require(m["enabled"]==1 and m["legacy_suspended"]==1,"CONTROLLER_INACTIVE")
            starts = m["starts"] if m["day"]==day else 0
            require(starts<LIMIT_PER_DAY,"DAILY_START_LIMIT")
            in_flight = self.actives()
            native = ticket.startswith("f139-nci04-")
            require((self.dual_native_schema()
                     and len(in_flight) < 2 and
                     all(r["ticket"].startswith("f139-nci04-")
                         for r in in_flight)) if native and in_flight
                     else not in_flight,
                    "CONCURRENT_ACTIVE_START_RISK")
            row=self.conn.execute("SELECT * FROM tasks WHERE ticket=?",(ticket,)).fetchone()
            require(row is not None and row["stage"]=="READY", "TASK_ALREADY_CLAIMED")
            if ticket.startswith("f139-nci04-"):
                from f139.nci04_owner_ledger import (
                    native_recent_starts, MAX_STARTS_PER_WINDOW)
                require(native_recent_starts(self, now) < MAX_STARTS_PER_WINDOW,
                        "NATIVE_TWO_PER_TEN_MINUTES_LIMIT")
            self.conn.execute("UPDATE tasks SET stage='START_RISK',started_at=? WHERE ticket=?",(now,ticket))
            self.conn.execute("UPDATE meta SET starts=?,day=? WHERE id=1",(starts+1,day))
            self.event("BEFORE_DISPATCH_INTENT",{"ticket":ticket,"started_at":now,"starts":starts+1})

    def dispatch_observed(self,ticket: str):
        with self.transaction():
            row=self.conn.execute("SELECT stage FROM tasks WHERE ticket=?",(ticket,)).fetchone()
            require(row and row["stage"]=="START_RISK","DISPATCH_STATE_DRIFT")
            self.conn.execute("UPDATE tasks SET stage='WAIT_PROVIDER' WHERE ticket=?",(ticket,))
            self.event("DISPATCH_POST_RETURNED",{"ticket":ticket})

    def custody_failed_native_provider(self, ticket: str, report: dict, *,
                                      late: bool = False):
        """Durably bind one authentic failed native provider attempt, never replay."""
        require(isinstance(ticket,str) and ticket.startswith("f139-nci04-")
                and TICKET.fullmatch(ticket) is not None
                and isinstance(report,dict)
                and set(report)=={"ticket","run_id","source_sha","jobs",
                                  "artifact_ids","provider_terminal",
                                  "scientific_first_use"}
                and report["ticket"]==ticket
                and type(report["run_id"]) is int and report["run_id"]>0
                and isinstance(report["source_sha"],str)
                and SHA.fullmatch(report["source_sha"]) is not None
                and report["provider_terminal"]=="FAILURE_NO_REPLAY"
                and report["scientific_first_use"] is False,
                "FAILED_PROVIDER_REPORT_INVALID")
        jobs=report["jobs"]
        require(isinstance(jobs,dict)
                and set(jobs)=={"windows-latest","ubuntu-latest"}
                and all(isinstance(jobs[name],dict)
                        and set(jobs[name])=={"job_id","conclusion"}
                        and type(jobs[name]["job_id"]) is int
                        and jobs[name]["job_id"]>0
                        and jobs[name]["conclusion"] in ("success","failure")
                        for name in jobs)
                and any(jobs[name]["conclusion"]=="failure" for name in jobs)
                and isinstance(report["artifact_ids"],list)
                and report["artifact_ids"]==sorted(set(report["artifact_ids"]))
                and all(type(x) is int and x>0 for x in report["artifact_ids"]),
                "FAILED_PROVIDER_OS_OR_ARTIFACT_INVALID")
        with self.transaction():
            self.verify()
            row=self.conn.execute(
                "SELECT stage,source_sha,quarantine_reason FROM tasks WHERE ticket=?",
                (ticket,)).fetchone()
            require(row is not None and row["source_sha"]==report["source_sha"],
                    "FAILED_PROVIDER_TASK_SOURCE_DRIFT")
            existing=[
                json.loads(r["payload"]) for r in self.conn.execute(
                    "SELECT payload FROM events WHERE kind='NATIVE_FAILED_PROVIDER_CUSTODY'")
                if json.loads(r["payload"]).get("ticket")==ticket]
            require(not existing,"FAILED_PROVIDER_ALREADY_CUSTODIED")
            payload={
                "schema":"forge.f139.owner-native-provider-negative.v2"
                    if late else "forge.f139.owner-native-provider-negative.v1",
                "ticket":ticket,"run_id":report["run_id"],
                "source_sha":report["source_sha"],
                "provider_sha256":hash_bytes(canonical(report)),
                "provider":report,"scientific_first_use":False,
            }
            if late:
                require(row["stage"]=="QUARANTINED"
                        and row["quarantine_reason"]=="FAILED_OR_CANCELLED_NO_REPLAY",
                        "LATE_PROVIDER_CUSTODY_TASK_NOT_QUARANTINED")
                matches=[]
                for q in self.conn.execute(
                        "SELECT seq,sha,payload FROM events "
                        "WHERE kind='ATTEMPT_QUARANTINED' ORDER BY seq"):
                    qp=json.loads(q["payload"])
                    if qp=={"ticket":ticket,
                            "reason":"FAILED_OR_CANCELLED_NO_REPLAY"}:
                        matches.append(q)
                require(len(matches)==1,"LATE_PROVIDER_QUARANTINE_EVENT_AMBIGUOUS")
                payload["quarantine_event_seq"]=matches[0]["seq"]
                payload["quarantine_event_sha256"]=matches[0]["sha"]
                self.event("NATIVE_FAILED_PROVIDER_CUSTODY",payload)
            else:
                require(row["stage"] in ("START_RISK","WAIT_PROVIDER"),
                        "FAILED_PROVIDER_TASK_NOT_ACTIVE")
                self.event("NATIVE_FAILED_PROVIDER_CUSTODY",payload)
                self.conn.execute(
                    "UPDATE tasks SET stage='QUARANTINED',quarantine_reason=? "
                    "WHERE ticket=?",("FAILED_OR_CANCELLED_NO_REPLAY",ticket))
                self.event("ATTEMPT_QUARANTINED",{
                    "ticket":ticket,"reason":"FAILED_OR_CANCELLED_NO_REPLAY"})
            self.verify()
        return True

    def terminal(self,ticket: str,run_id:int,evidence_dir:str,evidence_sha:str):
        require(run_id>0 and SHA.fullmatch(self.meta()["source_sha"]) and
                re.fullmatch(r"[a-f0-9]{64}",evidence_sha),"TERMINAL_PROOF_INVALID")
        with self.transaction():
            row=self.conn.execute("SELECT stage,run_id FROM tasks WHERE ticket=?",(ticket,)).fetchone()
            require(row and row["stage"] in ("START_RISK","WAIT_PROVIDER"),"TERMINAL_ALREADY_RECORDED")
            self.conn.execute("UPDATE tasks SET stage='VERIFIED',run_id=?,evidence_dir=?,evidence_sha=?,completed_at=? WHERE ticket=?",
                              (run_id,evidence_dir,evidence_sha,utc_now(),ticket))
            self.event("PROVIDER_VERIFIED_TERMINAL",{"ticket":ticket,"run_id":run_id,"evidence_sha":evidence_sha})

    def quarantine(self,ticket:str,reason:str):
        require(isinstance(reason,str) and re.fullmatch(r"[A-Z_]{3,72}",reason),"REASON_INVALID")
        with self.transaction():
            row=self.conn.execute("SELECT stage FROM tasks WHERE ticket=?",(ticket,)).fetchone()
            require(row and row["stage"] in ("START_RISK","WAIT_PROVIDER"),"QUARANTINE_STAGE_INVALID")
            self.conn.execute("UPDATE tasks SET stage='QUARANTINED',quarantine_reason=? WHERE ticket=?",(reason,ticket))
            self.event("ATTEMPT_QUARANTINED",{"ticket":ticket,"reason":reason})

    def status(self):
        self.verify()
        return {"meta":self.meta(),"tasks":[dict(x) for x in self.conn.execute("SELECT * FROM tasks ORDER BY ticket")]}


class GitHub:
    def __init__(self, runner=None):
        self.runner=runner or self._command

    @staticmethod
    def _command(args):
        require(shutil.which("gh") is not None,"GITHUB_CLI_NOT_INSTALLED")
        try:
            p=subprocess.run(["gh","api",*args],check=False,stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40)
        except subprocess.TimeoutExpired as exc:
            raise F139Error("F139_GITHUB_API_TIMEOUT") from exc
        require(p.returncode==0 and len(p.stdout)<MAX_ZIP_BYTES+100000, "GITHUB_API_FAILED")
        return p.stdout

    def get(self,route:str):
        require(route.startswith("repos/"+REPO+"/") and ".." not in route and " " not in route,
                "GITHUB_ROUTE_INVALID")
        raw=self.runner([route])
        try:
            return json.loads(raw)
        except (ValueError,UnicodeDecodeError) as exc:
            raise F139Error("F139_GITHUB_API_INVALID_JSON") from exc

    def native_repo_get(self, route: str):
        """Read-only provider for the bounded native autonomy feeder."""
        allowed = (
            "repos/"+REPO+"/",
            "repos/spoonman136668-ai/Wingless/",
            "repos/spoonman136668-ai/Yggdrasil/",
        )
        require(isinstance(route, str) and route.startswith(allowed)
                and "/../" not in route and not route.endswith("/..")
                and "\\" not in route and " " not in route
                and not route.startswith(("http://", "https://")),
                "NATIVE_FEED_ROUTE_INVALID")
        raw = self.runner([route])
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise F139Error("F139_GITHUB_API_INVALID_JSON") from exc

    def prepare_native_feed(self, source_sha: str,
                            existing_candidate_identities: set[str]):
        from f139.nci04_autonomy_feed import prepare_feed
        return prepare_feed(
            self.native_repo_get, source_sha=source_sha,
            existing_candidate_identities=existing_candidate_identities,
            steering_get=self.native_repo_get)

    def create_native_feed_issue(self, *, title: str, body: str):
        """Create an ordinary existing-schema owner issue; never dispatch here."""
        from f139.nci04_owner_issue import LABEL, OWNER, MAX_BODY_BYTES
        require(isinstance(title, str) and title.startswith("F139 auto-feed ")
                and 0 < len(title) <= 180
                and isinstance(body, str)
                and 0 < len(body.encode("utf-8")) <= MAX_BODY_BYTES,
                "NATIVE_FEED_ISSUE_PAYLOAD_INVALID")
        raw = self.runner([
            "--method", "POST", "repos/"+REPO+"/issues",
            "-f", "title="+title, "-f", "body="+body,
            "-f", "labels[]="+LABEL,
        ])
        try:
            issue = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise F139Error("F139_GITHUB_API_INVALID_JSON") from exc
        require(isinstance(issue, dict) and issue.get("state") == "open"
                and isinstance(issue.get("number"), int)
                and isinstance(issue.get("id"), int)
                and isinstance(issue.get("user"), dict)
                and issue["user"].get("login") == OWNER
                and issue.get("author_association") == "OWNER"
                and issue.get("body") == body
                and LABEL in [x.get("name") for x in issue.get("labels", [])
                              if isinstance(x, dict)],
                "NATIVE_FEED_CREATED_ISSUE_UNVERIFIED")
        return issue

    def owner_g3_write(self, method: str, route: str, payload: dict):
        """Three exact Yggdrasil draft-only write endpoints; no generic writer.

        Used ONLY by the original lock-held Windows owner. No automatic retry
        after an ambiguous remote write; the SQLite attempt event precedes it.
        """
        repo = "repos/spoonman136668-ai/Yggdrasil"
        branch = re.compile(r"f139/auto-g2-ygg-[a-f0-9]{12}-[a-f0-9]{12}\Z")
        if method == "POST" and route == repo + "/git/refs":
            require(isinstance(payload, dict) and set(payload) == {"ref", "sha"}
                    and isinstance(payload["ref"], str)
                    and payload["ref"].startswith("refs/heads/")
                    and branch.fullmatch(payload["ref"][11:]) is not None
                    and isinstance(payload["sha"], str)
                    and SHA.fullmatch(payload["sha"]) is not None,
                    "G3_REF_WRITE_NOT_BOUNDED")
        elif method == "PUT" and route == repo + "/contents/yggdrasil/public_causal_cells.py":
            require(isinstance(payload, dict) and set(payload) ==
                    {"message", "content", "sha", "branch"}
                    and isinstance(payload["branch"], str)
                    and branch.fullmatch(payload["branch"]) is not None
                    and isinstance(payload["sha"], str)
                    and SHA.fullmatch(payload["sha"]) is not None
                    and isinstance(payload["content"], str)
                    and 0 < len(payload["content"]) <= 50000
                    and payload["message"] in {
                        "F139 G2 DEV: bounded source-only public causal mechanism"},
                    "G3_CONTENT_WRITE_NOT_BOUNDED")
        elif method == "POST" and route == repo + "/pulls":
            require(isinstance(payload, dict) and set(payload) ==
                    {"title", "head", "base", "draft", "body"}
                    and payload["draft"] is True and payload["base"] == "main"
                    and payload["title"] ==
                    "F139 autonomy DEV: local evidence confidence gating"
                    and isinstance(payload["head"], str)
                    and branch.fullmatch(payload["head"]) is not None
                    and isinstance(payload["body"], str)
                    and 0 < len(payload["body"]) < 4000,
                    "G3_DRAFT_WRITE_NOT_BOUNDED")
        else:
            raise F139Error("F139_G3_WRITE_ENDPOINT_FORBIDDEN")
        require(shutil.which("gh") is not None, "GITHUB_CLI_NOT_INSTALLED")
        try:
            p = subprocess.run(
                ["gh", "api", "--method", method, route, "--input", "-"],
                input=canonical(payload), stdin=None, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=40, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise F139Error("F139_G3_WRITE_AMBIGUOUS_NO_RETRY") from exc
        require(p.returncode == 0 and 0 < len(p.stdout) < 100000,
                "G3_WRITE_AMBIGUOUS_NO_RETRY")
        try:
            return json.loads(p.stdout)
        except (ValueError, UnicodeDecodeError) as exc:
            raise F139Error("F139_G3_WRITE_RESPONSE_AMBIGUOUS_NO_RETRY") from exc

    def owner_model_write(self, method: str, route: str, payload: dict):
        """Narrow original-owner GitHub transport for source-only model drafts.

        Only the external original SingleOwner-locked publication function may
        call this. Nothing invokes it in run_once or from GitHub Actions.
        The original SHA-chained model attempt must be durable before any
        invocation. A failed or ambiguous API call is never retried.
        """
        from f139.nci04_native_contract import REPOS, model_source_path_allowed
        from f139.nci04_model_owner_publication import BRANCH
        require(type(payload) is dict, "MODEL_WRITE_PAYLOAD_INVALID")
        lane = None
        repo = None
        for candidate, (full, prefixes, suffix) in REPOS.items():
            stem = "repos/" + full
            if route.startswith(stem + "/"):
                lane, repo = candidate, stem
                break
        require(lane is not None and repo is not None,
                "MODEL_WRITE_TARGET_REPOSITORY_FORBIDDEN")
        indicator = "w" if lane == "Wingless" else "y"
        def branch_ok(value):
            return (isinstance(value, str) and
                    BRANCH.fullmatch(value) is not None and
                    value.startswith("f139/auto-model-" + indicator + "-"))
        if method == "POST" and route == repo + "/git/refs":
            require(set(payload) == {"ref", "sha"}
                    and isinstance(payload["ref"], str)
                    and payload["ref"].startswith("refs/heads/")
                    and branch_ok(payload["ref"][11:])
                    and isinstance(payload["sha"], str)
                    and SHA.fullmatch(payload["sha"]) is not None,
                    "MODEL_REF_WRITE_FORBIDDEN")
        elif method == "PUT" and route.startswith(repo + "/contents/"):
            path = route[len(repo + "/contents/"):]
            prefixes, suffix = REPOS[lane][1:]
            require(set(payload) == {"message", "content", "sha", "branch"}
                    and isinstance(path, str)
                    and model_source_path_allowed(lane, path)
                    and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}", path)
                        is not None
                    and all(x not in ("", ".", "..") and not x.startswith(".")
                            for x in path.split("/"))
                    and branch_ok(payload["branch"])
                    and payload["message"] ==
                        "F139 MODEL DEV: owner-validated isolated source candidate"
                    and isinstance(payload["sha"], str)
                    and SHA.fullmatch(payload["sha"]) is not None
                    and isinstance(payload["content"], str)
                    and 0 < len(payload["content"]) <= 50000,
                    "MODEL_SOURCE_WRITE_FORBIDDEN")
            try:
                decoded = base64.b64decode(payload["content"], validate=True)
                decoded.decode("utf-8", "strict")
            except (ValueError, UnicodeError, binascii.Error) as exc:
                raise F139Error("F139_MODEL_SOURCE_ENCODING_FORBIDDEN") from exc
            require(0 < len(decoded) <= 32768 and b"\x00" not in decoded
                    and base64.b64encode(decoded).decode("ascii") ==
                        payload["content"], "MODEL_SOURCE_BYTES_FORBIDDEN")
        elif method == "POST" and route == repo + "/pulls":
            require(set(payload) == {"title", "head", "base", "draft", "body"}
                    and payload["draft"] is True
                    and payload["base"] == "main"
                    and branch_ok(payload["head"])
                    and isinstance(payload["title"], str)
                    and re.fullmatch(
                        r"F139 autonomy DEV: bounded " + lane +
                        r" learning proposal [a-f0-9]{12}", payload["title"])
                        is not None
                    and isinstance(payload["body"], str)
                    and 0 < len(payload["body"].encode("utf-8")) <= 4000,
                    "MODEL_DRAFT_WRITE_FORBIDDEN")
            try:
                note = json.loads(payload["body"])
            except (ValueError, UnicodeError) as exc:
                raise F139Error("F139_MODEL_DRAFT_BODY_INVALID") from exc
            require(type(note) is dict
                    and note.get("schema") ==
                        "forge.f139.owner-model-draft-note.v1"
                    and note.get("scientific_first_use") is False
                    and note.get("dispatch_authorized") is False
                    and note.get("independent_scientific_acceptance") is False
                    and isinstance(note.get("candidate_identity"), str)
                    and re.fullmatch(r"[a-f0-9]{64}",
                                     note["candidate_identity"]) is not None
                    and payload["head"].split("-")[-2] ==
                        note["candidate_identity"][:20],
                    "MODEL_DRAFT_AUTHORITY_OR_IDENTITY_DRIFT")
        else:
            raise F139Error("F139_MODEL_WRITE_ENDPOINT_FORBIDDEN")
        require(shutil.which("gh") is not None, "GITHUB_CLI_NOT_INSTALLED")
        try:
            result = subprocess.run(
                ["gh", "api", "--method", method, route, "--input", "-"],
                input=canonical(payload), stdin=None, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=40, check=False)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise F139Error("F139_MODEL_WRITE_AMBIGUOUS_NO_RETRY") from exc
        require(result.returncode == 0 and 0 < len(result.stdout) < 100000,
                "MODEL_WRITE_AMBIGUOUS_NO_RETRY")
        try:
            return json.loads(result.stdout)
        except (ValueError, UnicodeDecodeError) as exc:
            raise F139Error("F139_MODEL_WRITE_RESPONSE_AMBIGUOUS_NO_RETRY") from exc

    def protected_main(self):
        branch=self.get("repos/"+REPO+"/branches/main")
        sha=branch.get("commit",{}).get("sha")
        require(isinstance(sha,str) and SHA.fullmatch(sha) and branch.get("protected") is True,
                "MAIN_IDENTITY_OR_PROTECTION_NOT_VERIFIED")
        return sha

    def research_only_main_advance(self, deployed_source: str,
                                   protected_source: str) -> bool:
        """Do not release whole-repository SHA pin for arbitrary merges.

        Permit only independently authenticated forward changes to isolated
        RSH research evidence files; runtime, workflows, secrets and workers
        remain pinned at the original immutable controller source.
        """
        from f139.nci04_source_continuity import (
            SourceContinuityDenied, prove_protected_research_only_advance)
        try:
            proof=prove_protected_research_only_advance(
                self.native_repo_get, deployed_source=deployed_source,
                protected_source=protected_source)
            return proof["runtime_source_unchanged"] is True
        except SourceContinuityDenied:
            return False

    def deployed_release_continuity(self, db, deployed_source: str,
                                    protected_source: str) -> bool:
        """Keep a certified native owner operating across unrelated merges.

        Protected main may advance; no newly merged code executes until an
        explicit original-owner source-transition with authentic ledger seal.
        The existing task, ledger and signed #807 owner policy remain pinned.
        """
        from f139.nci04_release_pin_continuity import (
            ReleaseContinuityDenied, prove_deployed_release_pin)
        from f139.nci04_owner_ledger import verify_native_activation
        try:
            db.verify()
            meta = db.meta()
            if (meta["source_sha"] != deployed_source
                    or not verify_native_activation(db)):
                return False
            root = Path(__file__).resolve().parent.parent
            def git(*args):
                p = subprocess.run(
                    ["git", "-C", str(root), *args],
                    capture_output=True, stdin=subprocess.DEVNULL,
                    timeout=15, check=False)
                if p.returncode != 0:
                    raise F139Error("F139_RELEASE_PIN_LOCAL_GIT_FAILED")
                return p.stdout.decode("utf-8").strip()
            if (git("rev-parse", "HEAD") != deployed_source
                    or git("status", "--porcelain", "--untracked-files=all")):
                return False
            evidence = prove_deployed_release_pin(
                self.native_repo_get,
                deployed_source=deployed_source,
                protected_source=protected_source)
            return evidence["existing_owner_policy_authorized"] is True
        except (F139Error, ReleaseContinuityDenied, ValueError,
                KeyError, TypeError, OSError, subprocess.TimeoutExpired):
            return False

    def legacy_dispatchers_disabled(self):
        """Read authoritative GitHub workflow states; no administrative mutation."""
        for name in ("forge-development-succession.yml", "forge-integrated-synthetic-cycle.yml"):
            workflow=self.get(f"repos/{REPO}/actions/workflows/{name}")
            require(workflow.get("state")=="disabled_manually" and workflow.get("path")==".github/workflows/"+name,
                    "LEGACY_GITHUB_DISPATCHER_STILL_ENABLED")
            history=self.get(f"repos/{REPO}/actions/workflows/{name}/runs?per_page=100")
            runs=history.get("workflow_runs")
            require(isinstance(runs,list) and isinstance(history.get("total_count"),int),
                    "LEGACY_RUN_HISTORY_UNVERIFIED")
            require(not any(x.get("status") in ("queued","in_progress","requested","waiting","pending")
                            for x in runs),"LEGACY_DISPATCH_STILL_IN_FLIGHT")
        return True

    def d2k_eligible_issues(self, source: str) -> list[dict]:
        """Authenticated owner-labeled, source-bound, fixed-kind issue catalog.

        The issue body is only declarative data. It cannot supply commands,
        source paths, arbitrary prompts, or science authorization.
        """
        require(isinstance(source,str) and SHA.fullmatch(source) is not None,
                "D2K_SOURCE_INVALID")
        accepted = []
        for page in (1, 2):
            items = self.get(
                "repos/" + REPO + "/issues?state=open&labels=" +
                D2K_WORK_LABEL + "&per_page=100&page=" + str(page))
            require(isinstance(items,list) and len(items)<=100,
                    "D2K_ISSUE_INDEX_INVALID")
            for raw in items:
                require(isinstance(raw,dict) and raw.get("state") == "open"
                        and "pull_request" not in raw
                        and isinstance(raw.get("number"),int) and raw["number"]>0
                        and isinstance(raw.get("id"),int) and raw["id"]>0
                        and isinstance(raw.get("user"),dict)
                        and raw["user"].get("login") == D2K_OWNER
                        and raw.get("author_association") == "OWNER"
                        and D2K_WORK_LABEL in [x.get("name") for x in
                                               raw.get("labels",[]) if isinstance(x,dict)],
                        "D2K_ISSUE_NOT_OWNER_QUALIFIED")
                body = raw.get("body")
                require(isinstance(body,str) and len(body)<2048,
                        "D2K_ISSUE_BODY_INVALID")
                try:
                    record=json.loads(body)
                except ValueError as exc:
                    raise F139Error("F139_D2K_ISSUE_NOT_JSON") from exc
                require(isinstance(record,dict) and set(record)=={
                    "schema","source_sha","lane","kind","target_package",
                    "scientific_first_use","paid_model_calls"
                } and record["schema"]=="forge.f139.d2k.owner-development.v1"
                    and record["source_sha"]==source
                    and record["lane"] in LANES
                    and record["kind"]==D2K_KIND
                    and record["target_package"] in D2K_ALLOWED_PACKAGES
                    and record["scientific_first_use"] is False
                    and type(record["paid_model_calls"]) is int
                    and record["paid_model_calls"]==0,
                    "D2K_ISSUE_POLICY_INVALID")
                accepted.append({
                    "ticket":"f139-d2k-i"+str(raw["number"])+"-"+source[:12]+
                             "-"+hash_bytes(canonical(record))[:8],
                    "issue_number":raw["number"],"issue_id":raw["id"],
                    "source_sha":source,"lane":record["lane"],
                    "kind":D2K_KIND, "target_package":record["target_package"],
                    "body_sha256":hash_bytes(canonical(record)),
                })
            if len(items)<100:
                break
        else:
            raise F139Error("F139_D2K_ISSUE_CATALOG_TRUNCATED")
        require(len({x["ticket"] for x in accepted})==len(accepted)
                and len({x["issue_id"] for x in accepted})==len(accepted),
                "D2K_DUPLICATE_ISSUE_IDENTITY")
        return sorted(accepted,key=lambda x:x["issue_number"])

    def native_eligible_issues(self, source: str, *,
                               historical_issues: dict | None = None):
        """Read-only authenticated issue catalog, including frozen history.

        Reverify immutable historical issue identities at their ORIGINAL
        source, then exclude only those exact already-admitted issues from
        new-source eligibility. Unknown stale/mutated issues fail closed.
        """
        from f139.nci04_owner_issue import (
            LABEL, OWNER, inspect_owner_issue, NativeIssueDenied)
        from f139.nci04_native_contract import NativeContractError
        require(isinstance(source,str) and SHA.fullmatch(source) is not None,
                "NATIVE_SOURCE_INVALID")
        historical_issues = {} if historical_issues is None else historical_issues
        require(isinstance(historical_issues, dict)
                and all(type(number) is int and type(identity) is tuple
                        and len(identity) == 4 and type(identity[0]) is int
                        and isinstance(identity[1], str) and SHA.fullmatch(identity[1])
                        and isinstance(identity[2], str)
                        and re.fullmatch(r"[a-f0-9]{64}", identity[2])
                        and isinstance(identity[3], str) and TICKET.fullmatch(identity[3])
                        for number, identity in historical_issues.items()),
                "NATIVE_HISTORICAL_CATALOG_INVALID")
        items, seen_numbers, seen_ids = [], set(), set()
        for page in (1, 2):
            docs = self.get(
                "repos/" + REPO + "/issues?state=open&labels=" + LABEL +
                "&per_page=100&page=" + str(page))
            require(isinstance(docs,list) and len(docs)<=100,
                    "NATIVE_ISSUE_CATALOG_INVALID")
            for raw in docs:
                # A previously admitted issue remains a frozen, failed or
                # completed historical record after a qualified transition.
                # Do not mistake it for an eligible candidate on the new SHA.
                require(isinstance(raw, dict)
                        and type(raw.get("number")) is int
                        and type(raw.get("id")) is int
                        and raw["number"] not in seen_numbers
                        and raw["id"] not in seen_ids,
                        "NATIVE_DUPLICATE_OR_INVALID_ISSUE_IDENTITY")
                seen_numbers.add(raw["number"])
                seen_ids.add(raw["id"])
                historical = historical_issues.get(raw["number"])
                # A declarative issue may only select a *pinned* native commit.
                # Independent GitHub API lookup binds actual Git tree identity.
                try:
                    body = json.loads(raw.get("body",""))
                    encoded = body["intent_base64"]
                    from f139.nci04_native_contract import canonical as _canonical
                    import base64
                    intent = json.loads(base64.b64decode(encoded,validate=True))
                    lane = intent["lane"]
                    require(lane in ("Wingless","Yggdrasil"),
                            "NATIVE_LANE_FORBIDDEN")
                    sha = intent["target_commit"]
                    require(isinstance(sha,str) and SHA.fullmatch(sha) is not None,
                            "NATIVE_TARGET_COMMIT_INVALID")
                    native_repo = "spoonman136668-ai/" + lane
                    raw_commit = self.runner([
                        "repos/" + native_repo + "/git/commits/" + sha])
                    commit = json.loads(raw_commit)
                    require(commit.get("sha")==sha
                            and isinstance(commit.get("tree"),dict)
                            and isinstance(commit["tree"].get("sha"),str)
                            and SHA.fullmatch(commit["tree"]["sha"]) is not None,
                            "NATIVE_TARGET_GIT_PROVIDER_DRIFT")
                    doc=inspect_owner_issue(
                        raw, protected_main=(historical[1] if historical else source),
                        authenticated_target_commit=sha,
                        authenticated_target_tree=commit["tree"]["sha"])
                except (ValueError,UnicodeError,KeyError,TypeError,
                        NativeIssueDenied,NativeContractError) as exc:
                    raise F139Error("F139_NATIVE_ISSUE_OR_SOURCE_REJECTED") from exc
                if historical:
                    require((doc.issue_id,doc.source_sha,doc.issue_body_sha256,
                             doc.ticket) == historical,
                            "NATIVE_HISTORICAL_ISSUE_DRIFT")
                    continue
                items.append(doc)
            if len(docs)<100:
                break
        else:
            raise F139Error("F139_NATIVE_CATALOG_TRUNCATED")
        require(len({x.number for x in items})==len(items)
                and len({x.issue_id for x in items})==len(items),
                "NATIVE_DUPLICATE_ISSUES")
        return sorted(items,key=lambda x:x.number)

    def dispatch_native(self, signed_fields: dict, issue):
        """One original workflow endpoint, not another scheduler/controller."""
        from f139.nci04_owner_issue import NativeIssue
        from f139.nci04_worker_v2 import SOURCE_SHA as V2_SOURCE_SHA
        from f139.nci04_worker_v2 import SOURCE_TREE as V2_SOURCE_TREE
        import base64
        require(isinstance(issue,NativeIssue)
                and signed_fields["ticket"]==issue.ticket
                and signed_fields["target_commit"]==issue.candidate.target_commit
                and signed_fields["target_tree_sha"]==issue.candidate.target_tree_sha,
                "NATIVE_DISPATCH_ISSUE_IDENTITY")
        from f139.nci04_release_pin_continuity import (
            verify_release_worker_branch, release_worker_branch)
        source = issue.source_sha
        require(source == signed_fields["source_sha"],
                "NATIVE_DISPATCH_SOURCE_IDENTITY_DRIFT")
        worker_ref = release_worker_branch(source)
        payload = [
            "--method","POST",
            "repos/"+REPO+"/actions/workflows/"+WORKFLOW+"/dispatches",
            "-f","ref="+worker_ref,
        ]
        # GitHub workflow_dispatch supports only TEN input keys; legacy
        # endpoint already consumes nine. Keep those exact preexisting fields
        # and add ONE source-bound, typed, encoded native bundle.
        for key in ("ticket","lane","source_sha","epoch","signature"):
            value=signed_fields[key]
            require(isinstance(value,str) and 0<len(value)<=128,
                    "NATIVE_DISPATCH_FIELD_INVALID")
            payload.extend(["-f","inputs["+key+"]="+value])
        base_keys = ("native_signature","issue_number","issue_id",
                     "body_sha256","qualification_key",
                     "target_commit","target_tree_sha")
        v2_keys = ("v2_original_event_seq","v2_original_event_sha256",
                   "v2_claim_event_seq","v2_claim_event_sha256",
                   "v2_owner_signature")
        v2 = signed_fields.get("native_protocol") == "v2"
        require(set(signed_fields) == set(("ticket","lane","source_sha",
                      "epoch","signature","intent_sha256",*base_keys,
                      *(("native_protocol",*v2_keys) if v2 else ())))
                and signed_fields["intent_sha256"] ==
                    issue.candidate.intent_sha256
                and (not v2 or (issue.lane == "Yggdrasil"
                       and issue.candidate.target_commit == V2_SOURCE_SHA
                       and issue.candidate.target_tree_sha == V2_SOURCE_TREE
                       and issue.candidate.path ==
                           "yggdrasil/public_causal_cells.py")),
                "NATIVE_DISPATCH_VERSION_OR_IDENTITY_DRIFT")
        bundle = {key:signed_fields[key] for key in base_keys}
        if v2:
            for key in v2_keys:
                value=signed_fields[key]
                require(isinstance(value,str)
                        and re.fullmatch(
                          r"[1-9][0-9]*" if key.endswith("_seq")
                          else r"[a-f0-9]{64}",value) is not None,
                        "NATIVE_V2_OWNER_CLAIM_FIELD_INVALID")
                bundle[key]=value
            # Reuse an existing D2K input key only on native tickets.
            # GitHub allows at most TEN workflow_dispatch inputs.
            payload.extend(["-f","inputs[target_package]=f139-nci04-v2"])
        bundle["intent_base64"] = base64.b64encode(issue.intent_raw).decode("ascii")
        encoded=base64.b64encode(canonical(bundle)).decode("ascii")
        require(0<len(encoded)<=60000,"NATIVE_DISPATCH_INTENT_TOO_LARGE")
        payload.extend(["-f","inputs[native_bundle]="+encoded])
        # Authenticate the exact released worker code AFTER typed/HMAC claim
        # validation, immediately before the ONE remote POST.
        require(verify_release_worker_branch(
                    self.native_repo_get, source) == worker_ref,
                "NATIVE_DISPATCH_WORKER_REF_RACE")
        self.runner(payload)

    def dispatch(self,ticket:str,lane:str,source:str,epoch:int,signature:str, *, d2k_fields=None):
        require(TICKET.fullmatch(ticket) and lane in LANES and SHA.fullmatch(source)
                and 0<epoch<2**31 and re.fullmatch(r"[a-f0-9]{64}",signature),
                "DISPATCH_NOT_ALLOWED")
        args=["--method","POST","repos/"+REPO+"/actions/workflows/"+WORKFLOW+"/dispatches",
              "-f","ref=main","-f","inputs[ticket]="+ticket,
              "-f","inputs[lane]="+lane,"-f","inputs[source_sha]="+source,
              "-f","inputs[epoch]="+str(epoch),"-f","inputs[signature]="+signature]
        if ticket.startswith("f139-d2k-"):
            require(isinstance(d2k_fields,dict) and set(d2k_fields)=={
                "issue_number","issue_id","body_sha256","target_package"},
                "D2K_SIGNED_DISPATCH_MISSING")
            for name in ("issue_number","issue_id","body_sha256","target_package"):
                args.extend(["-f","inputs["+name+"]="+d2k_fields[name]])
        else:
            require(d2k_fields is None,"D2K_FIELDS_ON_LEGACY_DISPATCH")
        self.runner(args)

    def candidates(self,ticket:str,started_at:str):
        # Frozen legacy/historical provider lookups remain main-scoped.
        return self._candidates_for_ref(ticket,started_at,"main")

    def candidates_for_source(self, ticket: str, started_at: str,
                              source_sha: str):
        """Look up once-only runs ONLY under exact authenticated release ref."""
        from f139.nci04_release_pin_continuity import (
            verify_release_worker_branch)
        ref = verify_release_worker_branch(self.native_repo_get, source_sha)
        return self._candidates_for_ref(ticket, started_at, ref)

    def _candidates_for_ref(self,ticket:str,started_at:str,ref:str):
        require(isinstance(ref,str)
                and re.fullmatch(r"(?:main|f139-owner-release-[a-f0-9]{40})",
                                 ref) is not None,
                "F139_WORKER_REF_INVALID")
        source_start=parse_time(started_at)
        found=[]
        for page in range(1,6):
            index=self.get("repos/"+REPO+"/actions/workflows/"+WORKFLOW+
                           "/runs?branch="+ref+"&event=workflow_dispatch&per_page=100&page="+str(page))
            rows=index.get("workflow_runs")
            require(isinstance(rows,list) and isinstance(index.get("total_count"),int),
                    "PROVIDER_HISTORY_INVALID")
            found.extend(run for run in rows if run.get("display_title")=="F139 "+ticket)
            if len(rows)<100 or not rows or parse_time(rows[-1]["created_at"])<source_start-dt.timedelta(minutes=2):
                break
        else:
            raise F139Error("F139_PROVIDER_HISTORY_TRUNCATED")
        require(len(found)<=1,"DUPLICATE_ATTEMPT_IDENTITIES")
        return found[0] if found else None

    def run_proof(self,run:dict,ticket:str,source:str,started_at:str):
        require(isinstance(run,dict) and run.get("display_title")=="F139 "+ticket
                and run.get("event")=="workflow_dispatch" and run.get("name")=="F139 "+ticket
                and run.get("workflow_id")==388797257
                and run.get("path")==".github/workflows/"+WORKFLOW
                and run.get("head_sha")==source and run.get("head_branch") in (
                    "main","f139-owner-release-"+source)
                and run.get("run_attempt")==1 and isinstance(run.get("id"),int)
                and run["id"]>0 and parse_time(run.get("created_at")) >= parse_time(started_at)-dt.timedelta(minutes=2),
                "PROVIDER_SOURCE_EVENT_SPOOFED")
        if run.get("status") in ("queued","requested","in_progress","waiting","pending"):
            return None
        require(run.get("status")=="completed" and run.get("conclusion")=="success",
                "FAILED_OR_CANCELLED_NO_REPLAY")
        rid=run["id"]
        jobs=self.get(f"repos/{REPO}/actions/runs/{rid}/jobs?per_page=100")
        arts=self.get(f"repos/{REPO}/actions/runs/{rid}/artifacts?per_page=100")
        jr,ar=jobs.get("jobs"),arts.get("artifacts")
        require(isinstance(jr,list) and isinstance(ar,list) and jobs.get("total_count")==len(jr)
                and arts.get("total_count")==len(ar) and len(jr)<=100 and len(ar)<=100,
                "PROVIDER_INDEX_TRUNCATED")
        native = ticket.startswith("f139-nci04-")
        job_prefix = "native-execute (" if native else "execute ("
        artifact_prefix = "forge-f139-native-receipt-" if native else "forge-f139-dev-receipt-"
        if native:
            authorized = [x for x in jr if x.get("name")=="native-authorize"]
            require(len(authorized)==1 and authorized[0].get("status")=="completed"
                    and authorized[0].get("conclusion")=="success",
                    "NATIVE_PROVIDER_AUTH_JOB_NOT_VERIFIED")
        for oslabel in ("windows-latest","ubuntu-latest"):
            matching=[x for x in jr if x.get("name")==job_prefix+oslabel+")"]
            require(len(matching)==1 and matching[0].get("status")=="completed"
                    and matching[0].get("conclusion")=="success", "WORKER_OS_NOT_VERIFIED")
            names=[x for x in ar if x.get("name")==artifact_prefix+oslabel]
            require(len(names)==1 and names[0].get("expired") is False
                    and names[0].get("workflow_run",{}).get("id")==rid
                    and names[0].get("workflow_run",{}).get("head_sha")==source
                    and re.fullmatch(r"sha256:[a-f0-9]{64}",names[0].get("digest") or ""),
                    "PROVIDER_ARTIFACT_NOT_QUALIFIED")
        return (rid,ar)

    def failed_native_provider_report(self, run: dict, ticket: str,
                                          source: str, started_at: str):
        """Authenticate one completed failed native run without replaying it."""
        require(isinstance(run,dict) and ticket.startswith("f139-nci04-")
                and run.get("display_title")=="F139 "+ticket
                and run.get("event")=="workflow_dispatch"
                and run.get("name")=="F139 "+ticket
                and run.get("workflow_id")==388797257
                and run.get("path")==".github/workflows/"+WORKFLOW
                and run.get("head_sha")==source and run.get("head_branch") in (
                    "main","f139-owner-release-"+source)
                and run.get("run_attempt")==1 and isinstance(run.get("id"),int)
                and run["id"]>0
                and parse_time(run.get("created_at")) >=
                    parse_time(started_at)-dt.timedelta(minutes=2)
                and run.get("status")=="completed"
                and run.get("conclusion")=="failure",
                "FAILED_PROVIDER_SOURCE_EVENT_UNVERIFIED")
        rid=run["id"]
        jobs_doc=self.get(f"repos/{REPO}/actions/runs/{rid}/jobs?per_page=100")
        arts_doc=self.get(f"repos/{REPO}/actions/runs/{rid}/artifacts?per_page=100")
        jobs,arts=jobs_doc.get("jobs"),arts_doc.get("artifacts")
        require(isinstance(jobs,list) and isinstance(arts,list)
                and jobs_doc.get("total_count")==len(jobs)
                and arts_doc.get("total_count")==len(arts)
                and len(jobs)<=100 and len(arts)<=100,
                "FAILED_PROVIDER_INDEX_TRUNCATED")
        auth=[x for x in jobs if x.get("name")=="native-authorize"]
        require(len(auth)==1 and auth[0].get("status")=="completed"
                and auth[0].get("conclusion")=="success",
                "FAILED_PROVIDER_AUTH_NOT_VERIFIED")
        out={}
        artifact_ids=[]
        for oslabel in ("windows-latest","ubuntu-latest"):
            match=[x for x in jobs
                   if x.get("name")=="native-execute ("+oslabel+")"]
            require(len(match)==1 and match[0].get("status")=="completed"
                    and match[0].get("conclusion") in ("success","failure")
                    and type(match[0].get("id")) is int and match[0]["id"]>0,
                    "FAILED_PROVIDER_OS_JOB_INVALID")
            out[oslabel]={"job_id":match[0]["id"],
                          "conclusion":match[0]["conclusion"]}
            named=[x for x in arts
                   if x.get("name")=="forge-f139-native-receipt-"+oslabel]
            require(len(named)==1 and named[0].get("expired") is False
                    and type(named[0].get("id")) is int and named[0]["id"]>0
                    and named[0].get("workflow_run",{}).get("id")==rid
                    and named[0].get("workflow_run",{}).get("head_sha")==source
                    and re.fullmatch(r"sha256:[a-f0-9]{64}",
                                     named[0].get("digest") or ""),
                    "FAILED_PROVIDER_ARTIFACT_INVALID")
            artifact_ids.append(named[0]["id"])
        require(any(v["conclusion"]=="failure" for v in out.values()),
                "FAILED_PROVIDER_HAS_NO_FAILED_OS")
        return {"ticket":ticket,"run_id":rid,"source_sha":source,
                "jobs":out,"artifact_ids":sorted(artifact_ids),
                "provider_terminal":"FAILURE_NO_REPLAY",
                "scientific_first_use":False}

    def artifact(self,artifact_id:int)->bytes:
        require(isinstance(artifact_id,int) and artifact_id>0,"ARTIFACT_ID_INVALID")
        zipbytes=self.runner([f"repos/{REPO}/actions/artifacts/{artifact_id}/zip"])
        require(isinstance(zipbytes,bytes) and 0<len(zipbytes)<MAX_ZIP_BYTES,"ARTIFACT_TOO_LARGE")
        return zipbytes


def native_original_running_publisher_profile(db_path: Path) -> bool:
    """Read-only verification of the ORIGINAL running task and Python child.

    This is intentionally NOT the disabled-task source-transition witness.
    It grants no source transition or science, and never exposes secrets.
    """
    require(os.name == "nt", "G3_ORIGINAL_OWNER_REQUIRES_WINDOWS")
    expected = Path(os.environ.get("LOCALAPPDATA", "")) / "FORGE-F139" / "state.sqlite"
    require(bool(os.environ.get("LOCALAPPDATA")) and
            Path(db_path).resolve() == expected.resolve(),
            "G3_ORIGINAL_DATABASE_PATH_DRIFT")
    require(SingleOwner.held(Path(db_path).with_suffix(".lock")),
            "G3_ORIGINAL_OWNER_MUTEX_NOT_HELD")
    exe = shutil.which("powershell.exe")
    require(exe is not None, "G3_WINDOWS_POWERSHELL_UNAVAILABLE")
    script = (
        "$ErrorActionPreference='Stop';"
        "$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop;"
        "if([string]$t.State -cne 'Running'){exit 41};"
        "$who=[Security.Principal.WindowsIdentity]::GetCurrent();"
        "$principal=[string]$t.Principal.UserId;"
        "$sid='';"
        "try{$sid=(New-Object Security.Principal.NTAccount($principal)).Translate("
        "[Security.Principal.SecurityIdentifier]).Value}catch{};"
        "if($principal -ine $who.Name -and $sid -cne $who.User.Value){exit 42};"
        "if(@($t.Actions).Count -ne 1){exit 43};"
        "$a=$t.Actions[0];"
        "if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe'){exit 44};"
        "$opts=[string]$a.Arguments;"
        "$root=[regex]::Match($opts,'(?i)(?:^|\\s)-RepositoryRoot\\s+\"([^\"]+)\"');"
        "$db=[regex]::Match($opts,'(?i)(?:^|\\s)-Database\\s+\"([^\"]+)\"');"
        "$wrapper=[regex]::Match($opts,'(?i)(?:^|\\s)-File\\s+\"([^\"]+)\"');"
        "if(-not($root.Success -and $db.Success -and $wrapper.Success)){exit 45};"
        "if([IO.Path]::GetFileName($wrapper.Groups[1].Value) -cne 'Run-FORGE-F139.ps1'){exit 46};"
        "if([IO.Path]::GetFullPath($root.Groups[1].Value) -ine "
        "[IO.Path]::GetFullPath($env:F139_EXPECTED_TASK_SOURCE_ROOT)){exit 47};"
        "if([IO.Path]::GetFullPath($db.Groups[1].Value) -ine "
        "[IO.Path]::GetFullPath($env:F139_EXPECTED_TASK_DATABASE)){exit 48};"
        "$self=Get-CimInstance Win32_Process -Filter "
        "\"ProcessId=$env:F139_EXPECTED_NATIVE_CLI_PID\" -ErrorAction Stop;"
        "if(-not $self -or $self.Name -ine 'python.exe' -or "
        "-not $self.CommandLine.Contains('f139.local_controller')){exit 49};"
        "$parent=Get-CimInstance Win32_Process -Filter "
        "\"ProcessId=$($self.ParentProcessId)\" -ErrorAction Stop;"
        "if(-not $parent -or $parent.Name -ine 'powershell.exe' -or "
        "-not $parent.CommandLine.Contains('Run-FORGE-F139.ps1')){exit 50};"
        "Write-Output 'F139_G3_ORIGINAL_RUNNING_OWNER=PASS'"
    )
    env = {**os.environ,
           "F139_EXPECTED_TASK_SOURCE_ROOT": str(Path(__file__).resolve().parent.parent),
           "F139_EXPECTED_TASK_DATABASE": str(Path(db_path).resolve()),
           "F139_EXPECTED_NATIVE_CLI_PID": str(os.getpid())}
    result = subprocess.run(
        [exe, "-NoProfile", "-NonInteractive", "-Command", script],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
        env=env, timeout=20, check=False)
    require(result.returncode == 0 and
            result.stdout.strip() == b"F139_G3_ORIGINAL_RUNNING_OWNER=PASS",
            "G3_ORIGINAL_RUNNING_TASK_OR_PROCESS_DRIFT")
    return True


def native_original_owner_profile(db_path: Path) -> bool:
    """Read-only SID, DB and *scheduled source root* custody check.

    The installed PowerShell wrapper can reside in the historical D2N tree,
    but its -RepositoryRoot parameter MUST equal the exact Python checkout
    executing a native source transition or activation. Never inspect or
    print DPAPI key material or the raw scheduled task command line.
    """
    require(os.name=="nt","NATIVE_OWNER_MUST_BE_WINDOWS")
    profile=os.environ.get("LOCALAPPDATA","")
    require(bool(profile),"OWNER_LOCALAPPDATA_MISSING")
    expected=Path(profile)/"FORGE-F139"/"state.sqlite"
    require(Path(db_path).resolve()==expected.resolve(),
            "ORIGINAL_OWNER_DATABASE_PROFILE_MISMATCH")
    source=shutil.which("powershell.exe")
    require(source is not None,"OWNER_WINDOWS_POWERSHELL_UNAVAILABLE")
    script=(
        "$ErrorActionPreference='Stop';"
        "$t=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop;"
        "$who=[Security.Principal.WindowsIdentity]::GetCurrent();"
        "$principal=[string]$t.Principal.UserId;"
        "$sid='';"
        "try{$sid=(New-Object Security.Principal.NTAccount($principal)).Translate("
        "[Security.Principal.SecurityIdentifier]).Value}catch{};"
        "if($principal -ine $who.Name -and $sid -ne $who.User.Value){exit 42};"
        # A source transition is allowed only while the ORIGINAL task is
        # disabled for the bounded owner cutover, preventing a scheduled
        # Python child from racing the SQLite source transition.
        "if($t.State -ne 'Disabled'){exit 43};"
        # Exclude ONLY this exact owner CLI process. Other F139 Python
        # children pointing at the same source/DB must still block the cutover.
        "$selfId=[int]$env:F139_EXPECTED_NATIVE_CLI_PID;"
        "if($selfId -le 0){exit 51};"
        "$processes=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
        "-ErrorAction Stop | Where-Object { [int]$_.ProcessId -ne $selfId -and $_.CommandLine -and "
        "$_.CommandLine.Contains('f139.local_controller') -and "
        "$_.CommandLine.Contains($env:F139_EXPECTED_TASK_DATABASE) });"
        "if($processes.Count -gt 0){exit 50};"
        "if(@($t.Actions).Count -ne 1){exit 44};"
        "$a=$t.Actions[0];"
        "if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe'){exit 45};"
        "$opts=[string]$a.Arguments;"
        "$root=[regex]::Match($opts,'(?i)(?:^|\\s)-RepositoryRoot\\s+\"([^\"]+)\"');"
        "$db=[regex]::Match($opts,'(?i)(?:^|\\s)-Database\\s+\"([^\"]+)\"');"
        "$wrapper=[regex]::Match($opts,'(?i)(?:^|\\s)-File\\s+\"([^\"]+)\"');"
        "if(-not($root.Success -and $db.Success -and $wrapper.Success)){exit 46};"
        "if([IO.Path]::GetFileName($wrapper.Groups[1].Value) -cne 'Run-FORGE-F139.ps1'){exit 47};"
        "if([IO.Path]::GetFullPath($root.Groups[1].Value) -ine "
        "[IO.Path]::GetFullPath($env:F139_EXPECTED_TASK_SOURCE_ROOT)){exit 48};"
        "if([IO.Path]::GetFullPath($db.Groups[1].Value) -ine "
        "[IO.Path]::GetFullPath($env:F139_EXPECTED_TASK_DATABASE)){exit 49};"
        "Write-Output 'F139_NATIVE_ORIGINAL_OWNER_PROFILE=PASS'"
    )
    env={**os.environ,
         "F139_EXPECTED_TASK_SOURCE_ROOT":str(Path(__file__).resolve().parent.parent),
         "F139_EXPECTED_TASK_DATABASE":str(Path(db_path).resolve()),
         "F139_EXPECTED_NATIVE_CLI_PID":str(os.getpid())}
    result=subprocess.run(
        [source,"-NoProfile","-NonInteractive","-Command",script],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,env=env,timeout=20,check=False)
    require(result.returncode==0 and
            result.stdout.strip()==b"F139_NATIVE_ORIGINAL_OWNER_PROFILE=PASS",
            "ORIGINAL_OWNER_PROFILE_TASK_ROUTE_OR_DB_DRIFT")
    return True


def legacy_windows_task_disabled():
    require(os.name=="nt","CUTOVER_MUST_RUN_ON_TARGET_WINDOWS_HOST")
    source=shutil.which("powershell.exe")
    require(source is not None,"WINDOWS_TASK_INSPECTION_UNAVAILABLE")
    command="$t=Get-ScheduledTask -TaskName 'FORGE-F137-WakeProbe' -ErrorAction SilentlyContinue; if ($null -eq $t -or $t.State -eq 'Disabled') { 'DISABLED' } else { 'ACTIVE'; exit 1 }"
    try:
        p=subprocess.run([source,"-NoProfile","-NonInteractive","-Command",command],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,check=False)
    except subprocess.TimeoutExpired as exc:
        raise F139Error("F139_LEGACY_TASK_INSPECTION_TIMEOUT") from exc
    require(p.returncode==0 and p.stdout.strip()==b"DISABLED",
            "LEGACY_WINDOWS_TASK_STILL_ENABLED")
    return True


def receipt_from_zip(raw:bytes,meta:dict,task:dict,run_id:int,oslabel:str,epoch:int=1, *, d2k_fields=None)->dict:
    require(isinstance(meta.get("digest"),str) and meta["digest"].startswith("sha256:")
            and hash_bytes(raw)==meta["digest"][7:]
            and len(raw)==meta.get("size_in_bytes"),"ARTIFACT_ZIP_DIGEST_DRIFT")
    d2k=task["ticket"].startswith("f139-d2k-")
    expected=["f139-receipt.json","f139-receipt.sha256"]
    if d2k: expected.append("f139-diagnostic.json")
    else: require(d2k_fields is None,"D2K_FIELDS_ON_LEGACY_RECEIPT")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names=archive.namelist()
            require(sorted(names)==sorted(expected) and len(names)==len(set(names)),
                    "ARTIFACT_MEMBER_SET_INVALID")
            require(all(not x.is_dir() and x.file_size <=
                        (32768 if x.filename=="f139-diagnostic.json" else MAX_RECEIPT_BYTES)
                        for x in archive.infolist()),"ARTIFACT_MEMBER_OVERSIZE")
            body=archive.read("f139-receipt.json")
            checksum=archive.read("f139-receipt.sha256")
            diagnostic_raw=archive.read("f139-diagnostic.json") if d2k else None
    except (OSError,zipfile.BadZipFile,ValueError,RuntimeError) as exc:
        raise F139Error("F139_ARTIFACT_ZIP_INVALID") from exc
    require(checksum==(hash_bytes(body)+"  f139-receipt.json\n").encode(),"RECEIPT_SHA_INVALID")
    try:
        value=json.loads(body)
        diagnostic=json.loads(diagnostic_raw) if d2k else None
    except (ValueError,UnicodeDecodeError) as exc:
        raise F139Error("F139_RECEIPT_JSON_INVALID") from exc
    require(isinstance(value,dict)
            and value.get("ticket")==task["ticket"] and value.get("lane")==task["lane"]
            and value.get("source_sha")==task["source_sha"] and value.get("epoch")==epoch
            and value.get("os")==oslabel and value.get("run_id")==run_id
            and value.get("development_only") is True
            and value.get("scientific_first_use_authorized") is False
            and type(value.get("scientific_originals_dispatched")) is int
            and value["scientific_originals_dispatched"]==0
            and type(value.get("accepted_ref_mutations")) is int
            and value["accepted_ref_mutations"]==0
            and type(value.get("paid_model_calls")) is int and value["paid_model_calls"]==0
            and type(value.get("codex_calls")) is int and value["codex_calls"]==0,
            "RECEIPT_FALSE_SOURCE_OR_SCIENCE")
    if not d2k:
        require(value.get("schema")=="forge.f139.development-worker-receipt.v1",
                "RECEIPT_LEGACY_SCHEMA_INVALID")
        return value
    require(isinstance(d2k_fields,dict) and set(d2k_fields)=={
        "issue_number","issue_id","body_sha256","target_package"},
        "D2K_RECEIPT_UNBOUND_ISSUE")
    require(set(value)=={
        "schema","ticket","lane","source_sha","epoch","run_id","os",
        "issue_number","issue_id","body_sha256","target_package",
        "diagnostic_sha256","outcome","development_only",
        "scientific_first_use_authorized","scientific_originals_dispatched",
        "accepted_ref_mutations","paid_model_calls","codex_calls"}
        and value["schema"]=="forge.f139.d2k.package-diagnostic-receipt.v1"
        and value["issue_number"]==int(d2k_fields["issue_number"])
        and value["issue_id"]==int(d2k_fields["issue_id"])
        and value["body_sha256"]==d2k_fields["body_sha256"]
        and value["target_package"]==d2k_fields["target_package"]
        and value["target_package"] in D2K_ALLOWED_PACKAGES
        and value["diagnostic_sha256"]==hash_bytes(diagnostic_raw)
        and value["outcome"] in ("PASS","TEST_FAILURE","TIMEOUT"),
        "D2K_RECEIPT_IDENTITY_OR_DIGEST")
    require(isinstance(diagnostic,dict) and set(diagnostic)=={
        "schema","source_sha","issue_number","issue_id","body_sha256",
        "target_package","run_id","os","outcome","returncode","duration_ms",
        "output_sha256","output_excerpt","output_bytes",
        "scientific_first_use","paid_model_calls"},
        "D2K_DIAGNOSTIC_FIELDS")
    require(diagnostic["schema"]=="forge.f139.d2k.package-diagnostic.v1"
            and diagnostic["source_sha"]==task["source_sha"]
            and diagnostic["issue_number"]==value["issue_number"]
            and diagnostic["issue_id"]==value["issue_id"]
            and diagnostic["body_sha256"]==value["body_sha256"]
            and diagnostic["target_package"]==value["target_package"]
            and diagnostic["run_id"]==run_id and diagnostic["os"]==oslabel
            and diagnostic["outcome"]==value["outcome"]
            and type(diagnostic["returncode"]) is int
            and ((diagnostic["outcome"]=="PASS" and diagnostic["returncode"]==0)
                 or (diagnostic["outcome"]=="TEST_FAILURE" and 0<diagnostic["returncode"]<=255)
                 or (diagnostic["outcome"]=="TIMEOUT" and diagnostic["returncode"]==-1))
            and type(diagnostic["duration_ms"]) is int
            and 0<=diagnostic["duration_ms"]<=120000
            and type(diagnostic["output_bytes"]) is int
            and 0<=diagnostic["output_bytes"]<=100000
            and isinstance(diagnostic["output_excerpt"],str)
            and len(diagnostic["output_excerpt"].encode("utf-8"))<=16384
            and isinstance(diagnostic["output_sha256"],str)
            and re.fullmatch(r"[a-f0-9]{64}",diagnostic["output_sha256"])
            and diagnostic["scientific_first_use"] is False
            and type(diagnostic["paid_model_calls"]) is int
            and diagnostic["paid_model_calls"]==0,
            "D2K_DIAGNOSTIC_IDENTITY_OR_OUTCOME")
    return value


def store_evidence(root:Path,ticket:str,run_id:int,archives:dict)->tuple[str,str]:
    """Retain original provider bytes; reconcile only exact prior completed custody.

    A crash after durable files but before the SQLite terminal transaction must
    not cause a second dispatch or falsely quarantine a valid original.
    Partial or changed custody is never silently repaired or overwritten.
    """
    folder=root/"evidence"/ticket/str(run_id)
    require(set(archives)=={"ubuntu-latest","windows-latest"} and
            all(isinstance(blob,bytes) and 0<len(blob)<MAX_ZIP_BYTES for blob in archives.values()),
            "EVIDENCE_INPUT_SET_INVALID")
    digests={oslabel:hash_bytes(blob) for oslabel,blob in archives.items()}
    report={"schema":"forge.f139.windows-evidence-manifest.v1","ticket":ticket,
            "run_id":run_id,"sha256":digests,"scientific_originals":0,"approved_science":False}
    payload=canonical(report)
    expected={oslabel+".zip":blob for oslabel,blob in archives.items()}
    expected["manifest.json"]=payload

    if folder.exists() or folder.is_symlink():
        # Exact-match readback is the only automatic post-crash recovery.
        # Never accept partial writes, symlinks, extra members or substituted bytes.
        require(folder.is_dir() and not folder.is_symlink(), "EVIDENCE_RECOVERY_CONFLICT")
        require({p.name for p in folder.iterdir()}==set(expected), "EVIDENCE_RECOVERY_CONFLICT")
        for name,data in expected.items():
            path=folder/name
            require(path.is_file() and not path.is_symlink() and path.read_bytes()==data,
                    "EVIDENCE_RECOVERY_CONFLICT")
        return (str(folder),hash_bytes(payload))

    folder.mkdir(parents=True)
    for name,data in expected.items():
        with (folder/name).open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    # A mid-write interruption retains the partial directory for investigation;
    # it cannot be replayed or mistaken for fully accepted evidence on recovery.
    return (str(folder),hash_bytes(payload))

def g54_original_canonical(db, *, through_seq=None):
    """Read G54 negative from the SAME original SQLite with canonical class identity.

    Python -m starts __main__.Database while the imported original verifier
    demands f139.local_controller.Database. Never relax that demand or copy
    SQLite: re-open the exact original path as the canonical read-only witness.
    In an active single-owner transaction, the committed original negative
    predates the V11 event and remains readable by the second connection.
    """
    from f139.local_controller import Database as CanonicalDatabase
    from f139.nci04_g54_ambiguous_start_custody import (
        verified_g54_ambiguous_start)
    if type(db) is CanonicalDatabase:
        return verified_g54_ambiguous_start(db, through_seq=through_seq)
    main=sys.modules.get("__main__")
    require(type(db).__module__=="__main__"
            and type(db).__name__=="Database"
            and main is not None
            and isinstance(getattr(main,"__file__",None),str)
            and Path(main.__file__).resolve(strict=True)==
                Path(__file__).resolve(strict=True)
            and isinstance(getattr(db,"filename",None),Path),
            "G54_CANONICAL_OWNER_SOURCE_REQUIRED")
    original=Path(db.filename).resolve(strict=True)
    canonical_db=CanonicalDatabase(original)
    try:
        require(Path(canonical_db.filename).resolve(strict=True)==original,
                "G54_CANONICAL_ORIGINAL_DB_PATH_DRIFT")
        return verified_g54_ambiguous_start(
            canonical_db, through_seq=through_seq)
    finally:
        canonical_db.close()


def v2_owner_terminal_release_guard(source_sha: str, db=None) -> bool:
    """Allow native V2 development after a sealed original V7/V8/V9/V10 transition
    and separate native development activation.

    An environment variable, issue label or a source SHA alone never arms
    the credentialed V2 signer. The G36 signed original claim still must
    verify on each individual V2 dispatch; G38 independently audits both
    provider receipts. No scientific first-use is granted.
    """
    if (type(db) is not Database or not isinstance(source_sha,str)
            or SHA.fullmatch(source_sha) is None):
        return False
    try:
        meta=db.meta()
        if (meta["source_sha"] != source_sha
                or not (meta["enabled"] == 1 and
                        meta["legacy_suspended"] == 1)):
            return False
        row=db.conn.execute(
            "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
            "ORDER BY seq DESC LIMIT 1").fetchone()
        if row is None:
            return False
        event=json.loads(row["payload"])
        v7 = (event.get("schema")=="forge.f139.source-transition.v7"
              and event.get("from_source_sha")==
                  "b2079282fed03df2203807de09b4f3e82bdfe05a")
        from f139.nci04_g49_prepost_negative import (
            verify_g49_custody, SOURCE_V7)
        v8 = (event.get("schema")=="forge.f139.source-transition.v8"
              and event.get("from_source_sha")==SOURCE_V7
              and verify_g49_custody(db))
        v9 = False
        if event.get("schema")=="forge.f139.source-transition.v9":
            # Database.verify seals the V9 transition to the unique terminal
            # V8 event and G49 custody; recheck the seal here before the signer
            # can dispatch any new work against this source.
            db.verify()
            v8_rows=[
                r for r in db.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema")==
                    "forge.f139.source-transition.v8"]
            v9=(len(v8_rows)==1
                and event.get("from_source_sha")==
                    json.loads(v8_rows[0]["payload"]).get("to_source_sha")
                and event.get("v8_terminal_event_sha256")==v8_rows[0]["sha"]
                and verify_g49_custody(db))
        v10 = False
        if event.get("schema")=="forge.f139.source-transition.v10":
            # Database.verify validates the V10 event's G49 custody, complete
            # quarantined negative set and terminal V9 event seal. Recheck the
            # exact predecessor link here before authorizing the V2 signer.
            db.verify()
            v9_rows=[
                r for r in db.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema")==
                    "forge.f139.source-transition.v9"]
            v10=(len(v9_rows)==1
                 and event.get("from_source_sha")==
                     json.loads(v9_rows[0]["payload"]).get("to_source_sha")
                 and event.get("v9_terminal_event_sha256")==v9_rows[0]["sha"]
                 and verify_g49_custody(db))
        v11 = False
        if event.get("schema")=="forge.f139.source-transition.v11":
            # A model-publisher release must not weaken the existing V2
            # provider signer or reclassify G54's ambiguous no-run as success.
            db.verify()
            from f139.nci04_g54_ambiguous_start_custody import (
                verified_g54_ambiguous_start)
            frozen = g54_original_canonical(db)
            v10_rows = [
                r for r in db.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema")==
                    "forge.f139.source-transition.v10"]
            v11 = (len(v10_rows)==1
                   and event.get("from_source_sha")==
                       json.loads(v10_rows[0]["payload"]).get("to_source_sha")
                   and event.get("v10_terminal_event_sha256")==v10_rows[0]["sha"]
                   and event.get("g54_ambiguous_start_event_sha256")==
                       frozen["quarantine_event_sha256"]
                   and verify_g49_custody(db))
        v12 = False
        if event.get("schema")=="forge.f139.source-transition.v12":
            db.verify()
            g54 = g54_original_canonical(db)
            v11_rows = [
                r for r in db.conn.execute(
                    "SELECT sha,payload FROM events "
                    "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema") ==
                   "forge.f139.source-transition.v11"]
            g3 = [r for r in db.conn.execute(
                "SELECT kind,sha FROM events WHERE kind IN "
                "('G3_DRAFT_ATTEMPTED','G3_DRAFT_AUTHENTICATED') "
                "ORDER BY seq")]
            v12=(len(v11_rows)==1
                 and event.get("from_source_sha") ==
                     json.loads(v11_rows[0]["payload"])["to_source_sha"]
                 and event.get("v11_terminal_event_sha256")==v11_rows[0]["sha"]
                 and event.get("g54_ambiguous_start_event_sha256") ==
                     g54["quarantine_event_sha256"]
                 and event.get("g3_draft_history_sha256") == hash_bytes(canonical(
                     [{"kind":r["kind"],"sha":r["sha"]} for r in g3]))
                 and verify_g49_custody(db))
        v13 = False
        if event.get("schema")=="forge.f139.source-transition.v13":
            db.verify()
            v12_rows=[r for r in db.conn.execute(
                "SELECT sha,payload FROM events "
                "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema")==
                   "forge.f139.source-transition.v12"]
            v13=(len(v12_rows)==1
                 and event.get("from_source_sha")==
                     json.loads(v12_rows[0]["payload"]).get("to_source_sha")
                 and event.get("v12_terminal_event_sha256")==v12_rows[0]["sha"]
                 and verify_g49_custody(db))
        v14 = False
        if event.get("schema")=="forge.f139.source-transition.v14":
            db.verify()
            v13_rows=[r for r in db.conn.execute(
                "SELECT sha,payload FROM events "
                "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema")==
                   "forge.f139.source-transition.v13"]
            v14=(len(v13_rows)==1
                 and event.get("from_source_sha")==
                     json.loads(v13_rows[0]["payload"]).get("to_source_sha")
                 and event.get("v13_terminal_event_sha256")==v13_rows[0]["sha"]
                 and verify_g49_custody(db))
        v15 = False
        if event.get("schema")=="forge.f139.source-transition.v15":
            db.verify()
            v14_rows=[r for r in db.conn.execute(
                "SELECT sha,payload FROM events "
                "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema")==
                   "forge.f139.source-transition.v14"]
            v15=(len(v14_rows)==1
                 and event.get("from_source_sha")==
                     json.loads(v14_rows[0]["payload"]).get("to_source_sha")
                 and event.get("v14_terminal_event_sha256")==v14_rows[0]["sha"]
                 and verify_g49_custody(db))
        v16 = False
        if event.get("schema")=="forge.f139.source-transition.v16":
            db.verify()
            v15_rows=[r for r in db.conn.execute(
                "SELECT sha,payload FROM events "
                "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema")==
                   "forge.f139.source-transition.v15"]
            v16=(len(v15_rows)==1
                 and event.get("from_source_sha")==
                     json.loads(v15_rows[0]["payload"]).get("to_source_sha")
                 and event.get("v15_terminal_event_sha256")==v15_rows[0]["sha"]
                 and verify_g49_custody(db))
        v17 = False
        if event.get("schema")=="forge.f139.source-transition.v17":
            db.verify()
            v16_rows=[r for r in db.conn.execute(
                "SELECT sha,payload FROM events "
                "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")
                if json.loads(r["payload"]).get("schema")==
                   "forge.f139.source-transition.v16"]
            v17=(len(v16_rows)==1
                 and event.get("from_source_sha")==
                     json.loads(v16_rows[0]["payload"]).get("to_source_sha")
                 and event.get("v16_terminal_event_sha256")==v16_rows[0]["sha"]
                 and verify_g49_custody(db))
        if not ((v7 or v8 or v9 or v10 or v11 or v12 or v13 or v14 or v15 or v16 or v17) and event.get("to_source_sha")==source_sha
                and event.get("v2_receipt_authorized") is False):
            return False
        from f139.nci04_owner_ledger import verify_native_activation
        return verify_native_activation(db)
    except (F139Error, sqlite3.DatabaseError, ValueError, TypeError, KeyError):
        return False


def original_owner_v2_guard_canonical(db, db_path: Path,
                                      source_sha: str) -> bool:
    """Run the strict V2 release guard on original canonical DB under -m.

    A Python -m entrypoint constructs __main__.Database. The G38 guard
    deliberately rejects that different type. Preserve its exact type check:
    use a verified, separately opened canonical handle to the SAME original
    SQLite ledger, never a relocated copy or a class-name comparison.
    """
    from f139.local_controller import (
        Database as CanonicalDatabase,
        v2_owner_terminal_release_guard as CanonicalGuard,
    )
    source = Path(db.filename).resolve(strict=True)
    require(source == Path(db_path).resolve(strict=True),
            "G52_ORIGINAL_V2_GUARD_DB_PATH_DRIFT")
    original_meta = db.meta()
    canonical = CanonicalDatabase(source)
    try:
        meta = canonical.meta()
        require(all(meta[k] == original_meta[k] for k in (
                "source_sha", "head_seq", "head_hash", "epoch")),
                "G52_ORIGINAL_V2_GUARD_LEDGER_DRIFT")
        return CanonicalGuard(source_sha, canonical)
    finally:
        canonical.close()


def settle_original_v2_canonical(db, api, db_path: Path, *,
                                 ticket: str, run_id: int,
                                 started_at: str, owner_key: str):
    """Keep the original mutex; settle with strict canonical DB/API types.

    G38 authenticates BOTH GitHub provider platforms and appends one real
    terminal receipt. __main__.Database/Hub are not those canonical types.
    Under the existing process mutex, use freshly verified handles pointed
    to the same original SQLite and the same gh provider. Never replay.
    """
    from f139.local_controller import (
        Database as CanonicalDatabase, GitHub as CanonicalGitHub,
    )
    from f139.nci04_g38_owner_terminal import settle_original_v2
    path = Path(db_path).resolve(strict=True)
    require(Path(db.filename).resolve(strict=True) == path
            and SingleOwner.held(path.with_suffix(".lock")),
            "G52_ORIGINAL_TERMINAL_LOCK_OR_PATH_DRIFT")
    original = db.meta()
    canonical_db = CanonicalDatabase(path)
    try:
        current = canonical_db.meta()
        require(all(current[k] == original[k] for k in (
            "source_sha", "head_seq", "head_hash", "epoch")),
            "G52_ORIGINAL_TERMINAL_LEDGER_DRIFT")
        return settle_original_v2(
            canonical_db, CanonicalGitHub(), path,
            ticket=ticket, run_id=run_id, started_at=started_at,
            owner_key=owner_key)
    finally:
        canonical_db.close()

def original_owner_v2_fields_canonical(db, db_path: Path, ticket: str,
                                       *, owner_hmac_key: str):
    """Resolve -m/__main__ class identity without relaxing the G36 type guard.

    The original tick owns the SingleOwner lock and has ALREADY persisted its
    unique BEFORE_DISPATCH_INTENT claim. G36 deliberately accepts only the
    canonical imported Database type. Open a SECOND verified handle to the
    SAME SQLite file solely to read that immutable claim and sign its fields.
    This function does not post a workflow or mutate claim/ledger state.
    """
    from f139.local_controller import Database as CanonicalDatabase
    from f139.nci04_g36_v2_dispatch import original_owner_v2_fields
    actual = Path(db.filename).resolve(strict=True)
    requested = Path(db_path).resolve(strict=True)
    require(actual == requested, "G47_ORIGINAL_DATABASE_PATH_DRIFT")
    expected = db.meta()
    canonical_db = CanonicalDatabase(actual)
    try:
        observed = canonical_db.meta()
        require(all(observed[key] == expected[key] for key in (
                    "source_sha", "head_seq", "head_hash", "epoch")),
                "G47_ORIGINAL_LEDGER_HEAD_DRIFT")
        return original_owner_v2_fields(
            canonical_db, ticket, owner_hmac_key=owner_hmac_key)
    finally:
        canonical_db.close()


def run_once(db:Database,api:GitHub,db_path:Path,hmac_key:str, *, now=None):
    timestamp=now or utc_now()
    require(len(hmac_key)>=32,"WORKER_HMAC_SECRET_MISSING")
    db.verify()
    from f139.nci04_owner_ledger import verify_native_activation
    # Original Tick/Loop now recognizes only a genuine append-only owner
    # activation event, not an issue label, environment toggle or auto-setup.
    native_enabled = verify_native_activation(db)
    meta=db.meta()
    require(meta["enabled"]==1 and meta["legacy_suspended"]==1,"CONTROLLER_INACTIVE_OR_LEGACY_RUNNING")
    # An unrelated protected-main merge must not prevent evidence-only
    # reconciliation of provider runs dispatched under the pinned old SHA.
    # New issue intake and dispatch still fail closed until exact owner cutover.
    protected_now=api.protected_main()
    source_matches=(protected_now==meta["source_sha"])
    if not source_matches:
        # Bounded research-only additions cannot silently rewrite the F139
        # runtime. Any other source drift retains the original dispatch block.
        verifier=getattr(api,"research_only_main_advance",None)
        if callable(verifier):
            source_matches=verifier(meta["source_sha"],protected_now) is True
        if not source_matches and native_enabled:
            pinned=getattr(api,"deployed_release_continuity",None)
            if callable(pinned):
                source_matches=pinned(
                    db,meta["source_sha"],protected_now) is True
    legacy_pending={}
    for active_record in db.actives():
        active=dict(active_record)
        try:
            pinned_lookup=getattr(api,"candidates_for_source",None)
            if (callable(pinned_lookup) and native_enabled
                    and active["ticket"].startswith("f139-nci04-")
                    and active["source_sha"]==meta["source_sha"]):
                run=pinned_lookup(active["ticket"],active["started_at"],
                                  active["source_sha"])
            else:
                run=api.candidates(active["ticket"],active["started_at"])
            if run is None:
                if not active["ticket"].startswith("f139-nci04-"):
                    legacy_pending[active["ticket"]]="START_RISK_PENDING_NO_REDISPATCH"
                continue  # Ambiguous provider startup remains sticky for this ticket.
            # A fresh G13-native Yggdrasil V2 ticket is never interpreted
            # by the old V1 receipt parser. The single original controller
            # authenticates GitHub and commits both OS results as one SQLite
            # transaction. Historical V1 and quarantined records unchanged.
            if active["ticket"].startswith("f139-nci04-"):
                from f139.nci04_owner_ledger import frozen_native_issue
                from f139.nci04_worker_v2 import SOURCE_SHA as V2_SHA
                from f139.nci04_worker_v2 import SOURCE_TREE as V2_TREE
                original = frozen_native_issue(db, active["ticket"])
                if (original.lane == "Yggdrasil"
                        and original.candidate.target_commit == V2_SHA
                        and original.candidate.target_tree_sha == V2_TREE
                        and original.candidate.path ==
                            "yggdrasil/public_causal_cells.py"):
                    if run.get("status") in (
                            "queued","requested","in_progress",
                            "waiting","pending"):
                        continue
                    from f139.nci04_g38_owner_terminal import settle_original_v2
                    try:
                        settle_original_v2_canonical(
                            db, api, db_path, ticket=active["ticket"],
                            run_id=run["id"], started_at=active["started_at"],
                            owner_key=hmac_key)
                    except (F139Error, ValueError):
                        # Fail closed for THIS original V2 ticket. Provider
                        # timeout, missing artifact or invalid signed receipt
                        # must not abort a tick before the other active native
                        # worker can reach its terminal. This attempt stays
                        # WAIT_PROVIDER: never requeue, synthesize a receipt,
                        # or infer success from incomplete provider evidence.
                        legacy_pending[active["ticket"]] = (
                            "V2_PROVIDER_EVIDENCE_UNVERIFIED_NO_REPLAY")
                        continue
                    continue
            result=api.run_proof(run,active["ticket"],active["source_sha"],active["started_at"])
            if result is None:
                if not active["ticket"].startswith("f139-nci04-"):
                    legacy_pending[active["ticket"]]="WORKER_RUNNING_NO_REDISPATCH"
                continue  # One in-flight native worker must not starve the second.
            rid,artifacts=result
            archives={}
            for oslabel in ("ubuntu-latest","windows-latest"):
                prefix=("forge-f139-native-receipt-" if
                        active["ticket"].startswith("f139-nci04-") else
                        "forge-f139-dev-receipt-")
                matching=[x for x in artifacts if x.get("name")==prefix+oslabel]
                require(len(matching)==1,"AMBIGUOUS_PROVIDER_ARTIFACT")
                raw=api.artifact(matching[0]["id"])
                if active["ticket"].startswith("f139-nci04-"):
                    from f139.nci04_provider_receipt import native_receipt_from_zip
                    from f139.nci04_owner_ledger import frozen_native_issue
                    native_receipt_from_zip(
                        raw, matching[0], active, rid, oslabel,
                        meta["epoch"], frozen_native_issue(db,active["ticket"]),
                        owner_hmac_key=hmac_key)
                else:
                    receipt_from_zip(raw,matching[0],active,rid,oslabel,meta["epoch"],
                                     d2k_fields=db.d2k_fields(active["ticket"]))
                archives[oslabel]=raw
            path,digest=store_evidence(db_path.parent,active["ticket"],rid,archives)
            db.terminal(active["ticket"],rid,path,digest)
        except F139Error as exc:
            # Provider failures are sticky. An API timeout is epistemically ambiguous;
            # preserve START_RISK and do not transition to a retryable READY.
            code=str(exc).removeprefix("F139_")
            if code not in {"GITHUB_API_TIMEOUT","GITHUB_API_FAILED","GITHUB_API_INVALID_JSON"}:
                reporter=getattr(api,"failed_native_provider_report",None)
                if (code=="FAILED_OR_CANCELLED_NO_REPLAY"
                        and active["ticket"].startswith("f139-nci04-")
                        and isinstance(locals().get("run"),dict)
                        and callable(reporter)):
                    report=reporter(
                        run,active["ticket"],active["source_sha"],active["started_at"])
                    db.custody_failed_native_provider(
                        active["ticket"],report,late=False)
                else:
                    db.quarantine(active["ticket"],
                        code if re.fullmatch(r"[A-Z_]{3,72}",code)
                        else "UNCLASSIFIED_REJECTION")
            raise
    remaining=db.actives()
    if not source_matches:
        return {"disposition":"MAIN_SOURCE_DRIFT_DISPATCH_BLOCKED",
                "owner_source_sha":meta["source_sha"],
                "protected_main_sha":protected_now,
                "active_tickets":[row["ticket"] for row in remaining],
                "scientific_first_use":False}
    if len(remaining) >= 2:
        return {"disposition":"TWO_NATIVE_WORKERS_ACTIVE_NO_REDISPATCH",
                "tickets":[row["ticket"] for row in remaining]}
    if remaining and not remaining[0]["ticket"].startswith("f139-nci04-"):
        return {"disposition":legacy_pending.get(
                    remaining[0]["ticket"],"WORKER_RUNNING_NO_REDISPATCH"),
                "ticket":remaining[0]["ticket"]}
    ready=db.ready()
    if ready is None and db.admit_d2j_succession():
        ready=db.ready()
    if ready is None and db.active() is None and db.meta()["head_seq"] >= 23:
        # Only issue-authorized development tasks; never invent work to stay busy.
        # Reuse the existing SQLite mutex, source check, and daily dispatch budget.
        known = {row["ticket"] for row in db.conn.execute("SELECT ticket FROM tasks")}
        seen_issue_numbers = {
            json.loads(row["payload"])["issue_number"]
            for row in db.conn.execute(
                "SELECT payload FROM events WHERE kind='DEVELOPMENT_WORK_ADMITTED'")
        }
        for item in api.d2k_eligible_issues(meta["source_sha"]):
            if item["ticket"] in known or item["issue_number"] in seen_issue_numbers:
                continue
            if db.admit_d2k_issue(item):
                ready=db.ready()
            break
    publication_slot_empty = False
    steering_selection = None  # Advisory observation; never an authority.
    if ready is None and native_enabled:
        # Same single-owner lock, SQLite ledger and once-only budget as D2K.
        # A source-pinned owner policy may replenish this EXISTING issue intake
        # from explicit owner-authored "F139 autonomy DEV:" native PRs. It
        # creates no second controller/scheduler/queue and grants no science.
        from f139.nci04_owner_ledger import admit_native_issue, native_events
        feeder = getattr(api, "prepare_native_feed", None)
        known = {row["ticket"] for row in db.conn.execute("SELECT ticket FROM tasks")}
        events = native_events(db)
        # Reconstruct historical identities only from the already-verified
        # append-only owner ledger. The public issue label alone cannot
        # reauthorize or replay any old native candidate.
        historical_issues = {
            event["issue_number"]: (
                event["issue_id"], event["source_sha"],
                event["issue_body_sha256"], event["ticket"])
            for event in events
        }
        eligible = api.native_eligible_issues(
            meta["source_sha"], historical_issues=historical_issues)
        for native_issue in eligible:
            if native_issue.ticket in known:
                continue
            if admit_native_issue(db, native_issue, timestamp):
                ready = db.ready()
            break
        if ready is None and not eligible and callable(feeder):
            from f139.nci04_autonomy_feed import (
                candidate_identity_from_intent_base64)
            existing_candidates = {
                candidate_identity_from_intent_base64(
                    event["native_intent_base64"])
                for event in events
                if isinstance(event.get("native_intent_base64"), str)
            }
            # No unauthenticated owner issue is inferred: the feed policy
            # itself is owner-authored and exact-source pinned, and every PR
            # candidate is independently rebound to an immutable commit/tree.
            feed = feeder(
                meta["source_sha"], existing_candidates)
            # Feeder authenticated all source-bound candidates before
            # producing this read-only selection telemetry.
            steering_selection = feed.get("steering")
            created_numbers = []
            for candidate in feed["candidates"]:
                created = api.create_native_feed_issue(
                    title=candidate["issue_title"],
                    body=candidate["issue_body"])
                created_numbers.append(created["number"])
            if not feed["candidates"]:
                publication_slot_empty = True
            if created_numbers:
                # Reuse the unchanged owner-issue authentication and ledger
                # admission path. Never dispatch directly from a PR.
                eligible = api.native_eligible_issues(
                    meta["source_sha"], historical_issues=historical_issues)
                for native_issue in eligible:
                    if native_issue.number not in created_numbers:
                        continue
                    if admit_native_issue(db, native_issue, timestamp):
                        ready = db.ready()
                    break
    if (ready is None and publication_slot_empty and not db.actives()
            and type(api) is GitHub):
        # Only the live original owner, under the existing SingleOwner mutex.
        # G3 is draft-only: the NEXT ordinary tick must discover/rehash the PR,
        # admit its issue and separately dispatch. Never dispatch from here.
        # After the finite G3 attempt is historically consumed, try exactly
        # one already-registered model-free G29 development mechanism through
        # the merged original-owner model response and draft publisher path.
        # This is finite, not general model inference or ongoing autonomous
        # research. It uses no API inference or Codex credits.
        prior_g3 = db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='G3_DRAFT_ATTEMPTED'"
        ).fetchone()[0]
        if prior_g3:
            # Every model draft, including G29, must have a separately
            # authenticated terminal publication before another model call.
            # A lost GitHub ACK or partial remote write is NEVER retryable,
            # even with fresh native outcomes.
            model_attempts=db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind='MODEL_DRAFT_ATTEMPTED'"
            ).fetchone()[0]
            model_successes=db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind='MODEL_DRAFT_AUTHENTICATED'"
            ).fetchone()[0]
            if model_attempts != model_successes:
                return {"disposition":"MODEL_DRAFT_UNRESOLVED_NO_REPLAY",
                        "scientific_first_use":False,
                        "worker_dispatched":False,"paid_model_calls":0}
            if model_successes:
                # The one frozen model-free G29 mechanism has completed. The
                # free reasoner is advisory-only, bounded to public data and
                # the original SHA-chained terminal outcomes. No credentials:
                # no request. No inferred science/merge/worker authority.
                from f139.nci04_owner_free_reasoner_proposal import (
                    run_original_free_reasoner_once)
                try:
                    return run_original_free_reasoner_once(
                        db, api, db_path, source_sha=meta["source_sha"],
                        owner_witness=lambda:
                            native_original_running_publisher_profile(db_path))
                except (F139Error, ValueError):
                    return {"disposition":"FREE_REASONER_GUARD_BLOCKED_FAIL_CLOSED",
                            "scientific_first_use":False,
                            "worker_dispatched":False,"paid_model_calls":0}
            from f139.nci04_owner_model_free_bootstrap import (
                run_original_g29_once)
            try:
                return run_original_g29_once(
                    db, api, db_path, meta["source_sha"],
                    owner_witness=lambda:
                        native_original_running_publisher_profile(db_path))
            except (F139Error, ValueError):
                # No G3 replay and no authority inferred from a failed G29
                # source or owner witness. The next normal tick can recheck
                # the original ledger; an ambiguous draft attempt stays stuck.
                return {"disposition":"LOCAL_G29_PUBLISH_BLOCKED_FAIL_CLOSED",
                        "scientific_first_use":False,
                        "worker_dispatched":False,
                        "paid_model_calls":0}
        from f139.nci04_owner_publication import publish_once
        try:
            publication = publish_once(
                db, api.native_repo_get, api.owner_g3_write,
                meta["source_sha"],
                owner_witness=lambda: native_original_running_publisher_profile(db_path))
        except (F139Error, ValueError):
            # Optional G3 publication must not terminate the original F139
            # reconciliation/dispatch loop on a failed owner or API preflight.
            publication = {"disposition": "G3_PUBLISH_BLOCKED_FAIL_CLOSED"}
        # Preserve truthful publication disposition (including no-retry).
        if steering_selection is not None and isinstance(publication, dict):
            publication = dict(publication, steering_selection=steering_selection)
        return publication
    if ready is None:
        report = {"disposition":"QUEUE_EMPTY_NO_SCIENCE",
                  "completed":db.conn.execute("SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'").fetchone()[0]}
        if steering_selection is not None:
            report["steering_selection"] = steering_selection
        return report
    task=dict(ready)
    # Never attempt V2 under legacy default routing: G35/G32 provider
    # terminal custody must be separately deployed before dispatch.
    v2_original=False
    if task["ticket"].startswith("f139-nci04-"):
        from f139.nci04_owner_ledger import frozen_native_issue
        from f139.nci04_worker_v2 import SOURCE_SHA as V2_SHA, SOURCE_TREE as V2_TREE
        proposed=frozen_native_issue(db,task["ticket"])
        v2_original=(proposed.lane=="Yggdrasil" and
                     proposed.candidate.target_commit==V2_SHA and
                     proposed.candidate.target_tree_sha==V2_TREE and
                     proposed.candidate.path=="yggdrasil/public_causal_cells.py")
        if v2_original and not original_owner_v2_guard_canonical(
                db, db_path, meta["source_sha"]):
            return {"disposition":"V2_TERMINAL_CUSTODY_NOT_AUTHORIZED",
                    "ticket":task["ticket"],"claimed":False,
                    "live_v2_dispatched":False,"science_authorized":False}
    db.claim(task["ticket"],timestamp)
    from f139.verify_ticket import signature as sign_worker_ticket
    d2k=db.d2k_fields(task["ticket"])
    native = task["ticket"].startswith("f139-nci04-")
    if native:
        require(native_enabled, "NATIVE_DISPATCH_NOT_ACTIVATED")
        from f139.nci04_owner_ledger import frozen_native_issue
        from f139.nci04_owner_issue import make_signed_dispatch_inputs
        issue = frozen_native_issue(db, task["ticket"])
        if v2_original:
            # Under this same ORIGINAL SingleOwner + START_RISK transaction
            # chain, produce a fresh V2 claim; never use a V1 fallback.
            fields = original_owner_v2_fields_canonical(
                db, db_path, task["ticket"], owner_hmac_key=hmac_key)
        else:
            fields = make_signed_dispatch_inputs(
                issue, owner_hmac_key=hmac_key, epoch=meta["epoch"])
        api.dispatch_native(fields, issue)
    else:
        signature=sign_worker_ticket(hmac_key,task["ticket"],task["lane"],
                                     task["source_sha"],str(meta["epoch"]),
                                     **(d2k or {}))
        if d2k is not None:
            api.dispatch(task["ticket"],task["lane"],task["source_sha"],
                         meta["epoch"],signature,d2k_fields=d2k)
        else:
            api.dispatch(task["ticket"],task["lane"],task["source_sha"],meta["epoch"],signature)
    db.dispatch_observed(task["ticket"])
    report = {"disposition":"DEVELOPMENT_DISPATCHED_ONCE",
              "ticket":task["ticket"],"science_authorized":False}
    if steering_selection is not None:
        report["steering_selection"] = steering_selection
    return report


def cli(argv=None):
    parser=argparse.ArgumentParser(description="FORGE F139 single Windows controller; development only")
    parser.add_argument("--db",type=Path,required=True)
    sub=parser.add_subparsers(dest="verb",required=True)
    init=sub.add_parser("init");init.add_argument("--source-sha",required=True)
    queue=sub.add_parser("queue");queue.add_argument("--manifest",type=Path,required=True)
    sub.add_parser("status")
    sub.add_parser("upgrade-native-two-slots")  # explicit original-owner action only
    enable=sub.add_parser("activate");enable.add_argument("--legacy-suspended-evidence",type=Path,required=True)
    sub.add_parser("tick")
    owner_native=sub.add_parser("activate-native")
    owner_native.add_argument("--approval",type=Path,required=True)
    transition=sub.add_parser("transition-qualified-native")
    transition.add_argument("--approval",type=Path,required=True)
    transition_v6=sub.add_parser("transition-qualified-native-v6")
    transition_v6.add_argument("--approval",type=Path,required=True)
    transition_v7=sub.add_parser("transition-qualified-native-v7")
    transition_v7.add_argument("--approval",type=Path,required=True)
    transition_v8=sub.add_parser("transition-qualified-native-v8")
    transition_v8.add_argument("--approval",type=Path,required=True)
    transition_v9=sub.add_parser("transition-qualified-native-v9")
    transition_v9.add_argument("--approval",type=Path,required=True)
    transition_v10=sub.add_parser("transition-qualified-native-v10")
    transition_v10.add_argument("--approval",type=Path,required=True)
    transition_v11=sub.add_parser("transition-qualified-native-v11")
    transition_v11.add_argument("--approval",type=Path,required=True)
    transition_v12=sub.add_parser("transition-qualified-native-v12")
    transition_v12.add_argument("--approval",type=Path,required=True)
    transition_v13=sub.add_parser("transition-qualified-native-v13")
    transition_v13.add_argument("--approval",type=Path,required=True)
    transition_v14=sub.add_parser("transition-qualified-native-v14")
    transition_v14.add_argument("--approval",type=Path,required=True)
    transition_v15=sub.add_parser("transition-qualified-native-v15")
    transition_v15.add_argument("--approval",type=Path,required=True)
    transition_v16=sub.add_parser("transition-qualified-native-v16")
    transition_v16.add_argument("--approval",type=Path,required=True)
    transition_v17=sub.add_parser("transition-qualified-native-v17")
    transition_v17.add_argument("--approval",type=Path,required=True)
    sub.add_parser("custody-original-native-negative")
    sub.add_parser("custody-original-native-split-negative")
    sub.add_parser("custody-quarantined-native-provider-failures")
    loop=sub.add_parser("loop");loop.add_argument("--seconds",type=int,default=45)
    args=parser.parse_args(argv)
    if args.verb=="init":
        db=Database.initialize(args.db,args.source_sha)
    else:
        db=Database(args.db)
    try:
        if args.verb=="queue":
            raw=args.manifest.read_bytes()
            require(len(raw)<=65536,"MANIFEST_TOO_LARGE")
            manifest=json.loads(raw)
            require(isinstance(manifest,dict) and set(manifest)=={"schema","source_sha","tasks"}
                    and manifest["schema"]=="forge.f139.development-queue.v1"
                    and manifest["source_sha"]==db.meta()["source_sha"],"MANIFEST_IDENTITY_INVALID")
            db.enqueue(manifest["tasks"],hash_bytes(raw))
        elif args.verb=="activate":
            # Not an authorization by itself: require qualified operator-created
            # attestation of a real F136/F137 disablement and tested source.
            path=args.legacy_suspended_evidence
            proof=json.loads(path.read_text())
            require(proof=={"schema":"forge.f139.local-cutover-evidence.v1",
                           "main_sha":db.meta()["source_sha"],"legacy_dispatch_disabled":True,
                           "independent_qualifier_pass":True,"controller_single_owner":True},
                    "CUTOVER_EVIDENCE_INCOMPLETE")
            require(GitHub().protected_main()==db.meta()["source_sha"],"CUTOVER_SOURCE_DRIFT")
            GitHub().legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            db.enable(legacy_suspended=True)
        elif args.verb=="upgrade-native-two-slots":
            # This is NEVER invoked on controller startup or on the worker.
            # The owner may explicitly migrate only its exact clean protected
            # source, after existing controlled source transition, with no
            # active tasks. No historical event is rewritten.
            native_original_owner_profile(args.db)
            api=GitHub()
            require(api.protected_main()==db.meta()["source_sha"],
                    "DUAL_NATIVE_UPGRADE_PROTECTED_SOURCE_DRIFT")
            checkout=Path(__file__).resolve().parent.parent
            def _git(*parts):
                p=subprocess.run(["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(p.returncode==0,"DUAL_NATIVE_UPGRADE_GIT_FAILED")
                return p.stdout.decode("utf-8").strip()
            require(_git("rev-parse","HEAD")==db.meta()["source_sha"]
                    and _git("status","--porcelain","--untracked-files=all")=="",
                    "DUAL_NATIVE_UPGRADE_UNQUALIFIED_CHECKOUT")
            with SingleOwner(args.db.with_suffix(".lock")):
                upgraded=db.enable_native_two_slots()
                print(json.dumps({
                    "native_two_slot_schema_upgraded":upgraded,
                    "source_sha":db.meta()["source_sha"],
                    "event_head_sha256":db.meta()["head_hash"],
                    "scientific_first_use":False},sort_keys=True))
        elif args.verb=="custody-original-native-negative":
            # One authorized, development-only owner CLI. No GitHub dispatch
            # method, second task, new controller or scientific first-use.
            from f139.nci04_negative_owner_store import (
                admit_original_negative_custody, RUN_ID as NEGATIVE_RUN_ID,
                ARTIFACT_ID as NEGATIVE_ARTIFACT_ID)
            native_original_owner_profile(args.db)
            legacy_windows_task_disabled()
            api=GitHub()
            checkout=Path(__file__).resolve().parent.parent
            head=subprocess.run(["git","-C",str(checkout),"rev-parse","HEAD"],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,timeout=15,check=False)
            clean=subprocess.run(["git","-C",str(checkout),"status","--porcelain",
                                  "--untracked-files=all"],stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,
                                 timeout=15,check=False)
            require(head.returncode==0 and clean.returncode==0
                    and not clean.stdout.strip()
                    and head.stdout.decode().strip()==api.protected_main(),
                    "NEGATIVE_CUSTODY_CHECKOUT_NOT_PROTECTED_MAIN")
            api.legacy_dispatchers_disabled()
            hmac_key=os.environ.get("F139_WORKER_HMAC_KEY","")
            require(len(hmac_key)>=32,"NEGATIVE_CUSTODY_OWNER_HMAC_UNAVAILABLE")
            with SingleOwner(args.db.with_suffix(".lock")):
                db.verify()
                # Verify original owner database is unchanged BEFORE making
                # any external retrieval. Never issue workflow_dispatch.
                from f139.nci04_negative_owner_store import (
                    OWNER_HEAD, SOURCE_SHA as NEGATIVE_SOURCE)
                meta=db.meta()
                require(meta["source_sha"]==NEGATIVE_SOURCE
                        and meta["head_seq"]==47
                        and meta["head_hash"]==OWNER_HEAD,
                        "NEGATIVE_CUSTODY_NOT_ORIGINAL_47_EVENT_BOUNDARY")
                run=api.get(f"repos/{REPO}/actions/runs/{NEGATIVE_RUN_ID}")
                run_jobs=api.get(
                    f"repos/{REPO}/actions/runs/{NEGATIVE_RUN_ID}/jobs?per_page=100")
                job_list=run_jobs.get("jobs")
                require(isinstance(job_list,list)
                        and run_jobs.get("total_count")==4
                        and len(job_list)==4,
                        "NEGATIVE_CUSTODY_PROVIDER_JOBS_INVALID")
                artifacts=api.get(
                    f"repos/{REPO}/actions/runs/{NEGATIVE_RUN_ID}/artifacts?per_page=100")
                archive_list=artifacts.get("artifacts")
                require(isinstance(archive_list,list)
                        and artifacts.get("total_count")==1
                        and len(archive_list)==1
                        and archive_list[0].get("id")==NEGATIVE_ARTIFACT_ID,
                        "NEGATIVE_CUSTODY_PROVIDER_ARTIFACT_INVALID")
                artifact=archive_list[0]
                archive=api.artifact(NEGATIVE_ARTIFACT_ID)
                result=admit_original_negative_custody(
                    db,run=run,jobs=job_list,artifact=artifact,
                    archive=archive,owner_hmac_key=hmac_key,
                    epoch=meta["epoch"])
                print(json.dumps(result,sort_keys=True))
        elif args.verb=="custody-original-native-split-negative":
            # Owner-only original #706 custody; never dispatch or replay a task.
            from f139.nci04_split_negative_owner_store import (
                admit_second_negative_custody, RUN_ID as SPLIT_RUN_ID,
                ARTIFACT_ID as SPLIT_ARTIFACT_ID, SOURCE as SPLIT_SOURCE,
                OWNER_HEAD_55 as SPLIT_HEAD_55)
            from f139.nci04_negative_owner_store import verify_original_negative_custody
            native_original_owner_profile(args.db)
            legacy_windows_task_disabled()
            api=GitHub()
            checkout=Path(__file__).resolve().parent.parent
            head=subprocess.run(["git","-C",str(checkout),"rev-parse","HEAD"],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,timeout=15,check=False)
            clean=subprocess.run(["git","-C",str(checkout),"status","--porcelain",
                                  "--untracked-files=all"],stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,
                                 timeout=15,check=False)
            require(head.returncode==0 and clean.returncode==0
                    and not clean.stdout.strip()
                    and head.stdout.decode().strip()==api.protected_main(),
                    "SPLIT_CUSTODY_CHECKOUT_NOT_PROTECTED_MAIN")
            api.legacy_dispatchers_disabled()
            hmac_key=os.environ.get("F139_WORKER_HMAC_KEY","")
            require(len(hmac_key)>=32,"SPLIT_CUSTODY_OWNER_HMAC_UNAVAILABLE")
            with SingleOwner(args.db.with_suffix(".lock")):
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==SPLIT_SOURCE
                        and meta["head_seq"]==55
                        and meta["head_hash"]==SPLIT_HEAD_55
                        and verify_original_negative_custody(db),
                        "SPLIT_CUSTODY_NOT_ORIGINAL_55_EVENT_BOUNDARY")
                run=api.get(f"repos/{REPO}/actions/runs/{SPLIT_RUN_ID}")
                run_jobs=api.get(
                    f"repos/{REPO}/actions/runs/{SPLIT_RUN_ID}/jobs?per_page=100")
                jobs=run_jobs.get("jobs")
                require(isinstance(jobs,list)
                        and run_jobs.get("total_count")==4 and len(jobs)==4,
                        "SPLIT_CUSTODY_PROVIDER_JOBS_INVALID")
                artifacts=api.get(
                    f"repos/{REPO}/actions/runs/{SPLIT_RUN_ID}/artifacts?per_page=100")
                items=artifacts.get("artifacts")
                require(isinstance(items,list) and artifacts.get("total_count")==1
                        and len(items)==1 and items[0].get("id")==SPLIT_ARTIFACT_ID,
                        "SPLIT_CUSTODY_PROVIDER_ARTIFACT_INVALID")
                archive=api.artifact(SPLIT_ARTIFACT_ID)
                result=admit_second_negative_custody(
                    db,run=run,jobs=jobs,artifacts=items,archive=archive,
                    owner_hmac_key=hmac_key,epoch=meta["epoch"])
                print(json.dumps(result,sort_keys=True))
        elif args.verb=="custody-quarantined-native-provider-failures":
            # Exact original failed attempts only; no replay or new dispatch.
            native_original_owner_profile(args.db)
            api=GitHub()
            checkout=Path(__file__).resolve().parent.parent
            head=subprocess.run(["git","-C",str(checkout),"rev-parse","HEAD"],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,timeout=15,check=False)
            clean=subprocess.run(["git","-C",str(checkout),"status","--porcelain",
                                  "--untracked-files=all"],stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,
                                 timeout=15,check=False)
            require(head.returncode==0 and clean.returncode==0
                    and not clean.stdout.strip()
                    and head.stdout.decode().strip()==api.protected_main(),
                    "LATE_CUSTODY_CHECKOUT_NOT_PROTECTED_MAIN")
            with SingleOwner(args.db.with_suffix(".lock")):
                db.verify()
                already=set(db.verified_native_provider_failures())
                rows=list(db.conn.execute(
                    "SELECT ticket,source_sha,started_at,stage,quarantine_reason "
                    "FROM tasks WHERE stage='QUARANTINED' "
                    "AND ticket LIKE 'f139-nci04-%' ORDER BY started_at,ticket"))
                added=[]
                for row in rows:
                    if row["ticket"] in already or row["quarantine_reason"]!=(
                            "FAILED_OR_CANCELLED_NO_REPLAY"):
                        continue
                    run=api.candidates(row["ticket"],row["started_at"])
                    require(run is not None,"LATE_CUSTODY_PROVIDER_RUN_MISSING")
                    report=api.failed_native_provider_report(
                        run,row["ticket"],row["source_sha"],row["started_at"])
                    db.custody_failed_native_provider(
                        row["ticket"],report,late=True)
                    added.append(row["ticket"])
                print(json.dumps({
                    "late_provider_negative_custody":"PASS",
                    "added_tickets":added,
                    "event_head":db.meta()["head_hash"],
                    "scientific_first_use":False},sort_keys=True))
        elif args.verb=="transition-qualified-native":
            # The owner must run this exact, qualified, protected-main checkout;
            # never rewrite historical identities or reset the event chain.
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"SOURCE_APPROVAL_FILE_INVALID")
            proof=json.loads(raw)
            from f139.nci04_owner_ledger import SEALED_OWNER_PREFIX_HEAD
            expected={"schema","from_source_sha","to_source_sha",
                      "expected_event_head_sha256","sealed_23_event_head_sha256",
                      "native_development_only","scientific_first_use",
                      "new_controller","paid_api_calls"}
            require(isinstance(proof,dict) and set(proof)==expected
                    and proof["schema"]==
                       "forge.f139.nci04.owner-source-transition-approval.v1"
                    and proof["from_source_sha"]==db.meta()["source_sha"]
                    and proof["expected_event_head_sha256"]==db.meta()["head_hash"]
                    and proof["sealed_23_event_head_sha256"]==SEALED_OWNER_PREFIX_HEAD
                    and proof["native_development_only"] is True
                    and proof["scientific_first_use"] is False
                    and proof["new_controller"] is False
                    and type(proof["paid_api_calls"]) is int
                    and proof["paid_api_calls"]==0
                    and isinstance(proof["to_source_sha"],str)
                    and SHA.fullmatch(proof["to_source_sha"]) is not None,
                    "SOURCE_TRANSITION_APPROVAL_INVALID")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read(*parts):
                p=subprocess.run(["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(p.returncode==0,"TRANSITION_CHECKOUT_GIT_FAILED")
                return p.stdout.decode("utf-8").strip()
            require(_git_read("rev-parse","HEAD")==proof["to_source_sha"]
                    and _git_read("status","--porcelain","--untracked-files=all")=="",
                    "TRANSITION_CHECKOUT_NOT_EXACT_CLEAN_SOURCE")
            api=GitHub()
            require(api.protected_main()==proof["to_source_sha"],
                    "TRANSITION_PROTECTED_MAIN_UNQUALIFIED")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                db.verify()
                require(db.meta()["head_hash"]==proof["expected_event_head_sha256"],
                        "TRANSITION_EVENT_HEAD_CHANGED")
                from f139.nci04_negative_owner_store import (
                    verify_original_negative_custody, TICKET as NEGATIVE_TICKET)
                excluded=list(db.conn.execute(
                    "SELECT ticket,stage FROM tasks WHERE stage!='VERIFIED'"))
                from f139.nci04_split_negative_owner_store import (
                    verify_second_negative_custody, TICKET as SECOND_TICKET)
                excluded_tickets={r["ticket"] for r in excluded}
                provider_negative_tickets=set(db.verified_native_provider_failures())
                has_certified_negative=(
                    len(excluded)==1 and excluded_tickets=={NEGATIVE_TICKET}
                    and excluded[0]["stage"]=="QUARANTINED"
                    and verify_original_negative_custody(db)
                    or len(excluded)==2
                    and excluded_tickets=={NEGATIVE_TICKET, SECOND_TICKET}
                    and all(r["stage"]=="QUARANTINED" for r in excluded)
                    and verify_original_negative_custody(db)
                    and verify_second_negative_custody(db)
                    or len(excluded)>=3
                    and excluded_tickets==(
                        {NEGATIVE_TICKET,SECOND_TICKET}|provider_negative_tickets)
                    and bool(provider_negative_tickets)
                    and all(r["stage"]=="QUARANTINED" for r in excluded)
                    and verify_original_negative_custody(db)
                    and verify_second_negative_custody(db))
                require(not excluded or has_certified_negative,
                        "NEGATIVE_HISTORY_NOT_SAFELY_CUSTODIED")
                db.transition_source(
                    proof["to_source_sha"],
                    allow_certified_negative=has_certified_negative)
                print(json.dumps({"native_source_transition":"PASS",
                    "source_sha":db.meta()["source_sha"],
                    "head_sha256":db.meta()["head_hash"],
                    "scientific_first_use":False},sort_keys=True))
        elif args.verb=="transition-qualified-native-v6":
            # DISTINCT operator action, never the legacy transition's approval.
            # No worker V2 activation, no new scheduler and no automatic promotion.
            from f139.nci04_v6_owner_release import validate_v6_owner_approval
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V6_SOURCE_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict, "V6_APPROVAL_MUST_BE_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v6(*parts):
                p=subprocess.run(["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(p.returncode==0,"V6_SOURCE_CHECKOUT_GIT_FAILED")
                return p.stdout.decode("utf-8").strip()
            require(_git_read_v6("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v6("status","--porcelain","--untracked-files=all")=="",
                    "V6_EXACT_CLEAN_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V6_PROTECTED_SOURCE_IDENTITY_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                db.verify()
                validate_v6_owner_approval(db,approval)
                db.transition_source(
                    approval["to_source_sha"],
                    allow_certified_negative=True,
                    allow_v6=True)
                db.verify()
                require(db.meta()["source_sha"]==approval["to_source_sha"]
                        and db.meta()["head_seq"]==approval["expected_event_head_seq"]+1,
                        "V6_TRANSACTION_RESULT_DRIFT")
                print(json.dumps({"native_v6_transition":"PASS",
                    "source_sha":db.meta()["source_sha"],
                    "event_head":db.meta()["head_hash"],
                    "v2_receipt_authorized":False,
                    "scientific_first_use":False},sort_keys=True))
        elif args.verb=="transition-qualified-native-v7":
            # One new source successor after fully consumed V6; no dispatch.
            from f139.nci04_v7_owner_release import validate_v7_original_owner
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V7_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V7_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v7(*parts):
                p=subprocess.run(["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(p.returncode==0,"V7_GIT_COMMAND_FAILED")
                return p.stdout.decode("utf-8").strip()
            require(_git_read_v7("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v7("status","--porcelain",
                                    "--untracked-files=all")=="",
                    "V7_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            github=GitHub()
            require(github.protected_main()==approval.get("to_source_sha"),
                    "V7_PROTECTED_MAIN_SHA_DRIFT")
            github.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                old_head=db.meta()["head_seq"]
                # Executing -m f139.local_controller instantiates Database
                # from __main__; the exact-type owner guard imports its
                # canonical class from f139.local_controller instead.
                # Validate on that canonical read-only handle, preserving
                # exact class identity; original db alone writes the V7 event.
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    validate_v7_original_owner(validator_db,approval)
                finally:
                    validator_db.close()
                db.transition_source(approval["to_source_sha"],
                    allow_certified_negative=True,allow_v7=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==old_head+1,
                        "V7_SOURCE_TRANSITION_NOT_ATOMIC")
                print(json.dumps({"native_v7_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],"event_seq":meta["head_seq"],
                    "v2_production_dispatch_authorized":False,
                    "scientific_first_use":False},sort_keys=True))
        elif args.verb=="transition-qualified-native-v17":
            # This is callable only by the already-qualified original owner.
            # Read-only preflight is necessary, not sufficient: caller must
            # independently authenticate protected main and the owner event.
            from f139.nci04_v17_owner_readonly_preflight import (
                verify_v17_readonly_preflight)
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V17_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V17_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v17(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V17_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v17("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v17("status","--porcelain",
                                      "--untracked-files=all")=="",
                    "V17_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V17_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    verify_v17_readonly_preflight(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v17=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V17_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v17_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "new_queue":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v16":
            # This is callable only by the already-qualified original owner.
            # Read-only preflight is necessary, not sufficient: caller must
            # independently authenticate protected main and the owner event.
            from f139.nci04_v16_owner_readonly_preflight import (
                verify_v16_readonly_preflight)
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V16_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V16_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v16(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V16_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v16("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v16("status","--porcelain",
                                      "--untracked-files=all")=="",
                    "V16_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V16_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    verify_v16_readonly_preflight(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v16=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V16_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v16_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "new_queue":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v15":
            # This is callable only by the already-qualified original owner.
            # Read-only preflight is necessary, not sufficient: caller must
            # independently authenticate protected main and the owner event.
            from f139.nci04_v15_owner_readonly_preflight import (
                verify_v15_readonly_preflight)
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V15_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V15_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v15(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V15_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v15("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v15("status","--porcelain",
                                      "--untracked-files=all")=="",
                    "V15_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V15_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    verify_v15_readonly_preflight(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v15=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V15_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v15_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "new_queue":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v14":
            # This is callable only by the already-qualified original owner.
            # Read-only preflight is necessary, not sufficient: caller must
            # independently authenticate protected main and the owner event.
            from f139.nci04_v14_owner_readonly_preflight import (
                verify_v14_readonly_preflight)
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V14_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V14_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v14(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V14_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v14("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v14("status","--porcelain",
                                      "--untracked-files=all")=="",
                    "V14_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V14_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    verify_v14_readonly_preflight(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v14=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V14_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v14_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "new_queue":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v13":
            # This is callable only by the already-qualified original owner.
            # Read-only preflight is necessary, not sufficient: caller must
            # independently authenticate protected main and the owner event.
            from f139.nci04_v13_owner_readonly_preflight import (
                verify_v13_readonly_preflight)
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V13_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V13_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v13(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V13_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v13("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v13("status","--porcelain",
                                      "--untracked-files=all")=="",
                    "V13_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V13_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    verify_v13_readonly_preflight(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v13=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V13_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v13_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "new_queue":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v12":
            # One source successor after consumed V11 activation; preserve G54 #989 and G3 history.
            from f139.nci04_v12_owner_release import validate_v12_original_owner
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V12_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V12_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v12(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V12_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v12("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v12("status","--porcelain",
                                      "--untracked-files=all")=="",
                    "V12_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V12_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    validate_v12_original_owner(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v12=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V12_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v12_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "new_queue":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v11":
            # One source successor after consumed V10 activation and G54 #989 original negative.
            from f139.nci04_v11_owner_release import validate_v11_original_owner
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V11_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V11_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v11(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V11_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v11("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v11("status","--porcelain",
                                      "--untracked-files=all")=="",
                    "V11_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V11_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    validate_v11_original_owner(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v11=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V11_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v11_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "new_queue":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v10":
            # One source successor after the consumed V9 transition and activation.
            from f139.nci04_v10_owner_release import validate_v10_original_owner
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V10_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V10_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v10(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V10_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v10("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v10("status","--porcelain",
                                      "--untracked-files=all")=="",
                    "V10_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V10_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    validate_v10_original_owner(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v10=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V10_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v10_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "new_queue":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v9":
            # One G54 V9 release, bound to the authenticated original owner and V8 ledger.
            from f139.nci04_v9_owner_release import validate_v9_original_owner
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V9_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V9_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v9(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V9_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v9("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v9("status","--porcelain",
                                     "--untracked-files=all")=="",
                    "V9_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V9_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    validate_v9_original_owner(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v9=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V9_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v9_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "v2_production_dispatch_authorized":False,
                    "new_controller":False,
                    "new_scheduler":False,
                    "paid_api_calls":0},sort_keys=True))
        elif args.verb=="transition-qualified-native-v8":
            # One original-owner-only release, after G49 negative custody.
            # Never replay the previous G39 V7 transition.
            from f139.nci04_v8_owner_release import validate_v8_original_owner
            native_original_owner_profile(args.db)
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"V8_APPROVAL_FILE_INVALID")
            approval=json.loads(raw)
            require(type(approval) is dict,"V8_APPROVAL_NOT_OBJECT")
            checkout=Path(__file__).resolve().parent.parent
            def _git_read_v8(*parts):
                result=subprocess.run(
                    ["git","-C",str(checkout),*parts],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,timeout=15,check=False)
                require(result.returncode==0,"V8_GIT_COMMAND_FAILED")
                return result.stdout.decode("utf-8").strip()
            require(_git_read_v8("rev-parse","HEAD")==approval.get("to_source_sha")
                    and _git_read_v8("status","--porcelain",
                                     "--untracked-files=all")=="",
                    "V8_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED")
            api=GitHub()
            require(api.protected_main()==approval.get("to_source_sha"),
                    "V8_PROTECTED_MAIN_SHA_DRIFT")
            api.legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            with SingleOwner(args.db.with_suffix(".lock")):
                from f139.local_controller import Database as CanonicalOwnerDB
                validator_db=CanonicalOwnerDB(args.db)
                try:
                    validate_v8_original_owner(validator_db,approval)
                finally:
                    validator_db.close()
                before=db.meta()["head_seq"]
                db.transition_source(approval["to_source_sha"],
                                     allow_certified_negative=True,
                                     allow_v8=True)
                db.verify()
                meta=db.meta()
                require(meta["source_sha"]==approval["to_source_sha"]
                        and meta["head_seq"]==before+1,
                        "V8_ONE_EVENT_TRANSITION_NOT_ATOMIC")
                print(json.dumps({
                    "native_v8_transition":"PASS",
                    "source_sha":meta["source_sha"],
                    "event_head":meta["head_hash"],
                    "event_seq":meta["head_seq"],
                    "scientific_first_use":False,
                    "new_dispatches":0},sort_keys=True))
        elif args.verb=="activate-native":
            # Owner-only, explicit admission. Does not create a second task or
            # controller and does not dispatch work. The existing scheduled
            # tick picks up only this authenticated SQLite activation event.
            native_original_owner_profile(args.db)
            require(GitHub().protected_main()==db.meta()["source_sha"],
                    "NATIVE_ACTIVATION_GITHUB_SOURCE_DRIFT")
            GitHub().legacy_dispatchers_disabled()
            legacy_windows_task_disabled()
            from f139.nci04_owner_ledger import activate_native
            raw=args.approval.read_bytes()
            require(0<len(raw)<=4096,"OWNER_APPROVAL_FILE_UNQUALIFIED")
            approval=json.loads(raw)
            with SingleOwner(args.db.with_suffix(".lock")):
                result=activate_native(db,approval)
                print(json.dumps({"native_development_activated":result,
                                  "source_sha":db.meta()["source_sha"],
                                  "event_head":db.meta()["head_hash"],
                                  "scientific_first_use":False},
                                 sort_keys=True))
        elif args.verb=="tick":
            with SingleOwner(args.db.with_suffix(".lock")):
                result=run_once(db,GitHub(),args.db,os.environ.get("F139_WORKER_HMAC_KEY",""))
                print(json.dumps(result,sort_keys=True))
        elif args.verb=="loop":
            require(15<=args.seconds<=300,"POLL_FREQUENCY_UNSAFE")
            while True:
                try:
                    with SingleOwner(args.db.with_suffix(".lock")):
                        result=run_once(db,GitHub(),args.db,os.environ.get("F139_WORKER_HMAC_KEY",""))
                        print(json.dumps({"at":utc_now(),**result},sort_keys=True),flush=True)
                except F139Error as exc:
                    print(json.dumps({"at":utc_now(),"blocked":str(exc),"science_authorized":False}),
                          file=sys.stderr,flush=True)
                time.sleep(args.seconds)
        print(json.dumps({"status":db.status()},default=str,sort_keys=True) if args.verb=="status" else "F139_COMMAND_COMPLETE")
    finally:
        db.close()


if __name__=="__main__":
    try:
        cli()
    except (F139Error,sqlite3.DatabaseError,OSError,ValueError) as exc:
        print("F139_FAIL_CLOSED "+str(exc),file=sys.stderr)
        raise SystemExit(1) from exc
