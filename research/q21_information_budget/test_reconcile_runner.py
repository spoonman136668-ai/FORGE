"""Synthetic receipt-only tests of R30, without Q21 cohort generation or fit."""
import copy
import unittest
import ast
from pathlib import Path
import evaluator as e
import sourcefree as src
import resource_meter as rm
import reconcile_runner as rec

DOC=src.protocol()

def stage(osname, title, rss, cpu, with_payload=True):
    iswin=osname=="Windows"
    receipt={
        "schema":"forge.q21.native-process-resource.v1",
        "stage":title,
        "platform":osname,
        "process_cpu_seconds":cpu,
        "process_peak_rss_bytes":rss,
        "start_process_peak_rss_bytes":rss-100,
        "rss_scope":"CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_STAGE",
        "io_measurement_source":("windows_getprocessiocounters"
                                 if iswin else "linux_proc_self_io"),
        "io":{
            "read_transfer_bytes":200,
            "write_transfer_bytes":500,
            "disk_read_bytes":None if iswin else 200,
            "disk_write_bytes":None if iswin else 100},
    }
    if with_payload:
        receipt["rss_scope"]="PROCESS_CUMULATIVE_HIGH_WATER_NOT_ISOLATED_PER_MODEL"
        receipt["payload"]={"serialized_bytes":1000,"serialized_sha256":"a"*64,
                            "encoding":"canonical_json_utf8"}
        receipt["communication"]={"adapter_mode":"none","wire_bytes":0,
                                   "adapter_bytes":0}
    return receipt

def observed(family):
    null=family==src.FAMILIES[2]
    means={name:(.61 if name==e.MEMORYLESS[0] else
                 .59 if name==e.HISTORY[0] and not null else
                 .607 if name==e.HISTORY[0] else .63)
           for name in e.ARM_NAMES}
    arms={}
    for name in e.ARM_NAMES:
        vl=.20 if name==e.MEMORYLESS[0] else (
            .19 if name==e.HISTORY[0] else .35)
        arms[name]={
            "fit_cost":{"fit_validation_nll":vl,"checkpoint_bytes":17,
                        "checkpoint_sha256":"b"*64},
            "result":{"mean_nll":means[name],
                      "episode_nll":[means[name]]*src.ROLE_COUNTS["DEV"],
                      "ordinary_bit_false_positive_count":1,
                      "dev_inference_cpu_s":.001},
        }
    gain=means[e.MEMORYLESS[0]]-means[e.HISTORY[0]]
    return {
        "family":family,
        "role_sha256":{"FIT_TRAIN":"1"*64,"FIT_VALID":"2"*64,"DEV":"3"*64},
        "arm_results":arms,
        "best_current":e.MEMORYLESS[0],"best_history":e.HISTORY[0],
        "gain":{"gain_nats_per_bit":gain,"lower_95":gain-.001,
                "upper_95":gain+.001,"resampling_unit":"EPISODE",
                "replicates":2048},
        "privileged_oracle_nll":.58,
        "oracle_is_not_matched_comparator":True,
        "public_oracle_headroom":means[e.MEMORYLESS[0]]-.58,
        "native_peak_rss_qualified":False,
        "protected_scientific_first_use":False,
    }

def envelope(osname):
    families={}
    for idx,family in enumerate(src.FAMILIES):
        obs=observed(family)
        gen=stage(osname,"sourcefree_generation_"+family,10000+idx*100,.03)
        fit=stage(osname,"full_fit_validation_dev_"+family,10300+idx*100,.12)
        fit["payload"]=rm.canonical_payload_size(obs)
        families[family]={
            "observed_metrics":obs,
            "source_generation_resources":gen,
            "fit_and_dev_resources":fit,
        }
    decision=e.preliminary_decision(
        {k:v["observed_metrics"] for k,v in families.items()},DOC)
    report={
        "schema":rec.SCHEMA,
        "frozen_protocol_blob":src.PROTOCOL_BLOB,
        "families":families,
        "frozen_preliminary_decision":decision,
        "whole_process_resources":stage(osname,"complete_Q21_development",
                                        11000,.55,False),
        "role_counts_per_family":dict(src.ROLE_COUNTS),
        "process_peak_rss_isolated_per_model":False,
        "communication":{"adapter_mode":"none","wire_bytes":0,
                         "adapter_bytes":0},
        "scientific_admission":"NOT_GRANTED_BY_THIS_MODULE",
        "protected_heldout_or_original_first_use":False,
    }
    report["receipt_storage"]=rm.canonical_payload_size(report)
    return {"schema":"forge.q21.external-readonly-envelope.v1",
            "os_name":osname,"candidate_source_sha":"d"*40,
            "runner_report":report}

