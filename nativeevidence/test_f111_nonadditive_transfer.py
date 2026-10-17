"""F111 adversarial tests: nonadditive source-ID and full-information controls.

The fixture is explicitly TEST ONLY; real acceptance revalidates current-run F110
JSON and receipt against full ancestor provenance and unchanged F110 results.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace
from unittest import mock

import f111_nonadditive_transfer as f111
import f110_capacity_transfer as f110
import f109_failure_driven_mechanisms as f109
import f103_yggdrasil_public_binding as ybind
from test_f110_capacity_transfer import local_evidence

SRC="a"*40

def fixture(root):
    local_evidence(root)
    record=f110.evaluate(SRC,root)
    report=root/"forge-f110-development/f110-capacity-matched-transfer.json"
    receipt=root/"forge-f110-development/f110-capacity-matched-transfer.sha256"
    report.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
    report.write_bytes(raw)
    receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n")
    return report,receipt

class F111NonadditiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.freeze_digest=f111.freeze()
    def setUp(self):
        self.old=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SRC
    def tearDown(self):
        if self.old is None:os.environ.pop("GITHUB_SHA",None)
        else:os.environ["GITHUB_SHA"]=self.old

    def test_first_commit_preimplementation_identity_and_authority_denied(self):
        self.assertEqual(self.cfg["parent_f110_exact_head_sha"],
                         "bc793d9d702a06f28bae452777c5c63cd39a2430")
        self.assertEqual(len(self.freeze_digest),64)
        self.assertTrue(self.cfg["authority"]["no_codex"])
        self.assertTrue(self.cfg["qualification"]["failed_hypothesis_not_CI_failure"])

    def test_three_fresh_noncyclic_public_source_representations(self):
        groups=f111.wing_groups()
        self.assertEqual([len(g) for g in groups],[48,48,48])
        self.assertEqual(len({c.public.base.seed for g in groups for c in g}),144)
        for group in groups:
            for c in group:
                self.assertEqual(sorted(c.ids_by_tag),[0,1,2,3])
                self.assertFalse(any(all(c.ids_by_tag[tag]==(tag+k)%4
                                         for tag in range(4)) for k in range(4)))
                pos=c.public.base.positive_values
                neg=c.public.base.negative_values
                self.assertTrue(f111.tag_lookup(c,pos))
                self.assertFalse(f111.tag_lookup(c,neg))
                self.assertEqual(sum(a!=b for a,b in zip(pos,neg)),1)

    def test_strong_public_metadata_control_inference_never_reads_oracle(self):
        c=f111.wing_groups()[0][0]
        model=f109.LearnedSourceRouting()
        with mock.patch.object(ybind,"coded_exact_binding_oracle",
                               side_effect=AssertionError("coded control used in model")):
            out1=f111.tag_lookup(c,c.public.base.positive_values)
            out2=model.predicts(c.public,c.public.base.positive_values)
        self.assertTrue(out1)
        self.assertIsInstance(out2,bool)
        altered=replace(c,ids_by_tag=tuple(reversed(c.ids_by_tag)))
        # Metadata affects full-information comparison without modifying observations.
        self.assertNotEqual(c.ids_by_tag,altered.ids_by_tag)

    def test_ygg_fresh_graphs_and_separate_exact_truth_control(self):
        groups=f111.ygg_groups()
        self.assertEqual([len(g) for g in groups],[48,48,48])
        self.assertEqual(len({p.seed for g in groups for p in g}),144)
        for j,group in enumerate(groups):
            for p in group:
                self.assertEqual(len(p.edges),12)
                self.assertTrue(ybind.coded_exact_binding_oracle(p,p.positive_variables))
                self.assertFalse(ybind.coded_exact_binding_oracle(p,p.negative_variables))
                if j in (0,2):
                    self.assertEqual(len(set(p.query_roles)),1)

    def test_parent_report_digest_and_result_tampering_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            report,receipt=fixture(root)
            digest=f111.read_parent(SRC,root,self.cfg)
            self.assertEqual(len(digest),64)
            report.write_bytes(report.read_bytes()+b" ")
            with self.assertRaisesRegex(f111.Quarantined,"RECEIPT_TAMPER"):
                f111.read_parent(SRC,root,self.cfg)

    def test_current_run_outputs_both_lanes_all_288_records(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            fixture(root)
            result=f111.evaluate(SRC,root)
        self.assertEqual(result["schema"],f111.REPORT)
        self.assertEqual(result["new_pairs_per_lane"],144)
        self.assertTrue(result["all_288_pairwise_decisions_retained"])
        self.assertEqual(len(result["outcomes"]),2)
        self.assertEqual(result["outcomes"][0]["total_pairs"],144)
        self.assertEqual(result["outcomes"][1]["total_pairs"],144)
        self.assertTrue(result["outcomes"][0]["exact_full_information_metadata_lookup_control"])
        for row in result["outcomes"]:
            self.assertEqual(len(row["blocks"]),3)
            self.assertTrue(all(len(g["individual_paired_decisions"])==48 for g in row["blocks"]))
            self.assertIn(row["disposition"],(
                "NONADDITIVE_REPRESENTATION_TRANSFER_NOT_PROVEN_NEGATIVE_RETAINED",
                "RESTRICTED_PUBLIC_REPRESENTATION_GAIN_NOT_SCIENCE",
                "NO_NEW_YGGDRASIL_SUPERIORITY_NEGATIVE_RETAINED",
                "RESTRICTED_PUBLIC_GRAPH_GAIN_NOT_SCIENCE"))
        self.assertEqual(result["codex_calls"],0)
        self.assertFalse(result["first_use_authorized"])
        self.assertEqual(result["accepted_ref_mutations"],0)

    def test_wrong_GITHUB_SHA_quarantined(self):
        with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
            with self.assertRaisesRegex(f111.Quarantined,"CURRENT_GITHUB_SOURCE_REQUIRED"):
                f111.evaluate(SRC,"/tmp/untrusted")

if __name__=="__main__":
    unittest.main()
