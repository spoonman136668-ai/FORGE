"""Read-only, allowlisted summary of original F139 model-free failures.

This module is inert unless invoked. It does not call a provider, open the
owner database, write to disk, or change the controller or policy. The source
of acceptable codes is the existing F139 allowlist, not the untrusted log.
"""
from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import sys
from typing import Iterable

from f139.nci04_model_free_failure import SAFE_CODES

SCHEMA = "forge.f139.model-free-readonly-summary.v1"
DISPOSITION = "MODEL_FREE_SEARCH_BLOCKED_FAIL_CLOSED"
MAX_TAIL_LINES = 2000
MAX_JSON_LINE_CHARS = 131072
OTHER = "REDACTED_OR_MISSING"
# These are the only code names emitted by classify_model_free_failure in
# addition to its audited F139_ allowlist.
FALLBACK_CODES = frozenset({
    "OS_ERROR_NO_DETAILS",
    "UNCLASSIFIED_F139_ERROR",
    "UNCLASSIFIED_VALUE_ERROR",
    "UNCLASSIFIED_FAILURE",
})


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def summarize_model_free_log(lines: Iterable[str]) -> dict:
    """Summarize a finite log tail without releasing unreviewed log content.

    Untrusted strings and all fields other than the exact, allowlisted
    failure_code are discarded. The resulting JSON is bounded and has no
    timestamps, paths, exception messages, provider output, or credentials.
    """
    tail = deque(lines, maxlen=MAX_TAIL_LINES)
    counts: Counter[str] = Counter()
    last = None
    observed = 0
    for line in tail:
        if (not isinstance(line, str) or len(line) > MAX_JSON_LINE_CHARS
                or not line.startswith("{")):
            continue
        try:
            obj = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except (TypeError, ValueError, json.JSONDecodeError, RecursionError):
            continue
        if not isinstance(obj, dict) or obj.get("disposition") != DISPOSITION:
            continue
        observed += 1
        raw_code = obj.get("failure_code")
        code = (raw_code if type(raw_code) is str and
                (raw_code in SAFE_CODES or raw_code in FALLBACK_CODES)
                else OTHER)
        counts[code] += 1
        last = code
    return {
        "schema": SCHEMA,
        "observed_blocked": observed,
        "last_code": last,
        "code_counts": dict(sorted(counts.items())),
        "tail_lines_limit": MAX_TAIL_LINES,
    }


def main(argv: list[str] | None = None) -> int:
    """Emit exactly one sanitized read-only summary for a given log path."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("F139_MODEL_FREE_LOG_SUMMARY=INVALID_ARGUMENTS")
        return 2
    try:
        log_path = Path(args[0])
        if log_path.is_symlink() or not log_path.is_file():
            print("F139_MODEL_FREE_LOG_SUMMARY=UNAVAILABLE")
            return 2
        with log_path.open("r", encoding="utf-8", errors="replace") as lines:
            result = summarize_model_free_log(lines)
    except (OSError, UnicodeError):
        print("F139_MODEL_FREE_LOG_SUMMARY=UNAVAILABLE")
        return 2
    print("F139_MODEL_FREE_LOG_SUMMARY=" +
          json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
