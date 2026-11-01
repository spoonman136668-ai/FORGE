"""Development-only, fixed-budget public-observation causal cells.

Sixteen total addresses: seven active and nine retained. No hidden outcome
oracle, transformer, model API, source-family selection or scientific authority.
This is a simple explicit-memory *control*, not evidence of novel cognition.
"""

from __future__ import annotations

import hashlib
import struct


class PublicCausalCells:
    """Fixed 16 x 2 action x 2 observed-outcome counters (128 learned bytes)."""

    __slots__ = ("_counts",)

    ACTIVE_SLOTS = 7
    RETAINED_SLOTS = 9
    LEARNED_BYTES = 16 * 2 * 2 * 2
    MAGIC = b"YPC1"
    CHECKPOINT_BYTES = len(MAGIC) + LEARNED_BYTES + 32

    def __init__(self) -> None:
        self._counts = [[[0, 0] for _ in range(2)] for _ in range(16)]

    @staticmethod
    def _bit(value: int, name: str) -> int:
        if type(value) is not int or value not in (0, 1):
            raise ValueError(f"PUBLIC_CAUSAL_{name}_INVALID")
        return value

    @classmethod
    def _address(cls, address: int, retained: bool) -> int:
        if type(retained) is not bool:
            raise ValueError("PUBLIC_CAUSAL_RETAINED_FLAG_INVALID")
        limit = cls.RETAINED_SLOTS if retained else cls.ACTIVE_SLOTS
        if type(address) is not int or not 0 <= address < limit:
            raise ValueError("PUBLIC_CAUSAL_ADDRESS_INVALID")
        return address + (cls.ACTIVE_SLOTS if retained else 0)

    def observe(self, address: int, action: int, public_outcome: int, *,
                retained: bool = False) -> None:
        """Learn only after the environment reveals an actual binary outcome."""
        cell = self._address(address, retained)
        arm = self._bit(action, "ACTION")
        result = self._bit(public_outcome, "PUBLIC_OUTCOME")
        old = self._counts[cell][arm][result]
        self._counts[cell][arm][result] = min(65535, old + 1)

    def choose(self, address: int, *, retained: bool = False) -> int | None:
        """Compare matched empirical rates. Abstain without both arms' evidence."""
        cell = self._address(address, retained)
        (zero0, one0), (zero1, one1) = self._counts[cell]
        trials0 = zero0 + one0
        trials1 = zero1 + one1
        if not trials0 or not trials1:
            return None
        # Exact integer cross-products avoid rounding/tuned thresholds.
        lhs, rhs = one0 * trials1, one1 * trials0
        if lhs == rhs:
            return None
        return 0 if lhs > rhs else 1

    def snapshot(self) -> bytes:
        """One immutable, versioned 164-byte checkpoint with SHA-256 integrity."""
        raw = bytearray(self.MAGIC)
        for cell in self._counts:
            for arm in cell:
                for count in arm:
                    raw.extend(struct.pack(">H", count))
        digest = hashlib.sha256(raw).digest()
        return bytes(raw) + digest

    @classmethod
    def restore(cls, checkpoint: bytes) -> "PublicCausalCells":
        if (type(checkpoint) is not bytes or
                len(checkpoint) != cls.CHECKPOINT_BYTES or
                checkpoint[:len(cls.MAGIC)] != cls.MAGIC or
                hashlib.sha256(checkpoint[:-32]).digest() != checkpoint[-32:]):
            raise ValueError("PUBLIC_CAUSAL_CHECKPOINT_REJECTED")
        learned = checkpoint[len(cls.MAGIC):-32]
        cells = cls()
        iterator = iter(struct.unpack(">" + ("H" * 64), learned))
        for i in range(16):
            for arm in range(2):
                for outcome in range(2):
                    cells._counts[i][arm][outcome] = next(iterator)
        return cells
