"""ACC-66 focused tests for one-pass spectral char prediction and source boundaries."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("acc66",Path(__file__).with_name("experiment.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class U23Evaluation(unittest.TestCase):
    def test_01_authentic_registry(self):
        self.assertEqual(m.source_identity()["registry_git_blob"],m.ORIGINAL_REGISTRY_BLOB)
    def test_02_prereg_immutable_identity(self):
        self.assertEqual(m.source_identity()["prereg_commit"],"87509a9551d0a572b3f910ea5e3826fa629efad2")
    def test_03_prior_austen_exposure_disclosed(self):
        self.assertEqual(m.source_identity()["source_exposure"],"AUSTEN_EXPOSED_IN_PRIOR_G74")
        self.assertFalse(m.source_identity()["source_training_heldout_verified"])
    def test_04_pinned_austen_sha_is_nonblank(self):
        self.assertEqual(len(m.AUSTEN_GIT_BLOB),40)
        self.assertEqual(len(m.AUSTEN_SHA256),64)
        self.assertEqual(m.AUSTEN_BYTES,717602)
    def test_05_frozen_starts_nonoverlap(self):
        self.assertEqual(m.STARTS,(24576,98304,196608))
        self.assertTrue(all(b-a>28000 for a,b in zip(m.STARTS,m.STARTS[1:])))
    def test_06_frozen_alphabet(self):
        self.assertEqual(len(m.ALPHABET),27)
        self.assertEqual(len(m.ALPHA_IDX),27)
    def test_07_slices_exact_nonoverlap(self):
        corpus="abcd"*60000
        s=m.slices(corpus,24576)
        self.assertEqual([len(s[n]) for n in m.OFFSETS],[14000,2000,4000,2000,6000])
    def test_08_frozen_examples_count(self):
        self.assertEqual(len(list(m.examples("abcd"*3500))),13996)
        self.assertEqual(len(list(m.examples("abc "*1000))),3996)
        self.assertEqual(len(list(m.examples("abc "*1500))),5996)
    def test_09_invalid_context(self):
        with self.assertRaises(ValueError):m.spectrum_power("ab")
        with self.assertRaises(ValueError):m.spectrum_power("ABCD")
    def test_10_phase_power_shift_invariance(self):
        for a in ("abcd","a bc","zzzy","abca"):
            self.assertEqual(m.spectrum_power(a),m.spectrum_power(a[1:]+a[0]))
    def test_11_phase_loss_rotation_collision(self):
        self.assertEqual(m.spectrum_power("abcd"),m.spectrum_power("bcda"))
        self.assertNotEqual("abcd","bcda")
    def test_12_different_character_bag_can_differ(self):
        self.assertNotEqual(m.spectrum_power("aaaa"),m.spectrum_power("abcd"))
    def test_13_power_integer_exact_no_float(self):
        for x in ("abcd"," zz ","abaa"):
            p=m.spectrum_power(x)
            self.assertEqual(len(p),81)
            self.assertTrue(all(type(v) is int and v>=0 for v in p))
    def test_14_phase_inverse_exact(self):
        for x in ("abcd","bcda","abba","zzzz","a bc"," cab"):
            self.assertEqual(m.inverse_phase(m.phase_preserved(x)),x)
    def test_15_phase_inverse_rejects_damage(self):
        with self.assertRaises(ValueError):m.inverse_phase((0,1,2))
    def test_16_modes_are_distinct(self):
        x="a bc"
        self.assertEqual(m.key("ngram1",x),"c")
        self.assertEqual(m.key("ngram2",x),"bc")
        self.assertEqual(m.key("ngram4",x),x)
        self.assertEqual(m.key("spectral_power_4",x),m.spectrum_power(x))
    def test_17_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):m.key("unsupported","abcd")
    def test_18_single_pass_train_count(self):
        model=m.train("ngram2","abcd"*3500)
        self.assertEqual(model["fit_examples"],13996)
        self.assertEqual(sum(model["global"]),13996)
    def test_19_smoothed_probability_valid(self):
        model=m.train("ngram1","abcd"*3500)
        z=m.eval_model(model,"abcd"*1000)
        self.assertEqual(z["examples"],3996)
        self.assertGreaterEqual(z["accuracy"],0)
        self.assertLessEqual(z["accuracy"],1)
        self.assertGreaterEqual(z["nll"],0)
    def test_20_prediction_digest_determinism(self):
        model=m.train("ngram2","abcd"*3500)
        self.assertEqual(m.eval_model(model,"abcd"*1000)["prediction_sha256"],
                         m.eval_model(model,"abcd"*1000)["prediction_sha256"])
    def test_21_serialized_tables_deterministic(self):
        a=m.train("ngram2","abcd"*3500)
        b=m.train("ngram2","abcd"*3500)
        self.assertEqual(m.byte_size(a),m.byte_size(b))
        self.assertGreater(m.byte_size(a),0)
    def test_22_dev_only_baseline_selector(self):
        dev={"ngram1":{"exact":10},"ngram2":{"exact":20},"ngram4":{"exact":15},
             "spectral_power_4":{"exact":999}}
        sizes={"ngram1":100,"ngram2":300,"ngram4":200,"spectral_power_4":1}
        self.assertEqual(m.select_control(dev,sizes),"ngram2")
    def test_23_tie_breaker_model_bytes(self):
        dev={"ngram1":{"exact":20},"ngram2":{"exact":20},"ngram4":{"exact":20}}
        sizes={"ngram1":200,"ngram2":100,"ngram4":400}
        self.assertEqual(m.select_control(dev,sizes),"ngram2")
    def test_24_fallback_on_unseen_context(self):
        model=m.train("ngram4","abcd"*3500)
        z=m.eval_model(model,"zzzz"*1000)
        self.assertEqual(z["unseen"],3996)
    def test_25_spectral_trained_one_pass(self):
        fit="abcd"*3500
        model=m.train("spectral_power_4",fit)
        self.assertEqual(model["fit_examples"],13996)
        z=m.eval_model(model,"abcd"*1000)
        self.assertEqual(z["examples"],3996)
    def test_26_alpha_source_context_never_leaks_label(self):
        a=list(m.examples("abcdz"))
        self.assertEqual(a,[("abcd","z")])
    def test_27_hash_does_not_rename_character_order(self):
        self.assertNotEqual(m.sha(b"abcd"),m.sha(b"bcda"))
    def test_28_frozen_model_count(self):
        self.assertEqual(m.MODELS,("ngram1","ngram2","ngram4","spectral_power_4"))

if __name__=="__main__":unittest.main()
