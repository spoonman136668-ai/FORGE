"""L10-B3 strict DEV_FIT supervision, learned-state and matched controls.

All data invented development fixtures. No WebNLG, L9, prospective examples,
external models or paid services.
"""
from dataclasses import replace
import json
import unittest

import l10_dev_source_custody as source
import l10_dev_matched_controls as control
import l10_devfit_template_candidate as trained
import l10_semantic_dev_oracle as oracle

def known():
    return source.development_collection("KNOWN_MAPPING")
def fitted(rows=None):
    d=known() if rows is None else rows
    return trained.fit_dev_only([x for x in d if x.split=="DEV_FIT"])

class CandidateTests(unittest.TestCase):
    def test_repeat_training_state_hash_and_frozen_source_custody(self):
        rows=known()
        a=fitted(rows)
        b=trained.fit_dev_only(list(reversed([x for x in rows if x.split=="DEV_FIT"])))
        self.assertEqual(a.state_sha256,b.state_sha256)
        self.assertEqual(a.fit_sources_sha256,b.fit_sources_sha256)
        self.assertEqual(a.templates,b.templates)
        self.assertGreater(a.state_bytes,0)
        self.assertTrue(trained.validate_state(a))
        self.assertEqual(a.fit_role,"L10_SYNTHETIC_DEV")
        self.assertEqual(a.fit_split,"DEV_FIT")
        self.assertEqual(a.supervision,trained.SUPERVISION)

    def test_supervised_training_only_then_source_only_inference(self):
        rows=known()
        model=fitted(rows)
        for row in rows:
            if row.split!="DEV_FIT":continue
            result=trained.infer(model,source.public_input(row))
            self.assertIs(type(result),str)
            self.assertEqual(oracle.evaluate_one(row.target,result)["exact_semantic_graph_success"],1)
        for row in rows:
            if row.split=="DEV_CHECK":
                observed=source.public_input(row)
                self.assertFalse(hasattr(observed,"target"))
                self.assertFalse(hasattr(observed,"reference"))
                outcome=trained.infer(model,observed)
                check=oracle.evaluate_one(row.target,outcome)
                self.assertIn(check["exact_semantic_graph_success"],(0,1))
                if outcome is None:
                    self.assertEqual(check["abstentions"],1)

    def test_train_on_check_or_heldout_fails_closed(self):
        rows=known()
        only_fit=[x for x in rows if x.split=="DEV_FIT"]
        forbidden=[x for x in rows if x.split=="DEV_CHECK"]
        for attempt in (only_fit+forbidden[:1],forbidden[:12],
                        only_fit[:-1],only_fit[:-1]+only_fit[:1]):
            with self.subTest(n=len(attempt)),self.assertRaises(ValueError):
                trained.fit_dev_only(attempt)
        modified=replace(only_fit[0],role=source.PROSPECTIVE_ROLE)
        with self.assertRaises(ValueError):
            trained.fit_dev_only([modified]+only_fit[1:])

    def test_no_mapping_no_semantic_invention(self):
        x=source.development_collection("WITHHELD_MAPPING")
        model=trained.fit_dev_only([z for z in x if z.split=="DEV_FIT"])
        self.assertEqual(model.templates,())
        self.assertEqual(model.supervision,"NO_SEMANTIC_SUPERVISION")
        for z in x:
            if z.split=="DEV_CHECK":
                self.assertIsNone(trained.infer(model,source.public_input(z)))
        with self.assertRaises(ValueError):
            trained.infer(model,source.public_input(known()[0]))

    def test_unknown_relation_or_missing_template_causes_whole_graph_abstention(self):
        state=fitted()
        check=[z for z in known() if z.split=="DEV_CHECK"]
        example=check[0]
        first=example.input.observed[0]
        key=f"{first.relation_code}:{first.polarity}"
        filtered=tuple((k,v) for k,v in state.templates if k!=key)
        body=trained.canonical_body(state.regime,state.fit_sources_sha256,filtered)
        raw=source.canonical_bytes(body)
        from hashlib import sha256
        corrupt=replace(state,templates=filtered,state_sha256=sha256(raw).hexdigest(),state_bytes=len(raw))
        self.assertTrue(trained.validate_state(corrupt))
        self.assertIsNone(trained.infer(corrupt,source.public_input(example)))

    def test_content_addressed_state_fails_on_tampering(self):
        state=fitted()
        for change in ({"state_sha256":"0"*64},{"state_bytes":0},
                       {"fit_sources_sha256":"f"*64},
                       {"supervision":"UNSUPERVISED_COGNITION"},
                       {"fit_role":"L10_PROSPECTIVE_NEW_SOURCE_FAMILY"},
                       {"fit_split":"DEV_CHECK"}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                trained.validate_state(replace(state,**change))
        if state.templates:
            key,template=state.templates[0]
            with self.assertRaises(ValueError):
                trained.validate_state(replace(state,templates=((key,template+" unrelated"),)+state.templates[1:]))

    def test_fit_state_never_contains_raw_names_or_reference_text(self):
        state=fitted()
        receipt=trained.state_only_receipt(state)
        encoded=json.dumps(receipt,sort_keys=True)
        self.assertEqual(receipt["prospective_examples_exposed"],0)
        self.assertFalse(receipt["scientific_go"])
        self.assertFalse(receipt["output_text_saved"])
        for entity in ("AsterF","BorealF","JunoF","Aster resides","DEV_CHECKI"):
            self.assertNotIn(entity,encoded)
        blob=source.canonical_bytes(trained.canonical_body(state.regime,state.fit_sources_sha256,state.templates))
        self.assertNotIn(b"AsterF",blob)
        self.assertNotIn(b"F0S0I",blob)
        self.assertNotIn(b"F1S0I",blob)

    def test_candidate_is_real_fitted_callback_on_same_dev_inputs(self):
        rows=known()
        state=fitted(rows)
        fit=[x for x in rows if x.split=="DEV_FIT"]
        method=control.make_controls(fit,lambda inp:trained.infer(state,inp))
        candidate=method[-1]
        method[-1]=replace(candidate,fitted_state_bytes=state.state_bytes,
                         fit_wall_seconds=state.fit_wall_seconds,fit_cpu_seconds=state.fit_cpu_seconds)
        out=control.benchmark_dev(rows,method,"KNOWN_MAPPING")
        self.assertEqual(out["methods"][0]["micro_exact_rate"],1.)
        self.assertEqual(out["methods"][1]["micro_exact_rate"],1.)
        self.assertLessEqual(out["methods"][-1]["micro_exact_rate"],1.)
        self.assertEqual(out["methods"][-1]["serialized_fitted_state_bytes"],state.state_bytes)
        self.assertEqual(out["methods"][-1]["fit_examples"],12)
        self.assertEqual(out["methods"][-1]["evaluation_examples"],12)
        self.assertEqual(out["methods"][-1]["flops"],"NOT_MEASURED")
        self.assertFalse(out["scientific_go"])
        self.assertEqual(out["prospective_source_examples_consumed"],0)

    def test_abstention_counted_full_denominator_under_unknown_fit(self):
        rows=source.development_collection("WITHHELD_MAPPING")
        model=trained.fit_dev_only([x for x in rows if x.split=="DEV_FIT"])
        fit=[x for x in rows if x.split=="DEV_FIT"]
        methods=control.make_controls(fit,lambda inp:trained.infer(model,inp))
        candidate=methods[-1]
        methods[-1]=replace(candidate,fitted_state_bytes=model.state_bytes,
                            fit_wall_seconds=model.fit_wall_seconds,fit_cpu_seconds=model.fit_cpu_seconds)
        summary=control.benchmark_dev(rows,methods,"WITHHELD_MAPPING")
        c=summary["methods"][-1]
        self.assertEqual(c["micro_exact_rate"],0)
        self.assertEqual(sum(f["abstentions"] for f in c["family_metrics"]),12)

    def test_unknown_source_families_not_generatable_by_this_candidate(self):
        self.assertFalse(hasattr(trained,"generate_prospective"))
        self.assertFalse(hasattr(trained,"L9_AUDIT_DEV"))
        self.assertEqual(trained.FIT_SPLIT,"DEV_FIT")

if __name__=="__main__":
    unittest.main()
