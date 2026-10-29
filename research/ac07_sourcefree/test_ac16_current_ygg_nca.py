"""AC-16 fail-closed public data and real native interface unit controls.

Fixtures below test our boundaries only; no fake DTR evidence is emitted.
"""
import unittest
try:
    import torch
    import ac16_current_ygg_nca as ac
except ModuleNotFoundError as exc:
    if exc.name != "torch":
        raise
    torch = None
    ac = None

@unittest.skipIf(torch is None, "AC16 original torch tests require isolated pinned CPU venv")
class AC16Tests(unittest.TestCase):
    def test_pinned_current_actual_native_src(self):
        self.assertEqual(ac.ACTIVE_YGG_SHA,"92c421a5475a27015a390efb88c373eb5f15379d")
        self.assertEqual(ac.NCA_BLOB,"7b15017b7f5c6f9b507bcf43f4545a3c972f40d1")
        self.assertEqual(ac.TRAINING_BLOB,"af610c4334d2dd16415b39dd344ae2ed82ddd931")
        self.assertNotEqual(ac.ACTIVE_YGG_SHA,ac.ac15.YGG_COMMIT)
        self.assertEqual(ac.EPOCHS,64)
        self.assertEqual(ac.STEPS,2)

    def test_spatial_channels_read_only_public_bits(self):
        rows=[(0,1,0,1),(1,0,1,0)]
        x=ac.spatial_encode(rows)
        self.assertEqual(tuple(x.shape),(2,8,5,5))
        self.assertEqual(float(x[0,1,2,2]),1.0)
        self.assertEqual(float(x[1,0,2,1]),1.0)
        self.assertEqual(float(x[1,2,2,3]),1.0)
        self.assertEqual(float(x[:,3,:,:].min()),1.0)
        # True labels must NOT appear as an input channel.
        x2=ac.spatial_encode([(0,1,0,0),(1,0,1,1)])
        self.assertTrue(torch.equal(x,x2))

    def test_nonbinary_fields_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"INVALID_PUBLIC_EVENT_BIT"):
            ac.spatial_encode([(0,1,2,0)])
        with self.assertRaisesRegex(RuntimeError,"INVALID_PUBLIC_EVENT_BIT"):
            ac.spatial_encode([(0,1,0,2)])

    def test_fully_fitted_tabular_no_oracle(self):
        fit=[(0,0,0,0),(0,0,0,1),(0,0,1,1),(1,1,0,0)]
        dev=[(0,0,0,0),(0,0,1,1),(1,0,1,1)]
        p,unseen=ac.tabular_probs(fit,dev)
        self.assertEqual(p,[0.5,2/3,0.5])
        self.assertEqual(unseen,1)

    def test_metric_baseline_uses_fixed_brier_and_exact_count(self):
        r=ac.metrics([0.25,0.75],[(0,0,0,0),(1,1,1,1)])
        self.assertEqual(r["correct_examples"],2)
        self.assertEqual(r["examples"],2)
        self.assertAlmostEqual(r["brier"],0.0625)

    def test_reject_unverified_parent_and_dev_update(self):
        with self.assertRaisesRegex(RuntimeError,"PARENT_REAL_SOURCE"):
            ac.validate_parent({"scientific_first_use":False})
        self.assertEqual(ac.ac15.FIT,tuple(range(760000,760008)))
        self.assertEqual(ac.ac15.DEV,tuple(range(760200,760204)))
        self.assertTrue(set(ac.ac15.FIT).isdisjoint(ac.ac15.DEV))

    def test_metric_cannot_claim_causal_value(self):
        self.assertEqual(ac.SCHEMA,"forge.ac16.actual-ygg-local-nca-public-development.v1")
        self.assertEqual(ac.STATE_CHANNELS,8)
        self.assertEqual(ac.GRID,5)
        self.assertEqual(ac.HIDDEN,16)

if __name__=="__main__":
    unittest.main()
