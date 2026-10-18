"""F124-AY source identity and PRESCIENCE synthetic model tests, no new TRAIN.

The public model is independently tested on synthetic round-composed examples.
No prospective AY task graph, TRAIN candidate score, or DEV is constructed.
"""
import inspect,unittest
import f124ay_train_source as source
import f124ay_learned_composition as model
import f124ay_fit_screen as screen

class OriginalFrozenAY(unittest.TestCase):
    def test_immutable_registration_and_no_DEV_source(self):
        d=source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(source.witness.blob(source.original.__file__),
                         source.PARENT_SOURCE_BLOB)
        self.assertEqual(d["lineage"]["qualified_AX_parent"],source.PARENT_SHA)
        self.assertEqual(d["source"]["public_answers_per_task"],48)
        self.assertEqual(len(d["models"]["frozen_arms"]),6)
        self.assertEqual(len(screen.ARMS),6)
        with self.assertRaises(Exception):
            source.rows("DEV")
        with self.assertRaises(Exception):
            source.build(source.COHORTS["Yggdrasil"]["DEV"].start,
                         source.VECTORS[0],"DEV")

    def test_no_oracle_inputs_to_public_learners(self):
        code=inspect.getsource(model)
        for item in ("import f124ay_train_source",
                     "import f124am_frozen_source",
                     "source.relation(","source.plain("):
            self.assertNotIn(item,code)
        self.assertEqual(model.MODES,
                         ("learned_two_round_keyed","learned_public_round_table"))

    def test_learned_unknown_8bit_round_key_on_synthetic_48(self):
        # Independently synthetic public pairs: no AY train seed/operator.
        key=73
        demos=[]
        for idx in range(48):
            x=(idx*1327+217) & 65535
            bits=model.bits16(x)
            y=model.forward_bits(bits,key)
            if idx in (3,7,11,26,30,35):
                y[(idx*5)%16]^=1
            demos.append({"input_bits":bits,"output_bits":y})
        for mode in model.MODES:
            trained=model.train(demos,mode)
            self.assertFalse(trained["operator_token_used"])
            self.assertFalse(trained["source_key_used"])
            self.assertGreater(trained["parameters_bits_lower"],0)
            result=model.predict(trained,demos[40]["output_bits"])
            self.assertEqual(len(result),16)
            self.assertTrue(all(x in (0,1) for x in result))
            checked=model.public_check(trained,demos)
            self.assertTrue(0<=checked<=128)
        chosen=model.train(demos,"learned_two_round_keyed")
        self.assertEqual(chosen["learned_key"],key)
        self.assertEqual(chosen["training_round_evaluations"],40*256*2)
        self.assertGreaterEqual(model.public_check(chosen,demos),96)
        with self.assertRaises(Exception):
            model.train(demos[:47],model.MODES[0])
        with self.assertRaises(Exception):
            model.train(demos,"non_preregistered")

    def test_fit_only_selection_and_held_screen_never_selects(self):
        fit={k:screen.card() for k,_,_ in screen.ARMS}
        self.assertEqual(screen.select_only_fit(fit),(None,0))
        fit["affine_basis48"]["paired"]=8
        fit["learned_roundkey_basis48"]["paired"]=10
        fit["learned_roundkey_basis48"]["by_operator"]["feistel"]["paired"]=2
        self.assertEqual(screen.select_only_fit(fit)[0],
                         "learned_roundkey_basis48")
        fit["learned_roundkey_basis48"]["FP"]=1
        self.assertIsNone(screen.select_only_fit(fit)[0])
if __name__=="__main__":unittest.main()
