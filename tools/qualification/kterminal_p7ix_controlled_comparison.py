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
    out = ROOT / "p7ix-private-test-list"
    err = ROOT / "p7ix-private-list-stderr"
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
    root = ROOT / ("p7ix-" + label + "-fixtures")
    require(not root.exists(), "FIXTURE_REUSE")
    env = dict(os.environ)
    env["K_TERMINAL_TEST_WORKSPACE"] = str(root)
    env["KABOOM_STAGE3_NATIVE_TAIL_RETENTION_ROOT"] = str(root / "tail")
    env["KABOOM_STAGE3_AUTHENTICATED_POST_RETENTION_ROOT"] = str(root / "post")
    env["KABOOM_STAGE3_PRIVATE_V2_RETENTION_ROOT"] = str(root / "private")
    for suffix in ("tail", "post", "private"):
        (root / suffix).mkdir(parents=True)
    output = ROOT / ("p7ix-private-" + label + ".jsonl")
    stderr = ROOT / ("p7ix-private-" + label + ".stderr")
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
    observer_line_nums = set()
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
        # Preserve only verified numeric assertion positions in the pinned
        # original observer test; never export source lines or private error text.
        if isinstance(name, str) and name.startswith(OBSERVER) and act == "output":
            output_text = item.get("Output", "")
            if isinstance(output_text, str):
                for hit in re.finditer(r"stage3-original-observer-forced-cuts_test\.go:(\d+)", output_text):
                    line_num = int(hit.group(1))
                    if 1 <= line_num <= 651 and len(observer_line_nums) < 12:
                        observer_line_nums.add(line_num)
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
        "observer_checked_in_failure_line_numbers": sorted(observer_line_nums),
        "failed_test_count": sum(z["fail"] > 0 for z in results.values()),
        "focal_test": results.get(os.environ["P7IX_FOCAL_TEST"], {}),
        "package_fail": package_failed, "unexpected_events": unexpected,
        "malformed_records": malformed, "timed_out": timed_out,
    }


def is_observer_failure(result):
    return bool(result["observer"].get("fail", 0)
                or result["observer_nested_fails"] > 0)


def isolated_observer_pass(result):
    return (result["complete"] and result["go_exit"] == 0 and
            result["observer"] == {"run": 1, "pass": 1, "fail": 0}
            and result["observer_nested_fails"] == 0 and
            not result["package_fail"])


