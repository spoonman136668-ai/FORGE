"""ACC-67: frozen U21 finite-state, learning, and source custody controls."""
import importlib.util
from pathlib import Path
import unittest

sp=importlib.util.spec_from_file_location("acc67_u21",Path(__file__).with_name("experiment.py"))
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)

class U21Research(unittest.TestCase):
    def test_01_original_claim_blob(self):
        self.assertEqual(m.source_custody()["original_git_blob"],m.REGISTRY_GIT_BLOB)
    def test_02_prereg_birth(self):
        self.assertEqual(m.source_custody()["prereg_commit"],"1c961a1793e8f453bc210a1fa33b12a83f780af5")
    def test_03_exposure_flag(self):
        self.assertEqual(m.source_custody()["source_previous_exposure"],"G74_AND_U23")
        self.assertFalse(m.source_custody()["scientific_new_first_use"])
    def test_04_original_chaos_recurrence_bound(self):
        self.assertTrue(all(0<=m.original_ac06_autonomous(i)<256 for i in range(256)))
    def test_05_original_infinite_state_falsifier(self):
        x=m.finite_witness()
        self.assertEqual(x["total_autonomous_seeds"],256)
        self.assertLessEqual(x["max_distinct_states_per_autonomous_orbit"],256)
        self.assertGreaterEqual(x["max_cycle"],1)
    def test_06_exhaustive_two_char_histories(self):
        x=m.finite_witness()
        self.assertEqual(x["two_character_histories"],729)
        self.assertLessEqual(x["distinct_eight_bit_states"],256)
        self.assertGreaterEqual(x["collision_histories"],473)
    def test_07_collision_example_authentic(self):
        x=m.finite_witness()["collision_example"]
        self.assertNotEqual(x["history_a"],x["history_b"])
        def end(history):
            state=m.SEED
            for char in history:state=m.advance("chaos_state",state,char)
            return state
        self.assertEqual(end(x["history_a"]),x["state"])
        self.assertEqual(end(x["history_b"]),x["state"])
    def test_08_not_claiming_external_memory_impossible(self):
        self.assertFalse(m.finite_witness()["unbounded_external_memory_ruled_out"])
    def test_09_frozen_uint8_models(self):
        self.assertEqual(m.SEED,17)
        self.assertEqual(m.CONTROLS,("ngram2","ngram4","linear_state","hash_state"))
    def test_10_state_update_deterministic(self):
        for mode in ("chaos_state","linear_state","hash_state"):
            for s in (0,17,100,255):
                self.assertEqual(m.advance(mode,s,"z"),m.advance(mode,s,"z"))
                self.assertIn(m.advance(mode,s,"z"),range(256))
    def test_11_bad_state_fails(self):
        for state in (-1,256):
            with self.assertRaises(ValueError):m.advance("chaos_state",state,"a")
        with self.assertRaises(ValueError):m.advance("chaos_state",17,"A")
    def test_12_bad_model_fails(self):
        with self.assertRaises(ValueError):m.advance("novel",17,"a")
        with self.assertRaises(ValueError):m.train("novel","abcd"*3500)
    def test_13_disjoint_frozen_source_windows(self):
        self.assertEqual(m.STARTS,(24576,98304,196608))
        self.assertTrue(all(b-a>28000 for a,b in zip(m.STARTS,m.STARTS[1:])))
    def test_14_per_segment_gap_custody(self):
        a=m.windows("abcd"*60000,24576)
        self.assertEqual([len(v) for v in a.values()],[14000,2000,4000,2000,6000])
    def test_15_exact_example_counts(self):
        for mode in m.MODELS:
            self.assertEqual(len(list(m.iter_examples("abcd"*3500,mode))),13996)
            self.assertEqual(len(list(m.iter_examples("abcd"*1000,mode))),3996)
            self.assertEqual(len(list(m.iter_examples("abcd"*1500,mode))),5996)
    def test_16_cold_state_replay(self):
        for mode in ("chaos_state","linear_state","hash_state"):
            a=list(m.iter_examples("abcd"*50,mode))
            self.assertEqual(a,list(m.iter_examples("abcd"*50,mode)))
    def test_17_state_can_reflect_order(self):
        x=m.advance("chaos_state",m.advance("chaos_state",17,"a"),"b")
        y=m.advance("chaos_state",m.advance("chaos_state",17,"b"),"a")
        self.assertNotEqual(x,y)
    def test_18_single_pass_training(self):
        for mode in m.MODELS:
            model=m.train(mode,"abcd"*3500)
            self.assertEqual(model["fit_count"],13996)
            self.assertEqual(sum(model["global"]),13996)
    def test_19_fitted_prediction_valid(self):
        for mode in m.MODELS:
            model=m.train(mode,"abcd"*3500)
            z=m.evaluate(model,"abcd"*1000)
            self.assertEqual(z["examples"],3996)
            self.assertGreaterEqual(z["nll"],0)
            self.assertGreaterEqual(z["accuracy"],0)
            self.assertLessEqual(z["accuracy"],1)
    def test_20_holdout_not_fit_reused(self):
        model=m.train("chaos_state","abcd"*3500)
        original=len(model["table"])
        m.evaluate(model,"zzzz"*1000)
        self.assertEqual(len(model["table"]),original)
    def test_21_same_cold_prediction_digest(self):
        model=m.train("chaos_state","abcd"*3500)
        a=m.evaluate(model,"abcd"*1000)["prediction_sha256"]
        b=m.evaluate(model,"abcd"*1000)["prediction_sha256"]
        self.assertEqual(a,b)
    def test_22_table_logical_bytes_recorded(self):
        model=m.train("chaos_state","abcd"*3500)
        self.assertGreater(m.table_bytes(model),0)
        self.assertEqual(m.table_bytes(model),m.table_bytes(model))
    def test_23_DEV_only_control_selector(self):
        d={x:{"correct":3} for x in m.CONTROLS}
        d["ngram4"]={"correct":10}
        d["chaos_state"]={"correct":100}
        sizes={x:200 for x in (*m.CONTROLS,"chaos_state")}
        self.assertEqual(m.choose_control(d,sizes),"ngram4")
    def test_24_tie_select_smallest_table(self):
        d={x:{"correct":10} for x in m.CONTROLS}
        sizes={x:100 for x in m.CONTROLS}
        sizes["hash_state"]=50
        self.assertEqual(m.choose_control(d,sizes),"hash_state")
    def test_25_bad_short_segment_fails(self):
        with self.assertRaises(ValueError):list(m.iter_examples("abcd","chaos_state"))
    def test_26_source_SHA_is_pinned(self):
        self.assertEqual(len(m.AUSTEN_GIT_BLOB),40)
        self.assertEqual(len(m.AUSTEN_SHA256),64)
        self.assertEqual(m.AUSTEN_BYTES,717602)
    def test_27_unseen_context_fallback(self):
        model=m.train("ngram4","abcd"*3500)
        z=m.evaluate(model,"zzzz"*1000)
        self.assertEqual(z["unseen"],3996)
    def test_28_NO_model_promotion_in_custody(self):
        self.assertFalse(m.source_custody()["scientific_new_first_use"])
        self.assertEqual(len(m.MODELS),5)

if __name__=="__main__":unittest.main()
