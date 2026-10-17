"""F106: frozen bounded model training, fresh cohorts and fail-closed F105 intake."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import f103_yggdrasil_public_binding as ybind
import f104_wingless_public_observations as wobserve
import f105_research_feedback as f105
import f106_automatic_challenge as f106
from test_f105_research_feedback import SHA,write_set

def prepare(root,negative=None):
    cfg,_=f105.freeze()
    write_set(root,cfg,changes=negative)
    advice=f105.evaluate(SHA,root)
    report=root/"forge-f105-development/f105-evidence-feedback-advisory.json"
    receipt=root/"forge-f105-development/f105-evidence-feedback-advisory.sha256"
    report.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(advice,sort_keys=True,separators=(",",":"))+"\n").encode()
    report.write_bytes(raw)
    receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n",
                       encoding="utf8")
    return report,receipt

class F106FreshDevelopment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg,cls.digest=f106.frozen()

    def setUp(self):
        self.saved_sha=os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"]=SHA

    def tearDown(self):
        if self.saved_sha is None:
            os.environ.pop("GITHUB_SHA",None)
        else:
            os.environ["GITHUB_SHA"]=self.saved_sha

    def test_preimplementation_parent_and_permit_freeze(self):
        self.assertEqual(f106.PARENT,self.cfg["parent_f105_exact_branch_head"])
        self.assertEqual(self.cfg["purpose"],
                         "ONE_BOUNDED_PUBLIC_DEVELOPMENT_EVIDENCE_TO_DECISION_TO_NEW_CHALLENGE_TO_FEEDBACK_CYCLE")
        self.assertTrue(self.cfg["training"]["no_retrain_or_tune_after_new_diagnostic"])
        self.assertTrue(self.cfg["scores"]["negative_result_does_not_abort_evidence_receipt"])
        self.assertEqual(len(self.digest),64)

    def test_two_new_seed_blocks_are_disjoint_and_ground_truth_valid(self):
        w=f106.wingless_new_challenge()
        y=f106.yggdrasil_new_challenge()
        self.assertEqual(len(w),48)
        self.assertEqual(len(y),48)
        self.assertEqual(len({(x.seed,x.specimen) for x in w}),48)
        self.assertEqual(len({(x.seed,x.specimen) for x in y}),48)
        self.assertEqual({x.specimen for x in w},{0,1})
        self.assertEqual({x.specimen for x in y},{0,1})
        for case in w:
            self.assertTrue(64200<=case.seed<=64223)
            self.assertEqual(len(case.observation_depths),4)
            self.assertEqual(sum(a!=b for a,b in zip(
                case.positive_values,case.negative_values)),1)
            self.assertTrue(wobserve.coded_depth_observation_oracle(
                case,case.positive_values))
            self.assertFalse(wobserve.coded_depth_observation_oracle(
                case,case.negative_values))
        for case in y:
            self.assertTrue(64300<=case.seed<=64323)
            self.assertEqual(len(case.edges),12)
            self.assertEqual(len(set(case.edges)),12)
            self.assertEqual(sum(a!=b for pair_a,pair_b in zip(
                case.positive_variables,case.negative_variables)
                for a,b in zip(pair_a,pair_b)),1)
            self.assertTrue(ybind.coded_exact_binding_oracle(
                case,case.positive_variables))
            self.assertFalse(ybind.coded_exact_binding_oracle(
                case,case.negative_variables))
            # Distinct from F103: connected cross-branch edges.
            self.assertEqual(len({v for edge in case.edges for v in edge})<=21,True)

    def test_model_prediction_never_invokes_ground_truth_oracle(self):
        w0=f106.wingless_new_challenge()[0]
        y0=f106.yggdrasil_new_challenge()[0]
        with mock.patch.object(wobserve,"coded_depth_observation_oracle",
                               side_effect=AssertionError("W oracle in inference")), \
             mock.patch.object(ybind,"coded_exact_binding_oracle",
                               side_effect=AssertionError("Y oracle in inference")):
            wobserve.LearnedObservationSelector().probability(w0,w0.positive_values)
            ybind.LearnedVariableBinder().probability(y0,y0.positive_variables)

    def test_actual_new_heldout_evidence_and_feedback_without_grants(self):
        with tempfile.TemporaryDirectory() as td:
            prepare(Path(td))
            outcome=f106.evaluate(SHA,td)
        self.assertEqual(outcome["schema"],f106.REPORT)
        self.assertEqual(outcome["new_public_challenge_pairs"],96)
        self.assertEqual(len(outcome["lanes"]),2)
        self.assertEqual(len(outcome["feedback_next_directions"]),2)
        self.assertTrue(outcome["real_cpu_model_training"])
        self.assertTrue(outcome["run_scoped_selection_verified"])
        for lane in outcome["lanes"]:
            self.assertEqual(lane["new_assessment_pairs"],48)
            self.assertEqual(lane["prior_parent_training_only_pairs"],96)
            self.assertEqual(lane["parent_training_steps"],100)
            self.assertEqual(lane["comparator_training_steps"],100)
            self.assertEqual(lane["coded_oracle_control_accuracy"],1)
            self.assertIn(lane["new_challenge_screen_passed"],(True,False))
            self.assertEqual(lane["successor_authority"],
                             "UNTESTED_PROPOSAL_ONLY_NO_DISPATCH_OR_PROMOTION")
            self.assertGreaterEqual(lane["negative_false_positive_rate"],0)
        self.assertEqual(outcome["new_protected_originals"],0)
        self.assertEqual(outcome["native_research_workers_dispatched"],0)
        self.assertEqual(outcome["external_paid_model_calls"],0)
        self.assertEqual(outcome["codex_invocations"],0)
        self.assertEqual(outcome["accepted_ref_mutations"],0)
        self.assertFalse(outcome["protected_first_use_authorized"])
        self.assertFalse(outcome["trained_policy_promoted"])

    def test_source_mismatch_denied(self):
        with tempfile.TemporaryDirectory() as td:
            prepare(Path(td))
            with mock.patch.dict(os.environ,{"GITHUB_SHA":"b"*40}):
                with self.assertRaisesRegex(f106.Quarantined,"GITHUB_SHA_DRIFT"):
                    f106.evaluate(SHA,td)

    def test_tampered_receipt_denied(self):
        with tempfile.TemporaryDirectory() as td:
            report,receipt=prepare(Path(td))
            report.write_bytes(report.read_bytes()+b" ")
            with self.assertRaisesRegex(f106.Quarantined,"TAMPERED_F105"):
                f106.f105_current_run(SHA,Path(td),self.cfg)

    def test_changed_unsupported_prior_choice_denied_no_fallback_dispatch(self):
        def negative_y(report,meta):
            report[meta["score_key"]][meta["primary"]]=0.5
            report[meta["worst_key"]]=0.5
            report[meta["screen_key"]]=False
        with tempfile.TemporaryDirectory() as td:
            prepare(Path(td),{"F103":negative_y})
            with self.assertRaisesRegex(f106.Quarantined,"UNSUPPORTED_AUTOMATIC_CHOICE"):
                f106.f105_current_run(SHA,Path(td),self.cfg)

    def test_fake_report_with_valid_checksum_still_denied(self):
        with tempfile.TemporaryDirectory() as td:
            report,receipt=prepare(Path(td))
            content=json.loads(report.read_text())
            content["selected_successors"][0]["parent_candidate_id"]="W100-C1"
            raw=json.dumps(content,sort_keys=True,separators=(",",":")).encode()+b"\n"
            report.write_bytes(raw)
            receipt.write_text(hashlib.sha256(raw).hexdigest()+"  "+report.name+"\n")
            with self.assertRaisesRegex(f106.Quarantined,"INCONSISTENT_F105"):
                f106.f105_current_run(SHA,Path(td),self.cfg)

if __name__=="__main__":
    unittest.main()
