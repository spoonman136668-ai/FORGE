"""T16-D source-neutral synthetic structural adapter checks only.

These are fabricated unit-test triples, not CLUTRR data, science source
births, results, held answers, or authorization.
"""
import importlib.util,sys,unittest
from pathlib import Path
p=Path(__file__).with_name("20261019-t16d-clutrr-native-compatibility.py")
s=importlib.util.spec_from_file_location("t16d_clutrr_adapter",p)
m=importlib.util.module_from_spec(s)
sys.modules[s.name]=m;s.loader.exec_module(m)
def e(a,r,b):return {"source":a,"relation":r,"target":b}

class SourceNeutralCompatibilityTests(unittest.TestCase):
    def test_inert_empty_no_admission(self):
        r=m.lane_screen(m.template_metadata(),[])
        self.assertEqual(set(r["per_lane"]),{"Wingless","Yggdrasil","MassResearch"})
        self.assertTrue(all(not x["eligible"] for x in r["per_lane"].values()))
        self.assertFalse(r["original_execution_authorized"])
        self.assertFalse(r["dataset_opened"])

    def test_reversible_synthetic_structural_graph_without_semantics_claim(self):
        sample=[e(100,"child",200),e(200,"sibling",300),
                e(300,"SO",400),e(400,"grand",500)]
        v=m.translate_public_edges(sample)
        self.assertEqual(m.reconstruct(v),tuple((x["source"],x["relation"],x["target"]) for x in sample))
        self.assertFalse(v["kinship_semantics_verified"])
        self.assertFalse(v["native_operator_isomorphism_proven"])

    def test_nonbijective_siblings_cannot_map_to_mass_sbox(self):
        sample=[e(50,"sibling",60),e(50,"sibling",70)]
        r=m.lane_screen(m.template_metadata(),sample)
        self.assertTrue(r["kinship_relation_nonfunctional_example"])
        self.assertIn("NONBIJECTIVE_ROLE_COUNTEREXAMPLE",r["per_lane"]["MassResearch"]["reasons"])
        self.assertIn("NONFUNCTIONAL_KINSHIP_COUNTEREXAMPLE",r["per_lane"]["Wingless"]["reasons"])

    def test_native_four_relation_limit_explicit(self):
        sample=[e(1000+i,role,2000+i) for i,role in enumerate(m.FAMILY_RELS[:5])]
        r=m.lane_screen(m.template_metadata(),sample)
        self.assertIn("MORE_THAN_FOUR_NATIVE_TYPED_RELATIONS",r["per_lane"]["Yggdrasil"]["reasons"])

    def test_serial_lower_bound_exceeded(self):
        sample=[e(10000+2*i,"child",10001+2*i) for i in range(26)]
        r=m.lane_screen(m.template_metadata(),sample)
        self.assertGreater(r["native_lower_bound_bytes"],144)
        self.assertIn("SERIAL_NATIVE_144B_LOWER_BOUND_EXCEEDED",r["per_lane"]["Yggdrasil"]["reasons"])

    def test_external_commit_or_rules_mutation_stops(self):
        for key in ("external_commit","external_tree","rules_blob",
                    "relations_blob","generator_blob","baseline_commit"):
            meta=m.template_metadata()
            meta[key]="f"*len(meta[key])
            with self.assertRaisesRegex(ValueError,"PIN_DRIFT"):
                m.lane_screen(meta,[])

    def test_license_rights_absent_still_closed(self):
        r=m.lane_screen(m.template_metadata(),[])
        for lane in r["per_lane"].values():
            self.assertIn("LICENSE_RIGHTS_NOT_INDEPENDENTLY_CLEARED",lane["reasons"])
            self.assertFalse(lane["eligible"])

    def test_claimed_booleans_do_not_substitute_for_external_signatures(self):
        x=m.template_metadata()
        for key in list(x):
            if type(x[key]) is bool:x[key]=True
        r=m.lane_screen(x,[e(1,"child",2)])
        self.assertFalse(r["independent_scientific_firstuse_proven"])
        self.assertFalse(r["original_execution_authorized"])
        self.assertFalse(r["per_lane"]["MassResearch"]["eligible"])

    def test_type_confusion_rejected(self):
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS"):
            m.translate_public_edges([e(True,"child",2)])
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS"):
            m.translate_public_edges([e(1,"invented",2)])
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS"):
            m.translate_public_edges([e(1,"child",1<<24)])

    def test_duplicate_or_long_edge_stream_fails(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            m.translate_public_edges([e(1,"child",2),e(1,"child",2)])
        with self.assertRaisesRegex(ValueError,"UNBOUNDED"):
            m.translate_public_edges([e(i,"child",i+1) for i in range(73)])

    def test_text_prose_not_falsely_converted_to_typed_kinship(self):
        with self.assertRaisesRegex(ValueError,"AMBIGUOUS"):
            m.translate_public_edges([{"story":"A is related to B","target":"grand"}])

    def test_missing_metadata_cannot_admit(self):
        meta=m.template_metadata()
        meta.pop("rules_blob")
        with self.assertRaisesRegex(ValueError,"SCHEMA_DRIFT"):
            m.lane_screen(meta,[])

    def test_origin_cannot_prove_original_firstuse(self):
        x=m.lane_screen(m.template_metadata(),[])
        self.assertTrue(x["independent_external_repo_authorship_known"])
        self.assertFalse(x["independent_scientific_firstuse_proven"])
        self.assertFalse(x["optimizer_admission"])

if __name__=="__main__":unittest.main()
