"""No-world fixture checks for frozen FIT seed binding and restoration."""
import unittest
from unittest.mock import patch
import itd02_r8_sixfield_fit as subject

class FitBindingTest(unittest.TestCase):
    def test_bind_and_restore(self):
        original=subject.k4y.SEEDS
        old_fit=subject.k4x.FIT_SEEDS
        def fake_fit():
            self.assertEqual(subject.k4y.SEEDS["FIT"],tuple(range(81400,81424)))
            return ([{"family":f,"seed":81400,"action":2} for f in ("empty","fourrooms") for _ in range(6000)],
                    [{"family":"empty","seed":81400}],
                    {f:{"public_steps":6000,"episodes_executed":1,"distinct_training_seeds":1} for f in ("empty","fourrooms")},
                    0.0,{"eligible":True})
        with patch.object(subject.k4y,"fit",side_effect=fake_fit),patch.object(subject,"fit_sixfield",return_value=({"model":1},"digest")):
            learned,receipt=subject.train_sixfield_fit()
        self.assertEqual(receipt["fit_seeds"],[81400,81423])
        self.assertEqual(receipt["fit_events"],12000)
        self.assertFalse(receipt["scientific_accepted"])
        self.assertIs(subject.k4y.SEEDS,original)
        self.assertIs(subject.k4x.FIT_SEEDS,old_fit)
    def test_failure_restores_seeds(self):
        original=subject.k4y.SEEDS
        old_fit=subject.k4x.FIT_SEEDS
        with patch.object(subject.k4y,"fit",side_effect=RuntimeError("fixture failure")):
            with self.assertRaisesRegex(RuntimeError,"fixture failure"):
                subject.train_sixfield_fit()
        self.assertIs(subject.k4y.SEEDS,original)
        self.assertIs(subject.k4x.FIT_SEEDS,old_fit)
    def test_short_fit_fails_closed(self):
        with patch.object(subject.k4y,"fit",return_value=([1],[1],{},0,{"eligible":True})):
            with self.assertRaisesRegex(ValueError,"NOT_QUALIFIED"):
                subject.train_sixfield_fit()

if __name__=="__main__":unittest.main()
