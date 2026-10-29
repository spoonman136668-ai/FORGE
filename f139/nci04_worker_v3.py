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
    need(_git(root, "rev-parse", "--is-shallow-repository") == "false"
         and _git(root, "remote") == "", "SOURCE_ANCESTRY_OR_REMOTE_DRIFT")
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
    need(tuple(argv) == BUILD or (module is not None and tuple(argv)==unit(module)),
         "ARBITRARY_COMMAND_REJECTED")
    t0 = time.monotonic()
    if runner is None:
        raw, exitcode, outcome = _bounded_capture(
            argv,cwd=root,env=_env(),timeout_seconds=120)
    else:
        p=runner(list(argv),cwd=root,env=_env(),stdin=subprocess.DEVNULL,
                 stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,
                 check=False)
        raw,exitcode=p.stdout or b"",p.returncode
        outcome="PASS" if exitcode==0 else "TEST_FAILURE"
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
        "child_peak_rss_bytes":None,
        "child_cpu_ms":None,
        "resource_budget_verified":False,
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
    # Never mark a resource-unverified native result as signed positive.
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
        "source_split_pass":True, "child_cpu_rss_verified":False,
        "native_qualified":False, "scientific_first_use":False,
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
         and report.get("native_qualified") is False
         and report.get("child_cpu_rss_verified") is False,
         "V3_NOT_YET_SIGNABLE_POSITIVE")
    return {
        "schema":RECEIPT,"ticket":admission.ticket,
        "source_sha":admission.source_sha,
        "run_id":admission.run_id, "os":admission.runner_os,
        "original_signed_admission_sha256":admission.authorization_sha256,
        "native_intent_sha256":admission.intent.intent_sha256,
        "qualification_key":admission.intent.qualification_key,
        "v3_report_sha256":digest(canonical(report)),
        "native_qualified":False, "development_only":True,
        "scientific_first_use_authorized":False,
        "accepted_ref_mutations":0, "paid_model_calls":0,
    }
