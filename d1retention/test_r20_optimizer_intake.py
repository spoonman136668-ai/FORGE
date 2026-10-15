"""Synthetic negative tests. Real readback runs only on authenticated CI."""
import pathlib,json,tempfile,hashlib,unittest
from unittest.mock import Mock
import r20_optimizer_intake as r20
COHORT=pathlib.Path(__file__).resolve().parents[1]/"reference/research-originals/20261013-six-recent-archive-cohort.json"
class R20Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name)
        self.manifest=json.loads(COHORT.read_bytes())
        for i,e in enumerate(self.manifest["entries"]):
            raw=(f"fixture-{i}".encode())*3
            (self.root/(str(e["run_id"])+".zip")).write_bytes(raw)
            e["archive_sha256"]=hashlib.sha256(raw).hexdigest()
        self.refresh()
    def refresh(self):
        self.raw=json.dumps(self.manifest,separators=(",",":")).encode()+b"\n"
        self.obs={
            "schema":"forge.research-archive.original-byte-inventory.v1",
            "mode":"ORIGINAL_ARCHIVE_BYTE_PRESERVATION_NOT_SCIENTIFIC_CUSTODY",
            "manifest_sha256":hashlib.sha256(self.raw).hexdigest(),
            "archive_count":6,"wingless_count":3,"yggdrasil_count":3,
            "original_execution_authorized":False,"complete_ckb_custody":False,
            "scientific_accepted":False,"accepted_ref_mutation":False,
            "observations":[{
                "lane":e["lane"],"experiment":e["experiment"],
                "original_run_id":e["run_id"],"original_head_sha":e["head_sha"],
                "artifact_id":e["artifact_id"],"archive_sha256":e["archive_sha256"],
                "archival_integrity_verified":True,
                "scientific_classification":"UNQUALIFIED_ORIGINAL_EVIDENCE_PRESERVED",
                "preregistration_verified":False,"first_use_reconciled":False,
                "scientific_accepted":False
            } for e in self.manifest["entries"]]
        }
    def assess(self,callback=None):
        if callback is None:callback=lambda e,m,b:len(b)
        return r20.qualify(self.raw,json.dumps(self.obs).encode(),self.root,callback)
    def test_source_only_non_authorizing(self):
        r=self.assess()
        self.assertEqual((r["github_d1_originals_joined"],r["wingless_originals"],r["yggdrasil_originals"]),(6,3,3))
        for x in ("scientific_accepted","five_optimizer_shadow_admitted",
                  "optimizer_dispatch_authorized","complete_first_use_reconciled"):
            self.assertIs(r[x],False)
        self.assertEqual(r["new_experiments"],0)
    def test_wrong_d1_size(self):
        with self.assertRaises(r20.R20Blocked):
            self.assess(lambda e,m,b:len(b)+1)
    def test_fake_bool_remote_size(self):
        with self.assertRaises(r20.R20Blocked):
            self.assess(lambda e,m,b:True)
    def test_source_corrupted_no_remote_call(self):
        e=self.manifest["entries"][0]
        (self.root/(str(e["run_id"])+".zip")).write_bytes(b"tamper")
        callback=Mock(return_value=42)
        with self.assertRaises(r20.R20Blocked):self.assess(callback)
        callback.assert_not_called()
    def test_source_missing(self):
        e=self.manifest["entries"][0]
        (self.root/(str(e["run_id"])+".zip")).unlink()
        with self.assertRaises(r20.R20Blocked):self.assess()
    def test_duplicate_artifact(self):
        self.manifest["entries"][3]["artifact_id"]=self.manifest["entries"][0]["artifact_id"]
        self.refresh()
        with self.assertRaises(r20.R20Blocked):self.assess()
    def test_first_use_forgery(self):
        self.obs["observations"][0]["first_use_reconciled"]=True
        with self.assertRaises(ValueError):self.assess()
    def test_cross_lane_swap(self):
        self.obs["observations"][3]["archive_sha256"]=self.obs["observations"][0]["archive_sha256"]
        with self.assertRaises(ValueError):self.assess()
    def test_missing_readback_callback(self):
        with self.assertRaises(r20.R20Blocked):self.assess(False)
    def test_worker_interruption_no_report(self):
        def interrupted(e,m,b):raise RuntimeError("worker interrupted")
        with self.assertRaises(RuntimeError):self.assess(interrupted)
