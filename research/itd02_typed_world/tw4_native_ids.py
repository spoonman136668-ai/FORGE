#!/usr/bin/env python3
"""TW4: original RPGWorldSim typed entity ID grammar; source-only DEV.

Matches original packages/sim-core/src/ids.ts at commit
0387a1322e8924625f4bdc6ddd6356d517901dfe.
No source import, action, observation custody or scientific admission.
"""
from __future__ import annotations
import re

CANONICAL_INDEX = re.compile(r"(?:0|[1-9][0-9]*)\Z")
MAX_SAFE_JS_INT = 9007199254740991


def source_entity_id(value: object, kind: str) -> bool:
    """Pure canonical typed-ID check (not existence/ownership proof)."""
    if type(value) is not str or type(kind) is not str:
        return False
    parts = value.split(":")
    if len(parts) != 2 or parts[0] != kind:
        return False
    numeric = parts[1]
    return bool(CANONICAL_INDEX.fullmatch(numeric)) and int(numeric) <= MAX_SAFE_JS_INT


if __name__ == "__main__":
    raise SystemExit("TW4_NO_ORIGINAL_SOURCE_EXECUTION")
