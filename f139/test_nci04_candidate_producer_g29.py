"""G29 inert source-only tests: prospective action probing, no worker."""
from __future__ import annotations

import hashlib
import unittest

from f139.nci04_candidate_producer_g29 import (
    G29Denied, MECHANISM, PARENT, PATH, mechanism_identity, produce_g29,
)
from f139.test_nci04_candidate_producer import SOURCE

# Existing frozen fixture has no _address; add its immutable address mapping
# only for isolated tests, not as a change to Yggdrasil production source.
BEFORE = SOURCE.replace(
    b"    def choose(self, address:",
    b"""    @classmethod
    def _address(cls, address: int, retained: bool) -> int:
        if type(retained) is not bool or type(address) is not int:
            raise ValueError("INVALID_ADDRESS")
        limit = cls.RETAINED_SLOTS if retained else cls.ACTIVE_SLOTS
        if not 0 <= address < limit:
            raise ValueError("INVALID_ADDRESS")
        return address + (cls.ACTIVE_SLOTS if retained else 0)

    def choose(self, address:""",
)
HISTORY = "e" * 64


def build(source=BEFORE, **kwargs):
    params = dict(lane="Yggdrasil", path=PATH, parent_commit=PARENT,
                  original=source,
                  original_sha256=hashlib.sha256(source).hexdigest(),
                  history_sha256=HISTORY, consumed_mechanisms=set(),
                  consumed_candidates=set(), scientific_first_use=False)
    params.update(kwargs)
    return produce_g29(**params)


def cell():
    namespace = {}
    exec(compile(build()["source"], "<G29-inert-fixture>", "exec"), namespace)
    return namespace["PublicCausalCells"]()


class G29SourceOnlyTests(unittest.TestCase):
    def test_determinism_and_authority_denial(self):
        a, b = build(), build()
        self.assertEqual(a, b)
        self.assertNotEqual(a["source"], BEFORE)
        self.assertEqual(a["record"]["mechanism"], MECHANISM)
        self.assertEqual(a["record"]["mechanism_sha256"], mechanism_identity())
        self.assertEqual(a["record"]["source_after_sha256"],
                         hashlib.sha256(a["source"]).hexdigest())
        for key in ("scientific_first_use", "dispatch_authorized",
                    "publish_authorized", "v1_worker_authorized",
                    "new_controller", "new_scheduler"):
            self.assertFalse(a["record"][key])

    def test_empty_tie_no_mutations(self):
        c = cell()
        original = repr(c._counts)
        self.assertEqual(c.probe_uncertain(0), 0)
        self.assertEqual(original, repr(c._counts))
        self.assertIsNone(c.choose(0))

    def test_equal_arm_counts_different_outcomes(self):
        c = cell()
        c._counts[0][0] = [0, 8]
        c._counts[0][1] = [4, 4]
        self.assertEqual(c.probe_uncertain(0), 1)
        c._counts[0][0], c._counts[0][1] = c._counts[0][1], c._counts[0][0]
        self.assertEqual(c.probe_uncertain(0), 0)

    def test_exploration_separate_from_empirical_choice(self):
        c = cell()
        c._counts[0][0] = [0, 9]
        c._counts[0][1] = [1, 0]
        self.assertEqual(c.choose(0), 0)
        self.assertEqual(c.probe_uncertain(0), 1)
        self.assertEqual(c.choose(0), 0)

    def test_context_and_retained_isolation(self):
        c = cell()
        c._counts[1][0] = [0, 100]
        c._counts[1][1] = [10, 10]
        c._counts[7][0] = [0, 100]
        c._counts[7][1] = [10, 10]
        self.assertEqual(c.probe_uncertain(0), 0)
        self.assertEqual(c.probe_uncertain(0, retained=True), 1)
        self.assertEqual(c.probe_uncertain(1), 1)

    def test_invalid_address_and_flag(self):
        c = cell()
        for a, r in ((-1, False), (7, False), (9, True),
                     (True, False), (0, 0)):
            with self.subTest(address=a, retained=r):
                with self.assertRaises(ValueError):
                    c.probe_uncertain(a, retained=r)

    def test_count_only_ablation_detects_difference(self):
        c = cell()
        c._counts[0][0] = [0, 8]
        c._counts[0][1] = [4, 4]
        count_only = 0  # Both arms have 8 observations, fixed tie.
        self.assertNotEqual(c.probe_uncertain(0), count_only)

    def test_reject_consumed_mechanism_and_candidate(self):
        a = build()
        with self.assertRaisesRegex(G29Denied, "MECHANISM_ALREADY_CONSUMED"):
            build(consumed_mechanisms={mechanism_identity()})
        with self.assertRaisesRegex(G29Denied, "CANDIDATE_ALREADY_CONSUMED"):
            build(consumed_candidates={a["candidate_identity"]})

    def test_fail_closed_on_drift(self):
        for key, bad in (
            ("parent_commit", "9" * 40), ("original_sha256", "0" * 64),
            ("history_sha256", "not-a-digest"), ("lane", "Wingless"),
            ("scientific_first_use", True), ("consumed_mechanisms", {"junk"}),
        ):
            with self.subTest(key=key):
                with self.assertRaisesRegex(G29Denied, "INPUT_OR_HISTORICAL"):
                    build(**{key: bad})

    def test_missing_repeated_or_already_modified_source(self):
        anchor = b"        return 0 if lhs > rhs else 1\n"
        with self.assertRaisesRegex(G29Denied, "SOURCE_BOUNDARY_DRIFT"):
            build(BEFORE.replace(anchor, b"        return 1 if lhs < rhs else 0\n"))
        with self.assertRaisesRegex(G29Denied, "SOURCE_BOUNDARY_DRIFT"):
            build(BEFORE + BEFORE)
        with self.assertRaisesRegex(G29Denied, "SOURCE_BOUNDARY_DRIFT"):
            build(build()["source"])


if __name__ == "__main__":
    unittest.main()
