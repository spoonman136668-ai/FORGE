#!/usr/bin/env python3
"""Pin every existing non-supervisor Go subprocess call exactly.

The original Linux public-isolation grep on main rejected these historical
calls indiscriminately. This guard remains fail-closed on any *additional*,
removed, moved, or modified exec.Command/exec.CommandContext occurrence.
The bounded supervisor has its own unchanged separate grep custody checks.
This is not a general-purpose subprocess permission or execution adapter.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

# Frozen existing FORGE source at the protected V18 merge commit
# 70923c933990f3788c6cae7206e81a6049be4dac. No new exception is granted.
EXPECTED = {
    "cyclecontroller/controller_test.go": Counter({
        'cmd:=exec.Command("go","build","-o",buildPath,"./cmd/forge-sandbox-worker")': 1,
    }),
    "cyclecontroller/controller.go": Counter({
        'cmd:=exec.CommandContext(bounded,worker,"--synthetic-only","--lane",lane,"--new-dir",childDir)': 1,
    }),
    "cmd/forge-code-atlas/main.go": Counter({
        'c:=exec.Command("git",args...);c.Dir=root': 1,
    }),
    "cmd/f96eval/main.go": Counter({
        'cmd:=exec.Command("git",args...)': 1,
    }),
    "cmd/f95audit/main.go": Counter({
        'c:=exec.Command("git",args...)': 1,
    }),
    "originalclaim/process_integration_test.go": Counter({
        'cmd:=exec.Command(os.Args[0],"-test.run=^TestR25WorkerChild$")': 2,
    }),
}


def collect(root: Path) -> dict[str, Counter]:
    actual: dict[str, Counter] = {}
    for path in sorted(root.rglob("*.go")):
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        # Retain the existing supervisor's independently counted exceptions.
        if rel.parts[0] == "subprocesssupervisor" or rel.parts[:2] == (
            "cmd", "forge-synthetic-supervisor"
        ):
            continue
        if path.is_symlink():
            raise ValueError("UNTRUSTED_GO_SYMLINK:" + rel.as_posix())
        for line in path.read_text(encoding="utf-8").splitlines():
            if "exec.Command" in line:
                actual.setdefault(rel.as_posix(), Counter())[line.strip()] += 1
    return actual


def check(root: Path) -> None:
    observed = collect(root)
    if observed != EXPECTED:
        missing = sorted(set(EXPECTED) - set(observed))
        added = sorted(set(observed) - set(EXPECTED))
        changed = sorted(
            path for path in set(EXPECTED) & set(observed)
            if EXPECTED[path] != observed[path]
        )
        raise ValueError(
            "FORGE_PUBLIC_SUBPROCESS_SOURCE_DRIFT:"
            f"missing={missing!r}:added={added!r}:changed={changed!r}"
        )


def main() -> int:
    try:
        check(Path(__file__).resolve().parents[1])
    except (ValueError, OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("FORGE_PUBLIC_NON_SUPERVISOR_SUBPROCESS_EXACT_EXISTING_SITES=PASS")
    print("FORGE_NEW_SUBPROCESS_SITES=ZERO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
