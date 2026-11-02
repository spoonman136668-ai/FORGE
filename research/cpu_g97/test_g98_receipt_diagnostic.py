"""G98 test-only receipt diagnostic negative controls."""
import copy, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from g98_receipt_diagnostic import diagnose, STRATA

def fixture():
    def rows():
        return [{"index":i,"prefix_id":i%4,"source_row":i,
                 "request_wall_ns":100,"clone_ns":0,
                 "hit":i>3,"admitted":i<4,"bypass":False} for i in range(48)]
    return {"schema":"forge.cpu-g97.development.v1","phase":"DEVELOPMENT_ONLY",
            "heldout_executed":False,"promotion_allowed":False,
            "engineering":"PASS","correctness":"PASS","decision":"DEVELOPMENT_NO_GO",
            "strata":{s:{"exact_parity":True,"repetitions":[{"rep":j+1,"arms":{
                "g97_overflow_bypass":{"rows":rows()},
                "no_cache":{"rows":rows()}}} for j in range(4)]} for s in STRATA}}

class G98Tests(unittest.TestCase):
    def test_counts_and_observation_boundary(self):
        result=diagnose(fixture())
        self.assertEqual(result["strata"]["overflow"]["repetitions"][0]["counts"],
                         {"hit":44,"admission":4,"bypass":0})
        self.assertIn("kv_construction_ns",result["unobserved"])
        self.assertFalse(result["promotion_allowed"])
    def test_rejects_protected_or_incomplete(self):
        for field,value in [("heldout_executed",True),("promotion_allowed",True),
                            ("correctness","UNVERIFIED"),("phase","HELDOUT")]:
            r=fixture();r[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):diagnose(r)
    def test_pair_drift_rejected(self):
        r=fixture();r["strata"]["mixed"]["repetitions"][2]["arms"]["no_cache"]["rows"][7]["source_row"]=999
        with self.assertRaisesRegex(ValueError,"PAIR_IDENTITY"):diagnose(r)
    def test_bad_cache_event_rejected(self):
        r=fixture();r["strata"]["bursty"]["repetitions"][0]["arms"]["g97_overflow_bypass"]["rows"][4]["admitted"]=True
        with self.assertRaisesRegex(ValueError,"INCONSISTENT"):diagnose(r)

if __name__=="__main__":unittest.main()
