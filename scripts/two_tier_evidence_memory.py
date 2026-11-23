"""Fixed-budget two-tier memory with context-isolated recency slots.

Development-only engineering prototype. Lifetime uint16 counts are monotonic.
Each address/action pair owns two recent outcome slots, so busy contexts cannot
evict another context's evidence. No production Yggdrasil integration.
"""
from __future__ import annotations
import hashlib
import struct

class TwoTierEvidence:
    """16 addresses x 2 actions x 2 outcomes, plus isolated recent outcome slots.

    Lifetime table: 128 bytes. Recent slots: 64 bytes. Header: 2 bytes.
    SHA-256 digest: 32 bytes. Checkpoint: 230 bytes; learned state: 194 bytes.
    Each address/action pair owns two one-byte slots; 255 marks an empty slot.
    """
    ADDRESSES = 16
    ACTIONS = 2
    OUTCOMES = 2
    LIFETIME_BYTES = ADDRESSES * ACTIONS * OUTCOMES * 2
    RECENT_CAPACITY = ADDRESSES * ACTIONS * 2
    RECENT_BYTES = RECENT_CAPACITY
    MAGIC = b"Y2T1"
    HEADER = struct.Struct(">BB")
    CHECKPOINT_BYTES = len(MAGIC) + HEADER.size + LIFETIME_BYTES + RECENT_BYTES + 32
    LEARNED_BYTES = LIFETIME_BYTES + RECENT_BYTES + HEADER.size

    def __init__(self):
        self._lifetime = [[[0, 0] for _ in range(2)] for _ in range(16)]
        self._recent = bytearray([255] * self.RECENT_CAPACITY)

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

    def _recent_slot(self, address, action):
        return (address * self.ACTIONS + action) * 2

    def observe(self, address, action, public_outcome):
        address = self._address(address)
        action = self._bit(action, "ACTION")
        outcome = self._bit(public_outcome, "OUTCOME")
        counts = self._lifetime[address][action]
        if counts[outcome] < 65535:
            counts[outcome] += 1
        slot = self._recent_slot(address, action)
        first, second = self._recent[slot:slot + 2]
        if first == 255:
            self._recent[slot] = outcome
        elif second == 255:
            self._recent[slot + 1] = outcome
        else:
            # Rotate only this address/action's two most recent outcomes.
            self._recent[slot] = second
            self._recent[slot + 1] = outcome

    def lifetime_counts(self, address, action):
        address = self._address(address)
        action = self._bit(action, "ACTION")
        return tuple(self._lifetime[address][action])

    def recent_counts(self, address, action):
        address = self._address(address)
        action = self._bit(action, "ACTION")
        slot = self._recent_slot(address, action)
        counts = [0, 0]
        for outcome in self._recent[slot:slot + 2]:
            if outcome in (0, 1):
                counts[outcome] += 1
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
        address = self._address(address)
        if type(minimum_support) is not int or not 1 <= minimum_support <= 64:
            raise ValueError("TWO_TIER_SUPPORT_INVALID")
        recent = self._winner(self.recent_counts(address, 0),
                              self.recent_counts(address, 1), minimum_support)
        return (recent if recent is not None else
                self.choose_lifetime(address, minimum_support=minimum_support))

    def snapshot(self):
        raw = bytearray(self.MAGIC)
        raw.extend(self.HEADER.pack(1, 0))
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
        version, reserved = cls.HEADER.unpack(checkpoint[offset:offset + cls.HEADER.size])
        offset += cls.HEADER.size
        if version != 1 or reserved != 0:
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
        for slot in range(0, cls.RECENT_CAPACITY, 2):
            first, second = cells._recent[slot:slot + 2]
            if first not in (0, 1, 255) or second not in (0, 1, 255):
                raise ValueError("TWO_TIER_CHECKPOINT_EVENT_INVALID")
            if first == 255 and second != 255:
                raise ValueError("TWO_TIER_CHECKPOINT_UNUSED_SLOT_NONZERO")
        return cells
