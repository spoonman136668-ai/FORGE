"""F124-DB source-free original operator constructor qualification."""
from __future__ import annotations
import ast
import copy
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124db_sourcefree_meta_tasks as author
import f124db_learned_meta_constructor as c
import f124db_independent_meta_peer as peer
import f124db_structural_trial as trial

class StructuralMetaTransfer(unittest.TestCase):
    def test_sourcefree_meta_episode_birth_freeze(self):
        tasks=author.meta_training()
        self.assertEqual(len(tasks),12)
        self.assertEqual([len(v) for v in tasks],[24]*12)
        self.assertEqual(author.meta_training(),tasks)
        for family in author.FAMILIES:
            for seed in author.SEEDS:
                cases=author.heldout(family,seed)
                self.assertEqual([len(cases[k]) for k in ("FIT","CHECK","HELDOUT")],
                                 [24,8,8])
                self.assertEqual(cases,author.heldout(family,seed))
    def test_independently_learned_primitive_library(self):
        meta=author.meta_training()
        a,rec=c.learn_library(meta)
        b,control=peer.train_meta(meta)
        self.assertEqual(len(a["learned_library"]),2)
        self.assertEqual(len(b["macros"]),2)
        self.assertEqual(a["learned_library"],b["macros"])
        self.assertEqual(rec["meta_supervised_event_rows"],2304)
        self.assertEqual(control["meta_training_event_rows"],2304)
    def test_new_composition_from_reusable_fit_learned_motifs(self):
        a,_=c.learn_library(author.meta_training())
        b,_=peer.train_meta(author.meta_training())
        for family in author.FAMILIES:
            for seed in author.SEEDS:
                data=author.heldout(family,seed)
                first,rec=c.fit_novel(a,data["FIT"])
                second,rr=peer.synth(b,data["FIT"])
                self.assertIsNotNone(first,(family,seed,rec))
                self.assertIsNotNone(second,(family,seed,rr))
                self.assertEqual(rec["learned_meta_motifs_used_in_program"],2)
                self.assertEqual(rr["learned_meta_motifs_used_in_program"],2)
                self.assertTrue(all(c.score(first,x)["exact"] for x in data["CHECK"]))
                self.assertTrue(all(peer.score(second,x)["exact"] for x in data["CHECK"]))
                self.assertTrue(all(c.score(first,x)["exact"] for x in data["HELDOUT"]))
                self.assertTrue(all(peer.score(second,x)["exact"] for x in data["HELDOUT"]))
    def test_motif_ablation_removes_actual_operator_construction(self):
        data=author.heldout(author.FAMILIES[0],61)
        learner,_=c.learn_library(author.meta_training())
        good,_=c.fit_novel(learner,data["FIT"])
        ablated,ablation=c.fit_novel({"learned_library":[]},data["FIT"])
        self.assertIsNotNone(good)
        self.assertIsNone(ablated)
        self.assertFalse(ablation["natural_FIT"])
        self.assertEqual(ablation["full_library_pair_search_budget"],0)
        # This ablation demonstrates that learned motifs materially occur
        # in program construction, NOT superiority over a fully trained peer.
    def test_role_permutation_invariance(self):
        m,_=c.learn_library(author.meta_training())
        d=author.heldout(author.FAMILIES[1],61)
        program,_=c.fit_novel(m,d["FIT"])
        x=d["HELDOUT"][0]
        maproles={"alpha":"beta","beta":"gamma","gamma":"alpha"}
        transformed={"initial":{maproles[k]:v for k,v in x["initial"].items()},
                     "events":[{**z,"target":maproles[z["target"]],
                                "source":maproles[z["source"]]} for z in x["events"]]}
        self.assertEqual(c.rollout(program,x),c.rollout(program,transformed))
    def test_no_target_teacher_forcing_at_check_or_holdout(self):
        meta,_=c.learn_library(author.meta_training())
        data=author.heldout(author.FAMILIES[0],61)
        model,_=c.fit_novel(meta,data["FIT"])
        ep=data["HELDOUT"][0]
        corrupted=copy.deepcopy(ep)
        for e in corrupted["events"]:e["observed"]^=15
        self.assertEqual(c.rollout(model,ep),c.rollout(model,corrupted))
    def test_both_strong_meta_trained_arms_share_public_source(self):
        one=trial.run(author.FAMILIES[0],61,"meta_constructor")
        two=trial.run(author.FAMILIES[0],61,"equal_meta_peer")
        for key in ("meta_task_public_sha256","heldout_FIT_sha256",
                    "heldout_CHECK_sha256","heldout_unseen_sha256"):
            self.assertEqual(one[key],two[key])
        self.assertTrue(one["cross_task_meta_trained"])
        self.assertTrue(two["cross_task_meta_trained"])
        self.assertFalse(one["scientific_acceptance"])
        self.assertFalse(two["scientific_acceptance"])
    def test_no_source_import_or_old_original_workflows(self):
        for module in ("f124db_learned_meta_constructor.py",
                       "f124db_independent_meta_peer.py"):
            imports=[]
            for n in ast.walk(ast.parse((HERE/module).read_text())):
                if isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
                if isinstance(n,ast.ImportFrom):imports.append(n.module or "")
            self.assertFalse(any(name.startswith(("f124db_sourcefree_meta_tasks",
                            "f124da_sourcefree_operators","f124co_","f124cu_"))
                            for name in imports))
if __name__=="__main__":unittest.main()
