"""Negative guards for pinned two-lane research evidence continuity."""
import hashlib
import json
import pathlib
import tempfile
import unittest
from unittest import mock
import gate as g

class GateTests(unittest.TestCase):
    def test_claims_exact_and_no_replay(self):
        for key,identity in g.CLAIMS.items():
            digest,experiment,prereg,worker,reviewer=identity
            source=g.W_SHA if key.startswith("w") else g.Y_SHA
            kw=("execute_blob","review_blob") if key.startswith("w") else ("worker_blob","reviewer_blob")
            x={"schema":"forge.r32-r33.first-use-consumed.v1" if key.startswith("w") else "forge.yggdrasil.e-first-use-consumed.v1",
               "experiment_id":experiment,"source_commit":source,"prereg_blob":prereg,
               kw[0]:worker,kw[1]:reviewer,"first_use_consumed":True,"rerun_allowed":False,
               "budget_limit" if key.startswith("w") else "budget_claims":2,
               "owner_approval_comment_id" if key.startswith("w") else "operator_approval_comment_id":1}
            # Exact content-addressed identity is mandatory; altered evidence cannot inherit a claim.
            with self.assertRaisesRegex(ValueError,"FIRST_USE_CLAIM_BLOB_DRIFT"):
                g.claim_ok((json.dumps(x)+"\n").encode(),key,source,
                           "wingless" if key.startswith("w") else "yggdrasil")
            self.assertEqual(len(digest),40)

    def test_duplicate_fields_and_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_FIELD"):
            g.load_json(b'{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError,"NONFINITE_JSON_NUMBER"):
            g.load_json(b'{"a":NaN}')

    def test_original_byte_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            (root/"original").mkdir();(root/"review").mkdir()
            payload=b'{"original":true}\n'
            (root/"original"/"original.json").write_bytes(payload)
            (root/"original"/"original.sha256").write_text(
                hashlib.sha256(payload).hexdigest()+"  original.json\n")
            (root/"review"/"independent-review.json").write_text('{"independently_validated":true}\n')
            original,_=g.original_and_review(root,"original","review")
            self.assertEqual(original,payload)
            (root/"original"/"original.json").write_bytes(payload+b'junk')
            with self.assertRaisesRegex(ValueError,"ORIGINAL_SHA256_MISMATCH"):
                g.original_and_review(root,"original","review")

    def test_one_lane_failure_never_erases_healthy_peer(self):
        def classify(root,source,lane):
            if lane=="wingless":raise ValueError("corrupt source-bound scientific review")
            return {"status":"QUALIFIED_HISTORICAL_TWO_ORIGINAL_CYCLE",
                    "originals":[{"outcome":"PARTIAL_EARLY_GAIN"}],
                    "originals_replayed":0,"new_originals_executed":0,
                    "next_science_dispatch_authorized":False}
        with mock.patch.object(g,"check_lane",side_effect=classify):
            report=g.audit("ignored","wingless","yggdrasil")
        self.assertEqual(report["lanes"]["wingless"]["status"],"QUARANTINED_NO_REPLAY")
        self.assertEqual(report["lanes"]["yggdrasil"]["status"],"QUALIFIED_HISTORICAL_TWO_ORIGINAL_CYCLE")
        self.assertFalse(report["both_real_lanes_verified"])
        self.assertEqual(report["new_originals_executed"],0)
        self.assertFalse(report["new_science_dispatch_authorized"])

    def test_both_healthy_does_not_grant_execution(self):
        expected={"status":"QUALIFIED_HISTORICAL_TWO_ORIGINAL_CYCLE",
                  "originals":[],"originals_replayed":0,
                  "new_originals_executed":0,"next_science_dispatch_authorized":False}
        with mock.patch.object(g,"check_lane",return_value=expected):
            report=g.audit("none","w","y")
        self.assertTrue(report["both_real_lanes_verified"])
        self.assertFalse(report["new_science_dispatch_authorized"])
        self.assertEqual(set(report["lanes"]),{"wingless","yggdrasil"})

if __name__=="__main__":
    unittest.main()
