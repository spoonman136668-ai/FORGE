"""Synthetic adversarial qualification of the independent L9 numerical verifier.

Constructs invented numerical receipts; NEVER reads WebNLG or neural weights.
"""
import copy
import json
import unittest
import l9_independent_numeric_evidence as v

def fake_case(category_id,n):
    d=n*2
    return dict(
        category_sha256=category_id,examples=n,triples=d,
        triple_proxy_hits=n,triple_denominator=d,missing_triples_proxy=n,
        requested_content_proxy_coverage=.5,
        entity_slot_hits=2*n,entity_slot_denominator=2*d,
        normalized_entity_slot_coverage=.5,
        abstentions=0,reference_count=n*2,reference_bytes=n*30,
        chrF_all_references_mean_per_example=.4,
        token_f1_all_references_mean_per_example=.3,
        negation_marker_examples=0,extra_train_entity_mentions=0,
        terminal_punctuation_examples=n,unresolved_placeholder_examples=0,
        repeated_adjacent_token_count=0)
def fake_arm(method):
    rows=[fake_case(k,n) for k,n in sorted(v.CATEGORIES.items())]
    return dict(schema=v.ARM_SCHEMA,
        status="NUMERICAL_PROXIES_ONLY_NOT_INDEPENDENT_SEMANTIC_GO",
        arm=method,source_role_sha256=v.ROLE,
        frozen_model_suite_git_blob=v.SUITE,
        role="L9_AUDIT_DEV",categories=rows,
        macro_by_heldout_category={k:{"requested_content_proxy_coverage":.5,
            "normalized_entity_slot_coverage":.5,
            "chrF_all_references_mean_per_example":.4,
            "token_f1_all_references_mean_per_example":.3}[k] for k in v.METRICS},
        micro_requested_content_proxy_coverage=.5,records=319,triple_denominator=638,
        serial_wall_seconds=1.,serial_cpu_seconds=.7,
        resource_flops="NOT_MEASURED",resource_energy="NOT_MEASURED",
        all_original_references_scored=True,model_reference_input_count=0,
        reference_contents_saved=False,raw_outputs_saved=False,
        official_test_consumed=False,scientific_go=False)
def fake():
    return dict(schema=v.BUNDLE_SCHEMA,status="UNFAMILIAR_AUDIT_NUMERIC_FIRST_USE_NOT_SEMANTIC_GO",
        source_role_sha256=v.ROLE,model_suite_git_blob=v.SUITE,
        arm_count=7,heldout_categories=3,heldout_examples=319,
        arms=[fake_arm(arm) for arm in v.METHODS],
        official_test_consumed=False,scientific_go=False,
        one_shot_schema=v.RUN_SCHEMA,selected_checkpoint_epoch=12,
        pre_admission_sha256=v.PRE,development_select_seal_sha256=v.SELECT,
        trained_candidate_state_sha256=v.CAND,trained_retrieval_state_sha256=v.RETR,
        selected_checkpoint_sha256=v.CHECKPOINTS,
        reconstructed_train_fit_wall_seconds=5.,
        reconstructed_train_fit_cpu_seconds=4.,
        model_load_and_graph_custody_wall_seconds=2.,
        all_seven_arms_prediction_wall_seconds=90.,
        reference_read_wall_seconds=3.,
        total_pipeline_wall_seconds=101.,
        total_pipeline_cpu_seconds=90.,
        python_peak_traced_bytes=123456,resource_energy="NOT_MEASURED",
        resource_flops="NOT_MEASURED",source_reference_leakage_to_model=False,
        all_seven_methods_completed_before_any_reference_access=True,
        all_original_references_averaged_per_example=True,
        additional_entity_mentions_inferred_from_train_vocabulary="NOT_MEASURED",
        audit_reference_read_count=319,independent_semantic_adjudication_complete=False)

