"""F124-BU nonconsuming unit tests; no scientific/source/protected first use."""
from __future__ import annotations
import importlib.util
import pathlib
import unittest

HERE=pathlib.Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


source=module("bu_nonregistered_source","f124bu_synthetic_crossover.py")
model=module("bu_exact_BQ_program","f124bq_program_learner.py")
audit=module("bu_natural_policy","f124bu_natural_workload.py")


class SourceNeutralAdmission(unittest.TestCase):
    def test_frozen_exact_two_ids_source_neutral_reversible_hard_negative(self):
        self.assertEqual(tuple(source.SEEDS),audit.CASES)
        for case in audit.CASES:
            task,private=source.make(case)
            self.assertEqual(len(task["FIT"]),40)
            self.assertEqual(len(task["CHECK"]),8)
            self.assertEqual(source.symbolic_path(task["positive"]),1)
            self.assertEqual(source.symbolic_path(task["hard_negative"]),0)
            self.assertEqual(private["fixture_type"],
                             "NONREGISTERED_SYNTHETIC_INTERSECTION_NOT_SCIENCE")
            fitted,receipt,plausible=model.learn(task["FIT"],task["CHECK"])
            self.assertIsNotNone(fitted,receipt)
            self.assertEqual(fitted[4:],(1,1))
            self.assertTrue(receipt["learned_from_FIT_only"])
            self.assertTrue(receipt["CHECK_can_only_veto"])
            self.assertTrue(model.causal_consensus(
                task["positive"],fitted,plausible)[0])
            self.assertFalse(model.causal_consensus(
                task["hard_negative"],fitted,plausible)[0])

    def test_no_registered_or_protected_source_ids_permitted(self):
        for case in (924000,925000,924100,925100,920000,
                     921000,"BU-SYN-03",None,504921):
            with self.assertRaises(ValueError):
                source.make(case)

    def test_strict_preflight_does_not_promote_abstention(self):
        fake=[{"case":case,"arm":arm,
               "route":"abstain" if arm=="AZ" else "frozen_BQ_program",
               "native_calls":0 if arm=="AZ" else 2,
               "natural_work_eligible":arm!="AZ",
               "public_pair_graph_sha256":case,
               "native_input_graphs":[],"native_full_outputs":[],
               "native_work":[],"native_call_input_hashes":[],
               "native_call_output_hashes":[]}
              for case in audit.CASES for arm in audit.ARMS]
        result=audit.preflight(fake)
        self.assertFalse(result["all_cases_naturally_eligible"])
        self.assertFalse(result["all_cases_same_normalized_native_work"])
        self.assertTrue(all(not x["route_eligible_without_forcing"]
                            for x in result["cases"].values()))


if __name__=="__main__":
    unittest.main()
