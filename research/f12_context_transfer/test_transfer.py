"""F12 synthetic-only integrity and transfer tests, never science."""
import copy
import unittest
from fit import (distance,choose,grouped,leave_family_out,evidence,RADII,
                 TRAIN,CHECK)
from verify import choose_action,case_set,recompute

def trial(seed,family,context,arm,loss):
    return {"seed":seed,"pair":[8,10],"regime":"onset1",
        "family":list(family),"matching_policy":"p1","arm":arm,
        "pre_mismatch":loss,"post_mismatch":0,
        "public_reads":10,
        "sample_trace":{"decision":{"public_start":context,
            "action_index":arm,"reads":10,"distinct_nonanchors":6,
            "physical_cells":[2,3,4,5,6,7]}}}

def samples():
    out=[]
    families=((1,3),(2,4),(3,5),(4,6))
    # 24 different identities per family via 2 seeds, 2 pairs, 2
    # regimes, 3 policies. Public context cycles across cases.
    for fi,family in enumerate(families):
        for seed in TRAIN:
            for pair in ([8,10],[11,13]):
                for regime in ("steady","onset1"):
                    for policy in ("p1","p2","p3"):
                        context=(fi*3+seed+pair[0])%14
                        for arm in range(6):
                            loss=(0 if arm==context%6 else 1+arm%3)
                            row=trial(seed,family,context,arm,loss)
                            row["pair"]=list(pair)
                            row["regime"]=regime
                            row["matching_policy"]=policy
                            out.append(row)
    return out

class F12Tests(unittest.TestCase):
    def test_circular_context_similarity(self):
        self.assertEqual(distance(13,0),1)
        self.assertEqual(distance(13,1),2)
        self.assertEqual(distance(4,11),7)
        self.assertEqual(RADII,(0,1,2,3,7))

    def test_training_only_cv_has_four_exclusive_family_holdouts(self):
        rows=samples()
        self.assertEqual(len(rows),576)
        groups=grouped(rows,TRAIN,tuple(range(6)))
        self.assertEqual(len(groups),96)
        card=leave_family_out(groups)
        self.assertEqual(len(card),len(RADII))
        self.assertTrue(all(sum(x["training_action_counts"])==96 for x in card))
        for radius in RADII:
            for context in range(14):
                self.assertEqual(choose(context,groups,radius),
                                 choose_action(context,groups,radius))

    def test_seed_exclusivity_and_counterfactual_integrity(self):
        rows=samples()
        with self.assertRaisesRegex(ValueError,"CASE_OR_SOURCE_ID"):
            grouped(rows,CHECK,tuple(range(6)))
        altered=copy.deepcopy(rows)
        altered[3]=copy.deepcopy(altered[0])
        with self.assertRaisesRegex(ValueError,"ONCE_ONLY_CASE_ACTION"):
            grouped(altered,TRAIN,tuple(range(6)))
        tamper=copy.deepcopy(rows)
        tamper[0]["sample_trace"]["decision"]["physical_cells"][0]=15
        with self.assertRaisesRegex(ValueError,"SENSOR_SET_OR_CONTEXT_NOT_MATCHED"):
            grouped(tamper,TRAIN,tuple(range(6)))
        withheld=copy.deepcopy(rows)
        withheld.pop()
        with self.assertRaisesRegex(ValueError,"ARM_CASE_COUNT"):
            grouped(withheld,TRAIN,tuple(range(6)))

    def test_source_born_witness_is_required(self):
        with self.assertRaisesRegex(ValueError,"PARENT_IDENTITY_AND_AUTHORITY"):
            evidence({}, {})
        parent={"schema":"forge.f11.automatic-task-aligned-information-value-engineering.v1",
                "status":"REUSED_F3_TRAIN_AND_VALIDATION_ONLY",
                "source_commit":"5797a257a75fe139313e8486cd1a1ae79c44b148",
                "scientific_dispatch_authorized":False,
                "scientific_winner_selected":False,
                "new_first_use_claims":0,"new_originals":0,
                "new_cohort_accesses":0,"paid_api_calls":0}
        with self.assertRaisesRegex(ValueError,"FROZEN_PARENT_MODEL"):
            evidence(parent,{})
        parent["scientific_dispatch_authorized"]=True
        with self.assertRaisesRegex(ValueError,"PARENT_IDENTITY_AND_AUTHORITY"):
            evidence(parent,{})

    def test_proposal_cannot_promote_without_signed_source(self):
        with self.assertRaisesRegex(ValueError,"PARENT_SOURCE_IDENTITY"):
            recompute(b"{}",b"{}",{})
        bad=copy.deepcopy(samples())
        bad[0]["pre_mismatch"]=9
        with self.assertRaisesRegex(ValueError,"PUBLIC_TRACE_OR_BUDGET"):
            grouped(bad,TRAIN,tuple(range(6)))

if __name__=="__main__":
    unittest.main()
