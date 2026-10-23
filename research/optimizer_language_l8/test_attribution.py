"""L8 prospective fallback and factual-coverage attribution tests.

Tests exclusively the saved original E2E public train/dev files, and
trained frozen original L7 models. The official E2E test is not used.
"""
import hashlib
import os
from pathlib import Path
import unittest

from source import FILES,ROLES,COUNTS,load,cohorts,parse_mr,identity,canonical,digest
from l7_source_original import verify
from models import ARMS,AttributionRealizer,trace_constrained,canonical_facts
from runner import preregistration_guard,evaluate,token_f1,contains_other_known_values


class L8FrozenFallbackAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=os.environ.get("L8_RAW_CORPUS_DIRECTORY")
        if not folder:
            raise RuntimeError("L8_PINNED_E2E_ORIGINAL_SOURCE_UNAVAILABLE")
        cls.raw={n:(Path(folder)/n).read_bytes() for n in FILES}
        cls.sha,cls.new,cls.old=load(folder)

    def test_frozen_protocol_unchanged_native_science_and_arm_inventory(self):
        proto=preregistration_guard()
        self.assertEqual(proto["original_E2E"]["source_roles"],COUNTS)
        self.assertEqual(set(proto["methods"]),set(ARMS))
        self.assertIn("Q21 protected original/FSA/HELD scientific first-use",
                      proto["governance"]["unchanged"])
        self.assertIn("FORGE F139 and any current controller/custody changes",
                      proto["governance"]["unchanged"])

    def test_original_external_E2E_exact_immutable_raw_hashes(self):
        for name in FILES:
            self.assertEqual(len(self.raw[name]),FILES[name][0])
            self.assertEqual(verify(self.raw[name],name),self.sha[name])

    def test_one_byte_source_mutation_and_truncation_fail_closed(self):
        for name in FILES:
            blob=bytearray(self.raw[name])
            blob[125]^=1
            with self.assertRaisesRegex(ValueError,"GIT_BLOB_DRIFT"):
                verify(bytes(blob),name)
            with self.assertRaisesRegex(ValueError,"RAW_SIZE_DRIFT"):
                verify(self.raw[name][:-1],name)

    def test_same_frozen_original_L7_train_semantic_identity(self):
        self.assertEqual(len(self.new["L8_TRAIN"]),700)
        self.assertEqual(
            {identity(r["mr"]) for r in self.new["L8_TRAIN"]},
            {identity(r["mr"]) for r in self.old["L7_TRAIN"]})
        self.assertEqual(
            self.new["L8_TRAIN"],self.old["L7_TRAIN"])

    def test_new_public_SELECT_and_DEV_do_not_overlap_original_L7_180(self):
        spent={identity(r["mr"]) for r in
               self.old["L7_SELECT"]+self.old["L7_DEV"]}
        original={identity(r["mr"]) for r in self.old["L7_TRAIN"]}
        selected={identity(r["mr"]) for r in self.new["L8_AUDIT_SELECT"]}
        fresh={identity(r["mr"]) for r in self.new["L8_AUDIT_DEV"]}
        self.assertEqual(len(spent),180)
        self.assertEqual(len(selected),80)
        self.assertEqual(len(fresh),160)
        self.assertFalse(spent&selected or spent&fresh or original&fresh)
        self.assertFalse(selected&fresh)

    def test_public_role_sha_digests_deterministic_and_distinct(self):
        a,_=cohorts(self.raw["trainset.csv"],self.raw["devset.csv"])
        self.assertEqual({k:digest(v) for k,v in a.items()},
                         {k:digest(v) for k,v in self.new.items()})
        self.assertEqual(len({digest(v) for v in self.new.values()}),3)

    def test_delex_model_parity_against_original_train_only(self):
        fit=self.new["L8_TRAIN"][:40]
        source=self.new["L8_AUDIT_DEV"][:2]
        m=AttributionRealizer("DELEX_TEMPLATE",fit)
        cp=m.checkpoint()
        for row in source:
            text,info=m.predict(row["mr"])
            original,_=m.model.generate(row["mr"])
            self.assertEqual(text,original)
            self.assertIn(info["route"],
                          ("learned_pattern","reference_fallback"))
        self.assertEqual(cp,m.checkpoint())

    def test_original_constrained_output_and_attribution_reconcile(self):
        m=AttributionRealizer("CONSTRAINED_TEMPLATE",
                             self.new["L8_TRAIN"][:40])
        previous=m.checkpoint()
        for row in self.new["L8_AUDIT_DEV"][:3]:
            text,info=m.predict(row["mr"])
            original,_=m.model.generate(row["mr"])
            self.assertEqual(text,original)
            self.assertIn(info["route"],("learned_pattern","canonical_fallback"))
        self.assertEqual(previous,m.checkpoint())

    def test_synthetic_known_missing_required_placeholders_abstains(self):
        train=[{"mr":{"name":"The Eagle","near":"King's College"},
                "ref":"{{unused}} The Eagle is near King's College."}]
        m=AttributionRealizer("CONSTRAINED_TEMPLATE",train)
        no=AttributionRealizer("NO_FALLBACK_CONSTRAINED",train,
                             shared_constrained=m.model)
        inp={"food":"Italian"}
        original,meta=m.predict(inp)
        abstained,info=no.predict(inp)
        self.assertEqual(meta["route"],"canonical_fallback")
        self.assertEqual(original,canonical_facts(inp))
        self.assertIsNone(abstained)
        self.assertEqual(info["route"],"abstained")

    def test_no_fallback_shares_exact_model_optimizer_and_checkpoint(self):
        train=self.new["L8_TRAIN"][:40]
        constrained=AttributionRealizer("CONSTRAINED_TEMPLATE",train)
        no=AttributionRealizer("NO_FALLBACK_CONSTRAINED",train,
                             shared_constrained=constrained.model)
        self.assertIs(no.model,constrained.model)
        self.assertEqual(no.checkpoint(),constrained.checkpoint())

    def test_canonical_control_copies_full_training_visible_MR_slots(self):
        model=AttributionRealizer("CANONICAL_FACTS",self.new["L8_TRAIN"][:8])
        mr={"name":"Eagle","food":"Italian","customerRating":"5 of 5"}
        output,info=model.predict(mr)
        self.assertEqual(info["route"],"canonical_direct")
        for value in mr.values():
            self.assertIn(value,output)

    def test_unfilled_no_fallback_abstention_counts_as_zero_coverage(self):
        train=[{"mr":{"name":"The Eagle","near":"King's College"},
                "ref":"The Eagle is near King's College."}]
        model=AttributionRealizer("CONSTRAINED_TEMPLATE",train)
        no=AttributionRealizer("NO_FALLBACK_CONSTRAINED",train,
                             shared_constrained=model.model)
        examples=[{"mr":{"food":"Italian"},"ref":"Italian food."}]
        inv={k:set() for k in ("name","near","food","area")}
        report=evaluate(no,examples,inv)
        self.assertEqual(report["records"],1)
        self.assertEqual(report["abstention_count"],1)
        self.assertEqual(report["five_literal_exact_copy_hits"],0)
        self.assertEqual(report["five_literal_copy_rate_with_abstention_zero"],0.)
        self.assertEqual(report["reference_token_F1_one_human_ref_NOT_fluency"],0.)

    def test_possible_conflicting_train_entity_not_adjudicated_semantics(self):
        inventory={"name":{"The Eagle","The Plough"},"near":set(),
                   "food":set(),"area":set()}
        observed=contains_other_known_values(
            "The Plough has a menu.",{"name":"The Eagle"},inventory)
        self.assertEqual(observed,1)
        observed=contains_other_known_values(
            "The Eagle has a menu.",{"name":"The Eagle"},inventory)
        self.assertEqual(observed,0)

    def test_human_reference_F1_proxy_not_fluency_or_entailment(self):
        self.assertEqual(token_f1("the eagle is near town","the eagle is near town"),1.)
        self.assertEqual(token_f1("abc","xyz"),0.)
        self.assertLess(token_f1("a b c","a b d"),1.)

    def test_scorer_produces_complete_source_coverage_and_immutable_model(self):
        fit=self.new["L8_TRAIN"][:40]
        model=AttributionRealizer("CANONICAL_FACTS",fit)
        frozen=model.checkpoint()
        report=evaluate(model,self.new["L8_AUDIT_DEV"][:5],
                        {k:set() for k in ("name","near","food","area")})
        self.assertEqual(report["records"],5)
        self.assertEqual(report["all_MR_keys_raw_literal_copy_proxy"],1.)
        self.assertEqual(report["abstention_count"],0)
        self.assertEqual(frozen,model.checkpoint())


if __name__=="__main__":
    unittest.main()
