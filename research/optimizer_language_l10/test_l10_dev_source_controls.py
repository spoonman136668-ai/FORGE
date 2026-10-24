"""L10-B adversarial development source custody and matched comparators.

No L9/WebNLG examples and no prospectively reserved heldout source families.
"""
import copy
from dataclasses import replace
import json
import unittest
import l10_semantic_dev_oracle as oracle
import l10_dev_source_custody as source
import l10_dev_matched_controls as control

class CustodyAndControls(unittest.TestCase):
    def test_exact_development_grid_and_hash_determinism(self):
        a=source.development_collection()
        b=source.development_collection()
        self.assertEqual(len(a),24)
        self.assertEqual([x.fixture_sha256 for x in a],[x.fixture_sha256 for x in b])
        self.assertEqual(len(set(x.fixture_sha256 for x in a)),24)
        self.assertEqual(len(set(x.target.source_identity_sha256 for x in a)),24)
        self.assertEqual(sum(x.split=="DEV_FIT" for x in a),12)
        self.assertEqual(sum(x.split=="DEV_CHECK" for x in a),12)
        self.assertTrue(all(x.role=="L10_SYNTHETIC_DEV" for x in a))
        self.assertTrue(source.validate_collection(a,"KNOWN_MAPPING"))
    def test_fresh_holdout_seeds_roles_and_family_names_unavailable(self):
        invalid=[
            ("dev-bindings",source.PROSPECTIVE_ROLE,0,"KNOWN_MAPPING"),
            ("L10_PROSPECTIVE_NEW_SOURCE_FAMILY","DEV_CHECK",0,"KNOWN_MAPPING"),
            ("dev-bindings","DEV_CHECK",0,"PROSPECTIVE_MAPPING"),
            ("new-world-episode","DEV_CHECK",0,"KNOWN_MAPPING"),
            ("dev-bindings","DEV_CHECK",-1,"KNOWN_MAPPING"),
            ("dev-bindings","DEV_CHECK",4,"KNOWN_MAPPING"),
        ]
        for args in invalid:
            with self.subTest(args=args),self.assertRaises(ValueError):
                source.make_dev_fixture(*args)
        self.assertFalse(hasattr(source,"PROSPECTIVE_SEED"))
    def test_same_truth_across_public_and_withheld_exposure_with_distinct_commitments(self):
        known=source.make_dev_fixture("dev-compositions","DEV_CHECK",0,"KNOWN_MAPPING")
        hidden=source.make_dev_fixture("dev-compositions","DEV_CHECK",0,"WITHHELD_MAPPING")
        self.assertEqual(known.target.source_identity_sha256,hidden.target.source_identity_sha256)
        self.assertNotEqual(known.fixture_sha256,hidden.fixture_sha256)
        self.assertEqual(known.input.observed,hidden.input.observed)
        self.assertEqual(known.input.public_lexicon,source.PREDICATE_LEXICON)
        self.assertEqual(hidden.input.public_lexicon,())
        self.assertEqual(control.canonical_facts(hidden.input),None)
        self.assertEqual(control.rule_paraphrase(hidden.input),None)
    def test_source_id_and_mapping_changes_fail_closed(self):
        f=source.make_dev_fixture("dev-negation","DEV_FIT",1,"KNOWN_MAPPING")
        for change in (
            {"fixture_sha256":"f"*64},
            {"role":source.PROSPECTIVE_ROLE},
            {"split":"DEV_AUDIT"},
            {"family":"alien-family"},
            {"target":replace(f.target,source_identity_sha256="0"*64)},
            {"input":replace(f.input,public_lexicon=())},
            {"input":replace(f.input,information_regime="WITHHELD_MAPPING")},
        ):
            with self.subTest(change=change),self.assertRaises(ValueError):
                source.validate_fixture(replace(f,**change))
    def test_source_deduplication_missing_family_or_exposure_drift_rejected(self):
        rows=source.development_collection()
        for altered in (rows[:-1],rows[:-1]+[rows[0]],
                        [replace(f,input=replace(f.input,public_lexicon=()))
                         if i==0 else f for i,f in enumerate(rows)]):
            with self.assertRaises(ValueError):
                source.validate_collection(altered,"KNOWN_MAPPING")
    def test_numeric_manifest_cannot_expose_generated_entities_or_targets(self):
        rows=source.development_collection()
        manifest=source.manifest_only(rows,"KNOWN_MAPPING")
        s=json.dumps(manifest)
        self.assertEqual(manifest["prospective_examples_generated"],0)
        self.assertEqual(manifest["fixtures"],24)
        self.assertFalse(manifest["scientific_go"])
        for token in ("AsterF0","BorealF","target","source_graph","raw_reference","DEV_CHECKI"):
            self.assertNotIn(token,s)
        self.assertEqual(len(manifest["rows"]),24)
    def test_known_mapping_canonical_ceiling_rule_and_shuffled_control(self):
        f=source.make_dev_fixture("dev-polarity","DEV_CHECK",3,"KNOWN_MAPPING")
        inputs=source.public_input(f)
        p=control.canonical_facts(inputs)
        r=control.rule_paraphrase(inputs)
        wrong=control.flip_polarity(inputs)
        self.assertEqual(oracle.evaluate_one(f.target,p)["exact_semantic_graph_success"],1)
        self.assertEqual(oracle.evaluate_one(f.target,r)["exact_semantic_graph_success"],1)
        self.assertEqual(oracle.evaluate_one(f.target,wrong)["exact_semantic_graph_success"],0)
        self.assertGreater(oracle.evaluate_one(f.target,wrong)["contradictory_claims"],0)
    def test_train_fit_rejects_development_check_or_duplicate(self):
        rows=source.development_collection()
        with self.assertRaises(ValueError):control.freeze_fit([r for r in rows if r.split=="DEV_CHECK"])
        with self.assertRaises(ValueError):control.freeze_fit([rows[0],rows[0]])
        fitted=[r for r in rows if r.split=="DEV_FIT"]
        state,n=control.freeze_fit(fitted)
        self.assertEqual(len(state),12)
        self.assertGreater(n,0)
        self.assertFalse(any(r.target.source_identity_sha256 in str(state) for r in rows))
    def test_matched_all_seven_comparators_same_observed_input_and_full_denominators(self):
        rows=source.development_collection()
        candidate_seen=[]
        def candidate(observed):
            self.assertIs(type(observed),source.ModelInput)
            self.assertFalse(hasattr(observed,"target"))
            self.assertFalse(hasattr(observed,"reference"))
            candidate_seen.append(control.signature(observed))
            return None
        fit=[x for x in rows if x.split=="DEV_FIT"]
        controls=control.make_controls(fit,candidate)
        self.assertEqual(tuple(x.name for x in controls),control.ARMS)
        result=control.benchmark_dev(rows,controls,"KNOWN_MAPPING")
        self.assertEqual(result["method_count"],7)
        self.assertEqual(len(candidate_seen),12)
        self.assertEqual(len(set(candidate_seen)),12)
        self.assertEqual(result["methods"][0]["micro_exact_rate"],1)
        self.assertEqual(result["methods"][1]["micro_exact_rate"],1)
        self.assertEqual(result["methods"][4]["micro_exact_rate"],0)
        self.assertEqual(result["methods"][5]["micro_exact_rate"],0)
        self.assertEqual(result["methods"][6]["micro_exact_rate"],0)
        self.assertTrue(all(x["evaluation_examples"]==12 and x["fit_examples"]==12
                            for x in result["methods"]))
        self.assertTrue(all(x["serialized_fitted_state_bytes"]>=0 for x in result["methods"]))
        self.assertFalse(result["scientific_go"])
        self.assertFalse(result["l9_audit_reused"])
    def test_information_insufficient_case_never_falsely_succeeds(self):
        rows=source.development_collection("WITHHELD_MAPPING")
        controls=control.make_controls([r for r in rows if r.split=="DEV_FIT"],lambda _:None)
        result=control.benchmark_dev(rows,controls,"WITHHELD_MAPPING")
        self.assertTrue(all(a["micro_exact_rate"]==0 for a in result["methods"]))
        self.assertEqual(result["methods"][0]["micro_exact_rate"],0)
        self.assertEqual(result["methods"][1]["micro_exact_rate"],0)
        self.assertEqual(result["prospective_source_examples_consumed"],0)
    def test_absent_candidate_or_missing_control_blocks(self):
        rows=source.development_collection()
        fit=[r for r in rows if r.split=="DEV_FIT"]
        with self.assertRaises(ValueError):control.make_controls(fit,None)
        controls=control.make_controls(fit,lambda _:None)
        with self.assertRaises(ValueError):control.benchmark_dev(rows,controls[:-1],"KNOWN_MAPPING")
        with self.assertRaises(ValueError):control.benchmark_dev(rows,controls[::-1],"KNOWN_MAPPING")
    def test_model_interfaces_not_allowed_to_observe_unauthorized_mapping(self):
        row=source.make_dev_fixture("dev-bindings","DEV_CHECK",2,"WITHHELD_MAPPING")
        leaked=replace(row.input,public_lexicon=source.PREDICATE_LEXICON)
        for fn in (control.canonical_facts,control.rule_paraphrase,control.flip_polarity):
            with self.subTest(fn=fn),self.assertRaises(ValueError):
                fn(leaked)
    def test_output_oracle_stays_strict_on_swapped_entity_roles_and_unsupported(self):
        row=source.make_dev_fixture("dev-bindings","DEV_CHECK",3,"KNOWN_MAPPING")
        x=source.public_input(row)
        cl=x.observed[0]
        wrong=source.ModelInput(
            (source.Observed(cl.object,cl.relation_code,cl.subject,cl.polarity),),
            x.public_lexicon,x.information_regime)
        self.assertEqual(oracle.evaluate_one(row.target,control.canonical_facts(wrong))["exact_semantic_graph_success"],0)
    def test_no_uncertified_prospective_source_evaluation_support(self):
        self.assertFalse(hasattr(source,"generate_prospective"))
        self.assertFalse(hasattr(control,"evaluate_prospective"))
        self.assertEqual(source.PROSPECTIVE_ROLE,"L10_PROSPECTIVE_NEW_SOURCE_FAMILY")
        self.assertEqual(control.OBS,"DEVELOPMENT_ONLY_NOT_PROSPECTIVE_SCIENTIFIC_EVIDENCE")

if __name__=="__main__":
    unittest.main()
