"""F105 tests: synthetic test-only receipts, plus live-hosted evidence readback in CI.

Test fixtures are deliberately LOCAL and never counted as authentic results.
The production program must ingest the existing F101-F104 workflow outputs.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import f105_research_feedback as f105

SHA="a"*40

def fake_report(key,meta,valid=True):
    spec=f105.EXPECT[key]
    value={
        "schema":meta["schema"],
        "source_sha":SHA,
        "lane":meta["lane"],
        "candidate_id":meta["id"],
        spec["pairs"]:144,
        spec["training"]:96,
        spec["assess"]:48,
        spec["trainable_field"]:spec["trainable"],
        spec["updates"]:100,
        spec["blind_updates"]:100,
        spec["negative"]:True,
        meta["score_key"]:{
            meta["primary"]:1.0,
            meta["blind"]:0.25 if key=="F104" else 0.0,
            meta["oracle"]:1.0,
            spec["control_shortcut"]:0.0,
            "permutation_ablation":0.0
        },
        meta["worst_key"]:1.0,
        meta["screen_key"]:True
    }
    for flag in spec["booleans"]:value[flag]=False
    for field in spec["zero"]:value[field]=0
    if key=="F102":value["coded_oracle_only_control"]=True
    if key=="F103":
        value["oracle_only_separate_control"]=True
        value["variable_renaming_agreement"]=1.0
    if key=="F104":
        value["coded_oracle_separate_control_only"]=True
        value["query_dependent_selection_fraction"]=1.0
        value["observation_budget_per_prediction"]=1
    return value

def write_set(root,cfg,changes=None):
    changes=changes or {}
    for key,entry in cfg["source_evidence"].items():
        data=fake_report(key,entry)
        if key in changes:changes[key](data,entry)
        relative=Path(entry["report_path"])
        report=root/relative
        receipt=root/entry["sha_path"]
        report.parent.mkdir(parents=True,exist_ok=True)
        raw=(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode("utf8")
        report.write_bytes(raw)
        receipt.write_text(hashlib.sha256(raw).hexdigest()+
                           "  "+report.name+"\n",encoding="utf8")

class F105EvidenceFeedback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.digest=f105.freeze()

    def test_exact_frozen_policy_and_original_source_blobs(self):
        self.assertEqual(self.cfg["parent_f104_exact_head_sha"],f105.PARENT)
        self.assertEqual(self.cfg["decision_policy"]["policy_id"],
                         "F105-D0-FROZEN-PAIRWISE-RISK-FIRST")
        self.assertEqual(set(self.cfg["source_evidence"]),set(f105.EXPECT))
        self.assertEqual(len(self.digest),64)

    def test_default_advisory_realistic_test_local_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            write_set(Path(td),self.cfg)
            with mock.patch.dict(os.environ,{"GITHUB_SHA":SHA}):
                result=f105.evaluate(SHA,td)
        self.assertEqual(result["input_observation_count"],4)
        self.assertEqual(result["development_pairs_observed"],576)
        self.assertEqual(len(result["selected_successors"]),2)
        successors={x["lane"]:x for x in result["selected_successors"]}
        self.assertEqual(successors["Wingless"]["parent_candidate_id"],"W100-C2")
        self.assertEqual(successors["Yggdrasil"]["parent_candidate_id"],"Y100-C2")
        self.assertEqual(successors["Yggdrasil"]["selected_successor_hypothesis"],
                         "ALIASING_AND_VARIABLE_REUSE_TRANSFER")
        self.assertEqual(result["original_experiment_dispatches"],0)
        self.assertEqual(result["codex_calls"],0)
        self.assertEqual(result["external_model_inference_calls"],0)
        self.assertFalse(result["protected_first_use_authorized"])

    def test_actual_negative_changes_advisory_without_relabeling(self):
        def negative(report,meta):
            report[meta["score_key"]][meta["primary"]]=0.5
            report[meta["worst_key"]]=0.5
            report[meta["screen_key"]]=False
        with tempfile.TemporaryDirectory() as td:
            write_set(Path(td),self.cfg,{"F103":negative})
            result=f105.evaluate(SHA,td)
        selection={x["lane"]:x for x in result["selected_successors"]}
        self.assertEqual(selection["Yggdrasil"]["parent_candidate_id"],"Y100-C2")
        self.assertEqual(selection["Yggdrasil"]["selection_reason"],
                         "FROZEN_PUBLIC_SCREEN_NEGATIVE_FALSIFY_OR_REPAIR")
        self.assertEqual(selection["Yggdrasil"]["selected_successor_hypothesis"],
                         "VARIABLE_BINDING_FALSIFICATION")
        self.assertEqual(result["new_scientific_originals_executed"],0)

    def test_missing_or_tampered_report_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_set(root,self.cfg)
            report=root/self.cfg["source_evidence"]["F104"]["report_path"]
            report.write_bytes(report.read_bytes()+b" ")
            with self.assertRaisesRegex(f105.Quarantined,"HASH_MISMATCH"):
                f105.evaluate(SHA,root)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_set(root,self.cfg)
            (root/self.cfg["source_evidence"]["F102"]["report_path"]).unlink()
            with self.assertRaises(OSError):
                f105.evaluate(SHA,root)

    def test_same_checksum_different_source_or_synthetic_authority_denied(self):
        def replay(report,meta):
            report["source_sha"]="b"*40
        with tempfile.TemporaryDirectory() as td:
            write_set(Path(td),self.cfg,{"F101":replay})
            with self.assertRaisesRegex(f105.Quarantined,"FOREIGN_REPORT"):
                f105.evaluate(SHA,td)
        def elevated(report,meta):
            report["accepted_ref_mutations"]=1
        with tempfile.TemporaryDirectory() as td:
            write_set(Path(td),self.cfg,{"F102":elevated})
            with self.assertRaisesRegex(f105.Quarantined,"UNAUTHORIZED_SCIENCE"):
                f105.evaluate(SHA,td)

    def test_missing_control_or_cherry_picked_population_denied(self):
        def remove_control(report,meta):
            report[meta["score_key"]].pop(meta["blind"])
        with tempfile.TemporaryDirectory() as td:
            write_set(Path(td),self.cfg,{"F104":remove_control})
            with self.assertRaisesRegex(f105.Quarantined,"FULL_POPULATION"):
                f105.evaluate(SHA,td)

    def test_no_unearned_screen_label(self):
        def flip_label(report,meta):
            report[meta["screen_key"]]=False
        with tempfile.TemporaryDirectory() as td:
            write_set(Path(td),self.cfg,{"F103":flip_label})
            with self.assertRaisesRegex(f105.Quarantined,"SCREEN_RECOMPUTATION"):
                f105.evaluate(SHA,td)

    def test_source_identity_and_traversal_guard(self):
        with tempfile.TemporaryDirectory() as td:
            write_set(Path(td),self.cfg)
            with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
                with self.assertRaisesRegex(f105.Quarantined,"CURRENT_GITHUB_SOURCE"):
                    f105.evaluate(SHA,td)
        bad=json.loads(json.dumps(self.cfg))
        bad["source_evidence"]["F101"]["report_path"]="../untrusted.json"
        with tempfile.TemporaryDirectory() as td:
            write_set(Path(td),self.cfg)
            with self.assertRaisesRegex(f105.Quarantined,"PATH_ESCAPES"):
                f105.read_evidence(SHA,Path(td),bad)

    def test_policy_uses_not_one_fabricated_constant_answer(self):
        a=dict(key="F103",lane="Yggdrasil",candidate_id="Y100-C2",
               paired_accuracy=0.5,worst_group_accuracy=0.5,
               public_screen_passed=False,source_report_sha256="a"*64)
        b=dict(key="F102",lane="Yggdrasil",candidate_id="Y100-C1",
               paired_accuracy=0.25,worst_group_accuracy=0.25,
               public_screen_passed=False,source_report_sha256="b"*64)
        c=dict(key="F101",lane="Wingless",candidate_id="W100-C1",
               paired_accuracy=1.0,worst_group_accuracy=1.0,
               public_screen_passed=True,source_report_sha256="c"*64)
        d=dict(key="F104",lane="Wingless",candidate_id="W100-C2",
               paired_accuracy=1.0,worst_group_accuracy=1.0,
               public_screen_passed=True,source_report_sha256="d"*64)
        selected=f105.choose({"F101":c,"F102":b,"F103":a,"F104":d},self.cfg)
        self.assertEqual(selected[1]["parent_candidate_id"],"Y100-C1")
        self.assertEqual(selected[1]["selected_successor_hypothesis"],
                         "ROLE_CONDITIONED_MESSAGE_FALSIFICATION")

if __name__=="__main__":
    unittest.main()
