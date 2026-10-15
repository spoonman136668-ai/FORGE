"""Synthetic failure and benign source fixtures only; no real GitHub requests."""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import r20b_readonly_prereg_audit as r20b

class R20B(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = r20b.decode(r20b.MANIFEST.read_bytes())
        cls.pins = r20b.decode(r20b.PINS.read_bytes())

    def fixture(self):
        manifest, pins = copy.deepcopy(self.manifest), copy.deepcopy(self.pins)
        responses = {}
        for row, p in zip(manifest["entries"], pins["entries"]):
            lane, head = row["lane"], row["head_sha"]
            responses[(lane, "actions/runs/" + str(row["run_id"]))] = {
                "id": row["run_id"], "run_attempt": 1, "head_sha": head,
                "event": "push", "status": "completed", "conclusion": "success",
                "path": row["workflow_path"],
                "repository": {"full_name": row["repository"]},
                "created_at": "2026-10-13T13:20:00Z",
            }
            responses[(lane, "commits/" + head)] = {
                "sha": head, "commit": {"committer": {"date": "2026-10-13T13:19:59Z"}},
            }
            responses[(lane, "contents/" + p["prereg_path"] + "?ref=" + head)] = {
                "type": "file", "path": p["prereg_path"], "sha": p["prereg_git_blob_sha"],
            }
        return manifest, pins, responses

    def verify(self, m, p, response):
        return r20b.audit(m, p, lambda lane, suffix: response[(lane, suffix)])

    def test_positive_technical_source_only(self):
        m, p, responses = self.fixture()
        report = self.verify(m, p, responses)
        self.assertEqual(report["github_prereg_blob_observations"], 6)
        for key in ("independent_source_birth_verified", "complete_first_use_reconciled",
                    "external_signer_custody_verified", "scientific_accepted",
                    "optimizer_promotion_authorized"):
            self.assertIs(report[key], False)
        self.assertEqual(report["new_originals_executed"], 0)

    def test_wrong_prereg_source_identity_denied(self):
        m,p,r=self.fixture()
        p["entries"][0]["prereg_git_blob_sha"] = "a" * 40
        with self.assertRaises(r20b.Blocked):
            self.verify(m,p,r)

    def test_false_custody_claim_denied(self):
        m,p,r=self.fixture()
        p["entries"][0]["complete_first_use_reconciled"] = True
        with self.assertRaises(r20b.Blocked):
            self.verify(m,p,r)

    def test_missing_original_denied(self):
        m,p,r=self.fixture()
        p["entries"].pop()
        with self.assertRaises(r20b.Blocked):
            self.verify(m,p,r)

    def test_cross_lane_denied(self):
        m,p,r=self.fixture()
        p["entries"][1]["lane"]="Yggdrasil"
        with self.assertRaises(r20b.Blocked):
            self.verify(m,p,r)

    def test_duplicate_json_keys_denied(self):
        with self.assertRaises(r20b.Blocked):
            r20b.decode(b'{"sha":"a","sha":"b"}')

    def test_run_metadata_drift_denied(self):
        for key, value in [("run_attempt",2), ("event","workflow_dispatch"),
                           ("head_sha","a"*40), ("conclusion","failure"),
                           ("status","in_progress"), ("path","fake.yml")]:
            with self.subTest(key=key):
                m,p,r=self.fixture()
                row=m["entries"][0]
                r[(row["lane"], "actions/runs/"+str(row["run_id"]))][key]=value
                with self.assertRaises(r20b.Blocked):
                    self.verify(m,p,r)

    def test_repository_mismatch_denied(self):
        m,p,r=self.fixture()
        row=m["entries"][0]
        r[(row["lane"], "actions/runs/"+str(row["run_id"]))]["repository"]["full_name"]="attacker/Wingless"
        with self.assertRaises(r20b.Blocked):
            self.verify(m,p,r)

    def test_live_git_blob_mismatch_denied(self):
        m,p,r=self.fixture()
        row,pin=m["entries"][0],p["entries"][0]
        r[(row["lane"],"contents/"+pin["prereg_path"]+"?ref="+row["head_sha"])]["sha"]="b"*40
        with self.assertRaises(r20b.Blocked):
            self.verify(m,p,r)

    def test_commit_postdates_run_denied(self):
        m,p,r=self.fixture()
        row=m["entries"][0]
        r[(row["lane"],"commits/"+row["head_sha"])]["commit"]["committer"]["date"]="2026-10-13T13:20:01Z"
        with self.assertRaises(r20b.Blocked):
            self.verify(m,p,r)

    def test_tampered_manifest_denied(self):
        m,p,r=self.fixture()
        m["entries"][0]["head_sha"]="b"*40
        with self.assertRaises(r20b.Blocked):
            self.verify(m,p,r)

if __name__=="__main__":
    unittest.main()
