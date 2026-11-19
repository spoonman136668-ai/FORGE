"""Pure offline safeguards for the Wingless branch-bound native proposal supplier."""
from __future__ import annotations

import hashlib
import unittest

from f139.nci04_wingless_source_producer import (
    LANE, PARENT, PATH, ANCHOR, WinglessSourceDenied,
    REPLACEMENT, mechanism_id, propose,
)

SOURCE = b'''package cognition

import (
 "math"
)
type FastSlowState struct { }
func (d *FastSlowState) ChooseDisagreementProbe(prior int) (int,bool,error) {
 disagreement0 := math.Abs(fast0 - slow0)
 disagreement1 := math.Abs(fast1 - slow1)
 if disagreement0 == disagreement1 { return 0, false, nil }
 if disagreement0 > disagreement1 { return 0, true, nil }
 return 1, true, nil
}
'''
HISTORY = "a" * 64


def blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def build(source=SOURCE, **overrides):
    args = {
        "lane": LANE, "parent_commit": PARENT, "path": PATH,
        "before_bytes": source, "verified_git_blob_sha": blob(source),
        "pinned_before_sha256": hashlib.sha256(source).hexdigest(),
        "owner_history_sha256": HISTORY,
        "consumed_mechanisms": set(),
        "consumed_source_sha256": set(),
    }
    args.update(overrides)
    return propose(**args)


class WinglessSourceSupplierTests(unittest.TestCase):
    def test_deterministic_real_source_transformation(self):
        a = build()
        b = build()
        self.assertEqual(a, b)
        self.assertEqual(a["source"], SOURCE.replace(
            ANCHOR.encode(), REPLACEMENT.encode(), 1))
        self.assertNotEqual(a["source"], SOURCE)
        self.assertEqual(a["record"]["parent_commit"], PARENT)
        self.assertEqual(a["record"]["path"], PATH)
        self.assertEqual(a["record"]["history_sha256"], HISTORY)
        self.assertEqual(a["record"]["after_sha256"],
                         hashlib.sha256(a["source"]).hexdigest())

    def test_one_precisely_bounded_intervention(self):
        self.assertEqual(build()["source"].count(
            b"if math.Max(disagreement0, disagreement1) < 0.10"), 1)
        self.assertEqual(build()["source"].count(b"ChooseDisagreementProbe"), 1)

    def test_no_execution_or_scientific_authority(self):
        r = build()["record"]
        for key in ("cross_platform_qualified", "original_owner_admitted",
                    "scientific_first_use", "dispatch_authorized",
                    "policy_promotion_authorized",
                    "independent_scientific_acceptance",
                    "new_controller", "new_scheduler"):
            self.assertIs(r[key], False)
        self.assertEqual(r["paid_model_calls"], 0)

    def test_candidate_identity_has_immutable_hashes(self):
        r = build()
        self.assertRegex(r["candidate_identity"], r"^[a-f0-9]{64}$")
        self.assertRegex(r["record_sha256"], r"^[a-f0-9]{64}$")
        self.assertTrue(r["pr_title"].startswith("F139 autonomy DEV:"))

    def test_consumed_mechanism_denied(self):
        with self.assertRaisesRegex(WinglessSourceDenied, "MECHANISM_ALREADY_CONSUMED"):
            build(consumed_mechanisms={mechanism_id()})

    def test_consumed_candidate_denied(self):
        after = build()["record"]["after_sha256"]
        with self.assertRaisesRegex(WinglessSourceDenied, "CANDIDATE_ALREADY_CONSUMED"):
            build(consumed_source_sha256={after})

    def test_lane_and_parent_cannot_change(self):
        for kwargs in ({"lane": "Yggdrasil"}, {"lane": "TTT-Hybrid"},
                       {"parent_commit": "1" * 40}, {"path": "model.py"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(WinglessSourceDenied, "TARGET_LINEAGE"):
                    build(**kwargs)

    def test_blob_or_source_digest_drift_denied(self):
        for kwargs in ({"verified_git_blob_sha": "1" * 40},
                       {"pinned_before_sha256": "f" * 64}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(WinglessSourceDenied, "SOURCE_OR_AUTHORITY"):
                    build(**kwargs)

    def test_history_missing_or_bad_denied(self):
        for value in ("", "x" * 64, "1" * 63):
            with self.subTest(value=value):
                with self.assertRaisesRegex(WinglessSourceDenied, "SOURCE_OR_AUTHORITY"):
                    build(owner_history_sha256=value)

    def test_frozen_source_anchor_must_be_unique(self):
        for source in (
            SOURCE.replace(ANCHOR.encode(), b" if true { return 0,false,nil }\n"),
            SOURCE + ANCHOR.encode(),
            SOURCE.replace(b"math.Abs(fast1 - slow1)", b"fast1"),
        ):
            with self.subTest(source=source[-70:]):
                with self.assertRaisesRegex(WinglessSourceDenied, "SOURCE_BOUNDARY"):
                    build(source)

    def test_no_future_science_or_invalid_consumed_set(self):
        with self.assertRaisesRegex(WinglessSourceDenied, "SOURCE_OR_AUTHORITY"):
            build(scientific_first_use=True)
        with self.assertRaisesRegex(WinglessSourceDenied, "SOURCE_OR_AUTHORITY"):
            build(consumed_source_sha256={"bogus"})

    def test_caller_cannot_inject_recipe(self):
        with self.assertRaises(TypeError):
            build(replacement="import os")
        with self.assertRaisesRegex(WinglessSourceDenied, "SOURCE_OR_AUTHORITY"):
            build(before_bytes=SOURCE.decode())


if __name__ == "__main__":
    unittest.main()
