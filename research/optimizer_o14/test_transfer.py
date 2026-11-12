"""O14 exact prospective structural transfer and public-source custody tests."""
import hashlib
import math
import unittest

from public_source import (
    FIT_FAMILIES,TRANSFER_FAMILIES,FAMILIES,ROLES,ROLE_COUNTS,
    SourceCustodyRefused,episode,episodes,interleaved_fit,role_digest,
    seed,STEPS,
)
from runner import ARMS,FIT_ARMS,assert_prereg,fitted_model,nll
from o13_original_belief import LearnedPublicBelief
from o4_original_controls import PublicRecurrent,PublicActionHMM,PublicHistoryCounts


class O14ProspectiveTests(unittest.TestCase):
    def test_frozen_inventory_exact(self):
        p=assert_prereg()
        self.assertEqual(tuple(p["arms"]),ARMS)
        self.assertEqual(p["role_family_matrix"],ROLE_COUNTS)
        self.assertEqual(tuple(p["families"]),FAMILIES)
        self.assertEqual(p["steps_per_episode"],32)

    def test_nine_role_family_source_identities_and_chains(self):
        digests=[]
        for role,allow in ROLE_COUNTS.items():
            for fam,count in allow.items():
                batch=episodes(role,fam)
                self.assertEqual(len(batch),count)
                self.assertTrue(all(len(ep)==STEPS for ep in batch))
                for ep in batch:
                    self.assertTrue(all(len(row)==3 and
                                        all(type(bit) is int and bit in (0,1)
                                            for bit in row)
                                        for row in ep))
                    self.assertTrue(all(ep[j][2]==ep[j+1][0]
                                        for j in range(STEPS-1)))
                digests.append(role_digest(batch))
        self.assertEqual(len(digests),9)
        self.assertEqual(len(set(digests)),9)

    def test_transfer_cannot_be_requested_as_fitting_source(self):
        for family in TRANSFER_FAMILIES:
            for role in ("O14_FIT_TRAIN","O14_FIT_SELECT",
                         "O14_INDOMAIN_DEV"):
                with self.assertRaises(SourceCustodyRefused):
                    episode(role,family,0)
        for family in FIT_FAMILIES:
            with self.assertRaises(SourceCustodyRefused):
                episodes("O14_ZERO_SHOT_TRANSFER",family)

    def test_protected_and_old_reused_role_names_fail_closed(self):
        for role in ("HELD","ORIGINAL","Q21N01_PUBLIC_DEV",
                     "O13_PUBLIC_TRAIN","O13_PUBLIC_DEV",
                     "O14_DEV","FIT_TRAIN"):
            with self.assertRaises(SourceCustodyRefused):
                episode(role,FIT_FAMILIES[0],0)
        for i in (-1,24,True,1.0,"2"):
            with self.assertRaises(SourceCustodyRefused):
                seed("O14_FIT_TRAIN",FIT_FAMILIES[0],i)

    def test_train_and_select_interleaving_is_predeclared(self):
        fit=interleaved_fit("O14_FIT_TRAIN")
        sel=interleaved_fit("O14_FIT_SELECT")
        self.assertEqual((len(fit),len(sel)),(48,16))
        for index in range(24):
            self.assertEqual(fit[2*index],
                             episode("O14_FIT_TRAIN",FIT_FAMILIES[0],index))
            self.assertEqual(fit[2*index+1],
                             episode("O14_FIT_TRAIN",FIT_FAMILIES[1],index))
        for invalid_role in ("O14_INDOMAIN_DEV","O14_ZERO_SHOT_TRANSFER"):
            with self.assertRaises(SourceCustodyRefused):
                interleaved_fit(invalid_role)

    def test_unfamiliar_structures_have_public_information_only(self):
        ternary=episodes("O14_ZERO_SHOT_TRANSFER",
                         "XFER_C_THREE_STATE_CYCLE")[0]
        coupled=episodes("O14_ZERO_SHOT_TRANSFER",
                         "XFER_D_COUPLED_BIT_MEMORY")[0]
        self.assertNotEqual(ternary,coupled)
        for ep in (ternary,coupled):
            self.assertTrue(all(len(row)==3 for row in ep))
        self.assertNotEqual(
            role_digest(episodes("O14_ZERO_SHOT_TRANSFER",
                                 "XFER_NULL_IID")),
            role_digest(episodes("O14_ZERO_SHOT_TRANSFER",
                                 "XFER_C_THREE_STATE_CYCLE")))

    def test_original_fitted_controls_have_same_public_train(self):
        train=interleaved_fit("O14_FIT_TRAIN")[:8]
        selection=interleaved_fit("O14_FIT_SELECT")[:4]
        for arm in FIT_ARMS:
            with self.subTest(arm=arm):
                model,selection_meta=fitted_model(arm,train,selection)
                cp=model.checkpoint()
                self.assertTrue(math.isfinite(selection_meta["select_nll"]))
                self.assertGreater(model.updates,0)
                self.assertTrue(math.isfinite(nll(model,selection)))
                self.assertEqual(model.checkpoint(),cp)

    def test_trained_original_o13_state_erasure_is_no_retraining(self):
        train=interleaved_fit("O14_FIT_TRAIN")[:8]
        model=LearnedPublicBelief("FULL_CREDIT_BELIEF",17)
        model.fit(train)
        before=model.checkpoint()
        sample=episodes("O14_ZERO_SHOT_TRANSFER",
                        "XFER_C_THREE_STATE_CYCLE")[:2]
        normal=nll(model,sample)
        erased=nll(model,sample,erased=True)
        self.assertTrue(math.isfinite(normal) and math.isfinite(erased))
        self.assertEqual(before,model.checkpoint())
        self.assertEqual(model.updates,24)

    def test_heldout_prediction_does_not_fit_or_choose_seed(self):
        train=interleaved_fit("O14_FIT_TRAIN")[:8]
        selection=interleaved_fit("O14_FIT_SELECT")[:4]
        model,meta=fitted_model("O13_STOP_CREDIT_FROZEN_SOURCE",
                                train,selection)
        self.assertIn(meta["chosen_start"],(17,31))
        cp=model.checkpoint()
        for fam in TRANSFER_FAMILIES:
            score=nll(model,episodes("O14_ZERO_SHOT_TRANSFER",fam)[:2])
            self.assertGreaterEqual(score,0.)
            self.assertEqual(cp,model.checkpoint())

    def test_null_uniform_chance_diagnostic(self):
        self.assertAlmostEqual(-math.log(.5),math.log(2),places=12)
        self.assertEqual(
            episode("O14_ZERO_SHOT_TRANSFER","XFER_NULL_IID",0),
            episode("O14_ZERO_SHOT_TRANSFER","XFER_NULL_IID",0))


if __name__=="__main__":
    unittest.main()
