import json
import unittest

import l9_model_suite as m

class ModelSuiteTests(unittest.TestCase):
    def ex(self, role="L9_TRAIN", ref="Alice was born in Paris."):
        triples=(m.Triple("Alice","birthPlace","Paris"),)
        return m.Example(role=role,graph_sha256="a"*64,triples=triples,reference=ref)

    def test_fixed_byte_codec_roundtrip(self):
        text="Café Δ"
        enc=m.encode_target(text)
        self.assertIsNotNone(enc)
        self.assertEqual(m.decode_generated(enc[1]),m.normalize_space(text))
        self.assertIsNone(m.decode_generated([255,255,m.EOS]))

    def test_source_overlength_never_truncates(self):
        triples=(m.Triple("A"*3000,"p","B"),)
        self.assertIsNone(m.encode_source(triples))

    def test_candidate_is_train_only_and_abstains_without_template(self):
        state=m.fit_candidate([self.ex(),self.ex(ref="Alice was born in Paris!")])
        cfg=m.CandidateConfig(1,8," ")
        out=m.realize_candidate(state,self.ex().triples,cfg)
        self.assertIn("Alice",out)
        self.assertIn("Paris",out)
        self.assertIsNone(m.realize_candidate(state,(m.Triple("Alice","unknownPredicate","Paris"),),cfg))
        with self.assertRaises(ValueError):
            m.fit_candidate([self.ex(role="L9_SELECT")])

    def test_candidate_state_is_deterministic(self):
        a=m.fit_candidate([self.ex(),self.ex(ref="Alice was born in Paris!")])
        b=m.fit_candidate(list(reversed([self.ex(),self.ex(ref="Alice was born in Paris!")])))
        self.assertEqual(m.canonical_json_bytes(a),m.canonical_json_bytes(b))

    def test_retrieval_exact_match_and_train_only(self):
        state=m.fit_retrieval([self.ex(ref="Alice was born in Paris."),self.ex(ref="Alice is from Paris.")])
        self.assertEqual(m.realize_retrieval(state,self.ex().triples),"Alice is from Paris.")
        with self.assertRaises(ValueError):
            m.fit_retrieval([self.ex(role="L9_AUDIT_DEV")])

    def test_parameter_formulas_are_exact_and_below_ceiling(self):
        self.assertEqual(m.expected_gru_parameters(),433795)
        self.assertEqual(m.expected_transformer_parameters(),449251)
        self.assertLessEqual(m.expected_gru_parameters(),m.PARAMETER_CEILING)
        self.assertLessEqual(m.expected_transformer_parameters(),m.PARAMETER_CEILING)

    def test_frozen_grids_and_seeds(self):
        self.assertEqual(m.MANDATORY_SEEDS,(1701,1702))
        self.assertEqual(m.CHECKPOINT_EPOCHS,(4,8,12))
        self.assertEqual(len(m.CANDIDATE_GRID),8)
        self.assertTrue(all(x.min_template_support in (1,2) for x in m.CANDIDATE_GRID))
        self.assertTrue(all(x.max_templates_per_predicate in (4,8) for x in m.CANDIDATE_GRID))
        self.assertTrue(all(x.joiner in (" ","; ") for x in m.CANDIDATE_GRID))

    def test_selection_is_select_only_and_requires_both_seeds(self):
        rows=[]
        for seed in m.MANDATORY_SEEDS:
            for epoch in m.CHECKPOINT_EPOCHS:
                rows.append(m.CheckpointMetric("L9_SELECT",seed,epoch,0.5+epoch/100,0.2,1,1000+epoch))
        chosen=m.choose_checkpoint(rows)
        self.assertEqual(chosen,{1701:12,1702:12})
        rows[0]=m.dataclasses.replace(rows[0],role="L9_AUDIT_DEV")
        with self.assertRaises(ValueError):
            m.choose_checkpoint(rows)

    def test_audit_guard(self):
        m.assert_audit_not_used([self.ex(role="L9_TRAIN")])
        with self.assertRaises(ValueError):
            m.assert_audit_not_used([self.ex(role="L9_AUDIT_DEV")])

    def test_contract_constants_match_file(self):
        contract=json.load(open("L9_MODEL_CONTRACT.json","r",encoding="utf-8"))
        self.assertEqual(contract["shared_representation"]["tokenizer"]["vocab_size"],m.VOCAB_SIZE)
        self.assertEqual(contract["resource_ceiling"]["trainable_parameters_max"],m.PARAMETER_CEILING)
        self.assertEqual(tuple(contract["common_training"]["mandatory_training_seeds"]),m.MANDATORY_SEEDS)
        self.assertEqual(tuple(contract["common_training"]["selected_checkpoint_epochs"]),m.CHECKPOINT_EPOCHS)

if __name__=="__main__":
    unittest.main()
