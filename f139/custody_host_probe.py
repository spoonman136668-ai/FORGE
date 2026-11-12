"""F139-D2K-CUSTODY/B: bounded, no-data-access runner admission.

Operator-supplied repository variables are admission declarations, *not*
independent proof of workstation isolation or an independent signed ledger.
A successful result authorizes nothing beyond runner identity observation.
"""
import hashlib
import json
import os
import re
import sys

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
REPO = "spoonman136668-ai/FORGE"
RUNNER = "FORGE-CODEX-REMOTE"
MAIN_REF = "refs/heads/main"


class AdmissionBlocked(RuntimeError):
    pass


def require(assertion, name):
    if not assertion:
        raise AdmissionBlocked("F139_D2K_RUNNER_"+name)


def source_admission(data):
    require(data.get("repository")==REPO, "REPOSITORY_DRIFT")
    require(data.get("event")=="workflow_dispatch", "EVENT_NOT_MANUAL")
    require(data.get("ref")==MAIN_REF, "NOT_PROTECTED_MAIN")
    main=data.get("main", "")
    require(bool(HEX40.fullmatch(main)), "MAIN_NOT_SHA")
    require(main==data.get("request_source")==data.get("pinned_source"),
            "UNQUALIFIED_SOURCE_OR_VARIABLE")
    require(data.get("isolation_declared")=="true",
            "ISOLATION_DECLARATION_MISSING")
    head=data.get("request_head", "")
    require(bool(HEX64.fullmatch(head))
            and head==data.get("pinned_head"),
            "INDEPENDENT_HEAD_NOT_PREPINNED")
    machine=data.get("pinned_machine", "")
    require(bool(HEX64.fullmatch(machine)), "MACHINE_IDENTITY_NOT_PREPINNED")
    return {
        "schema":"forge.f139.d2k-custody.runner-preflight.v1",
        "disposition":"SOURCE_AND_DECLARED_PINS_MATCH_HOST_NOT_OBSERVED",
        "workstation_reads":0,"controller_actions":0,"research_jobs_started":0,
        "historical_custody_verified":False,"scientific_first_use":False,
    }


def host_observation(data):
    require(data.get("repository")==REPO, "REPOSITORY_DRIFT")
    require(data.get("event")=="workflow_dispatch", "EVENT_NOT_MANUAL")
    require(data.get("ref")==MAIN_REF, "NOT_PROTECTED_MAIN")
    require(data.get("runner_name")==RUNNER and data.get("runner_os")=="Windows",
            "UNQUALIFIED_RUNNER_NAME_OR_OS")
    require(data.get("isolation_declared")=="true",
            "ISOLATION_DECLARATION_MISSING")
    hostname=data.get("hostname", "")
    require(0<len(hostname)<=256 and "\n" not in hostname and "\r" not in hostname,
            "HOSTNAME_INVALID")
    observed=hashlib.sha256(hostname.upper().encode("utf-8")).hexdigest()
    require(observed==data.get("pinned_machine"), "MACHINE_WITNESS_MISMATCH")
    require(bool(HEX40.fullmatch(data.get("main","")))
            and data["main"]==data.get("pinned_source")
            and data["main"]==data.get("request_source"),
            "HOST_SOURCE_DRIFT")
    require(bool(HEX64.fullmatch(data.get("request_head","")))
            and data.get("request_head")==data.get("pinned_head"),
            "HOST_HEAD_NOT_PREPINNED")
    return {
        "schema":"forge.f139.d2k-custody.runner-preflight.v1",
        "disposition":"RUNNER_MACHINE_IDENTITY_OBSERVED_ISOLATION_NOT_INDEPENDENTLY_VERIFIED",
        "runner_name":RUNNER,"machine_sha256":observed,
        "workstation_reads":0,"controller_actions":0,"research_jobs_started":0,
        "historical_custody_verified":False,"scientific_first_use":False,
    }


def main():
    require(len(sys.argv)==2 and sys.argv[1] in ("source","host"),"INVOCATION_INVALID")
    base={
        "repository":os.getenv("GITHUB_REPOSITORY",""),
        "event":os.getenv("GITHUB_EVENT_NAME",""),
        "ref":os.getenv("GITHUB_REF",""),
        "main":os.getenv("GITHUB_SHA",""),
        "request_source":os.getenv("F139_REQUEST_SOURCE",""),
        "request_head":os.getenv("F139_REQUEST_HEAD",""),
        "pinned_source":os.getenv("F139_PINNED_SOURCE",""),
        "pinned_head":os.getenv("F139_PINNED_HEAD",""),
        "pinned_machine":os.getenv("F139_PINNED_MACHINE",""),
        "isolation_declared":os.getenv("F139_ISOLATION_DECLARED",""),
        "runner_name":os.getenv("RUNNER_NAME",""),
        "runner_os":os.getenv("RUNNER_OS",""),
        "hostname":os.getenv("COMPUTERNAME",""),
    }
    answer=source_admission(base) if sys.argv[1]=="source" else host_observation(base)
    print(json.dumps(answer,sort_keys=True,separators=(",",":")))


if __name__=="__main__":
    try:main()
    except AdmissionBlocked as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1) from exc
