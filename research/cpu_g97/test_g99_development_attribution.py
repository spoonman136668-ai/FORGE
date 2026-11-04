"""G99 offline receipt tests: no model weights, network or protected cohort."""
import hashlib
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from g99_development_attribution import report,STRATA,PHASES

class G99Tests(unittest.TestCase):
    def setUp(self):
        self.stream=b'{"frozen":"development"}\n'
        self.sha=hashlib.sha256(self.stream).hexdigest()
        self.source='a'*40
        self.r={"schema":"forge.cpu-g97.development.v1","phase":"DEVELOPMENT_ONLY",
                "source_sha":self.source,"model_revision":"pinned","weights_sha256":"b"*64,
                "development_stream_sha256":self.sha,"heldout_executed":False,
                "promotion_allowed":False,"decision":"DEVELOPMENT_NO_GO","strata":{}}
        self.t={"schema":"forge.cpu-g98.original-development-timing.v1","phase":"DEVELOPMENT_ONLY",
                "source_sha":self.source,"model_revision":"pinned","weights_sha256":"b"*64,
                "development_stream_sha256":self.sha,"heldout_executed":False,
                "promotion_allowed":False,"diagnostic_only":True,"strata":{}}
        for name in STRATA:
            reps=[]
            for rep in range(1,5):
                base=[];candidate=[]
                for i in range(48):
                    row={"index":i,"prefix_id":i%4,"source_row":i,"output_sha256":str(i),
                         "request_wall_ns":100,"clone_ns":0,"hit":False,"admitted":False,"bypass":True}
                    c={**row,"request_wall_ns":80}
                    if i==0:
                        c.update(request_wall_ns=200,admitted=True,bypass=False,clone_ns=5)
                    base.append(row);candidate.append(c)
                reps.append({"rep":rep,"arms":{"no_cache":{"rows":base},"g97_overflow_bypass":{"rows":candidate}}})
            self.r["strata"][name]={"exact_parity":True,"repetitions":reps}
            self.t["strata"][name]={"parity":"PASS","timing_accepted":True,
                 "source_sha":self.source,"development_stream_sha256":self.sha,
                 "timing":{"durations_ns":{p:[1] for p in PHASES}}}
    def run_report(self):
        return report(self.r,self.t,self.stream,artifact_sha256='c'*64)
    def test_classifies_worst_as_admission_and_preserves_provenance(self):
        out=self.run_report()
        self.assertEqual(out["strata"]["overflow"]["worst_pair"]["decision"],"admitted_miss")
        self.assertEqual(out["strata"]["mixed"]["paired_requests"],192)
        self.assertEqual(out["strata"]["bursty"]["failing_floor_count"],4)
        self.assertFalse(out["promotion_allowed"])
    def test_rejects_mismatched_pair(self):
        self.r["strata"]["mixed"]["repetitions"][0]["arms"]["g97_overflow_bypass"]["rows"][0]["source_row"]=999
        with self.assertRaisesRegex(ValueError,"PAIRED_IDENTITY_DRIFT"):self.run_report()
    def test_rejects_heldout(self):
        self.r["heldout_executed"]=True
        with self.assertRaisesRegex(ValueError,"PROTECTED_OR_PROMOTED"):self.run_report()
    def test_rejects_stream_hash_drift(self):
        with self.assertRaisesRegex(ValueError,"STREAM_DIGEST_DRIFT"):
            report(self.r,self.t,b'changed',artifact_sha256='c'*64)
    def test_rejects_missing_parity(self):
        self.t["strata"]["overflow"]["parity"]="UNVERIFIED"
        with self.assertRaisesRegex(ValueError,"PARITY_OR_TIMING_MISSING"):self.run_report()
if __name__=="__main__":unittest.main()
