"""F14 synthetic negative contracts only; no scientific originals."""
import copy
import unittest
from train import grouped,fit,choose,digest,cross_family,execute
from verify import parse,estimate,select,fingerprint,review

def rows():
    out=[]
    for family in range(4):
        for seed in (67204,67205):
            for pair in ([8,10],[11,13]):
                for regime in ("steady","onset1"):
                    for policy in ("a","b","c"):
                        c=(family*5+seed+pair[0]+(regime=="onset1"))%16
                        values=[[c,(c+3)%16],[(c+4)%16,(c+5)%16],
                                [0,0],[0,0],[0,0]]
                        for arm in range(6):
                            out.append({"seed":seed,"pair":pair,
                                "regime":regime,"family":[family],
                                "matching_policy":policy,"arm":arm,
                                "pre_mismatch":0 if arm==(c%6) else (arm+2)%5,
                                "post_mismatch":0,"public_reads":10,
                                "sample_trace":{"addresses":[[0,1],[0,1],
                                [2,3],[4,5],[6,7]],
                                "public_values":copy.deepcopy(values),
                                "decision":{"action_index":arm,"reads":10}}})
    return out

class FactorizedTests(unittest.TestCase):
    def test_matched_real_source_format_and_independent_predictions(self):
        raw=rows()
        self.assertEqual(len(raw),576)
        primary=grouped(raw,(67204,67205))
        independent=parse(raw,(67204,67205))
        self.assertEqual(len(primary),len(independent))
        self.assertEqual(len(cross_family(primary)),4)
        for smooth in (4,12,36,108):
            model=fit(primary,smooth)
            witness=estimate(independent,smooth)
            self.assertEqual(digest(model),fingerprint(witness))
            for key in list(primary)[:12]:
                observed=primary[key][0]["public"]
                self.assertEqual(choose(observed,model),
                                 select(observed,witness))

    def test_untrusted_or_missing_cases_rejected(self):
        wrong=rows()
        wrong.pop()
        with self.assertRaisesRegex(ValueError,"FULL_SOURCE_COUNTERFACTUALS"):
            grouped(wrong,(67204,67205))
        with self.assertRaisesRegex(ValueError,"COMPLETE_SOURCE_ARMS"):
            parse(wrong,(67204,67205))
        with self.assertRaisesRegex(ValueError,"PINNED_ORIGINAL_WITNESS"):
            execute(b"{}",b"{}",b"{}",b"{}")
        with self.assertRaisesRegex(ValueError,"REVIEWED_PARENT_NEGATIVE"):
            review({},(b"{}",b"{}",b"{}",b"{}"))

    def test_out_of_range_public_denied(self):
        primary=grouped(rows(),(67204,67205))
        with self.assertRaisesRegex(ValueError,"PUBLIC_ONLY_FEATURES"):
            choose((0,1,2,16),fit(primary,12))

if __name__=="__main__":unittest.main()
