"""Adversarial source-only tests for the L9 audit first-use boundary."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import l9_audit_firstuse_prefit as gate

ROOT=Path(__file__).resolve().parent


class AuditFirstUsePrefitTests(unittest.TestCase):
    def plan(self):
        return json.loads((ROOT/gate.PLAN_FILE).read_text())

    def fake_seal(self):
        rows=[]
        for (arm,seed),chk in gate.EXPECTED_SELECTED.items():
            rows.append({
                "arm":arm,"seed":seed,"selected_epoch":12,
                "all_epoch_checkpoint_sha256":{"12":chk},
                **({"checkpoint_sha256":chk} if arm=="GRU_SEQ2SEQ"
                   else {"selected_checkpoint_sha256":chk,
                         "original_v1_select_outcome":"CANCELLED_90M_NO_RECEIPT"}),
                "receipt_type":("ORIGINAL_FROZEN_V1" if arm=="GRU_SEQ2SEQ"
                    else "SEPARATELY_QUALIFIED_RECOVERY_V2_NOT_V1")})
        return {
            "schema":"forge.optimizer.language.l9.mixed-gru-v1-transformer-v2-select-seal-v1",
            "status":"FOUR_CHOICE_MIXED_V1_GRU_V2_TRANSFORMER_DEV_SEALED",
            "source_role_sha256":gate.ROLE_SHA,
            "model_suite_git_blob":gate.SOURCE_GIT_BLOBS["l9_model_suite.py"],
            "all_four_choices_complete":True,
            "original_v1_select_seal_complete":False,
            "audit_dev_references_consumed":False,
            "official_test_consumed":False,"scientific_go":False,
            "neural_checkpoint_selection":rows,
            "candidate":{"selected_config":{
                "min_template_support":1,"max_templates_per_predicate":4,"joiner":" "}},
        }

    def synthetic_seal(self):
        return (json.dumps(self.fake_seal(),sort_keys=True,separators=(",",":"))+"\n").encode()

    def test_exact_frozen_source_blobs(self):
        result=gate.verify_frozen_sources(ROOT)
        self.assertEqual(result,gate.SOURCE_GIT_BLOBS)

    def test_actual_plan_immutable_boundaries(self):
        result=gate.check_plan(self.plan(),ROOT)
        self.assertEqual(result["audit_count"],319)
        self.assertEqual(result["heldout_categories"],3)
        self.assertEqual(result["method_count"],7)
        self.assertEqual(result["train_audit_graph_overlap"],0)
        self.assertFalse(result["first_use_authorized"])

    def test_plan_tampering_hard_rejections(self):
        edits=[
            lambda d:d["fixed_methods"].pop(),
            lambda d:d["fixed_methods"].append(d["fixed_methods"][0]),
            lambda d:d["source_custody"].update({"expected_audit_dev":318}),
            lambda d:d["source_custody"].update({"expected_heldout_categories":2}),
            lambda d:d["source_custody"].update({"expected_train_audit_graph_overlap":1}),
            lambda d:d["source_custody"].update({"quarantined_train_records":0}),
            lambda d:d["source_custody"].update({"role_identity_sha256":"a"*64}),
            lambda d:d["source_custody"].update({"test_tree_content_read":True}),
            lambda d:d["frozen_select"].update({"mixed_select_seal_sha256":"f"*64}),
            lambda d:d["frozen_select"].update({"original_v1_transformer_select_success":True}),
            lambda d:d["semantic_controls"].update({"macro_average_each_category_equal_weight":False}),
            lambda d:d["semantic_controls"].update({"abstention_zero_coverage_include_all_denominators":False}),
            lambda d:d["semantic_controls"].update({"no_category_or_seed_dropping":False}),
            lambda d:d["semantic_controls"].update({"candidate_no_canonical_facts_fallback":False}),
            lambda d:d["metrics_required"]["per_heldout_category"].remove("multireference_chrF"),
            lambda d:d["metrics_required"]["whole_audit"].remove("energy_or_NOT_MEASURED"),
            lambda d:d["first_use"].update({"current_authorized_protected_first_use":True}),
            lambda d:d["first_use"].update({"audit_reference_bytes_read_in_this_gate":1}),
            lambda d:d["first_use"].update({"official_test_content_allowed":True}),
            lambda d:d["first_use"].update({"scientific_go":True}),
            lambda d:d["advancement"].update({"automated_scientific_go_from_this_contract":True}),
        ]
        for i,edit in enumerate(edits):
            with self.subTest(negative=i):
                value=self.plan();edit(value)
                with self.assertRaises(ValueError):
                    gate.check_plan(value,ROOT)

    def test_synthetic_complete_category_macro_equal_weights(self):
        categories=("FAKE_A","FAKE_B","FAKE_C")
        rows=[]
        for method in gate.METHODS:
            rows.extend((
                {"category":"FAKE_A","method":method,"total":1,"hit":1,"abstentions":0},
                {"category":"FAKE_B","method":method,"total":9,"hit":0,"abstentions":9},
                {"category":"FAKE_C","method":method,"total":10,"hit":0,"abstentions":10}))
        score=gate.per_category_macro(rows,categories)
        self.assertTrue(all(abs(v-1/3)<1e-8 for v in score.values()))
        self.assertNotAlmostEqual(next(iter(score.values())),1/20)

    def test_synthetic_missing_method_and_category_fail(self):
        c=("A","B","C")
        rows=[{"category":cat,"method":method,"total":3,"hit":0,"abstentions":3}
              for cat in c for method in gate.METHODS]
        self.assertEqual(set(gate.per_category_macro(rows,c)),set(gate.METHODS))
        negatives=[
            rows[:-1],rows+[rows[0]],
            [dict(x,abstentions=3,hit=1) if i==0 else x for i,x in enumerate(rows)],
            [dict(x,total=0) if i==0 else x for i,x in enumerate(rows)],
            [dict(x,category="AUDIT_DEV_REAL") if i==0 else x for i,x in enumerate(rows)],
        ]
        for i,value in enumerate(negatives):
            with self.subTest(negative=i),self.assertRaises(ValueError):
                gate.per_category_macro(value,c)
        with self.assertRaises(ValueError):
            gate.per_category_macro(rows,("A","B","B"))

    def test_v2_seal_requires_exact_identity_and_no_first_use(self):
        raw=self.synthetic_seal()
        with patch.object(gate,"SEALED_SHA",gate.sha(raw)):
            result=gate.check_mixed_seal(raw)
            self.assertEqual(result["selected_models"],4)
            self.assertEqual(result["separate_v2_transformer_seeds"],2)
        with self.assertRaisesRegex(ValueError,"ORIGINAL_MIXED_SEAL_SHA"):
            gate.check_mixed_seal(raw)
        tweaks=[
            lambda d:d.update({"schema":"forge.optimizer.language.l9.select-seal-development-v1"}),
            lambda d:d.update({"scientific_go":True}),
            lambda d:d.update({"audit_dev_references_consumed":True}),
            lambda d:d.update({"original_v1_select_seal_complete":True}),
            lambda d:d["neural_checkpoint_selection"].pop(),
            lambda d:d["neural_checkpoint_selection"][0].update({"selected_epoch":8}),
            lambda d:d["neural_checkpoint_selection"][0].update({"checkpoint_sha256":"f"*64}),
            lambda d:d["neural_checkpoint_selection"][2].update({"receipt_type":"ORIGINAL_FROZEN_V1"}),
            lambda d:d["neural_checkpoint_selection"][3].update({"seed":1701}),
            lambda d:d["candidate"]["selected_config"].update({"min_template_support":2}),
        ]
        for i,edit in enumerate(tweaks):
            d=self.fake_seal();edit(d)
            data=(json.dumps(d,sort_keys=True,separators=(",",":"))+"\n").encode()
            with self.subTest(negative=i),patch.object(gate,"SEALED_SHA",gate.sha(data)):
                with self.assertRaises(ValueError):
                    gate.check_mixed_seal(data)

    def test_outfile_no_overwrite_and_fail_before_first_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"receipt.json"
            raw=self.synthetic_seal()
            with self.assertRaisesRegex(ValueError,"ORIGINAL_MIXED_SEAL_SHA"):
                gate.evaluate_source_only(ROOT,raw,out=output)
            self.assertFalse(output.exists())
            output.write_text("{}")
            with self.assertRaisesRegex(ValueError,"REFUSE_RECEIPT_OVERWRITE"):
                gate.evaluate_source_only(ROOT,raw,out=output)
            self.assertEqual(output.read_text(),"{}")

    def test_no_audit_loader_in_current_execution_module(self):
        source=(ROOT/"l9_audit_firstuse_prefit.py").read_text()
        for forbidden in ("load_audit(", "load_train_select(", "torch.load(",
                          "import torch","git clone","cat-file",
                          "requests.","subprocess.","urlopen("):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
