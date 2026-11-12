"""F58 fixed action/consequence ridge falsifier, synthetic numerical unit controls.

No environment, no new seed, no original scientific first-use. Original physics
is evaluated only by the separate protocol-pinned hosted FIT-only trial.
"""
import ast
import inspect
import math
import unittest
from unittest.mock import patch

import numpy as np
import f58_original_acrobot_fit_torque_rule as f58


class F58ActionConditionedRuleTests(unittest.TestCase):
    def setUp(self):
        self.phi=np.asarray([
            [1.,.1,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.],
            [1.,.4,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.],
            [1.,.2,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.],
            [1.,.9,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.],
        ],dtype=np.float64)
        self.actions=np.asarray([0,1,2,0],dtype=np.int64)

    def test_frozen_source_and_parent_falsifier(self):
        self.assertEqual(f58.PROTOCOL_COMMIT,
                         "ec22d962f145f2f55262368b3a5f7381f4806c50")
        self.assertEqual(f58.PROTOCOL_BLOB,
                         "a8396cab6180e0aaefbbc799d1f7b8b770d3a372")
        self.assertEqual(f58.ROOTS,(21011,21017,21019,21023,21029,21031))
        self.assertEqual(f58.FIT_SHA256,
                         "63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a")
        self.assertEqual(f58.ARMS,("factorized-torque","action-specific-ridge",
                                    "action-blind-ridge","shuffled-torque"))
        self.assertEqual(f58.RIDGE,.05)

    def test_factorized_signed_torque_and_zero_action(self):
        x=f58.design(self.phi,self.actions,"factorized-torque")
        self.assertEqual(x.shape,(4,30))
        np.testing.assert_array_equal(x[:,:15],self.phi)
        np.testing.assert_array_equal(x[0,15:],-self.phi[0])
        np.testing.assert_array_equal(x[1,15:],np.zeros(15))
        np.testing.assert_array_equal(x[2,15:],self.phi[2])

    def test_fully_trained_strong_onehot_and_action_blind_controls(self):
        x=f58.design(self.phi,self.actions,"action-specific-ridge")
        self.assertEqual(x.shape,(4,45))
        for i,a in enumerate(self.actions):
            np.testing.assert_array_equal(x[i,15*a:15*(a+1)],self.phi[i])
            self.assertEqual(np.count_nonzero(x[i,:15*a]),0)
            self.assertEqual(np.count_nonzero(x[i,15*(a+1):]),0)
        np.testing.assert_array_equal(
            f58.design(self.phi,self.actions,"action-blind-ridge"),self.phi)

    def test_invalid_actions_and_unfrozen_estimator_rejected(self):
        for bad in (np.asarray([0,1,3,0]),np.asarray([0,1,-1,0]),
                    np.asarray([0.,1.,2.,0.])):
            with self.assertRaises(ValueError):
                f58.design(self.phi,bad,"factorized-torque")
        with self.assertRaises(ValueError):
            f58.design(self.phi,self.actions,"oracle")
        with self.assertRaises(ValueError):
            f58.design(np.zeros((4,14)),self.actions,"action-blind-ridge")

    def test_closed_form_ridge_learns_nontrivial_torque_rule(self):
        rng=np.random.default_rng(581234)
        phi=np.ones((120,15))
        phi[:,1]=rng.normal(size=120)
        phi[:,2]=rng.normal(size=120)
        actions=np.tile(np.asarray([0,1,2]),40)
        t=actions-1.
        y=np.column_stack((.01+.10*phi[:,1]+.3*t,
                           -.04+.05*phi[:,2]-.2*t))
        x=f58.design(phi,actions,"factorized-torque")
        w=f58.ridge_fit(x,y)
        self.assertEqual(w.shape,(30,2))
        self.assertGreater(np.linalg.norm(w[15:]),.09)  # ridge shrinks the true .1 torque coefficient
        self.assertLess(float(np.mean((x@w-y)**2)),1e-5)
        self.assertEqual(f58.f51.digest(w.tolist()),
                         f58.f51.digest(f58.ridge_fit(x,y).tolist()))

    def test_frozen_thresholds_preserve_negative_and_strong_baseline(self):
        folds=[{"arms":{
            "factorized-torque":{"mse":.05,"effect_norm":.1},
            "action-specific-ridge":{"mse":.07},
        }} for _ in range(6)]
        good={"factorized-torque":.05,"action-specific-ridge":.07,
              "action-blind-ridge":.09,"shuffled-torque":.09}
        classification,checks=f58.decide(good,folds)
        self.assertEqual(classification,f58.SIGNAL)
        self.assertEqual(checks["candidate_beats_action_specific_roots"],6)
        weak=dict(good,**{"factorized-torque":.071})
        self.assertEqual(f58.decide(weak,folds)[0],f58.NO_GO)
        weakfolds=[{"arms":{"factorized-torque":{"mse":.08,"effect_norm":.1},
                            "action-specific-ridge":{"mse":.07}}}
                   if i<2 else folds[i] for i in range(6)]
        self.assertEqual(f58.decide(good,weakfolds)[0],f58.NO_GO)
        no_effect=[{"arms":{"factorized-torque":{"mse":.05,"effect_norm":0.},
                             "action-specific-ridge":{"mse":.07}}}
                   if i==0 else folds[i] for i in range(6)]
        self.assertEqual(f58.decide(good,no_effect)[0],f58.NO_GO)

    def test_shuffled_training_action_is_seed_pinned(self):
        # Prevent a positive result arising from an unshuffled negative arm.
        rng=np.random.default_rng(581000+f58.ROOTS[0])
        target=np.arange(27,dtype=np.int64)%3
        expected=rng.permutation(target)
        with patch.object(f58,"ridge_fit",side_effect=RuntimeError("FIT_MARKER")):
            # compare_arm must encounter a matrix built from the shuffled labels.
            original=f58.design
            seen=[]
            def recorded(phi,actions,arm):
                seen.append((arm,np.asarray(actions).copy()))
                return original(phi,actions,arm)
            x=np.tile(np.eye(15)[:3],(9,1))
            y=np.zeros((27,2))
            with patch.object(f58,"design",side_effect=recorded):
                with self.assertRaisesRegex(RuntimeError,"FIT_MARKER"):
                    f58.compare_arm((x,target,y),(x,target,y),
                                    "shuffled-torque",f58.ROOTS[0])
            np.testing.assert_array_equal(seen[0][1],expected)

    def test_no_new_physics_dispatch_in_f58_source(self):
        tree=ast.parse(inspect.getsource(f58))
        imports=set()
        attrs=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):
                imports.add(node.module)
            elif isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                attrs.add(node.func.attr)
        self.assertEqual(imports,{"json","math","os","pathlib","sys","time",
                                   "numpy","f51_original_acrobot_transfer_dev",
                                   "f53_original_acrobot_supported_residual_dev"})
        self.assertFalse({"step","reset","make","evaluate","dispatch",
                          "start_scientific_experiment","CompareAndSwap"}&attrs)
        self.assertNotIn("gymnasium",imports)


if __name__=="__main__":
    unittest.main()
