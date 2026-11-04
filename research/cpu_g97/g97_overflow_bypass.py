#!/usr/bin/env python3
"""G97 online-only overflow-bypass cache policy; no inference or network calls."""
from collections import deque
from research.cpu_g96.g96_admission import AdmissionCache, CAPACITY, BYTE_LIMIT

WINDOW = 16
ENTER_DISTINCT = CAPACITY + 1
ENTER_HIT_NUMERATOR = 1
ENTER_HIT_DENOMINATOR = 8

class OverflowBypassCache(AdmissionCache):
    """Retain G96 LRU behavior except for bounded online overflow bypass.

    Each decision uses only preceding requests. Existing resident hits always work.
    An unseen key is bypassed while overflow is active. After a stable 16-request
    history containing <=4 distinct keys, normal LRU admission resumes.
    """
    def __init__(self, capacity=CAPACITY, byte_limit=BYTE_LIMIT):
        super().__init__("lru", capacity=capacity, byte_limit=byte_limit)
        self.history = deque(maxlen=WINDOW)
        self.overflow = False
        self.transitions = 0
        self.decision_count = 0

    def request(self, key, bytes_, build):
        # Validate before touching history or invoking the callback.
        if not isinstance(key, str) or not key:
            raise ValueError("G97_INVALID_KEY")
        if not isinstance(bytes_, int) or bytes_ < 0:
            raise ValueError("G97_INVALID_BYTES")
        self.decision_count += 1
        if len(self.history) == WINDOW:
            distinct = len({k for k, _ in self.history})
            hits = sum(hit for _, hit in self.history)
            if self.overflow:
                if distinct <= CAPACITY:
                    self.overflow = False
                    self.transitions += 1
            elif distinct >= ENTER_DISTINCT and hits * ENTER_HIT_DENOMINATOR < WINDOW * ENTER_HIT_NUMERATOR:
                self.overflow = True
                self.transitions += 1

        if self.overflow and key not in self.entries:
            # Preserve G96 miss accounting without constructing a KV object.
            self.clock += 1
            self.seen[key] += 1
            self.misses += 1
            self.bypasses += 1
            self.history.append((key, False))
            return None, False, False

        value, hit, admitted = super().request(key, bytes_, build)
        self.history.append((key, hit))
        return value, hit, admitted
