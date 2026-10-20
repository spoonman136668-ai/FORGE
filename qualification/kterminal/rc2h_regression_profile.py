#!/usr/bin/env python3
"""RC2-H read-only timing profile for an exact-source Go -json regression.

Never executes or alters tests. Reads the existing private JSONL locally;
prints only allowlisted package names, Go test names, elapsed seconds, and
counts. Does not upload fixture output or save a copy of sensitive test logs.
This is performance evidence, not a substitute for full regression PASS.
"""
import argparse
import collections
import json
import pathlib
import re
import sys

PACKAGE = re.compile(r"^k-terminal(?:/[A-Za-z0-9_./-]+)?$")
TEST = re.compile(r"^(?:Test|Example)[A-Za-z0-9_./#-]{0,220}$")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=pathlib.Path)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.sha):
        parser.error("--sha must be a full exact 40-hex source commit")
    if not args.jsonl.is_file():
        parser.error("missing regression JSONL; never infer a PASS")
    counts = collections.Counter()
    packages = {}
    tests = {}
    seen_run = set()
    seen_done = set()
    failed_tests = set()
    bad_lines = 0
    with args.jsonl.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                ev = json.loads(line)
            except (ValueError, TypeError):
                bad_lines += 1
                continue
            pkg = ev.get("Package", "")
            name = ev.get("Test", "")
            action = ev.get("Action", "")
            if not PACKAGE.fullmatch(pkg):
                continue
            elapsed = ev.get("Elapsed")
            if action in ("pass", "fail") and not name:
                packages[pkg] = {"status": action, "elapsed_s": elapsed}
                counts["finished_packages"] += 1
                if action == "fail":
                    counts["failed_packages"] += 1
            if not isinstance(name, str) or not TEST.fullmatch(name):
                continue
            if action == "run":
                seen_run.add((pkg, name))
                if "/" not in name:
                    counts["top_level_run"] += 1
            if action in ("pass", "fail"):
                seen_done.add((pkg, name))
                if action == "fail":
                    failed_tests.add((pkg, name))
                if "/" not in name:
                    counts["top_level_done"] += 1
                    tests[(pkg, name)] = {
                        "status": action,
                        "elapsed_s": elapsed,
                    }
    missing = sorted(seen_run - seen_done)
    pending = len(missing)
    if pending:
        counts["started_without_terminal_event"] = pending
    data = {
        "schema": "kterminal.rc2h.regression-duration-profile.v1",
        "source_sha": args.sha,
        "data_origin": "existing Go -json output only",
        "source_lines_corrupt": bad_lines,
        "counts": dict(counts),
        "slowest_packages": [
            {"package": p, **v}
            for p, v in sorted(packages.items(), key=lambda x: -(x[1]["elapsed_s"] or 0))
        ][:max(1, min(args.top, 25))],
        "slowest_top_level_tests": [
            {"package": key[0], "test": key[1], **v}
            for key, v in sorted(tests.items(), key=lambda x: -(x[1]["elapsed_s"] or 0))
        ][:max(1, min(args.top, 25))],
        "failed_tests": [
            {"package": p, "test": n}
            for p, n in sorted(failed_tests)
        ][:30],
        "missing_terminal_event_count": pending,
        "pass_claim_allowed": False,
        "warning": "Durations alone cannot prove coverage, accounting equivalence or qualification.",
    }
    print(json.dumps(data, sort_keys=True, indent=2))
    return 2 if bad_lines or pending or failed_tests or counts["failed_packages"] else 0


if __name__ == "__main__":
    sys.exit(main())