class TestQ21UnifiedReadOnly(unittest.TestCase):
    def setUp(self):
        self.windows=envelope("Windows")
        self.linux=envelope("Linux")

    def check(self):
        return rec.compare(self.windows,self.linux,DOC)

    def reseal(self,osname):
        o=self.windows if osname=="Windows" else self.linux
        report=o["runner_report"]
        report.pop("receipt_storage",None)
        report["receipt_storage"]=rm.canonical_payload_size(report)

    def test_readonly_two_os_advisory_and_no_science(self):
        out=self.check()
        self.assertTrue(out["matched_reported_cohorts"])
        self.assertTrue(out["scores_reproducible_within_1e_minus_6"])
        self.assertEqual(out["checkpoint_hash_divergences"],[])
        self.assertEqual(out["scientific_first_use"],
                         "NOT_AUTHENTICATED_NOT_AUTHORIZED")

    def test_changed_checkpoint_hash_is_disclosed_not_claimed_identical(self):
        data=self.linux["runner_report"]["families"][src.FAMILIES[0]]
        data["observed_metrics"]["arm_results"][e.HISTORY[0]][
            "fit_cost"]["checkpoint_sha256"]="c"*64
        data["fit_and_dev_resources"]["payload"]=rm.canonical_payload_size(
            data["observed_metrics"])
        self.reseal("Linux")
        out=self.check()
        self.assertEqual(len(out["checkpoint_hash_divergences"]),1)

    def test_cohort_and_model_selection_cannot_drift(self):
        data=self.linux["runner_report"]["families"][src.FAMILIES[0]]
        data["observed_metrics"]["role_sha256"]["DEV"]="f"*64
        data["fit_and_dev_resources"]["payload"]=rm.canonical_payload_size(
            data["observed_metrics"])
        self.reseal("Linux")
        with self.assertRaisesRegex(ValueError,"COHORT_SOURCE_DRIFT"):
            self.check()
        self.linux=envelope("Linux")
        data=self.linux["runner_report"]["families"][src.FAMILIES[0]]
        data["observed_metrics"]["best_history"]=e.HISTORY[1]
        data["fit_and_dev_resources"]["payload"]=rm.canonical_payload_size(
            data["observed_metrics"])
        self.reseal("Linux")
        with self.assertRaisesRegex(ValueError,"DEV_SET_WINNER_SELECTION"):
            self.check()

    def test_frozen_protocol_and_whole_receipt_tamper_rejected(self):
        self.windows["runner_report"]["frozen_protocol_blob"]="a"*40
        with self.assertRaisesRegex(ValueError,"PREREG_ID"):
            self.check()
        self.windows=envelope("Windows")
        self.windows["runner_report"]["receipt_storage"]["serialized_bytes"]+=1
        with self.assertRaisesRegex(ValueError,"FINAL_RECEIPT_PAYLOAD_INTEGRITY"):
            self.check()

    def test_native_cpu_rss_wire_and_privileged_oracle_are_required(self):
        report=self.windows["runner_report"]
        report["whole_process_resources"]["process_cpu_seconds"]=.05
        self.reseal("Windows")
        with self.assertRaisesRegex(ValueError,"WHOLE_PROCESS_CPU_EXCLUDES"):
            self.check()
        self.windows=envelope("Windows")
        report=self.windows["runner_report"]
        report["process_peak_rss_isolated_per_model"]=True
        self.reseal("Windows")
        with self.assertRaisesRegex(ValueError,"FAKE_MODEL_RSS_ISOLATION"):
            self.check()
        self.windows=envelope("Windows")
        report=self.windows["runner_report"]
        report["communication"]["wire_bytes"]=8
        self.reseal("Windows")
        with self.assertRaisesRegex(ValueError,"NO_TRANSPORT"):
            self.check()

    def test_fully_resource_integrated_must_not_claim_per_model_memory(self):
        report=self.windows["runner_report"]
        item=report["families"][src.FAMILIES[0]]
        item["fit_and_dev_resources"]["rss_scope"]="PER_MODEL_RSS"
        self.reseal("Windows")
        with self.assertRaisesRegex(ValueError,"EVALUATION_RSS_SCOPE"):
            self.check()

    def test_decision_drift_within_frozen_float_tolerance_rejected(self):
        # Both numerical intervals are within <=1e-6 of one another,
        # but only one clears the frozen lower bound.
        family=src.FAMILIES[0]
        a=self.windows["runner_report"]["families"][family]["observed_metrics"]
        b=self.linux["runner_report"]["families"][family]["observed_metrics"]
        a["gain"]["lower_95"]=.00200005
        b["gain"]["lower_95"]=.00199995
        for platform,obs in (("Windows",a),("Linux",b)):
            item=(self.windows if platform=="Windows" else self.linux)[
                "runner_report"]["families"][family]
            item["fit_and_dev_resources"]["payload"]=rm.canonical_payload_size(obs)
            report=(self.windows if platform=="Windows" else self.linux)["runner_report"]
            report["frozen_preliminary_decision"]=e.preliminary_decision(
                {k:v["observed_metrics"] for k,v in report["families"].items()},DOC)
            self.reseal(platform)
        with self.assertRaisesRegex(ValueError,"CROSS_OS_DECISION_DRIFT"):
            self.check()

    def test_reconciler_never_calls_generator_or_fit_or_controller(self):
        tree=ast.parse(Path(rec.__file__).read_text(encoding="utf-8"))
        blocked={"generate","fit_gradient","fit_hmm",
                 "execute_development","evaluate_one_family","dispatch"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                self.assertNotIn(node.func.attr,blocked)

if __name__=="__main__":
    unittest.main()
