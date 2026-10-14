"""F13 synthetic negative contracts; never presented as science."""
import copy,unittest
from train import grouped,features,distance,infer,training_crossfamily,execute
from verify import cases,decision,verify

def samples():
    rows=[]
    for fi in range(4):
        for seed in (67204,67205):
            for pair in ([8,10],[11,13]):
                for regime in ("steady","onset1"):
                    for matching in ("p1","p2","p3"):
                        base=(fi*3+seed+pair[0])%16
                        public=[[base,(base+1)%16],
                                [(base+1)%16,(base+2)%16],
                                [0,0],[0,0],[0,0]]
                        for action in range(6):
                            rows.append({"seed":seed,"pair":list(pair),
                                "regime":regime,"family":[fi],
                                "matching_policy":matching,"arm":action,
                                "pre_mismatch":0 if action==base%6 else 1+action%3,
                                "post_mismatch":0,"public_reads":10,
                                "sample_trace":{"addresses":[[0,1],[0,1],
                                    [2,3],[4,5],[6,7]],
                                    "public_values":copy.deepcopy(public),
                                    "decision":{"action_index":action}}})
    return rows

class RawPublicValueTests(unittest.TestCase):
    def test_exact_train_only_four_source_folds(self):
        rows=samples()
        self.assertEqual(len(rows),576)
        data=grouped(rows,(67204,67205))
        self.assertEqual(len(data),96)
        independent=cases(rows,(67204,67205))
        for k in (4,12,24,72):
            for key,record in list(data.items())[:8]:
                p=features(record)
                self.assertEqual(infer(p,data,k),
                                 decision(p,independent,k))
        self.assertEqual(len(training_crossfamily(data)),4)
        self.assertTrue(all(sum(a["action_counts"])==96
                            for a in training_crossfamily(data)))

    def test_raw_public_sensor_values_change_prediction(self):
        data=grouped(samples(),(67204,67205))
        first=(3,4,4,5)
        second=(12,13,13,14)
        self.assertNotEqual(distance(first,second),0)
        self.assertGreater(distance(first,second),0)
        self.assertEqual(infer(first,data,4),decision(first,cases(samples(),(67204,67205)),4))

    def test_missing_counterfactual_and_first_use_fail_closed(self):
        rows=samples()
        wrong=copy.deepcopy(rows);wrong[0]["seed"]=67600
        with self.assertRaisesRegex(ValueError,"HISTORICAL_SCOPE"):
            grouped(wrong,(67204,67205))
        wrong=copy.deepcopy(rows)
        wrong[0]["sample_trace"]["public_values"][0][0]=99
        with self.assertRaisesRegex(ValueError,"PUBLIC_FOUR_ANCHOR_SCALARS"):
            grouped(wrong,(67204,67205))
        wrong=copy.deepcopy(rows);wrong.pop()
        with self.assertRaisesRegex(ValueError,"FULL_SOURCE_COUNTERFACTUALS"):
            grouped(wrong,(67204,67205))

    def test_unverified_sources_cannot_mint_scientific_clearance(self):
        with self.assertRaisesRegex(ValueError,"INDEPENDENT_ORIGINAL_SOURCE"):
            execute(b"{}",b"{}",b"{}",b"{}")
        with self.assertRaisesRegex(ValueError,"PARENT_EVIDENCE"):
            verify({},(b"{}",b"{}",b"{}",b"{}"))

if __name__=="__main__":unittest.main()
