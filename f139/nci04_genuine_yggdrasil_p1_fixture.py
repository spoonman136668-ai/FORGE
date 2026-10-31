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

    def observed_action_contrast(self, address: int, *,
                                 retained: bool = False) -> tuple[int, int] | None:
        """Exact public-outcome rate contrast (action 1 minus action 0).

        Return (signed_numerator, positive_denominator), not a float. Both
        actions must have independently observed outcomes, or abstain. Only
        public action/outcome counts are read; correlation is not treated as
        an intervention or a counterfactual. No learned bytes, checkpoint
        format, confidence threshold or existing decisions are changed.
        """
        cell = self._address(address, retained)
        (fail0, success0), (fail1, success1) = self._counts[cell]
        total0 = fail0 + success0
        total1 = fail1 + success1
        if not total0 or not total1:
            return None
        return (success1 * total0 - success0 * total1, total0 * total1)

    def choose_wilson(self, address: int, *, retained: bool = False) -> int | None:
        """Optional 95% Wilson-interval abstention control, not a learned oracle.

        Each arm needs independently observed public outcomes. Return an
        action only when its *lower* success bound exceeds the other arm's
        upper bound. Otherwise abstain instead of converting sparse noise
        into a certain action. No counter or checkpoint bytes are changed.
        """
        from math import sqrt

        cell = self._address(address, retained)
        (zero0, one0), (zero1, one1) = self._counts[cell]

        def bounds(failures: int, successes: int) -> tuple[float, float] | None:
            trials = failures + successes
            if trials == 0:
                return None
            # Fixed conventional two-sided 95% normal quantile: no tuning on
            # held-out rewards, adaptive thresholds, or private world state.
            z = 1.959963984540054
            z2 = z * z
            p = successes / trials
            divisor = 1.0 + z2 / trials
            center = (p + z2 / (2.0 * trials)) / divisor
            radius = z * sqrt((p * (1.0 - p) + z2 / (4.0 * trials))
                              / trials) / divisor
            return center - radius, center + radius

        arm0 = bounds(zero0, one0)
        arm1 = bounds(zero1, one1)
        if arm0 is None or arm1 is None:
            return None
        if arm0[0] > arm1[1]:
            return 0
        if arm1[0] > arm0[1]:
            return 1
        return None

    def choose_posterior_public_cost_p1(self, address: int,
                                             cost0: int, cost1: int, *,
                                             reward_value: int = 1,
                                             retained: bool = False) -> int | None:
        """Opt-in posterior-smoothed empirical public-cost control.

        Symmetric Beta(1,1) pseudo-counts; no hidden outcomes,
        intervention oracle, new learned bytes or checkpoint modifications.
        Independent observed outcomes are required for both actions.
        """
        if (type(cost0) is not int or type(cost1) is not int
                or not 0 <= cost0 <= 65535 or not 0 <= cost1 <= 65535):
            raise ValueError("PUBLIC_CAUSAL_COST_INVALID")
        if type(reward_value) is not int or not 1 <= reward_value <= 65535:
            raise ValueError("PUBLIC_CAUSAL_REWARD_VALUE_INVALID")
        cell = self._address(address, retained)
        (fail0, success0), (fail1, success1) = self._counts[cell]
        n0, n1 = fail0 + success0, fail1 + success1
        if not n0 or not n1:
            return None
        d0, d1 = n0 + 2, n1 + 2
        lhs = ((success0 + 1) * reward_value - cost0 * d0) * d1
        rhs = ((success1 + 1) * reward_value - cost1 * d1) * d0
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
