#!/usr/bin/env python3
"""P7-I/Y: classify genuine frozen observer-only Windows failures without leaking
private source, test stdout/stderr, original child markers or account records.
No product modification, no fixture reuse, no scheduling or timeout relaxation.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(os.environ["RUNNER_TEMP"])
TARGET = "TestStage3OriginalObserverForcedBoundaries"
KT_SOURCE = "ba11a398586df9fe5233624d9cf115aeec76d11a"
CONTROLS = (
    ("p7ix-original", "567963f9ff1dc19a19c8ed678e3dfe7b68d0641f70b99b738e7d91ba7540028b",
     "P7IX_OBSERVER_CAN_FAIL_ALONE_NO_PAIR_CAUSALITY"),
    ("p7ix-corrected", "999b292841821614293e44e1b19c5d599a9dbe4255d2f63fcd15e0430cda0d29",
     "P7IX_OBSERVER_FAILED_PAIR_AND_LATER_SOLO_CONTEXT_UNRESOLVED"),
)
BOUND = 13 * 60
CLASSIFIERS = {
    "original bounded marker sharing/read policy refused": "MARKER_READ_OR_CHILD_EXIT",
    "owned child exited before publishing required marker": "CHILD_EXIT_BEFORE_MARKER",
    "owned child completion timed out": "CHILD_JOIN_TIMEOUT",
    "uninterrupted/restarted actual child failed": "CHILD_EXIT_NONZERO",
    "owned observer child failed Kill/Wait": "OWNED_CHILD_KILL_JOIN",
    "forced marker identity mismatch": "CUT_MARKER_IDENTITY",
    "parent exact uninterrupted original source comparison failed": "ORIGINAL_ORACLE_MISMATCH",
    "requested original source boundary was not reached": "FORCED_BOUNDARY_NOT_REACHED",
    "original independent oracle changed": "ORACLE_MUTATION",
    "partial cut lacks actual complete journal": "PARTIAL_JOURNAL",
}
ALLOWED_CLASSES = set(CLASSIFIERS.values()) | {"OTHER_FAILURE_OR_TIMEOUT", "NO_FAILURE"}


class Rejected(Exception):
    pass


def require(ok, message):
    if not ok:
        raise Rejected(message)


def provenance():
    for directory, seal, expected in CONTROLS:
        folder = ROOT / directory
        p = folder / "receipt.json"
        h = folder / "receipt.sha256"
        require(p.is_file() and h.is_file() and p.stat().st_size <= 30000,
                "PREDECESSOR_ARTIFACT_MISSING_OR_LARGE")
        data = p.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        require(digest == seal and h.read_text(encoding="ascii").strip() == seal,
                "PREDECESSOR_SEAL_DRIFT")
        obj = json.loads(data)
        require(obj.get("classification") == expected
                and obj.get("pinned_private_source_sha") == KT_SOURCE,
                "PREDECESSOR_SCOPE_OR_DISPOSITION_DRIFT")
        require(obj.get("broker_orders") == 0 and obj.get("source_modified") is False,
                "PREDECESSOR_UNSAFE_ADMISSION")
    print("P7IY_TWO_PREDECESSOR_SEALS=VERIFIED")


def worker(trial):
    root = ROOT / ("p7iy-" + trial)
    require(not root.exists(), "FIXTURE_ALREADY_EXISTS")
    for sub in ("tail", "post", "private"):
        (root / sub).mkdir(parents=True)
    env = dict(os.environ)
    env.update({
        "K_TERMINAL_TEST_WORKSPACE": str(root),
        "KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT": str(root / "tail"),
        "KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT": str(root / "post"),
        "KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT": str(root / "private"),
    })
    events_path = ROOT / ("p7iy-" + trial + "-private-events.jsonl")
    stderr_path = ROOT / ("p7iy-" + trial + "-private-stderr.txt")
    start = time.monotonic()
    timed_out = False
    with events_path.open("wb") as out, stderr_path.open("wb") as err:
        try:
            task = subprocess.run(
                ["go", "test", "-json", "-count=1", "-p=1", "-parallel=4",
                 "-timeout=12m", "-run=^" + TARGET + "$", "./pkg"],
                stdout=out, stderr=err, env=env, timeout=BOUND, check=False)
            status = task.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            status = 124
    require(events_path.stat().st_size <= 70_000_000, "PRIVATE_EVENTS_TOO_LARGE")
    counts = {}
    failure_msgs = {}
    main = {"run": 0, "pass": 0, "fail": 0}
    package = {"pass": 0, "fail": 0}
    malformed = 0
    for line in events_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if not isinstance(e, dict):
            malformed += 1
            continue
        test, action = e.get("Test"), e.get("Action")
        if test is None and action in package:
            package[action] += 1
        if test == TARGET and action in main:
            main[action] += 1
        if not isinstance(test, str) or not test.startswith(TARGET + "/"):
            continue
        nested = test[len(TARGET) + 1:]
        # Only fully specified product/scenario leaves; exclude product parents.
        if len(nested.split("/")) != 2:
            continue
        digest = hashlib.sha256(test.encode("utf-8")).hexdigest()[:16]
        row = counts.setdefault(digest, {"run": 0, "pass": 0, "fail": 0})
        if action in row:
            row[action] += 1
        if action == "output":
            output = e.get("Output", "")
            if isinstance(output, str) and len(output) <= 20000:
                categories = failure_msgs.setdefault(digest, set())
                for literal, cls in CLASSIFIERS.items():
                    if literal in output:
                        categories.add(cls)
    failures = {}
    for digest, row in sorted(counts.items()):
        if row["fail"]:
            cats = failure_msgs.get(digest, set())
            failures[digest] = sorted(cats) if cats else ["OTHER_FAILURE_OR_TIMEOUT"]
    # Failure classifications must never depend on private raw output being public.
    complete = (not timed_out and malformed == 0 and
                len(counts) == 26 and
                all(x["run"] == 1 and x["pass"] + x["fail"] == 1 for x in counts.values()) and
                main["run"] == 1 and main["pass"] + main["fail"] == 1)
    return {
        "trial": trial,
        "elapsed_seconds": int(time.monotonic() - start),
        "top": main, "package": package,
        "leaf_cases_seen": len(counts),
        "leaf_cases_pass": sum(x["pass"] for x in counts.values()),
        "leaf_cases_fail": sum(x["fail"] for x in counts.values()),
        "failed_scenario_hash_and_class": failures,
        "go_exit": status, "timed_out": timed_out,
        "malformed_json_lines": malformed, "complete": complete,
    }


def main():
    require(os.environ.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
            and os.environ.get("RUNNER_OS") == "Windows", "WRONG_HOSTED_CONTEXT")
    require(os.environ.get("GOMAXPROCS") == "4"
            and os.environ.get("K_TERMINAL_EXECUTION_MODE") == "PAPER"
            and os.environ.get("K_TERMINAL_NATIVE_TIMING") == "0"
            and os.environ.get("K_TERMINAL_P5_LATENCY") == "0",
            "FROZEN_WINDOWS_SCHEDULING_DRIFT")
    for name in ("COINBASE_API_KEY", "COINBASE_API_SECRET", "CDP_API_KEY_NAME",
                 "CDP_API_KEY_PRIVATE_KEY", "K_TERMINAL_API_KEY",
                 "K_TERMINAL_API_SECRET"):
        require(not os.getenv(name), "REAL_BROKER_CREDENTIALS_PRESENT")
    provenance()
    trials = [worker("first"), worker("second")]
    if any(not trial["complete"] for trial in trials):
        verdict = "P7IY_INCOMPLETE_OR_TIMED_OUT"
    elif any(trial["top"]["fail"] or trial["go_exit"] for trial in trials):
        verdict = "P7IY_OBSERVER_ALONE_FAILURE_REPRODUCED_WITH_SCENARIO_CLASS"
    else:
        verdict = "P7IY_TWO_OBSERVER_SOLO_RUNS_PASS_PRIOR_FLAKE_NOT_CLEARED"
    report = {
        "schema": "forge.kterminal.p7iy.original-observer-failure-class.v1",
        "forge_head_sha": os.environ["GITHUB_SHA"],
        "private_kt_sha": KT_SOURCE,
        "observer_source_blob": "bee85ee3441b0f66399ab6c42f8b09635ba44c6b",
        "frozen_scheduler": "go1.26.5 windows-2022 GOMAXPROCS=4 -p=1 -parallel=4",
        "trials": trials,
        "verdict": verdict,
        "original_full_windows_regression": "FAILED_NOT_WAIVED",
        "product_or_original_tests_modified": False,
        "user_data_or_raw_logs_uploaded": False,
        "research_and_owner_runner_used": False,
        "real_broker_orders": 0,
        "managed_desktop_or_real_latency_qualified": False,
    }
    out = ROOT / "p7iy-sanitized"
    out.mkdir(exist_ok=False)
    data = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    (out / "receipt.json").write_bytes(data)
    checksum = hashlib.sha256(data).hexdigest()
    (out / "receipt.sha256").write_text(checksum, encoding="ascii")
    for t in trials:
        print("P7IY_" + t["trial"].upper() + "_COMPLETE=" + str(t["complete"]))
        print("P7IY_" + t["trial"].upper() + "_LEAF_FAIL_COUNT=" + str(t["leaf_cases_fail"]))
        print("P7IY_" + t["trial"].upper() + "_TOP_PASS=" + str(t["top"]["pass"]))
    print("P7IY_VERDICT=" + verdict)
    print("P7IY_RECEIPT_SHA256=" + checksum)
    print("P7IY_PRIVATE_SOURCE_AND_LOGS_EXPORTED=FALSE")
    if verdict != "P7IY_TWO_OBSERVER_SOLO_RUNS_PASS_PRIOR_FLAKE_NOT_CLEARED":
        raise Rejected("NEGATIVE_OR_INCOMPLETE_TEST_CLASSIFICATION")


if __name__ == "__main__":
    try:
        main()
    except Rejected as e:
        print("P7IY_FAIL_CLOSED=" + str(e), file=sys.stderr)
        sys.exit(2)
    except Exception:
        print("P7IY_FAIL_CLOSED=UNCLASSIFIED_RUNTIME_OR_INPUT_ERROR", file=sys.stderr)
        sys.exit(2)
