#!/usr/bin/env python3
"""G100 experimental online first-use deferral; model-free development only.

Not a G97 replacement, original-model adapter, performance verdict, or held-out
policy. No future traffic, labels, model predictions, or timing outcomes are read.
"""
from research.cpu_g97.g97_overflow_bypass import (OverflowBypassCache, WINDOW, ENTER_DISTINCT, ENTER_HIT_NUMERATOR, ENTER_HIT_DENOMINATOR)
from research.cpu_g96.g96_admission import CAPACITY
from research.cpu_g96.g96_admission import build_traffic, BYTE_LIMIT

class DeferredFirstAdmissionCache(OverflowBypassCache):
    """Defer construction on a key's first-ever miss; retain G97 thereafter.

    A repeated miss may still be admitted and incur build cost. This candidate
    deliberately does not claim to resolve the frozen per-request speed floor.
    """
    def request(self, key, bytes_, build):
        if not isinstance(key, str) or not key:
            raise ValueError("G100_INVALID_KEY")
        if not isinstance(bytes_, int) or bytes_ < 0:
            raise ValueError("G100_INVALID_BYTES")
        if key not in self.entries and self.seen[key] == 0:
            # G97 normally advances overflow state before deciding a request.
            # First-use deferral must preserve that online transition even when
            # no resident KV is built; evaluate strictly preceding history.
            if len(self.history) == WINDOW:
                distinct = len({past_key for past_key, _ in self.history})
                hits = sum(hit for _, hit in self.history)
                if self.overflow:
                    if distinct <= CAPACITY:
                        self.overflow = False
                        self.transitions += 1
                elif distinct >= ENTER_DISTINCT and hits * ENTER_HIT_DENOMINATOR < WINDOW * ENTER_HIT_NUMERATOR:
                    self.overflow = True
                    self.transitions += 1
            # Mirror the G96/G97 miss counters and online history; never call build.
            self.decision_count += 1
            self.clock += 1
            self.seen[key] += 1
            self.misses += 1
            self.bypasses += 1
            self.history.append((key, False))
            return None, False, False
        return super().request(key, bytes_, build)

def replay(stratum, cache_cls, *, bytes_per_key=1):
    """Deterministic bookkeeping comparison; counts are NOT latency evidence."""
    cache = cache_cls()
    calls = {"build": 0}
    def build(key):
        calls["build"] += 1
        return key
    for item in build_traffic(stratum, cycles=1):
        key = "prefix-%d" % item["prefix_id"]
        cache.request(key, bytes_per_key, lambda key=key: build(key))
        if len(cache.entries) > 4 or cache.resident_bytes() > BYTE_LIMIT:
            raise RuntimeError("G100_CACHE_BUDGET_VIOLATION")
    return {"requests":48, "hits":cache.hits, "misses":cache.misses,
            "admissions":cache.admissions, "evictions":cache.evictions,
            "bypasses":cache.bypasses, "build_calls":calls["build"],
            "max_final_resident_bytes":cache.resident_bytes()}
