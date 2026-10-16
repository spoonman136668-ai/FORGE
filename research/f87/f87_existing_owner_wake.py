#!/usr/bin/env python3
"""F87: independently re-read one immutable CKB owner wake; never admit first-use.

This is a narrow historic observation. A successful CKB wake is NOT a witness
of a new original, live lease status, scientific acceptance or FORGE authority.
Only GitHub-sourced run and job metadata enter. No network, writes or secrets.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

SCHEMA = "forge.f87.existing-ckb-owner-wake-observation.v1"
REPO = "spoonman136668-ai/ckb-plane"
SOURCE = "fab36e7c488f930505fcbaeb5f5bf04806e50c5b"
RUN = 38928134866
PATH = ".github/workflows/research-loop-headless-wake-v2.yml"
OBSERVED = {
    "S67 CKB exclusive one-use signed S13 intent": "S13_OWNER_INTENT",
    "S67 durably upload signed original intent BEFORE any dispatch": "S13_ARCHIVE",
    "S67 dispatch UNIQUE S13 original only after GitHub custody": "S13_DISPATCH",
    "S74 CKB exclusive S14 first-use signed intent": "S14_OWNER_INTENT",
    "S74 upload one CKB original signed S14 intent before dispatch": "S14_ARCHIVE",
    "S74 independently authenticate retained signed intent ZIP and permanent S14 ledger": "S14_WITNESS",
    "S74 single S14 original dispatch only after source-bound archive custody": "S14_DISPATCH",
}

class Blocked(ValueError):
    pass

def need(test, reason):
    if not test:
        raise Blocked("F87_" + reason)

def strict_json(raw):
    need(0 < len(raw) <= 2000000, "INPUT_SIZE")
    def no_duplicates(pairs):
        out = {}
        for k, v in pairs:
            need(k not in out, "DUPLICATE_KEY")
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=no_duplicates,
                      parse_constant=lambda _: (_ for _ in ()).throw(Blocked("F87_NONFINITE")))

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
       separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()

def audit(run, jobs):
    need(type(run) is dict and type(jobs) is dict, "INPUT_SHAPES")
    need(type(run.get("id")) is int and run["id"] == RUN
         and run.get("run_attempt") == 1
         and run.get("name") == "Headless deterministic research loop wake v2"
         and run.get("event") == "workflow_dispatch"
         and run.get("path") == PATH
         and run.get("head_branch") == "main"
         and run.get("head_sha") == SOURCE
         and run.get("head_repository", {}).get("full_name") == REPO
         and run.get("repository", {}).get("full_name") == REPO
         and run.get("status") == "completed"
         and run.get("conclusion") == "success", "RUN_IDENTITY")
    rows = jobs.get("jobs")
    need(type(rows) is list and len(rows) == 1, "JOB_SET")
    job = rows[0]
    need(type(job) is dict and type(job.get("run_id")) is int
         and job["run_id"] == RUN and job.get("run_attempt") == 1
         and job.get("name") == "wake"
         and job.get("status") == "completed"
         and job.get("conclusion") == "success"
         and type(job.get("id")) is int and job["id"] > 0, "WAKE_JOB_IDENTITY")
    steps = job.get("steps")
    need(type(steps) is list and 40 <= len(steps) <= 100, "STEP_SET")
    indexed, numbers = {}, set()
    for s in steps:
        need(type(s) is dict and type(s.get("number")) is int
             and s["number"] > 0 and type(s.get("name")) is str
             and len(s["name"]) <= 180 and s["name"] not in indexed
             and s["number"] not in numbers, "STEP_IDENTITY")
        indexed[s["name"]] = s
        numbers.add(s["number"])
    signals = []
    for title, short in OBSERVED.items():
        s = indexed.get(title)
        need(s is not None and s.get("status") == "completed"
             and s.get("conclusion") == "skipped", "OBSERVED_FIRSTUSE_STEP_CHANGED")
        signals.append({"stage": short, "step_number": s["number"],
                        "observed_conclusion": "skipped"})
    # Deliberate non-inference: skipped in ONE wake does not establish that a
    # historical lease is still unused, or that the owner was rejected.
    return {"schema": SCHEMA, "scope": "PINNED_READONLY_SINGLE_WAKE_SNAPSHOT",
            "repository": REPO, "source_sha": SOURCE, "run_id": RUN,
            "run_attempt": 1, "job_id": job["id"],
            "verified_step_metadata_sha256": digest(signals),
            "source_steps": signals,
            "observed_s13_s14_steps_skipped": True,
            "complete_owner_lease_history_qualified": False,
            "independent_preoutcome_owner_witness_qualified": False,
            "current_firstuse_availability_proven": False,
            "firstuse_dispatch_authorized": False,
            "dream_rsi_pareto_activation_authorized": False,
            "cloudflare_written": False,
            "controller_mutated": False,
            "disposition": "AUTHENTIC_CKB_WAKE_OBSERVED_NO_NEW_SCIENTIFIC_AUTHORITY"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--jobs", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    obj = audit(strict_json(pathlib.Path(a.run).read_bytes()),
                strict_json(pathlib.Path(a.jobs).read_bytes()))
    pathlib.Path(a.out).write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")
    print("F87_CKB_OWNER_WAKE_PINNED_READBACK=PASS")
    print("F87_INDEPENDENT_FIRSTUSE_AUTHORITY=NOT_ESTABLISHED")

if __name__ == "__main__":
    try:
        main()
    except (Blocked, ValueError, KeyError, TypeError, OSError):
        print("F87_OWNER_WAKE_AUDIT=BLOCKED", file=sys.stderr)
        raise SystemExit(1)
