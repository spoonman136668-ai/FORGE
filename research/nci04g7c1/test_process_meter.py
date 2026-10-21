#!/usr/bin/env python3
"""NCI-04G7C-1 focused engineering smoke; never scientific admission."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from process_meter import MeterBlocked, command_receipt, group_rss_bytes

BASE=Path(__file__).resolve().parent
CONTRACT=BASE/"task_resource_contract.json"

class MeterAndContractTests(unittest.TestCase):
    def test_external_task_contract_has_no_scientific_authority(self):
        d=json.loads(CONTRACT.read_text("utf-8"))
        self.assertEqual(d["schema"],"forge.nci04g7c1.task-resource-prequalification.v1")
        self.assertEqual(d["parent_source_intake"]["head"],
                         "b40a3f038266fec5d065986b9f93d46f02f13d6b")
        self.assertIs(d["sealed_scientific_evaluation"],False)
        self.assertEqual(d["protected_first_use"],{
            "originals":0,"intents":0,"admissions":0,
            "holdouts_opened":0,"replay_authorized":False})
        self.assertEqual({v["lane"] for v in d["task_interfaces"]},
                         {"Wingless","Yggdrasil"})
        self.assertTrue(all(v["independently_selected_unseen_tasks"]=="NOT_FROZEN"
                            for v in d["task_interfaces"]))
        c=d["complete_resource_contract"]
        self.assertEqual(c["qualification"],
                         "NOT_COMPLETE_OR_SCIENTIFICALLY_ACCEPTED")
        self.assertIn("peak aggregate simultaneous process-tree RSS bytes", c["metrics"])
        self.assertIn("all subprocess descendants", c["include"])
        self.assertIn("checkpoint save/load/restart", c["include"])

    def test_bounded_grouped_meter_discloses_incomplete_memory(self):
        # Source-free *meter* smoke only; no cognitive benchmark/training.
        with tempfile.TemporaryDirectory() as tmp:
            argv=[sys.executable,"-B","-c",
                "import subprocess,sys,time; "
                "p=subprocess.run([sys.executable,'-B','-c',"
                "'import time; x=bytearray(2_000_000); time.sleep(.045)'],check=True); "
                "print('METER_CHILD_OK')"]
            result=command_receipt(argv,Path(tmp),timeout_s=5.0)
            self.assertEqual(result["exit_code"],0)
            self.assertGreater(result["sample_count"],0)
            self.assertGreaterEqual(result["sampled_processes_max_simultaneous"],1)
            self.assertGreater(result["reaped_group_user_system_cpu_ns"],0)
            self.assertGreater(result["sampled_process_group_peak_rss_bytes_lower_bound"],0)
            self.assertEqual(len(result["stdout_stderr_sha256"]),64)
            self.assertIs(result["peak_aggregate_rss_complete"],False)
            self.assertIs(result["child_escape_attested"],False)
            self.assertIs(result["all_in_resource_parity_qualified"],False)
            self.assertIs(result["scientific_first_use"],False)
            self.assertEqual(result["classification"],
                             "PARTIAL_DEVELOPMENT_RESOURCE_DIAGNOSTIC_ONLY")
            print("NCI04G7C1_METER_SMOKE="+json.dumps(result,sort_keys=True))

    def test_fail_closed_on_bad_or_failed_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd=Path(tmp)
            with self.assertRaises(MeterBlocked):
                command_receipt([],cwd)
            with self.assertRaises(MeterBlocked):
                command_receipt([sys.executable,"-B","-c","raise SystemExit(7)"],cwd)
            with self.assertRaises(MeterBlocked):
                command_receipt([sys.executable,"-B","-c","import time; time.sleep(2)"],
                                cwd,timeout_s=.1)
            self.assertEqual(group_rss_bytes(-9999),(0,0))

if __name__=="__main__":
    unittest.main(verbosity=2)
