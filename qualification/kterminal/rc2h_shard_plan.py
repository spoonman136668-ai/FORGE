#!/usr/bin/env python3
"""RC2-H lossless, source-pinned *planning* of Go pkg top-level test shards.

This tool does not run tests and does not accept cached test PASS as evidence.
It consumes actual 'go test -list .' inventories from the frozen original and
candidate with the same Go toolchain and environment, and fails closed unless
candidate-original == the single expected new test. It generates anchored -run
expressions for independent PROCESS shards, not goroutine-parallel subtests.
Fuzz seeds and Examples are included; benchmarks are intentionally excluded
because ordinary 'go test' does not execute benchmark functions.

This is a dry-run plan only: before adopting sharding as a final acceptance
method, compare its complete -json outcomes with a full serial execution on
the exact same source and test environment, including test/subtest names,
failure/fatal behavior and financial evidence hashes.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

GO_TOP_LEVEL = re.compile(r"^(Test[A-Za-z0-9_]+|Example[A-Za-z0-9_]*|Fuzz[A-Za-z0-9_]+)$")
IGNORED_GO = re.compile(r"^(?:Benchmark[A-Za-z0-9_]+|TestMain|ok[ \t].*|\?[ \t].*|FAIL(?:[ \t].*)?|warning:.*)$")
EXPECTED_ADDITION = "TestHistoricalPnLFullAuditClockAndImmutableJournal"


def parse_inventory(path):
    if not path.is_file():
        raise ValueError("MISSING_INVENTORY:" + str(path))
    names = []
    bad = []
    for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
        line = raw.strip()
        if not line or IGNORED_GO.fullmatch(line):
            continue
        if GO_TOP_LEVEL.fullmatch(line):
            names.append(line)
        else:
            bad.append(line[:80])
    if bad or len(names) != len(set(names)) or not names:
        raise ValueError("AMBIGUOUS_TEST_LIST:bad_lines=" + str(len(bad)) +
                         ",duplicates=" + str(len(names) - len(set(names))) +
                         ",count=" + str(len(names)))
    return sorted(names)


def fingerprint(names):
    return hashlib.sha256(("\\n".join(names) + "\\n").encode("utf-8")).hexdigest()


def calculate(original, candidate, shards, max_regex_bytes):
    if set(candidate) - set(original) != {EXPECTED_ADDITION}:
        raise ValueError("CANDIDATE_ADDITIONS_NOT_EXACTLY_EXPECTED")
    if set(original) - set(candidate):
        raise ValueError("ORIGINAL_TEST_REMOVED")
    output = [[] for _ in range(shards)]
    for test in candidate:
        index = int(hashlib.sha256(test.encode("utf-8")).hexdigest()[:8], 16) % shards
        output[index].append(test)
    if any(not group for group in output):
        raise ValueError("EMPTY_SHARD")
    if sorted(x for group in output for x in group) != candidate:
        raise ValueError("SHARD_COVERAGE_OR_DUPLICATION")
    plans = []
    for index, group in enumerate(output):
        # Exact top-level names, with /subtests inherited automatically.
        regex = "^(" + "|".join(re.escape(x) for x in group) + ")$"
        if len(regex.encode("utf-8")) > max_regex_bytes:
            raise ValueError("COMMAND_LINE_LIMIT_SHARD_" + str(index))
        plans.append({"id": index, "top_level_count": len(group),
                      "run_regex": regex,
                      "top_level_names_sha256": fingerprint(group),
                      "exact_names": group})
    return {
        "schema": "kterminal.rc2h.go-pkg-test-shard-plan.v1",
        "original_count": len(original),
        "candidate_count": len(candidate),
        "expected_new_test": EXPECTED_ADDITION,
        "original_inventory_sha256": fingerprint(original),
        "candidate_inventory_sha256": fingerprint(candidate),
        "shards": plans,
        "all_candidate_tests_covered_once": True,
        "test_assertions_modified": False,
        "runtime_equivalence_qualified": False,
        "warning": "This is only a coverage-exact plan. Runtime regression still required.",
    }


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--original", required=True, type=pathlib.Path)
    cli.add_argument("--candidate", required=True, type=pathlib.Path)
    cli.add_argument("--shards", type=int, choices=(2, 3, 4), default=4)
    cli.add_argument("--max-regex-bytes", type=int, default=6200)
    cli.add_argument("--original-sha", required=True)
    cli.add_argument("--candidate-sha", required=True)
    cli.add_argument("--output", type=pathlib.Path)
    opt = cli.parse_args()
    if opt.original_sha != "eb5d225ae73b698a59c68d840daf1ec678e1a0ec" or opt.candidate_sha != "b8c2052d530cdff93462dfccc21b28f3824e5531":
        cli.error("FROZEN_SOURCE_IDENTITY_MISMATCH")
    try:
        plan = calculate(parse_inventory(opt.original), parse_inventory(opt.candidate),
                         opt.shards, opt.max_regex_bytes)
    except ValueError as e:
        print("KTERM_RC2H_SHARD_COVERAGE=FAIL_CLOSED:" + str(e), file=sys.stderr)
        return 2
    plan["original_sha"] = opt.original_sha
    plan["candidate_sha"] = opt.candidate_sha
    encoded = json.dumps(plan, sort_keys=True, indent=2)
    if opt.output:
        if opt.output.exists():
            print("KTERM_RC2H_PLAN_OUTPUT_ALREADY_EXISTS", file=sys.stderr)
            return 2
        opt.output.write_text(encoded + "\n", encoding="utf-8")
    # Never dump source-private individual test names into public CI.
    print("KTERM_RC2H_CANDIDATE_TEST_COUNT="+str(plan["candidate_count"]))
    print("KTERM_RC2H_ORIGINAL_TEST_COUNT="+str(plan["original_count"]))
    print("KTERM_RC2H_SHARDS="+str(len(plan["shards"])))
    print("KTERM_RC2H_EXACT_STATIC_COVERAGE=PASS")
    print("KTERM_RC2H_RUNTIME_EQUIVALENCE=NOT_YET_QUALIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
