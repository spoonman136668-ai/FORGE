"""F124-DI development-only qualification, no new original science."""
from __future__ import annotations
import ast
import copy
import sys
from pathlib import Path
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124di_sourcefree_development as source
import f124di_cv_degree_prior as candidate
import f124di_independent_cv_peer as equal
import f124di_zero_oracle_trial as trial

class ZeroOracleFITLearnedPrior(unittest.TestCase):
    def test_deterministic_source_only_development_roster(self):
        self.assertEqual(source.SEEDS,(701,702,703,704))
        self.assertEqual(len(source.FAMILIES),4)
        for family in source.FAMILIES:
            d=source.development(family,701)
            self.assertEqual(d,source.development(family,701))
            self.assertEqual([len(d[k]) for k in ("FIT","CHECK","HELDOUT")],[24,8,8])
            for ep in d["HELDOUT"]:
                other=source.matched_negative(ep)
                self.assertNotEqual(other,ep)
                self.assertEqual(sorted(z["observed"] for z in ep["events"]),
                                 sorted(z["observed"] for z in other["events"]))
    def test_equal_candidate_and_peer_hypothesis_space_and_ranks(self):
        self.assertEqual(candidate.PAIRS,equal.PAIRS)
        self.assertEqual(candidate.DEGREES,equal.DEGREES)
        self.assertEqual(candidate.MASKS,equal.TRUNCMASK)
        self.assertEqual(len(candidate.PAIRS)*len(candidate.DEGREES),40)
        self.assertEqual(candidate.MASKS[4].bit_count(),163)
    def test_no_source_or_private_future_labels_enter_learners(self):
        for filename in ("f124di_cv_degree_prior.py",
                         "f124di_independent_cv_peer.py"):
            imported=[]
            for n in ast.walk(ast.parse((HERE/filename).read_text())):
                if isinstance(n,ast.Import):imported.extend(z.name for z in n.names)
                elif isinstance(n,ast.ImportFrom):imported.append(n.module or "")
            self.assertNotIn("f124di_sourcefree_development",imported)
            self.assertNotIn("f124di_zero_oracle_trial",imported)
    def test_two_independently_fitted_models_receive_same_training(self):
        d=source.development(source.FAMILIES[2],701)
        a,aa=candidate.learn(d["FIT"])
        b,bb=equal.fit(d["FIT"])
        self.assertEqual(aa.get("new_oracle_answers"),0)
        self.assertEqual(bb.get("new_oracle_answers"),0)
        self.assertEqual(aa.get("CV_exact_full_trajectories_of_4"),
                         bb.get("CV_exact_full_trajectories_of_4"))
        self.assertEqual(aa.get("CV_bit_errors"),bb.get("CV_bit_errors"))
        if a is not None and b is not None:
            e=d["CHECK"][0]
            self.assertEqual(candidate.score(a,e)["native_events"],8)
            self.assertEqual(equal.score(b,e)["native_events"],8)
    def test_no_teacher_forcing_at_CHECK_or_dev_heldout(self):
        d=source.development(source.FAMILIES[2],701)
        for train,score in ((candidate.learn,candidate.score),
                            (equal.fit,equal.score)):
            model,receipt=train(d["FIT"])
            if model is None:continue
            ep=d["HELDOUT"][0];copy_ep=copy.deepcopy(ep)
            for event in copy_ep["events"]:event["observed"]^=15
            self.assertNotEqual(score(model,ep)["exact"],score(model,copy_ep)["exact"])
    def test_development_trial_marks_no_firstuse_and_same_public_hashes(self):
        fam=source.FAMILIES[2]
        a=trial.trial(fam,701,trial.ARMS[0])
        b=trial.trial(fam,701,trial.ARMS[1])
        for field in ("FIT_public_sha256","CHECK_public_sha256","HELDOUT_public_sha256"):
            self.assertEqual(a[field],b[field])
        self.assertEqual(a["new_oracle_queries_or_labels"],0)
        self.assertEqual(b["new_oracle_queries_or_labels"],0)
        self.assertEqual(a["original_scientific_firstuse"],0)
        self.assertFalse(a["scientific_acceptance"])
if __name__=="__main__":unittest.main()
