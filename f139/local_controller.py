"""F139 native workstation controller. One owner, SQLite, GitHub as a worker only.

This controller NEVER authorizes scientific originals, optimizer promotion, or
GitHub protected-ref mutation. The workflow it can call is fixed in source.
"""
from __future__ import annotations

import argparse
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
LIMIT_PER_DAY = 48
MAX_ZIP_BYTES = 2_000_000
MAX_RECEIPT_BYTES = 8192
D2K_WORK_LABEL = "f139-development-eligible"
D2K_KIND = "model-free-development-advisory"
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
        return self

    def __exit__(self, *_):
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

    def close(self):
        self.conn.close()

    def meta(self):
        row = self.conn.execute("SELECT * FROM meta WHERE id=1").fetchone()
        require(row is not None and row["schema"] == SCHEMA and SHA.fullmatch(row["source_sha"]) is not None
                and row["epoch"] > 0 and row["enabled"] in (0,1) and row["legacy_suspended"] in (0,1)
                and row["starts"] >= 0 and row["head_seq"] >= 0
                and re.fullmatch(r"[a-f0-9]{64}", row["head_hash"]), "METADATA_CORRUPT")
        return dict(row)

    def verify(self):
        meta = self.meta()
        head, count = ZERO, 0
        source_transitions = []
        for row in self.conn.execute("SELECT * FROM events ORDER BY seq"):
            count += 1
            require(row["seq"] == count and row["prior_sha"] == head, "EVIDENCE_CHAIN_DISCONTINUITY")
            doc = json.loads(row["payload"])
            require(canonical(doc).decode() == row["payload"], "NONCANONICAL_EVENT")
            entry = {"seq": count, "prior_sha": head, "kind": row["kind"], "payload": doc}
            head = hash_bytes(canonical(entry))
            require(head == row["sha"], "EVIDENCE_CHAIN_TAMPERED")
            if row["kind"] == "DEVELOPMENT_WORK_ADMITTED":
                require(isinstance(doc, dict) and set(doc) == {
                    "schema", "source_sha", "ticket", "issue_number", "issue_id",
                    "lane", "kind", "body_sha256", "manifest_sha256",
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
                    "kind":doc["kind"], "body_sha256":doc["body_sha256"],
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
                require(isinstance(doc, dict) and set(doc) == {
                    "schema", "from_source_sha", "to_source_sha", "prior_event_head_sha256",
                    "verified_historical_tasks", "new_dispatches", "scientific_first_use"},
                    "SOURCE_TRANSITION_EVENT_FIELDS")
                require(doc["schema"] == "forge.f139.source-transition.v1"
                        and isinstance(doc["from_source_sha"], str)
                        and SHA.fullmatch(doc["from_source_sha"])
                        and isinstance(doc["to_source_sha"], str)
                        and SHA.fullmatch(doc["to_source_sha"])
                        and doc["from_source_sha"] != doc["to_source_sha"]
                        and doc["prior_event_head_sha256"] == row["prior_sha"]
                        and isinstance(doc["verified_historical_tasks"], int)
                        and doc["verified_historical_tasks"] > 0
                        and type(doc["new_dispatches"]) is int
                        and doc["new_dispatches"] == 0
                        and doc["scientific_first_use"] is False,
                        "SOURCE_TRANSITION_EVENT_INVALID")
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
        for row in self.conn.execute("SELECT ticket,lane,source_sha,stage,run_id,evidence_dir,evidence_sha FROM tasks"):
            historical = (row["source_sha"] in historical_sources and
                          row["stage"] == "VERIFIED" and
                          isinstance(row["run_id"], int) and row["run_id"] > 0 and
                          isinstance(row["evidence_dir"], str) and bool(row["evidence_dir"]) and
                          isinstance(row["evidence_sha"], str) and
                          re.fullmatch(r"[a-f0-9]{64}", row["evidence_sha"]) is not None)
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
        active = self.conn.execute("SELECT COUNT(*) FROM tasks WHERE stage IN ('START_RISK','WAIT_PROVIDER')").fetchone()[0]
        require(active <= 1, "MULTIPLE_ACTIVE_PROVIDER_DISPATCHES")

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
        require(re.fullmatch(r"[A-Z_]{3,48}", kind) is not None, "INVALID_EVENT_KIND")
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

    def transition_source(self, new_source_sha: str):
        """Append immutable authority evidence; never rewrite historical task source or run."""
        require(isinstance(new_source_sha, str) and SHA.fullmatch(new_source_sha),
                "SOURCE_TRANSITION_NEW_SHA_INVALID")
        with self.transaction():
            meta = self.meta()
            require(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
                    and new_source_sha != meta["source_sha"],
                    "SOURCE_TRANSITION_OWNER_OR_IDENTITY_INVALID")
            tasks = list(self.conn.execute("SELECT * FROM tasks"))
            require(tasks and all(
                row["stage"] == "VERIFIED" and row["run_id"] is not None
                and isinstance(row["evidence_sha"], str)
                and re.fullmatch(r"[a-f0-9]{64}", row["evidence_sha"]) is not None
                and row["evidence_dir"] for row in tasks),
                "SOURCE_TRANSITION_UNVERIFIED_OR_PENDING_TASK")
            prior = meta["head_hash"]
            self.conn.execute("UPDATE meta SET source_sha=? WHERE id=1", (new_source_sha,))
            self.event("SOURCE_TRANSITION_ADMITTED", {
                "schema": "forge.f139.source-transition.v1",
                "from_source_sha": meta["source_sha"],
                "to_source_sha": new_source_sha,
                "prior_event_head_sha256": prior,
                "verified_historical_tasks": len(tasks),
                "new_dispatches": 0,
                "scientific_first_use": False,
            })
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
        require(isinstance(issue, dict) and set(issue) == {
                    "ticket", "issue_number", "issue_id", "source_sha",
                    "lane", "kind", "body_sha256"
                } and issue["source_sha"] == meta["source_sha"]
                and issue["lane"] in LANES and issue["kind"] == D2K_KIND,
                "D2K_ISSUE_IDENTITY_INVALID")
        ticket = issue["ticket"]
        require(isinstance(ticket, str) and TICKET.fullmatch(ticket)
                and ticket == "f139-d2k-i" + str(issue["issue_number"]) + "-" +
                  meta["source_sha"][:12] + "-" + issue["body_sha256"][:8], "D2K_TICKET_IDENTITY_INVALID")
        with self.transaction():
            self.verify()
            require(self.active() is None and self.ready() is None,
                    "D2K_PENDING_WORK_NOT_EMPTY")
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
            prior = meta["head_hash"]
            manifest = {
                "schema":"forge.f139.d2k.issue-work.v1",
                "source_sha":meta["source_sha"], "ticket":ticket,
                "issue_number":issue["issue_number"], "issue_id":issue["issue_id"],
                "lane":issue["lane"], "kind":issue["kind"],
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

    def active(self):
        return self.conn.execute("SELECT * FROM tasks WHERE stage IN ('START_RISK','WAIT_PROVIDER') ORDER BY ticket LIMIT 1").fetchone()

    def ready(self):
        return self.conn.execute("SELECT * FROM tasks WHERE stage='READY' ORDER BY ticket LIMIT 1").fetchone()

    def claim(self, ticket: str, now: str):
        day = now[:10]
        with self.transaction():
            m = self.meta()
            require(m["enabled"]==1 and m["legacy_suspended"]==1,"CONTROLLER_INACTIVE")
            starts = m["starts"] if m["day"]==day else 0
            require(starts<LIMIT_PER_DAY,"DAILY_START_LIMIT")
            require(self.active() is None,"CONCURRENT_ACTIVE_START_RISK")
            row=self.conn.execute("SELECT * FROM tasks WHERE ticket=?",(ticket,)).fetchone()
            require(row is not None and row["stage"]=="READY", "TASK_ALREADY_CLAIMED")
            self.conn.execute("UPDATE tasks SET stage='START_RISK',started_at=? WHERE ticket=?",(now,ticket))
            self.conn.execute("UPDATE meta SET starts=?,day=? WHERE id=1",(starts+1,day))
            self.event("BEFORE_DISPATCH_INTENT",{"ticket":ticket,"started_at":now,"starts":starts+1})

    def dispatch_observed(self,ticket: str):
        with self.transaction():
            row=self.conn.execute("SELECT stage FROM tasks WHERE ticket=?",(ticket,)).fetchone()
            require(row and row["stage"]=="START_RISK","DISPATCH_STATE_DRIFT")
            self.conn.execute("UPDATE tasks SET stage='WAIT_PROVIDER' WHERE ticket=?",(ticket,))
            self.event("DISPATCH_POST_RETURNED",{"ticket":ticket})

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

    def protected_main(self):
        branch=self.get("repos/"+REPO+"/branches/main")
        sha=branch.get("commit",{}).get("sha")
        require(isinstance(sha,str) and SHA.fullmatch(sha) and branch.get("protected") is True,
                "MAIN_IDENTITY_OR_PROTECTION_NOT_VERIFIED")
        return sha

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
                    "schema","source_sha","lane","kind",
                    "scientific_first_use","paid_model_calls"
                } and record["schema"]=="forge.f139.d2k.owner-development.v1"
                    and record["source_sha"]==source
                    and record["lane"] in LANES
                    and record["kind"]==D2K_KIND
                    and record["scientific_first_use"] is False
                    and type(record["paid_model_calls"]) is int
                    and record["paid_model_calls"]==0,
                    "D2K_ISSUE_POLICY_INVALID")
                accepted.append({
                    "ticket":"f139-d2k-i"+str(raw["number"])+"-"+source[:12]+
                             "-"+hash_bytes(canonical(record))[:8],
                    "issue_number":raw["number"],"issue_id":raw["id"],
                    "source_sha":source,"lane":record["lane"],
                    "kind":D2K_KIND,
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

    def dispatch(self,ticket:str,lane:str,source:str,epoch:int,signature:str):
        require(TICKET.fullmatch(ticket) and lane in LANES and SHA.fullmatch(source)
                and 0<epoch<2**31 and re.fullmatch(r"[a-f0-9]{64}",signature),"DISPATCH_NOT_ALLOWED")
        path="repos/"+REPO+"/actions/workflows/"+WORKFLOW+"/dispatches"
        self.runner(["--method","POST",path,"-f","ref=main",
                     "-f","inputs[ticket]="+ticket,"-f","inputs[lane]="+lane,
                     "-f","inputs[source_sha]="+source,"-f","inputs[epoch]="+str(epoch),
                     "-f","inputs[signature]="+signature])

    def candidates(self,ticket:str,started_at:str):
        source_start=parse_time(started_at)
        found=[]
        for page in range(1,6):
            index=self.get("repos/"+REPO+"/actions/workflows/"+WORKFLOW+
                           "/runs?branch=main&event=workflow_dispatch&per_page=100&page="+str(page))
            rows=index.get("workflow_runs")
            require(isinstance(rows,list) and isinstance(index.get("total_count"),int),"PROVIDER_HISTORY_INVALID")
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
                and run.get("head_sha")==source and run.get("head_branch")=="main"
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
        for oslabel in ("windows-latest","ubuntu-latest"):
            matching=[x for x in jr if x.get("name")=="execute ("+oslabel+")"]
            require(len(matching)==1 and matching[0].get("status")=="completed"
                    and matching[0].get("conclusion")=="success", "WORKER_OS_NOT_VERIFIED")
            names=[x for x in ar if x.get("name")=="forge-f139-dev-receipt-"+oslabel]
            require(len(names)==1 and names[0].get("expired") is False
                    and names[0].get("workflow_run",{}).get("id")==rid
                    and names[0].get("workflow_run",{}).get("head_sha")==source
                    and re.fullmatch(r"sha256:[a-f0-9]{64}",names[0].get("digest") or ""),
                    "PROVIDER_ARTIFACT_NOT_QUALIFIED")
        return (rid,ar)

    def artifact(self,artifact_id:int)->bytes:
        require(isinstance(artifact_id,int) and artifact_id>0,"ARTIFACT_ID_INVALID")
        zipbytes=self.runner([f"repos/{REPO}/actions/artifacts/{artifact_id}/zip"])
        require(isinstance(zipbytes,bytes) and 0<len(zipbytes)<MAX_ZIP_BYTES,"ARTIFACT_TOO_LARGE")
        return zipbytes


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


def receipt_from_zip(raw:bytes,meta:dict,task:dict,run_id:int,oslabel:str,epoch:int=1)->dict:
    require(hash_bytes(raw)==meta["digest"][7:] and len(raw)==meta.get("size_in_bytes"),
            "ARTIFACT_ZIP_DIGEST_DRIFT")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names=archive.namelist()
            require(sorted(names)==["f139-receipt.json","f139-receipt.sha256"]
                    and len(names)==len(set(names)),"ARTIFACT_MEMBER_SET_INVALID")
            require(all(x.file_size<=MAX_RECEIPT_BYTES and not x.is_dir() for x in archive.infolist()),
                    "ARTIFACT_MEMBER_OVERSIZE")
            body=archive.read("f139-receipt.json")
            receipt=archive.read("f139-receipt.sha256")
    except (OSError,zipfile.BadZipFile,ValueError,RuntimeError) as exc:
        raise F139Error("F139_ARTIFACT_ZIP_INVALID") from exc
    require(receipt==(hash_bytes(body)+"  f139-receipt.json\n").encode(),"RECEIPT_SHA_INVALID")
    try:
        value=json.loads(body)
    except ValueError as exc:
        raise F139Error("F139_RECEIPT_JSON_INVALID") from exc
    require(isinstance(value,dict) and value.get("schema")=="forge.f139.development-worker-receipt.v1"
            and value.get("ticket")==task["ticket"] and value.get("lane")==task["lane"]
            and value.get("source_sha")==task["source_sha"] and value.get("epoch")==epoch
            and value.get("os")==oslabel and value.get("run_id")==run_id
            and value.get("development_only") is True and value.get("scientific_first_use_authorized") is False
            and value.get("scientific_originals_dispatched")==0 and value.get("accepted_ref_mutations")==0
            and value.get("paid_model_calls")==0 and value.get("codex_calls")==0,
            "RECEIPT_FALSE_SOURCE_OR_SCIENCE")
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

def run_once(db:Database,api:GitHub,db_path:Path,hmac_key:str, *, now=None):
    timestamp=now or utc_now()
    require(len(hmac_key)>=32,"WORKER_HMAC_SECRET_MISSING")
    db.verify()
    meta=db.meta()
    require(meta["enabled"]==1 and meta["legacy_suspended"]==1,"CONTROLLER_INACTIVE_OR_LEGACY_RUNNING")
    require(api.protected_main()==meta["source_sha"],"MAIN_SOURCE_DRIFT")
    active=db.active()
    if active is not None:
        active=dict(active)
        try:
            run=api.candidates(active["ticket"],active["started_at"])
            if run is None:
                return {"disposition":"START_RISK_PENDING_NO_REDISPATCH","ticket":active["ticket"]}
            result=api.run_proof(run,active["ticket"],active["source_sha"],active["started_at"])
            if result is None:
                return {"disposition":"WORKER_RUNNING_NO_REDISPATCH","ticket":active["ticket"]}
            rid,artifacts=result
            archives={}
            for oslabel in ("ubuntu-latest","windows-latest"):
                matching=[x for x in artifacts if x.get("name")=="forge-f139-dev-receipt-"+oslabel]
                require(len(matching)==1,"AMBIGUOUS_PROVIDER_ARTIFACT")
                raw=api.artifact(matching[0]["id"])
                receipt_from_zip(raw,matching[0],active,rid,oslabel,meta["epoch"])
                archives[oslabel]=raw
            path,digest=store_evidence(db_path.parent,active["ticket"],rid,archives)
            db.terminal(active["ticket"],rid,path,digest)
        except F139Error as exc:
            # Provider failures are sticky. An API timeout is epistemically ambiguous;
            # preserve START_RISK and do not transition to a retryable READY.
            code=str(exc).removeprefix("F139_")
            if code not in {"GITHUB_API_TIMEOUT","GITHUB_API_FAILED","GITHUB_API_INVALID_JSON"}:
                db.quarantine(active["ticket"],code if re.fullmatch(r"[A-Z_]{3,72}",code) else "UNCLASSIFIED_REJECTION")
            raise
    ready=db.ready()
    if ready is None and db.admit_d2j_succession():
        ready=db.ready()
    if ready is None and db.meta()["head_seq"] >= 23:
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
    if ready is None:
        return {"disposition":"QUEUE_EMPTY_NO_SCIENCE","completed":db.conn.execute("SELECT COUNT(*) FROM tasks WHERE stage='VERIFIED'").fetchone()[0]}
    task=dict(ready)
    db.claim(task["ticket"],timestamp)
    # HMAC uses the same frozen wire schema as f139.verify_ticket on GitHub.
    import hmac
    payload="\n".join(("F139-DISPATCH-V1",REPO,WORKFLOW,task["ticket"],task["lane"],task["source_sha"],str(meta["epoch"])))+"\n"
    signature=hmac.new(hmac_key.encode(),payload.encode(),hashlib.sha256).hexdigest()
    api.dispatch(task["ticket"],task["lane"],task["source_sha"],meta["epoch"],signature)
    db.dispatch_observed(task["ticket"])
    return {"disposition":"DEVELOPMENT_DISPATCHED_ONCE","ticket":task["ticket"],"science_authorized":False}


def cli(argv=None):
    parser=argparse.ArgumentParser(description="FORGE F139 single Windows controller; development only")
    parser.add_argument("--db",type=Path,required=True)
    sub=parser.add_subparsers(dest="verb",required=True)
    init=sub.add_parser("init");init.add_argument("--source-sha",required=True)
    queue=sub.add_parser("queue");queue.add_argument("--manifest",type=Path,required=True)
    sub.add_parser("status")
    enable=sub.add_parser("activate");enable.add_argument("--legacy-suspended-evidence",type=Path,required=True)
    sub.add_parser("tick")
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
