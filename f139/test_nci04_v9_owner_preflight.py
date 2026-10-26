"""Bounded read-only V9 preflight unit tests; no owner state mutation."""
import unittest
from unittest.mock import patch

from f139.nci04_v9_owner_preflight import (
    SHA, V9TransitionDenied, verify_v9_owner_preflight,
)


class V9PreflightTests(unittest.TestCase):
    def test_sha_is_exact(self):
        self.assertIsNotNone(SHA.fullmatch("a" * 40))
        self.assertIsNone(SHA.fullmatch("a" * 40 + "x"))
        self.assertIsNone(SHA.fullmatch("a" * 39))
        self.assertIsNone(SHA.fullmatch("z" * 40))

    def test_rejects_noncanonical_database_before_reading(self):
        with self.assertRaisesRegex(V9TransitionDenied, "ORIGINAL_DATABASE"):
            verify_v9_owner_preflight(
                object(), lambda _: {},
                expected_old_source="a" * 40,
                target_source="b" * 40,
            )


if __name__ == "__main__":
    unittest.main()
