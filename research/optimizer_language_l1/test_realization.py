"""L1 adversarial tests: frozen corpus, exact role separation, trained controls."""
import hashlib
import math
import unittest

from public_language import (
    NAMESPACE,ROLES,COUNTS,AGENTS,OBJECTS,
    NotPublicRole,dataset,role_hash,surface_slots,render,
)
from learners import (
    PublicCategoricalHeads,MemorizedFullMeaning,SelectiveChunkRepair,
)
from runner import ARMS,guard,edit_distance,evaluate


class L1AlignedLanguage(unittest.TestCase):
    def test_frozen_protocol_before_learner_execution(self):
        p=guard()
        self.assertEqual(tuple(p["models"]),ARMS)
        self.assertEqual(p["roles"],COUNTS)
        self.assertIn("not parameter-matched",
                      p["training"]["model_capacity"])

    def test_exact_unique_role_data_and_frozen_hashes(self):
        hashes=[]
        keysets=[]
        for role in ROLES:
            rows=dataset(role)
            self.assertEqual(len(rows),COUNTS[role])
            hashes.append(role_hash(role))
            keys={tuple(x["meaning"]) for x in rows}
            self.assertEqual(len(keys),len(rows))
            keysets.append(keys)
            for row in rows:
                expected=surface_slots(tuple(row["meaning"]))
                self.assertEqual(row["slots"],list(expected))
                self.assertTrue(render(expected).endswith("."))
        self.assertEqual(len(set(hashes)),4)
        for i in range(len(keysets)):
            for j in range(i+1,len(keysets)):
                self.assertFalse(keysets[i] & keysets[j])

    def test_composition_pair_disjoint_but_values_in_training(self):
        train=dataset("L1_TRAIN")
        novel=dataset("L1_NOVEL_COMPOSITION_DEV")
        self.assertTrue(all(r["meaning"][0]=="eli" and r["meaning"][2]=="door"
                            for r in novel))
        self.assertTrue(all(not(r["meaning"][0]=="eli" and r["meaning"][2]=="door")
                            for r in train))
        self.assertIn("eli",{r["meaning"][0] for r in train})
        self.assertIn("door",{r["meaning"][2] for r in train})

    def test_old_protected_roles_not_reachable(self):
        for role in ("HELD","Q21N01","O14_ZERO_SHOT_TRANSFER",
                     "L1_HELD","L1_DEV","FIT_TRAIN","O13_PUBLIC_DEV"):
            with self.assertRaises(NotPublicRole):
                dataset(role)

    def test_surface_sentence_grammar_and_morphology(self):
        a=("ava","carry","gate","present",0,"quickly")
        b=("ava","carry","gate","past",0,"quickly")
        c=("ava","carry","gate","present",1,"quickly")
        d=("ava","carry","gate","future",1,"quickly")
        self.assertIn("carries",render(surface_slots(a)))
        self.assertIn("carried",render(surface_slots(b)))
        self.assertIn("does not carry",render(surface_slots(c)))
        self.assertIn("will not carry",render(surface_slots(d)))

    def test_train_parallel_and_autoregressive_on_equal_public_annotations(self):
        train=dataset("L1_TRAIN")[:96]
        select=dataset("L1_SELECT")[:20]
        probe=dataset("L1_NOVEL_COMPOSITION_DEV")[:5]
        for ar in (False,True):
            model=PublicCategoricalHeads(autoregressive=ar).fit(train,select)
            cp=model.checkpoint()
            self.assertEqual(len(model.subsets),8)
            self.assertTrue(all(len(x)<=3 for x in model.subsets))
            for row in probe:
                chunks,operations=model.generate(row["meaning"])
                self.assertEqual(len(chunks),8)
                self.assertGreater(operations,8)
            self.assertEqual(model.checkpoint(),cp)

    def test_unconditional_and_full_lookup_are_strict_memorization_controls(self):
        train=dataset("L1_TRAIN")[:96]
        select=dataset("L1_SELECT")[:20]
        uncond=PublicCategoricalHeads(unconditional=True).fit(train,select)
        lookup=MemorizedFullMeaning(train,uncond)
        first=train[0]
        generated,_=lookup.generate(first["meaning"])
        self.assertEqual(list(generated),first["slots"])
        unseen=dataset("L1_NOVEL_COMPOSITION_DEV")[0]
        unknown,_=lookup.generate(unseen["meaning"])
        baseline,_=uncond.generate(unseen["meaning"])
        self.assertEqual(unknown,baseline)

    def test_repair_threshold_selected_on_select_and_no_dev_mutation(self):
        train=dataset("L1_TRAIN")[:96]
        select=dataset("L1_SELECT")[:20]
        factor=PublicCategoricalHeads().fit(train,select)
        ar=PublicCategoricalHeads(autoregressive=True).fit(train,select)
        repair=SelectiveChunkRepair(factor,ar).select(select)
        self.assertIn(repair.threshold,(.05,.15,.30))
        cp=repair.checkpoint()
        data=dataset("L1_NOVEL_COMPOSITION_DEV")[:8]
        obs=evaluate("PARALLEL_SELECTIVE_REPAIR",repair,data)
        self.assertGreaterEqual(obs["exact_utterance_accuracy"],0)
        self.assertLessEqual(obs["exact_utterance_accuracy"],1)
        self.assertEqual(repair.checkpoint(),cp)

    def test_edit_distance_and_metric_sanity(self):
        self.assertEqual(edit_distance("abc","abc"),0)
        self.assertEqual(edit_distance("abc","ab"),1)
        self.assertEqual(edit_distance("","abc"),3)
        self.assertEqual(edit_distance("kitten","sitting"),3)

    def test_invalid_meaning_never_gets_a_generator_template(self):
        with self.assertRaises(ValueError):
            surface_slots(("ava","carry","gate","present",2,"quickly"))
        with self.assertRaises(ValueError):
            surface_slots(("ava","carry","gate","present",0,"unlisted"))

    def test_select_repair_threshold_double_selection_rejected(self):
        train=dataset("L1_TRAIN")[:64]
        select=dataset("L1_SELECT")[:12]
        p=PublicCategoricalHeads().fit(train,select)
        a=PublicCategoricalHeads(True).fit(train,select)
        r=SelectiveChunkRepair(p,a).select(select)
        with self.assertRaises(ValueError):
            r.select(select)


if __name__=="__main__":
    unittest.main()
