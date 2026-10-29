"""Production-path F139 V19 native V3 split runner (no owner/dispatch authority).

Unlike diagnostic G36, this accepts the exact owner-signed Candidate for a
FUTURE independently authorized original issue, not the failed issue #1138.
The signed producer is still the ORIGINAL controller. Never import this module
from a V1/V2 dispatch or treat source-only PASS as native provider qualification.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from f139.nci04_native_contract import Candidate, canonical, digest
from f139.nci04_native_worker import _bounded_capture, _git, _inspect_checkout, stage_candidate
from f139.nci04_signed_native import NativeAdmission

SCHEMA = "forge.f139.nci04.native-development-diagnostic.v3"
RECEIPT = "forge.f139.nci04.native-execution-receipt.v3"
TEST = re.compile(r"test_[a-zA-Z0-9_]+\.py\Z")
ATLAS = "test_code_atlas.py"
TARGET = "yggdrasil/public_causal_cells.py"
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
CLOSED = "G29_CHANGED_SOURCE_EXPECTED_REJECTION"
COMMAND = ("python", "-B", "-m", "unittest", "discover", "-s", "tests")
BUILD = ("python", "-B", "-m", "compileall", "-q", "yggdrasil", "scripts")
MAX_OUTPUT = 1_000_000
BUDGET_MIN_MS = 1
BUDGET_MAX_MS = 180_000


class V3Denied(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise V3Denied("F139_NCI04_V3_" + reason)


def inventory(candidate, original):
    need(type(candidate) is Candidate and candidate.lane == "Yggdrasil"
         and candidate.path == TARGET, "ISSUE_SCOPE_REQUIRED")
    root = _inspect_checkout(Path(original), candidate)
    need(_git(root, "rev-parse", "--is-shallow-repository") == "false",
         "SOURCE_ANCESTRY_DRIFT")
    tracked = _git(root, "ls-tree", "-r", "--name-only", "HEAD", "tests")
    modules = tuple(sorted(x.removeprefix("tests/") for x in tracked.splitlines()
                           if re.fullmatch(r"tests/test_[a-zA-Z0-9_]+\.py", x)))
    actual = tuple(sorted(p.name for p in (root / "tests").glob("test_*.py")))
    need(len(modules) >= 5 and ATLAS in modules
         and modules == actual and len(set(modules)) == len(modules),
         "COMPLETE_NATIVE_TEST_INVENTORY_REQUIRED")
    source = root / ".ice" / "code-atlas.json"
    need(source.is_file() and not source.is_symlink(), "FROZEN_G29_SOURCE_MISSING")
    import json
    try:
        meta = json.loads(source.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise V3Denied("F139_NCI04_V3_BAD_G29_SOURCE") from exc
    need(type(meta) is dict and meta.get("schema") ==
         "yggdrasil.ice.source-locator.v1"
         and meta.get("source_reviewed_labels") == 0
         and meta.get("source_commit") != ""
         and meta.get("authority") == "advisory-locators-only"
         and meta.get("wingless_evidence_imported") is False,
         "FROZEN_G29_CONTRACT_DRIFT")
    return root, modules


def _env():
    allowed = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR",
               "SYSTEMDRIVE", "PATHEXT", "COMSPEC", "TMP", "TEMP", "TMPDIR",
               "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL"}
    e = {k:v for k,v in os.environ.items() if k.upper() in allowed}
    e.update({"PYTHONDONTWRITEBYTECODE":"1", "GIT_TERMINAL_PROMPT":"0",
              "GOPROXY":"off", "GOSUMDB":"off", "GOTOOLCHAIN":"local"})
    return e


def unit(module):
    need(type(module) is str and TEST.fullmatch(module) is not None,
         "NONFIXED_TEST_COMMAND")
    return COMMAND + ("-p", module, "-v")


def invoke(argv, root, *, module=None, expected_rejection=False, runner=None):
    need(tuple(argv) == BUILD or
         (module=="test_*.py" and tuple(argv)==COMMAND+("-p","test_*.py","-v")) or
         (module is not None and module!="test_*.py" and tuple(argv)==unit(module)),
         "ARBITRARY_COMMAND_REJECTED")
    t0 = time.monotonic()
    if runner is None:
        from f139.nci04_v3_bounded_resource import bounded_sampled_process
        measured=bounded_sampled_process(argv,cwd=root,env=_env())
        raw,exitcode=measured["stdout"],measured["returncode"]
        outcome="PASS" if exitcode==0 else "TEST_FAILURE"
    else:
        p=runner(list(argv),cwd=root,env=_env(),stdin=subprocess.DEVNULL,
                 stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,
                 check=False)
        raw,exitcode=p.stdout or b"",p.returncode
        outcome="PASS" if exitcode==0 else "TEST_FAILURE"
        measured={"child_peak_rss_bytes":None,"child_cpu_ms":None,
                  "resource_samples":0,"resource_accounting":"not-measured",
                  "resource_budget_verified":False}
    need(type(raw) is bytes and len(raw) <= MAX_OUTPUT,
         "CHILD_OUTPUT_NOT_BOUNDED")
    count = None
    if module is not None:
        found = re.findall(rb"Ran\s+([0-9]+)\s+tests?\s+in\b",raw)
        count = int(found[-1]) if found else 0
    need(module is None or count>0,"ZERO_DISCOVERED_TESTS")
    if expected_rejection:
        exact = (outcome=="TEST_FAILURE" and exitcode>0
                 and module==ATLAS
                 and (b"working source mismatch: "+TARGET.encode()) in raw
                 and b"YGG_ATLAS_FAIL_CLOSED" in raw)
        need(exact, "G29_EXPECTED_NEGATIVE_NOT_AUTHENTIC")
        status=CLOSED
    else:
        need(outcome=="PASS" and exitcode==0,
             "POSITIVE_NATIVE_TEST_OR_COMPILE_FAILED")
        status="PASS"
    return {
        "argv":list(argv), "status":status, "returncode":exitcode,
        "discovered_tests":count, "output_sha256":digest(raw),
        "output_bytes":len(raw),
        "elapsed_ms":int((time.monotonic()-t0)*1000),
        "child_peak_rss_bytes":measured["child_peak_rss_bytes"],
        "child_cpu_ms":measured["child_cpu_ms"],
        "resource_samples":measured["resource_samples"],
        "resource_accounting":measured["resource_accounting"],
        "resource_budget_verified":measured["resource_budget_verified"],
    }


def run_v3(candidate, original, scratch, *, oslabel, runner=None):
    """Real split test algorithm; requires external budget and signed custody."""
    need(oslabel in ("ubuntu-latest","windows-latest")
         and ((os.name=="nt")== (oslabel=="windows-latest")),
         "RUNNER_OS_NOT_AUTHENTIC")
    root, modules = inventory(candidate, original)
    scratch=Path(scratch).resolve(strict=True)
    need(scratch.is_dir() and not scratch.is_symlink()
         and scratch!=root and not scratch.is_relative_to(root)
         and not root.is_relative_to(scratch), "STAGE_NOT_DISJOINT")
    pristine = invoke(unit(ATLAS),root,module=ATLAS,runner=runner)
    # The actual baseline full suite must pass BEFORE the overlay is applied.
    full = invoke(COMMAND+("-p","test_*.py","-v"),root,
                  module="test_*.py",runner=runner)
    stage = stage_candidate(candidate,root,scratch)
    try:
        modified=stage/"checkout"
        need(_git(modified,"rev-parse","HEAD")==candidate.target_commit
             and _git(modified,"remote")==""
             and _git(modified,"diff","--name-only")==TARGET,
             "ONE_SOURCE_OVERLAY_REQUIRED")
        g29=invoke(unit(ATLAS),modified,module=ATLAS,
                   expected_rejection=True,runner=runner)
        positive=[]
        for name in modules:
            if name!=ATLAS:
                positive.append((name,invoke(unit(name),modified,
                                             module=name,runner=runner)))
        build=invoke(BUILD,modified,runner=runner)
        need(_git(modified,"diff","--name-only")==TARGET,
             "CANDIDATE_OVERLAY_MUTATED")
    finally:
        def fix_readonly(fn,path,exc):
            import stat
            need(isinstance(exc[1],PermissionError), "STAGE_DELETE_FAILED")
            os.chmod(path,stat.S_IREAD|stat.S_IWRITE)
            fn(path)
        shutil.rmtree(stage,onerror=fix_readonly if os.name=="nt" else None)
    need(tuple(x[0] for x in positive)==tuple(x for x in modules if x!=ATLAS)
         and all(e["discovered_tests"]>0 and e["status"]=="PASS"
                 for _,e in positive), "BEHAVIOR_INVENTORY_INCOMPLETE")
    all_results=[pristine,full,g29,*dict(positive).values(),build]
    budget_pass=all(row["resource_budget_verified"] is True
                    and type(row["child_cpu_ms"]) is int
                    and row["child_cpu_ms"]>0
                    and type(row["child_peak_rss_bytes"]) is int
                    and row["child_peak_rss_bytes"]>0
                    for row in all_results)
    return {
        "schema":SCHEMA, "ticket_source_commit":candidate.target_commit,
        "target_tree_sha":candidate.target_tree_sha,
        "intent_sha256":candidate.intent_sha256,
        "qualification_key":candidate.qualification_key,
        "path":candidate.path, "candidate_sha256":candidate.after_sha256,
        "os":oslabel, "source_module_inventory":list(modules),
        "baseline_g29":pristine, "baseline_full":full,
        "candidate_g29_negative":g29,
        "candidate_nonatlas":dict(positive), "candidate_compile":build,
        "baseline_full_pass":True, "all_candidate_modules_pass":True,
        "g29_modified_source_expected_negative":True,
        "source_split_pass":True, "child_cpu_rss_verified":budget_pass,
        "resource_accounting":"psutil-sampled-process-tree-v1" if budget_pass
            else "not-qualified-synthetic-or-missing-sample",
        "native_qualified":budget_pass, "scientific_first_use":False,
        "protected_holdouts_accessed":0,"accepted_ref_mutations":0,
        "paid_model_calls":0,
    }


def receipt_v3(admission:NativeAdmission, report:dict):
    need(isinstance(admission,NativeAdmission)
         and type(report) is dict
         and report.get("schema")==SCHEMA
         and admission.runner_os==report.get("os")
         and admission.intent.target_commit==report.get("ticket_source_commit")
         and admission.intent.target_tree_sha==report.get("target_tree_sha")
         and admission.intent.intent_sha256==report.get("intent_sha256")
         and admission.intent.qualification_key==report.get("qualification_key")
         and type(report.get("native_qualified")) is bool
         and type(report.get("child_cpu_rss_verified")) is bool
         and report["native_qualified"] is report["child_cpu_rss_verified"],
         "V3_SIGNED_SOURCE_OR_RESOURCE_CLAIM_INVALID")
    if report["native_qualified"]:
        from f139.nci04_v3_bounded_resource import (
            MAX_SAMPLED_RSS_BYTES, MAX_SAMPLED_CPU_MS)
        inventory=report.get("source_module_inventory")
        require(type(inventory) is list and len(inventory)>=5
                and len(set(inventory))==len(inventory)
                and ATLAS in inventory
                and set(report.get("candidate_nonatlas",{}))==
                    set(inventory)-{ATLAS}
                and report.get("source_split_pass") is True
                and report.get("baseline_full_pass") is True
                and report.get("all_candidate_modules_pass") is True
                and report.get("g29_modified_source_expected_negative") is True
                and report.get("candidate_g29_negative",{}).get("status")==CLOSED
                and report.get("resource_accounting")==
                    "psutil-sampled-process-tree-v1",
                "V3_PRODUCTION_TEST_INVENTORY_INCOMPLETE")
        expected={
            "baseline_g29":(unit(ATLAS),"PASS"),
            "baseline_full":(COMMAND+("-p","test_*.py","-v"),"PASS"),
            "candidate_g29_negative":(unit(ATLAS),CLOSED),
            "candidate_compile":(BUILD,"PASS"),
        }
        entries=[(report[k],argv,state) for k,(argv,state) in expected.items()]
        entries.extend((report["candidate_nonatlas"][name],unit(name),"PASS")
                       for name in inventory if name!=ATLAS)
        for row,argv,state in entries:
            require(type(row) is dict and row.get("argv")==list(argv)
                    and row.get("status")==state
                    and type(row.get("returncode")) is int
                    and ((state=="PASS" and row["returncode"]==0)
                         or (state==CLOSED and row["returncode"]>0))
                    and (argv==BUILD or
                         (type(row.get("discovered_tests")) is int
                          and row["discovered_tests"]>0))
                    and row.get("resource_budget_verified") is True
                    and type(row.get("resource_samples")) is int
                    and row["resource_samples"]>0
                    and type(row.get("child_peak_rss_bytes")) is int
                    and 0<row["child_peak_rss_bytes"]<=MAX_SAMPLED_RSS_BYTES
                    and type(row.get("child_cpu_ms")) is int
                    and 0<row["child_cpu_ms"]<=MAX_SAMPLED_CPU_MS
                    and row.get("resource_accounting")==
                        "psutil-sampled-process-tree-v1",
                    "V3_POSITIVE_TEST_OR_RESOURCE_FORGERY")
    return {
        "schema":RECEIPT,"ticket":admission.ticket,
        "source_sha":admission.source_sha,
        "run_id":admission.run_id, "os":admission.runner_os,
        "original_signed_admission_sha256":admission.authorization_sha256,
        "native_intent_sha256":admission.intent.intent_sha256,
        "qualification_key":admission.intent.qualification_key,
        "v3_report_sha256":digest(canonical(report)),
        "native_qualified":report["native_qualified"],
        "resource_accounting":report.get("resource_accounting"),
        "development_only":True,
        "scientific_first_use_authorized":False,
        "accepted_ref_mutations":0, "paid_model_calls":0,
    }
