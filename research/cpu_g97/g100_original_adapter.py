#!/usr/bin/env python3
"""Isolated G100 original-model adapter using the frozen G96 execution path.

No new model inference, generation, traffic selection or timing harness is
implemented here. The substitution is process-local and must not run alongside
another G96/G97 adapter in the same interpreter.
"""
from research.cpu_g97 import g97_original_adapter as g97
from research.cpu_g97.g100_deferred_admission import DeferredFirstAdmissionCache


def run_g100(model, stream, prefixes, keys, torch, proc):
    """Run frozen original GPT-2 policy with a G100 cache, restoring on failure."""
    frozen = g97.frozen
    original = frozen.AdmissionCache
    try:
        frozen.AdmissionCache = lambda policy, calibration=None: DeferredFirstAdmissionCache()
        return frozen.run_policy(model, stream, prefixes, keys, "lru", torch, proc)
    finally:
        frozen.AdmissionCache = original
