"""F124-BK exact-head, nonconsuming native graph/scorer regression tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


native=module("bk_native_test","f124bk_native_graph.py")
measure=module("bk_measure_test","f124bk_measure.py")


class NativeIntegrationTests(unittest.TestCase):
    def test_same_48_public_native_ygg_graph_and_unchanged_az(self):
        for tag in ("U","R"):
            learned=native.evaluate("learned",tag)
            original=native.evaluate("AZ",tag)
            self.assertEqual(learned["same_public_48_sha256"],
                             original["same_public_48_sha256"])
            self.assertEqual(learned["same_public_graph_sha256"],
                             original["same_public_graph_sha256"])
            self.assertEqual(learned["native_graph_edges"],12)
            self.assertEqual(original["native_graph_roles"],7)
            self.assertTrue(learned["native_path_evidence"][
                "original_native_scorer_invoked"])
            self.assertEqual(learned["native_path_evidence"][
                "edge_inverse_calls"],12)
            work=learned["native_path_evidence"]["graph_work"]
            self.assertLessEqual(work["max_active"],7)
            self.assertLessEqual(work["max_retained"],9)
            self.assertFalse(learned["scientific_accepted"])
            self.assertFalse(learned["whole_resource_parity_qualified"])
            self.assertFalse(original["protected_U_or_R_generated"])
            self.assertFalse(original["registered_TRAIN_reexecuted"])

    def test_protected_sources_never_admitted(self):
        for arm,tag in (("learned","U_HOLDOUT"),("AZ","SEALED_R"),
                        ("unknown","U")):
            with self.assertRaises(RuntimeError):
                native.evaluate(arm,tag)
        with self.assertRaises(RuntimeError):
            native.source_public("902000")

    def test_generated_graph_is_public_and_non_oracular(self):
        fit,check=native.source_public("U")
        graph=native.public_native_graph(fit,check)
        self.assertEqual(set(graph),{"start","target","roles","edges","demos"})
        self.assertEqual(len(graph["demos"]),24)
        self.assertEqual(len(graph["edges"]),12)
        self.assertEqual(len(set(edge["from"] for edge in graph["edges"])),12)
        self.assertTrue(all("source_key" not in edge and
                            "oracle" not in edge for edge in graph["edges"]))

    def test_no_resource_acceptance_from_synthetic_report(self):
        sample=[]
        for tag in ("U","R"):
            for arm in ("learned","AZ"):
                for _ in range(3):
                    native_stub={"same_public_48_sha256":tag,
                                 "same_public_graph_sha256":tag,
                                 "native_path_evidence":{
                                     "original_native_scorer_invoked":True,
                                     "graph_work":{"max_active":1,"max_retained":0}}}
                    sample.append({"arm":arm,"tag":tag,
                        "task_CPU_ns_including_source_import_fit_and_graph_score":1000,
                        "whole_process_peak_RSS_bytes":100000000,
                        "native_execution":native_stub})
        report=measure.aggregate(sample)
        self.assertEqual(report["samples"],12)
        self.assertFalse(report["resource_parity_authority"])
        self.assertFalse(report["U_R_authentic_graphs_executed"])
        self.assertFalse(report["positive_retention_tested"])
        self.assertFalse(report["scientific_admission"])
        self.assertFalse(report["separate_original_TRAIN_observation"][
            "complete_original_raw_firstuse_receipt_archived"])
        sample[0]["native_execution"]["same_public_48_sha256"]="tampered"
        with self.assertRaises(RuntimeError):
            measure.aggregate(sample)


if __name__=="__main__":
    unittest.main()
