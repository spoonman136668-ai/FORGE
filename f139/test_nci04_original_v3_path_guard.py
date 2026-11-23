"""V20 original owner V3 settlement path regression (synthetic, no host authority).

pathlib.Path() constructs WindowsPath/PosixPath, not an object whose
concrete type is exactly pathlib.Path. The owner lock must still be held
before the settlement can reach real database verification.
"""
from pathlib import Path
import unittest
from unittest.mock import patch

from f139 import nci04_original_v3_terminal as v3


class _VerificationReached(Exception):
    """Proof that the original type/lock guard passed; no mutation performed."""


class _ProbeDB:
    def verify(self):
        raise _VerificationReached()


class _ProbeAPI:
    pass


class _HeldOwner:
    calls = []

    @classmethod
    def held(cls, path):
        cls.calls.append(path)
        return True


class _UnlockedOwner:
    @staticmethod
    def held(path):
        return False


class OriginalV3PathGuardTests(unittest.TestCase):
    def setUp(self):
        _HeldOwner.calls = []
        self.db = _ProbeDB()
        self.api = _ProbeAPI()
        self.path = Path("test-only-original-state.sqlite")

    def invoke(self, path):
        return v3.settle_original_v3(
            self.db, self.api, path, ticket="test-only",
            run_id=123, started_at="2026-10-29T22:55:50Z",
            owner_key="not-a-real-secret",
        )

    def test_concrete_path_reaches_database_verification_only_with_owner_lock(self):
        # Python supplies WindowsPath on the real owner, PosixPath on Linux.
        self.assertIsNot(type(self.path), Path)
        with patch.object(v3, "Database", _ProbeDB), \
             patch.object(v3, "GitHub", _ProbeAPI), \
             patch.object(v3, "SingleOwner", _HeldOwner):
            with self.assertRaises(_VerificationReached):
                self.invoke(self.path)
        self.assertEqual(_HeldOwner.calls, [self.path.with_suffix(".lock")])

    def test_unheld_original_owner_lock_still_fails_closed(self):
        with patch.object(v3, "Database", _ProbeDB), \
             patch.object(v3, "GitHub", _ProbeAPI), \
             patch.object(v3, "SingleOwner", _UnlockedOwner):
            with self.assertRaisesRegex(
                v3.V3TerminalDenied, "SINGLE_ORIGINAL_OWNER_ONLY"
            ):
                self.invoke(self.path)

    def test_non_path_input_still_fails_closed(self):
        with patch.object(v3, "Database", _ProbeDB), \
             patch.object(v3, "GitHub", _ProbeAPI), \
             patch.object(v3, "SingleOwner", _HeldOwner):
            with self.assertRaisesRegex(
                v3.V3TerminalDenied, "SINGLE_ORIGINAL_OWNER_ONLY"
            ):
                self.invoke("test-only-original-state.sqlite")
        self.assertEqual(_HeldOwner.calls, [])


if __name__ == "__main__":
    unittest.main()
