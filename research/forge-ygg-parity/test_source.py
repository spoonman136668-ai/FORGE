"""Bounded source and negative acceptance: no live science, no first-use."""
import hashlib,importlib.util,json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED="031fa0e6ed051a439b1c31d334f30ca8c4af5dec"
def import_module(name):
    spec=importlib.util.spec_from_file_location("parity_"+name,ROOT/(name+".py"))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Integrity(unittest.TestCase):
    def test_frozen_ids_cohorts_reviewer_negative(self):
        raw=subprocess.check_output(["git","show","HEAD:research/forge-ygg-parity/prereg.json"])
        digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        self.assertEqual(digest,EXPECTED)
        m=json.loads(raw)
        self.assertEqual(len(m["studies"]),3)
        ids=[x["experiment_id"] for x in m["studies"]]
        self.assertEqual(ids,["Y-FORGE-REAL-INTERRUPT-01","Y-FORGE-PARITY-A1-ONSET1","Y-FORGE-PARITY-A2-ONSET1"])
        used=set(range(8224,8272))
        for study in m["studies"]:
            seeds=study["dev_seeds"]+study["sealed_seeds"]
            self.assertEqual((len(study["dev_seeds"]),len(study["sealed_seeds"])),(8,16))
            self.assertEqual(len(seeds),len(set(seeds)))
            self.assertFalse(used.intersection(seeds))
            used.update(seeds)
        self.assertEqual(m["limit"]["external_model_calls"],0)
        self.assertEqual(m["limit"]["max_originals"],3)
        self.assertEqual(m["first_use"]["retry_attempt_one_only"],True)
        review=import_module("independent_review")
        for p in (b"{}",b"null",b'{"duplicate":1,"duplicate":2}'):
            with self.assertRaises((ValueError,TypeError,KeyError,AttributeError)):
                review.verify(raw,p,ids[1])
        worker=import_module("run_original")
        self.assertEqual(worker.MANIFEST,EXPECTED)
        self.assertEqual(worker.IDS,tuple(ids))
    def test_quarantine_rejects_missing_replay_receipt(self):
        import tempfile
        runner=import_module("interrupt_real_worker")
        with tempfile.TemporaryDirectory() as t:
            from pathlib import Path
            with self.assertRaises(FileNotFoundError):
                runner.quarantine(Path(t),Path(t)/"quarantine.json")
if __name__=="__main__":unittest.main()