class IndependentVerificationTests(unittest.TestCase):
    def check(self,data):
        return v.verify(v.canonical(data))
    def test_positive_invented_numeric_data_does_not_claim_go(self):
        d=self.check(fake())
        self.assertEqual(d["status"],"VERIFIED_NUMERIC_RECEIPT_NOT_INDEPENDENT_SEMANTIC_VALIDATION")
        self.assertFalse(d["scientific_go"])
        self.assertTrue(d["no_new_audit_read"])
        self.assertEqual(d["category_example_counts"],[31,153,135])
    def test_authentic_frozen_source_label_order_valid_but_cross_arm_reordering_fails(self):
        # Source rows are label-sorted; hashed identifiers are not hash-sorted.
        # This test reproduces the independently authenticated source order,
        # without touching actual references or first-use models.
        order=["ccc9ff052aee8da1c7d607bee2283e981bd0bdce2de409fe3789ada64e20e080",
               "70b1e8e06785cae451496104850781f33faf6cc8e0777ecd3a9ccaaefb154b2d",
               "6c58160fe1935610171c4ef8e12c2fcb96cbb168db852a927e968b8dda7b0e11"]
        d=fake()
        for arm in d["arms"]:
            by_hash={r["category_sha256"]:r for r in arm["categories"]}
            arm["categories"]=[by_hash[k] for k in order]
        self.assertEqual(self.check(d)["heldout_examples"],319)
        d["arms"][-1]["categories"].reverse()
        with self.assertRaisesRegex(ValueError,"cross-arm category order drift"):
            self.check(d)

    def test_unrecognized_raw_source_fields_rejected(self):
        for target in ("top","arm","category"):
            d=fake()
            if target=="top":d["raw_reference"]="DO_NOT_SAVE"
            if target=="arm":d["arms"][0]["predictions"]="DO_NOT_SAVE"
            if target=="category":d["arms"][1]["categories"][0]["original_graph"]="DO_NOT_SAVE"
            with self.subTest(target=target),self.assertRaises(ValueError):
                self.check(d)
    def test_role_model_and_selection_drift_rejected(self):
        for key,bad in (
            ("source_role_sha256","x"*64),("trained_candidate_state_sha256","x"*64),
            ("trained_retrieval_state_sha256","x"*64),
            ("pre_admission_sha256","x"*64),
            ("selected_checkpoint_epoch",8),
            ("audit_reference_read_count",318),
            ("scientific_go",True),
            ("official_test_consumed",True),
            ("source_reference_leakage_to_model",True),
            ("independent_semantic_adjudication_complete",True),
            ("selected_checkpoint_sha256",{})):
            d=fake();d[key]=bad
            with self.subTest(field=key),self.assertRaises(ValueError):
                self.check(d)
    def test_missing_duplicate_and_reordered_arms_rejected(self):
        for kind in ("missing","duplicate","reorder"):
            d=fake()
            if kind=="missing":d["arms"].pop()
            if kind=="duplicate":d["arms"][-1]=copy.deepcopy(d["arms"][0])
            if kind=="reorder":d["arms"][0],d["arms"][1]=d["arms"][1],d["arms"][0]
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.check(d)
    def test_all_three_frozen_categories_and_counts_required(self):
        for kind in ("wrong_count","duplicate_category","missing_category","wrong_category"):
            d=fake();rows=d["arms"][0]["categories"]
            if kind=="wrong_count":rows[0]["examples"]-=1
            if kind=="duplicate_category":rows[1]["category_sha256"]=rows[0]["category_sha256"]
            if kind=="missing_category":rows.pop()
            if kind=="wrong_category":rows[0]["category_sha256"]="b"*64
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.check(d)
    def test_inconsistent_denominators_and_macro_micro_rejected(self):
        for key,val in (("triple_proxy_hits",2),("triple_denominator",5),
                        ("missing_triples_proxy",5),("reference_count",0),
                        ("entity_slot_denominator",1),("abstentions",1000)):
            d=fake();d["arms"][2]["categories"][0][key]=val
            with self.subTest(field=key),self.assertRaises(ValueError):self.check(d)
        for key in v.METRICS:
            d=fake();d["arms"][0]["macro_by_heldout_category"][key]=.05
            with self.subTest(macro=key),self.assertRaises(ValueError):self.check(d)
        d=fake();d["arms"][0]["micro_requested_content_proxy_coverage"]=.1
        with self.assertRaises(ValueError):self.check(d)
    def test_reference_inputs_or_mismatched_reference_population_rejected(self):
        d=fake();d["arms"][-1]["model_reference_input_count"]=1
        with self.assertRaises(ValueError):self.check(d)
        d=fake();d["arms"][-1]["categories"][0]["reference_bytes"]+=1
        with self.assertRaises(ValueError):self.check(d)
    def test_nan_inf_duplicate_keys_and_noncanonical_json_rejected(self):
        raw=v.canonical(fake())
        with self.assertRaises(ValueError):v.load_numeric_bytes(raw+b" \n")
        with self.assertRaises(ValueError):v.load_numeric_bytes(raw.replace(b'"arm_count":7',b'"arm_count":7,"arm_count":7',1))
        with self.assertRaises(ValueError):v.load_numeric_bytes(raw.replace(b'"arm_count":7',b'"arm_count":NaN',1))
        with self.assertRaises(ValueError):v.load_numeric_bytes(raw.replace(b'"arm_count":7',b'"arm_count":Infinity',1))
    def test_resource_finiteness_and_missing_measurement_marker_required(self):
        for k,val in (("python_peak_traced_bytes",-1),("total_pipeline_wall_seconds",float("nan")),
                      ("resource_flops",0),("resource_energy","ESTIMATE")):
            d=fake();d[k]=val
            with self.subTest(resource=k),self.assertRaises(ValueError):
                v.check(d)
    def test_metric_direction_is_non_adjudicative(self):
        d=fake()
        for r in d["arms"][2]["categories"]:
            r["triple_proxy_hits"]=r["triple_denominator"]
            r["missing_triples_proxy"]=0
            r["requested_content_proxy_coverage"]=1.
        d["arms"][2]["micro_requested_content_proxy_coverage"]=1.
        d["arms"][2]["macro_by_heldout_category"]["requested_content_proxy_coverage"]=1.
        x=self.check(d)
        self.assertEqual(x["candidate_vs_retrieval_macro_proxy_direction"],"CANDIDATE_PROXY_GREATER")
        self.assertFalse(x["scientific_go"])
if __name__=="__main__":unittest.main()
