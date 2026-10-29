"""AC-08 no-first-use reconciliation tests, exact source IDs and negatives."""
import json
import unittest
from unittest.mock import patch
import ac08_portfolio as p

class AC08PortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=p.report()

    def test_whole_portfolio_source_bound_and_unique(self):
        r=self.r
        rows=r["portfolio_rows"]
        self.assertEqual(r["unique_claim_count"],36)
        self.assertEqual(len(rows),36)
        self.assertEqual(len({x["claim_id"] for x in rows}),36)
        self.assertEqual(set(r["actual_sourcefree_original_ids"]),
                         {"U%02d"%i for i in range(1,31)})
        self.assertEqual(set(r["actual_six_native_ids"]),
                         {"AC-D%d"%i for i in range(1,7)})
        self.assertEqual(sum(x["measured_by"]=="AC05" for x in rows),6)
        self.assertEqual(sum(x["measured_by"]=="AC06" for x in rows),15)
        self.assertEqual(sum(x["measured_by"]=="AC07" for x in rows),15)

    def test_original_claims_are_restricted_not_full_ai_research(self):
        orig=[v for v in self.r["portfolio_rows"] if v["claim_id"].startswith("U")]
        self.assertEqual(len(orig),30)
        self.assertTrue(all(not v["native_learning_superiority_proven"] for v in orig))
        self.assertTrue(all(not v["science_admitted"] for v in orig))
        self.assertEqual(set(self.r["physical_substitute_only_ids"]),{"U03","U06"})
        byid={v["claim_id"]:v for v in orig}
        self.assertEqual(byid["U03"]["evidence_scope"],"SOFTWARE_SUBSTITUTE_NOT_PHYSICAL_PROOF")
        self.assertEqual(byid["U06"]["evidence_scope"],"SOFTWARE_SUBSTITUTE_NOT_PHYSICAL_PROOF")
        self.assertTrue(all(v["evidence_scope"]=="RESTRICTED_SYNTHETIC_ONLY"
                            for v in orig if v["claim_id"] not in {"U03","U06"}))

    def test_native_priorities_are_falsifiable_and_avoid_proclamation(self):
        order=self.r["conditional_first_native_pilot_questions"]
        self.assertEqual([x["claim_id"] for x in order],
                         ["AC-D1","AC-D5","AC-D3"])
        self.assertEqual([x["lane"] for x in order],
                         ["Wingless","Yggdrasil","Wingless/BIO"])
        self.assertTrue(all(x["decision"]=="PREPARE_ONLY" for x in order))
        self.assertTrue(all(len(x["critical_test"])>80 for x in order))
        self.assertTrue(self.r["negative_evidence_preserved"])

    def test_draft_chain_is_not_asserted_as_merged_main(self):
        self.assertEqual(self.r["stacked_draft_pr_chain"],
                         [1054,1055,1057,1058,1060,1061,1062])
        self.assertEqual(set(self.r["source_evidence_commit_pins"]),
                         {"AC05","AC06","AC07"})
        self.assertTrue(all(len(x)==40 for x in
                            self.r["source_evidence_commit_pins"].values()))

    def test_science_admission_and_controller_guards_remain_closed(self):
        r=self.r
        for key in ("independent_itd02_consequence_source_verified",
                    "native_model_learning_superiority_proven",
                    "scientific_first_use_authorized",
                    "scientific_admission_authorized",
                    "model_promotion_authorized","controller_or_queue_changed"):
            self.assertFalse(r[key])
        self.assertTrue(r["overlapping_active_research_priorities_must_continue"])
        self.assertEqual(r["scope"],"READ_ONLY_RECONCILIATION_OF_SYNTHETIC_DEVELOPMENT")

    def test_source_group_drift_cannot_silently_change_coverage(self):
        with patch.object(p,"AC06_ORIGINAL",p.AC06_ORIGINAL-{"U07"}):
            with self.assertRaisesRegex(RuntimeError,"AC06_SOURCE_COVERAGE_DRIFT"):
                p.report()

    def test_json_artifact_roundtrip_is_lossless(self):
        self.assertEqual(json.loads(json.dumps(self.r,sort_keys=True)),self.r)

if __name__=="__main__":
    unittest.main()
