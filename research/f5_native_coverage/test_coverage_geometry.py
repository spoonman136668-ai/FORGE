"""Independent exhaustive minimax certificate for F5 public sensing geometry."""
import unittest
from itertools import combinations
from collections import Counter
from coverage_geometry import (
    BASELINE_OFFSETS,N,rotation_exposures,evaluate,optimize
)
from policy import choose

class CoverageGeometryTests(unittest.TestCase):
    def test_exhaustive_global_optimum_and_no_science_authority(self):
        result=optimize()
        self.assertEqual(result["enumerated_offset_patterns"],286)
        self.assertEqual(result["nonanchor_pair_count"],91)
        self.assertEqual(result["optimal_offsets"],[0,1,4,6])
        self.assertEqual(result["optimal"]["worst_pair_exposure"],7)
        self.assertEqual(result["baseline"]["worst_pair_exposure"],5)
        self.assertEqual(result["new_development_cohorts_accessed"],0)
        self.assertEqual(result["new_sealed_cohorts_accessed"],0)
        self.assertFalse(result["prospective_scientific_execution_authorized"])

    def test_independently_recompute_nonoracle_exposure_certificate(self):
        # This witness uses an alternative counting formulation: count
        # offsets that miss both swap endpoints, rather than count detections.
        chosen=(0,1,4,6)
        baseline=BASELINE_OFFSETS
        all_pairs=list(combinations(range(2,16),2))
        self.assertEqual(len(all_pairs),91)
        assert_worst=[]
        for offsets in (baseline,chosen):
            seen=Counter()
            for a,b in all_pairs:
                misses=0
                for rotation in range(14):
                    obs={((x+rotation)%14)+2 for x in offsets}
                    if a not in obs and b not in obs:misses+=1
                seen[14-misses]+=1
            assert_worst.append(min(seen))
            self.assertEqual(sum(seen.values()),91)
            self.assertEqual(seen,Counter({
                int(k):v for k,v in evaluate(offsets)["pair_exposure_histogram"].items()
            }))
        self.assertEqual(assert_worst,[5,7])

    def test_all_candidate_offset_patterns_have_worst_exposure_at_most_seven(self):
        maximum=0
        for other in combinations(range(1,N),3):
            offsets=(0,)+other
            maximum=max(maximum,min(rotation_exposures(offsets).values()))
        self.assertEqual(maximum,7)

    def test_policy_uses_qualified_offsets_from_actual_prior_public_values(self):
        for b0 in range(14):
            # Valid synthetic public calibration: a=1, d=0. Compute
            # rotation from observed public b0 using the exact modulo-16
            # calibration followed by the modulo-14 geometry transform.
            start=(b0+3)%14
            h={0:{0:b0,1:(b0+1)%16},
               1:{0:b0,1:(b0+1)%16},
               3:{0:b0,1:(b0+1)%16}}
            first=choose("F5-COVERAGE",5,h)
            self.assertEqual(first,tuple(((start+x)%14)+2 for x in (0,1)))
            h[5]={addr:(b0+addr)%16 for addr in first}
            second=choose("F5-COVERAGE",7,h)
            self.assertEqual(second,tuple(((start+x)%14)+2 for x in (4,6)))
            self.assertEqual(len(set(first+second)),4)

    def test_invalid_or_over_budget_candidate_rejected(self):
        for invalid in ((0,1,1,6),(0,1,4,15),(1,2,3,4),(0,1,4)):
            with self.assertRaisesRegex(ValueError,"F5_GEOMETRY_INVALID_OFFSETS"):
                rotation_exposures(invalid)

if __name__=="__main__":
    unittest.main()
