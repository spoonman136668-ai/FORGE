"""Bounded two-tier evidence prototype for a historical saturation regression.

Development-only engineering prototype. Lifetime counters are monotonic uint16
values. A distinct fixed-size ring stores recent public outcomes; recency never
rewrites lifetime counts. This module is not Yggdrasil production code, is not
wired to a learner/controller, and supplies no scientific evidence by itself.
"""
from __future__ import annotations

import hashlib
import struct

class TwoTierEvidence:
    """16 addresses x 2 actions x 2 outcomes, plus 64 one-byte recent events.

    Lifetime table: 128 bytes. Recent ring: 64 bytes. Header: 6 bytes.
    SHA-256 integrity digest: 32 bytes. Total checkpoint: 230 bytes.
    Event byte packs address (4 bits), action (1 bit), public outcome (1 bit).
    """

    ADDRESSES = 16
    ACTIONS = 2
    OUTCOMES = 2
    LIFETIME_BYTES = ADDRESSES * ACTIONS * OUTCOMES * 2
    RECENT_CAPACITY = 64
    RECENT_BYTES = RECENT_CAPACITY
    MAGIC = b"Y2T1"
    HEADER = struct.Struct(">BB")
    CHECKPOINT_BYTES = len(MAGIC) + HEADER.size + LIFETIME_BYTES + RECENT_BYTES + 32
    LEARNED_BYTES = LIFETIME_BYTES + RECENT_BYTES + HEADER.size

    def __init__(self):
        self._lifetime = [[[0, 0] for _ in range(2)] for _ in range(16)]
        self._recent = bytearray(self.RECENT_CAPACITY)
        self._cursor = 0
        self._recent_count = 0

    @staticmethod
    def _bit(value, name):
        if type(value) is not int or value not in (0, 1):
            raise ValueError("TWO_TIER_" + name + "_INVALID")
        return value

    @staticmethod
    def _address(value):
        if type(value) is not int or not 0 <= value < 16:
            raise ValueError("TWO_TIER_ADDRESS_INVALID")
        return value

    def observe(self, address, action, public_outcome):
        """Commit only a revealed binary environment outcome."""
        address = self._address(address)
        action = self._bit(action, "ACTION")
        outcome = self._bit(public_outcome, "OUTCOME")
        counts = self._lifetime[address][action]
        # Lifetime evidence is monotonic and saturating; never halve or wrap.
        if counts[outcome] < 65535:
            counts[outcome] += 1
        event = (address << 2) | (action << 1) | outcome
        self._recent[self._cursor] = event
        self._cursor = (self._cursor + 1) % self.RECENT_CAPACITY
        self._recent_count = min(self.RECENT_CAPACITY, self._recent_count + 1)

    def lifetime_counts(self, address, action):
        address = self._address(address)
        action = self._bit(action, "ACTION")
        return tuple(self._lifetime[address][action])

    def recent_counts(self, address, action):
        address = self._address(address)
        action = self._bit(action, "ACTION")
        counts = [0, 0]
        start = (self._cursor - self._recent_count) % self.RECENT_CAPACITY
        for offset in range(self._recent_count):
            event = self._recent[(start + offset) % self.RECENT_CAPACITY]
            if (event >> 2) == address and ((event >> 1) & 1) == action:
                counts[event & 1] += 1
        return tuple(counts)

    @staticmethod
    def _winner(zero_counts, one_counts, minimum_support):
        total0 = sum(zero_counts)
        total1 = sum(one_counts)
        if total0 < minimum_support or total1 < minimum_support:
            return None
        lhs, rhs = zero_counts[1] * total1, one_counts[1] * total0
        if lhs == rhs:
            return None
        return 0 if lhs > rhs else 1

    def choose_lifetime(self, address, *, minimum_support=2):
        address = self._address(address)
        if type(minimum_support) is not int or not 1 <= minimum_support <= 64:
            raise ValueError("TWO_TIER_SUPPORT_INVALID")
        return self._winner(self._lifetime[address][0],
                            self._lifetime[address][1], minimum_support)

    def choose(self, address, *, minimum_support=2):
        """Use recent evidence when both arms are supported; else lifetime fallback."""
        address = self._address(address)
        if type(minimum_support) is not int or not 1 <= minimum_support <= 64:
            raise ValueError("TWO_TIER_SUPPORT_INVALID")
        recent = self._winner(self.recent_counts(address, 0),
                              self.recent_counts(address, 1), minimum_support)
        if recent is not None:
            return recent
        return self.choose_lifetime(address, minimum_support=minimum_support)

    def snapshot(self):
        raw = bytearray(self.MAGIC)
        raw.extend(self.HEADER.pack(self._cursor, self._recent_count))
        for cell in self._lifetime:
            for arm in cell:
                for count in arm:
                    raw.extend(struct.pack(">H", count))
        raw.extend(self._recent)
        return bytes(raw) + hashlib.sha256(raw).digest()

    @classmethod
    def restore(cls, checkpoint):
        if (type(checkpoint) is not bytes or len(checkpoint) != cls.CHECKPOINT_BYTES
                or checkpoint[:len(cls.MAGIC)] != cls.MAGIC
                or hashlib.sha256(checkpoint[:-32]).digest() != checkpoint[-32:]):
            raise ValueError("TWO_TIER_CHECKPOINT_REJECTED")
        offset = len(cls.MAGIC)
        cursor, recent_count = cls.HEADER.unpack(checkpoint[offset:offset + cls.HEADER.size])
        offset += cls.HEADER.size
        if (cursor >= cls.RECENT_CAPACITY or recent_count > cls.RECENT_CAPACITY
                or (recent_count == 0 and cursor != 0)
                or (0 < recent_count < cls.RECENT_CAPACITY and cursor != recent_count)):
            raise ValueError("TWO_TIER_CHECKPOINT_HEADER_INVALID")
        learned = checkpoint[offset:-32]
        cells = cls()
        counts_len = cls.LIFETIME_BYTES
        values = iter(struct.unpack(">" + ("H" * 64), learned[:counts_len]))
        for address in range(cls.ADDRESSES):
            for action in range(cls.ACTIONS):
                for outcome in range(cls.OUTCOMES):
                    cells._lifetime[address][action][outcome] = next(values)
        cells._recent[:] = learned[counts_len:]
        cells._cursor = cursor
        cells._recent_count = recent_count
        # Empty/unused ring slots must remain canonical zero to reject hidden payload.
        used = {(cursor - recent_count + i) % cls.RECENT_CAPACITY
                for i in range(recent_count)}
        if any(value != 0 for i, value in enumerate(cells._recent) if i not in used):
            raise ValueError("TWO_TIER_CHECKPOINT_UNUSED_SLOT_NONZERO")
        if any(value >> 6 for value in cells._recent):
            raise ValueError("TWO_TIER_CHECKPOINT_EVENT_INVALID")
        return cells
