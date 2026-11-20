"""Non-dispatch Yggdrasil development work-order adapter negative controls."""
import copy
import unittest

from f139.ckad_development_order_adapter import (
    compile_development_order, SOURCE_MODE, TARGET_SCHEMA,
)
from f139.ckad_campaign_request import CampaignDenied, validate_campaign
from f139.ckad_stage_custody import CKAD25_DEV_SHA, CKAD25_DEV_TREE
from f139.test_ckad_campaign_request import campaign


def eligible():
    c = campaign()
    c["plan"]["candidate_sha"] = CKAD25_DEV_SHA
    c["plan"]["candidate_tree"] = CKAD25_DEV_TREE
    c["plan"]["stages"][0]["phase"] = "learn"
    c["plan"]["stages"][0]["id"] = "learn-01"
    c["plan"]["stages"][1]["phase"] = "evaluate"
    c["plan"]["stages"][1]["id"] = "evaluate-02"
    c["plan"]["stages"][2]["phase"] = "resume"
    c["plan"]["stages"][2]["id"] = "resume-03"
    c["plan"]["stages"][1]["max_interventions"] = 0
    c["max_total_interventions"] = 0
    validate_campaign(c)
    return c


class YggdrasilDevelopmentAdapterTests(unittest.TestCase):
    def test_translation_matches_native_dev_stage_but_never_authorizes(self):
        c = eligible()
        result = compile_development_order(
            c, [], source_ref_sha256="a"*64, packet_sha256="b"*64)
        req = result["source_owned_request"]
        self.assertEqual(req["schema"], TARGET_SCHEMA)
        self.assertEqual(req["source_commit"], CKAD25_DEV_SHA)
        self.assertEqual(req["source_tree"], CKAD25_DEV_TREE)
        self.assertEqual(req["source_mode"], SOURCE_MODE)
        self.assertEqual(req["phase"], "learn")
        self.assertEqual(req["max_wall_seconds"], 10)
        self.assertEqual(len(result["source_owned_request_sha256"]), 64)
        for k in ("source_owner_packet_authenticated",
                  "source_owner_execution_authorized",
                  "source_owner_run_authenticated",
                  "dispatch_authorized","training_execution_authorized",
                  "scientific_pass","promotion_authorized"):
            self.assertFalse(result[k])

    def test_unqualified_old_source_and_wrong_science_scope_fail(self):
        c = eligible()
        from f139.ckad_stage_custody import CKAD13_SHA, CKAD13_TREE
        c["plan"]["candidate_sha"] = CKAD13_SHA
        c["plan"]["candidate_tree"] = CKAD13_TREE
        with self.assertRaises(CampaignDenied):
            compile_development_order(c, [], source_ref_sha256="a"*64,
                                      packet_sha256="b"*64)
        c = eligible()
        c["scientific_first_use"] = True
        with self.assertRaises(CampaignDenied):
            compile_development_order(c, [], source_ref_sha256="a"*64,
                                      packet_sha256="b"*64)

    def test_wrong_packet_and_stage_rejected(self):
        c = eligible()
        with self.assertRaises(CampaignDenied):
            compile_development_order(c, [], source_ref_sha256="x",
                                      packet_sha256="b"*64)
        with self.assertRaises(CampaignDenied):
            compile_development_order(c, [], source_ref_sha256="a"*64,
                                      packet_sha256="b"*63)
        c = eligible()
        c["plan"]["stages"][0]["max_interventions"] = 1
        c["max_total_interventions"] = 1
        with self.assertRaises(CampaignDenied):
            compile_development_order(c, [], source_ref_sha256="a"*64,
                                      packet_sha256="b"*64)

    def test_stage_wall_budget_cap_rejects_oversized(self):
        c = eligible()
        c["plan"]["stages"][0]["max_cpu_seconds"] = 121
        c["max_total_cpu_seconds"] = 141
        with self.assertRaises(CampaignDenied):
            compile_development_order(c, [], source_ref_sha256="a"*64,
                                      packet_sha256="b"*64)


if __name__=="__main__":
    unittest.main()
