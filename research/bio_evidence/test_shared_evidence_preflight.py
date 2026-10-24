import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from shared_evidence_preflight import lookup

def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        git(self.root,"init","-q")
        git(self.root,"config","user.email","test@example.invalid")
        git(self.root,"config","user.name","Evidence Test")
        self.source="archive/research/bio/2026-10-23/original_reports/BIO01_report.md"
        self.write(self.source,"Memory rehearsal and conventional replay\n")
        digest=hashlib.sha256((self.root/self.source).read_bytes()).hexdigest()
        self.catalog={"schema":"mind-palace.research-evidence-catalog.v1",
                      "authority":"ADVISORY_HISTORICAL_ONLY",
                      "research_archives":[{"program":"BIO",
                          "index":"archive/research/bio/2026-10-23/findings.json",
                          "scientific_acceptance":"NOT_AUTHENTICATED_OR_ESTABLISHED",
                          "scientific_finding_count":2}]}
        def finding(i,claim,verdict):
            return {"finding_id":f"BIOF-{i:03}","experiment_id":"BIO-01",
                    "claim":claim,"control_comparison":"Standard conventional rehearsal",
                    "limitations":"Synthetic memory transfer only","gate_verdict":verdict,
                    "source_repo_path":self.source,"source_sha256":digest,
                    "evidence_status":"HISTORICAL_PROVISIONAL_ONLY",
                    "wingless_yggdrasil_integration":"NOT_AUTHORIZED"}
        self.index={"schema":"bio.findings.repo.historical.v1",
                    "status":"ADVISORY_HISTORICAL_NOT_ACCEPTED","record_count":2,
                    "findings":[finding(1,"memory replay retained data","BOUNDED_PASS"),
                                finding(2,"replay failed conventional controls","SCIENTIFIC_FAIL")]}
        self.commit()
    def tearDown(self):
        self.tmp.cleanup()
    def write(self,path,value):
        p=self.root/path
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(value)
    def commit(self):
        self.write("docs/RESEARCH_EVIDENCE_CATALOG.json",json.dumps(self.catalog))
        self.write("archive/research/bio/2026-10-23/findings.json",json.dumps(self.index))
        git(self.root,"add",".")
        git(self.root,"commit","-qm","synthetic source")
        self.sha=git(self.root,"rev-parse","HEAD")

    def test_positive_and_negative_are_advisory(self):
        out=lookup(self.root,self.sha,"memory replay")
        self.assertEqual(2,len(out["retrieved"]))
        self.assertEqual({"BOUNDED_PASS","SCIENTIFIC_FAIL"},
                         {v["verdict"] for v in out["retrieved"]})
        self.assertFalse(out["scientific_acceptance"])
        self.assertFalse(out["model_integration_authorized"])

    def test_commit_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_PIN_DRIFT"):
            lookup(self.root,"a"*40,"memory replay")

    def test_dirty_tracked_source_rejected(self):
        self.write(self.source,"Tampered")
        with self.assertRaisesRegex(ValueError,"DIRTY_SOURCE"):
            lookup(self.root,self.sha,"memory")

    def test_source_hash_mismatch_rejected(self):
        self.index["findings"][1]["source_sha256"]="0"*64
        self.commit()
        with self.assertRaisesRegex(ValueError,"SOURCE_HASH_DRIFT"):
            lookup(self.root,self.sha,"memory replay")

    def test_unsupported_source_not_silently_accepted(self):
        self.index["findings"][0]["source_repo_path"]="archive/research/bio/2026-10-23/resumed_evidence_packages/test.zip"
        self.commit()
        with self.assertRaisesRegex(ValueError,"SOURCE_NOT_DIRECTLY_VERIFIABLE"):
            lookup(self.root,self.sha,"memory replay")

    def test_forged_integration_rejected(self):
        self.index["findings"][0]["wingless_yggdrasil_integration"]="AUTHORIZED"
        self.commit()
        with self.assertRaisesRegex(ValueError,"ACCEPTANCE_DRIFT"):
            lookup(self.root,self.sha,"memory")

    def test_unknown_topic_returns_no_match(self):
        self.assertEqual([],lookup(self.root,self.sha,"electromagnetism")["retrieved"])

if __name__ == "__main__":
    unittest.main()