def main():
    require(os.environ.get("GITHUB_REPOSITORY") == "spoonman136668-ai/FORGE" and
            os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted" and
            os.environ.get("RUNNER_OS") == "Windows",
            "FORGE_HOSTED_WINDOWS_REQUIRED")
    require(os.environ.get("GOMAXPROCS") == "4" and
            os.environ.get("K_TERMINAL_EXECUTION_MODE") == "PAPER" and
            os.environ.get("K_TERMINAL_P5_LATENCY") == "0" and
            os.environ.get("K_TERMINAL_NATIVE_TIMING") == "0",
            "HISTORICAL_PAPER_SCHEDULING_DRIFT")
    for key in ("COINBASE_API_KEY", "COINBASE_API_SECRET", "CDP_API_KEY_NAME",
                "CDP_API_KEY_PRIVATE_KEY", "K_TERMINAL_API_KEY", "K_TERMINAL_API_SECRET"):
        require(not os.environ.get(key), "BROKER_CREDENTIAL_ENV_PRESENT")
    focal, focal_hash, source_count = private_failed_identity()
    prior_hash = "ea47979420d7faceace89bfded71c5138a03b3bac5cc2e682033040d55fde0bb"
    previous = receipt(ROOT / "p7ix-pair-previous" / "receipt.json", prior_hash)
    require(previous.get("disposition") == "P7IW_PAIR_INTERACTION_FAILURE_REPRODUCED",
            "PREVIOUS_PAIR_NOT_FAILED")
    require(previous.get("private_source_sha") == KT_SHA and
            previous.get("previous_suite_receipt_sha256") == SUITE_SEAL and
            previous.get("previous_focused_receipt_sha256") == FOCUSED_SEAL and
            previous.get("focal_test_hash_prefix") == focal_hash,
            "PREVIOUS_PAIR_CUSTODY_DRIFT")
    old_pair = previous.get("pair", {})
    require(old_pair.get("complete") is True and
            old_pair.get("focal_test") == {"run": 1, "pass": 1, "fail": 0} and
            (old_pair.get("observer", {}).get("fail", 0) > 0 or
             old_pair.get("observer_nested_fails", 0) > 0),
            "PREVIOUS_PAIR_OBSERVER_FAILURE_NOT_AUTHENTICATED")
    os.environ["P7IX_FOCAL_TEST"] = focal

    # Fixed prospective comparison: same frozen test source, compiler, CPU policy
    # and Go parallelism, independent fixture roots, no shared child state.
    solo_a = run_tests([OBSERVER], "observer_alone_a", 720)
    pair_b = run_tests([OBSERVER, focal], "observer_plus_focal_b", 780)
    solo_c = None
    if is_observer_failure(pair_b):
        solo_c = run_tests([OBSERVER], "observer_alone_c", 720)

    valid = all(x["complete"] for x in (solo_a, pair_b) + ((solo_c,) if solo_c else ()))
    if not valid:
        disposition = "P7IX_COMPARISON_INCOMPLETE"
    elif not isolated_observer_pass(solo_a):
        disposition = "P7IX_OBSERVER_CAN_FAIL_ALONE_NO_PAIR_CAUSALITY"
    elif is_observer_failure(pair_b) and solo_c is not None and isolated_observer_pass(solo_c):
        disposition = "P7IX_ALONE_PASS_PAIR_FAIL_ALONE_PASS_CONTEXT_ASSOCIATION"
    elif is_observer_failure(pair_b):
        disposition = "P7IX_OBSERVER_FAILED_PAIR_AND_LATER_SOLO_CONTEXT_UNRESOLVED"
    elif pair_b["go_exit"] != 0 or pair_b["focal_test"].get("fail", 0):
        disposition = "P7IX_PAIRED_FOCAL_OR_OTHER_FAILURE"
    else:
        disposition = "P7IX_ALL_OBSERVED_CONTROLS_PASS_PRIOR_FAILURE_NOT_REPRODUCED"

    report = {
        "schema": "forge.kterminal.p7ix.observer-pair-controls.v1",
        "forge_head_sha": os.environ["GITHUB_SHA"],
        "pinned_private_source_sha": KT_SHA,
        "observer_test_public_identity": OBSERVER,
        "focal_test_hash_prefix": focal_hash,
        "source_files_verified": source_count,
        "prior_package_failure_seal": SUITE_SEAL,
        "prior_focal_isolated_pass_seal": FOCUSED_SEAL,
        "prior_observer_pair_failure_seal": prior_hash,
        "scheduler": "GOMAXPROCS=4; go test -p=1 -parallel=4 -count=1",
        "observer_solo_a": solo_a,
        "observer_focal_pair_b": pair_b,
        "observer_solo_c_if_needed": solo_c,
        "classification": disposition,
        "original_full_windows_regression": "FAILED_NOT_WAIVED",
        "real_trading_authorized": False,
        "broker_orders": 0,
        "source_modified": False,
        "private_test_names_or_raw_logs_uploaded": False,
        "local_or_research_runner_used": False,
        "desktop_installed_acceptance": False,
        "real_order_latency_measured": False,
    }
    folder = ROOT / "p7ix-sanitized"
    folder.mkdir(exist_ok=False)
    data = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    (folder / "receipt.json").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (folder / "receipt.sha256").write_text(digest, encoding="ascii")
    print("P7IX_PREDECESSOR_RECEIPTS=AUTHENTICATED")
    print("P7IX_PRIVATE_TEST_IDENTITIES=VERIFIED")
    print("P7IX_OBSERVER_SOLO_A_PASS=" + str(solo_a["observer"].get("pass", 0)))
    print("P7IX_OBSERVER_SOLO_A_FAIL=" + str(solo_a["observer"].get("fail", 0)))
    print("P7IX_PAIRED_OBSERVER_PASS=" + str(pair_b["observer"].get("pass", 0)))
    print("P7IX_PAIRED_OBSERVER_FAIL=" + str(pair_b["observer"].get("fail", 0)))
    print("P7IX_PAIRED_FOCAL_PASS=" + str(pair_b["focal_test"].get("pass", 0)))
    if solo_c is not None:
        print("P7IX_OBSERVER_SOLO_C_PASS=" + str(solo_c["observer"].get("pass", 0)))
        print("P7IX_OBSERVER_SOLO_C_FAIL=" + str(solo_c["observer"].get("fail", 0)))
    print("P7IX_DISPOSITION=" + disposition)
    print("P7IX_RECEIPT_SHA256=" + digest)
    print("P7IX_PRIVATE_LOGS_AND_SOURCE_EXPORTED=FALSE")
    if disposition != "P7IX_ALL_OBSERVED_CONTROLS_PASS_PRIOR_FAILURE_NOT_REPRODUCED":
        raise Denied("FAIL_CLOSED_OR_NEGATIVE_CAUSAL_COMPARISON")


if __name__ == "__main__":
    try:
        main()
    except Denied as e:
        print("P7IX_FAIL_CLOSED=" + str(e), file=sys.stderr)
        sys.exit(2)
    except Exception:
        print("P7IX_FAIL_CLOSED=UNCLASSIFIED_RUNTIME_ERROR", file=sys.stderr)
        sys.exit(2)
