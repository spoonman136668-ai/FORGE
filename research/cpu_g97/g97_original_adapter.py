#!/usr/bin/env python3
"""G97 original-model adapter; reuses the frozen G96 execution path.

The G96 function resolves AdmissionCache from its module globals. Temporarily
substitute the G97 class for this one call, then restore the original. This
keeps the exact prompt, decode, parity and measurement implementation identical.
Never call this concurrently with G96 runs in the same interpreter.
"""
import sys
from pathlib import Path
G96 = Path(__file__).resolve().parents[1] / "cpu_g96"
if str(G96) not in sys.path:
    sys.path.insert(0, str(G96))
import g96_original_adapter as frozen
from g97_overflow_bypass import OverflowBypassCache

def run_g97(model, stream, prefixes, keys, torch, proc):
    original = frozen.AdmissionCache
    try:
        frozen.AdmissionCache = lambda policy, calibration=None: OverflowBypassCache()
        return frozen.run_policy(model, stream, prefixes, keys, "lru", torch, proc)
    finally:
        frozen.AdmissionCache = original
