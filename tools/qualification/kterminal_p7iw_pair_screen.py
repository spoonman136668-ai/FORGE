#!/usr/bin/env python3
"""P7-I/W: bounded, private-source Windows interaction test.
All original source, identifiers, process output and raw events stay on the
ephemeral FORGE-hosted worker. Only a sanitized SHA-256 receipt is published.
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
KT_SHA = "ba11a398586df9fe5233624d9cf115aeec76d11a"
OBSERVER = "TestStage3OriginalObserverForcedBoundaries"
SUITE_SEAL = "7fb89a178e5b13489c8037b6f759ce75e30f00a0f7646f5893aa73e340041dfa"
FOCUSED_SEAL = "e8e5b59f196d309199c487b8248de4496ebdab25a35648a1709a4fe6e5004f47"
IDENT = re.compile(r"^Test[A-Za-z0-9_]+$")
DECL = re.compile(r"(?m)^func\s+(Test[A-Za-z0-9_]+)\s*\(")


class Denied(Exception):
    pass


def require(ok, name):
    if not ok:
        raise Denied(name)


def receipt(file, seal):
    data = file.read_bytes()
    require(len(data) < 30000, "PREDECESSOR_RECEIPT_OVERSIZED")
    digest = hashlib.sha256(data).hexdigest()
    require(digest == seal, "PREDECESSOR_RECEIPT_HASH_DRIFT")
    require((file.parent / "receipt.sha256").read_text(encoding="ascii").strip() == digest,
            "PREDECESSOR_SEAL_INVALID")
    value = json.loads(data)
    require(isinstance(value, dict), "PREDECESSOR_RECEIPT_INVALID")
    return value


def private_failed_identity():
    prev = receipt(ROOT / "p7iu-previous" / "receipt.json", SUITE_SEAL)
    solo = receipt(ROOT / "p7iv-previous" / "receipt.json", FOCUSED_SEAL)
    require(prev.get("disposition") == "P7IU_OBSERVER_PASS_OTHER_PACKAGE_FAILURE",
            "PREDECESSOR_CLASSIFICATION_DRIFT")
    require(prev.get("exact_kterminal_source_sha") == KT_SHA,
            "SUITE_SOURCE_DRIFT")
    require(prev.get("observer_top_level") == {"run": 1, "pass": 1, "fail": 0},
            "OBSERVER_WAS_NOT_CONFIRMED_PASS")
    require(prev.get("observer_failed_subtests") == 0, "OBSERVER_NESTED_FAILURE")
    failed = prev.get("other_failed_test_name_hash_prefixes")
    require(isinstance(failed, list) and len(failed) == 1
            and re.fullmatch("[0-9a-f]{16}", failed[0]),
            "UNIQUE_FAILED_IDENTITY_UNAVAILABLE")
    require(solo.get("disposition") ==
            "P7IV_FAILED_TEST_PASSED_ALONE_SUITE_INTERFERENCE_SUSPECTED",
            "FOCUSED_PREDECESSOR_STATUS_DRIFT")
    require(solo.get("kterminal_pinned_sha") == KT_SHA and
            solo.get("previous_receipt_sha256") == SUITE_SEAL and
            solo.get("one_failed_test_hash_prefix") == failed[0],
            "FOCUSED_CUSTODY_CHAIN_MISMATCH")
    require(solo.get("single_test_events") == {"run": 1, "pass": 1, "fail": 0},
            "PREDECESSOR_FOCUSED_DID_NOT_PASS")
    source_files = sorted(Path("pkg").glob("*_test.go"))
    require(0 < len(source_files) < 1000, "PRIVATE_TEST_SOURCE_SCOPE")
    matches = []
    for file in source_files:
        raw = file.read_text(encoding="utf-8", errors="replace")
        for candidate in DECL.findall(raw):
            if hashlib.sha256(candidate.encode()).hexdigest()[:16] == failed[0]:
                matches.append(candidate)
    require(len(matches) == 1 and matches[0] != OBSERVER,
            "PRIVATE_FAILED_IDENTITY_NOT_UNIQUE")
    return matches[0], failed[0], len(source_files)


def list_registered_tests():
    out = ROOT / "p7iw-private-test-list"
    err = ROOT / "p7iw-private-list-stderr"
    with out.open("wb") as f, err.open("wb") as e:
        p = subprocess.run(["go", "test", "-list", "^Test", "./pkg"],
                           stdout=f, stderr=e, timeout=180, check=False)
    require(p.returncode == 0 and out.stat().st_size < 1000000,
            "TEST_REGISTRATION_LIST_BLOCKED")
    values = [x.strip() for x in out.read_text(errors="replace").splitlines()]
    names = [x for x in values if IDENT.fullmatch(x)]
    require(len(names) > 2 and len(names) == len(set(names)) and len(names) < 2000,
            "REGISTRATION_LIST_BOUNDS")
    return names


def run_tests(names, label, limit):
    require(all(IDENT.fullmatch(x) for x in names) and len(names) <= 700,
            "TEST_NAME_BOUNDARY")
    selector = "^(?:" + "|".join(re.escape(x) for x in names) + ")$"
    require(len(selector) < 18000, "TEST_SELECTOR_BOUNDARY")
    root = ROOT / ("p7iw-" + label + "-fixtures")
    require(not root.exists(), "FIXTURE_REUSE")
    env = dict(os.environ)
    env["K_TERMINAL_TEST_WORKSPACE"] = str(root)
    env["KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT"] = str(root / "tail")
    env["KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT"] = str(root / "post")
    env["KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT"] = str(root / "private")
    for suffix in ("tail", "post", "private"):
        (root / suffix).mkdir(parents=True)
    output = ROOT / ("p7iw-private-" + label + ".jsonl")
    stderr = ROOT / ("p7iw-private-" + label + ".stderr")
    start = time.monotonic()
    timed_out = False
    with output.open("wb") as fout, stderr.open("wb") as ferr:
        try:
            proc = subprocess.run([
                "go", "test", "-json", "-count=1", "-p=1", "-parallel=4",
                "-timeout=" + str(limit) + "s", "-run=" + selector, "./pkg"
            ], stdout=fout, stderr=ferr, env=env,
               timeout=limit + 35, check=False)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = 124
    require(output.stat().st_size < 90_000_000, "TEST_JSON_SIZE_BOUND")
    results = {x: {"run": 0, "pass": 0, "fail": 0} for x in names}
    unexpected = 0
    malformed = 0
    package_failed = False
    observer_nested_fails = 0
    for line in output.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if not isinstance(item, dict):
            malformed += 1
            continue
        act, name = item.get("Action"), item.get("Test")
        if act == "fail" and name is None:
            package_failed = True
        if isinstance(name, str) and act in ("run", "pass", "fail"):
            if name in results:
                results[name][act] += 1
            elif name.startswith(OBSERVER + "/"):
                if act == "fail":
                    observer_nested_fails += 1
            elif "/" not in name:
                unexpected += 1
    complete = (not timed_out and malformed == 0 and unexpected == 0 and
                all(z["run"] == 1 and z["pass"] + z["fail"] == 1 for z in results.values()))
    # Do not export private test identifiers except the already public observer name.
    observer = results.get(OBSERVER, {})
    return {
        "complete": complete, "go_exit": exit_code,
        "elapsed_seconds": round(time.monotonic() - start),
        "requested_tests": len(names),
        "observer": observer,
        "observer_nested_fails": observer_nested_fails,
        "failed_test_count": sum(z["fail"] > 0 for z in results.values()),
        "focal_test": results.get(os.environ["P7IW_FOCAL_TEST"], {}),
        "package_fail": package_failed, "unexpected_events": unexpected,
        "malformed_records": malformed, "timed_out": timed_out,
    }


def main():
    require(os.environ.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE" and
            os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted" and
            os.environ.get("RUNNER_OS") == "Windows",
            "NOT_FORGE_HOSTED_WINDOWS")
    require(os.environ.get("GOMAXPROCS") == "4" and
            os.environ.get("K_TERMINAL_EXECUTION_MODE") == "PAPER" and
            os.environ.get("K_TERMINAL_P5_LATENCY") == "0" and
            os.environ.get("K_TERMINAL_NATIVE_TIMING") == "0",
            "HISTORICAL_SCHEDULING_OR_PAPER_DRIFT")
    for key in ("COINBASE_API_KEY", "COINBASE_API_SECRET", "CDP_API_KEY_NAME",
                "CDP_API_KEY_PRIVATE_KEY", "K_TERMINAL_API_KEY", "K_TERMINAL_API_SECRET"):
        require(not os.environ.get(key), "REAL_BROKER_CREDENTIAL_ENV_PRESENT")
    focal, focal_hash, source_count = private_failed_identity()
    names = list_registered_tests()
    require(focal in names and OBSERVER in names, "REGISTERED_TEST_ABSENT")
    os.environ["P7IW_FOCAL_TEST"] = focal
    pair = run_tests([OBSERVER, focal], "pair", 840)
    subgroup = None
    if not pair["complete"]:
        disposition = "P7IW_PAIR_INCOMPLETE"
    elif pair["focal_test"]["fail"] or pair["observer"]["fail"] or pair["observer_nested_fails"]:
        disposition = "P7IW_PAIR_INTERACTION_FAILURE_REPRODUCED"
    elif pair["go_exit"] != 0:
        disposition = "P7IW_PAIR_PACKAGE_FAILURE_UNCLASSIFIED"
    else:
        remaining = [x for x in names if x not in (OBSERVER, focal)]
        count = (len(remaining) + 1) // 2
        selected = remaining[:count]
        require(len(selected) >= 1 and len(selected) <= 700, "BISECTION_COHORT_UNBOUNDED")
        subgroup = run_tests([OBSERVER, focal] + selected, "half", 1080)
        if not subgroup["complete"]:
            disposition = "P7IW_FIRST_HALF_INCOMPLETE"
        elif subgroup["focal_test"]["fail"] or subgroup["observer"]["fail"] or subgroup["observer_nested_fails"]:
            disposition = "P7IW_FIRST_HALF_CONTEXT_REPRODUCED"
        elif subgroup["go_exit"] != 0:
            disposition = "P7IW_FIRST_HALF_OTHER_TEST_FAILURE"
        else:
            disposition = "P7IW_FIRST_HALF_PASSED_INTERFERENCE_NOT_YET_REPRODUCED"
    receipt_value = {
        "schema": "forge.kterminal.p7iw.paired-half-context.v1",
        "forge_source_sha": os.environ["GITHUB_SHA"],
        "private_source_sha": KT_SHA,
        "source_test_files_examined": source_count,
        "focal_test_hash_prefix": focal_hash,
        "previous_suite_receipt_sha256": SUITE_SEAL,
        "previous_focused_receipt_sha256": FOCUSED_SEAL,
        "registered_original_top_level_tests": len(names),
        "scheduler": "GOMAXPROCS=4; go -p=1; test -parallel=4; count=1",
        "pair": pair, "first_half": subgroup,
        "disposition": disposition,
        "original_full_regression": "FAILED_NOT_WAIVED",
        "product_test_source_modified": False,
        "private_source_or_raw_test_output_uploaded": False,
        "owner_or_research_runner_used": False,
        "broker_orders": 0, "field_latency_measured": False,
    }
    folder = ROOT / "p7iw-sanitized"
    folder.mkdir(exist_ok=False)
    data = json.dumps(receipt_value, sort_keys=True, separators=(",", ":")).encode()
    (folder / "receipt.json").write_bytes(data)
    h = hashlib.sha256(data).hexdigest()
    (folder / "receipt.sha256").write_text(h, encoding="ascii")
    print("P7IW_PREDECESSOR_CUSTODY=PASS")
    print("P7IW_PRIVATE_SOURCE_HASH_RESOLUTION=PASS")
    print("P7IW_PAIR_COMPLETE=" + str(pair["complete"]))
    print("P7IW_PAIR_FOCAL_PASS=" + str(pair["focal_test"].get("pass", 0)))
    print("P7IW_PAIR_FOCAL_FAIL=" + str(pair["focal_test"].get("fail", 0)))
    print("P7IW_PAIR_OBSERVER_PASS=" + str(pair["observer"].get("pass", 0)))
    if subgroup:
        print("P7IW_FIRST_HALF_COMPLETE=" + str(subgroup["complete"]))
        print("P7IW_FIRST_HALF_FOCAL_PASS=" + str(subgroup["focal_test"].get("pass", 0)))
        print("P7IW_FIRST_HALF_FOCAL_FAIL=" + str(subgroup["focal_test"].get("fail", 0)))
    print("P7IW_DISPOSITION=" + disposition)
    print("P7IW_RECEIPT_SHA256=" + h)
    print("P7IW_PRIVATE_NAMES_AND_LOGS_EXPORTED=FALSE")
    if disposition in ("P7IW_PAIR_INCOMPLETE", "P7IW_PAIR_PACKAGE_FAILURE_UNCLASSIFIED",
                       "P7IW_FIRST_HALF_INCOMPLETE", "P7IW_FIRST_HALF_OTHER_TEST_FAILURE",
                       "P7IW_PAIR_INTERACTION_FAILURE_REPRODUCED",
                       "P7IW_FIRST_HALF_CONTEXT_REPRODUCED"):
        raise Denied("SCIENTIFIC_TEST_REPRODUCED_OR_INCOMPLETE")


if __name__ == "__main__":
    try:
        main()
    except Denied as e:
        print("P7IW_FAIL_CLOSED=" + str(e), file=sys.stderr)
        sys.exit(2)
    except Exception:
        print("P7IW_FAIL_CLOSED=UNCLASSIFIED_RUNTIME_ERROR", file=sys.stderr)
        sys.exit(2)
