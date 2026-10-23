"""Q21N-01 preregistration qualification. Handwritten mutations; zero cohorts."""
import copy
import hashlib
import unittest
from pathlib import Path
import prereg_guard as gate


class NativeProtocolQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen, cls.original = gate.read_protocol()

    def test_frozen_protocol_exact_git_blobs_and_no_execution(self):
        receipt = gate.preflight()
        self.assertEqual(receipt["state"], "SOURCE_ONLY_FROZEN_PROTOCOL_PASS")
        self.assertEqual(receipt["protocol_git_blob"],gate.NEW_PROTOCOL_BLOB)
        self.assertEqual(receipt["predecessor_git_blob"],gate.LEGACY_PROTOCOL_BLOB)
        self.assertEqual(receipt["cohorts_generated"], 0)
        self.assertEqual(receipt["models_trained"], 0)
        self.assertFalse(receipt["scientific_first_use"])
        self.assertFalse(receipt["authority_admitted"])

    def test_new_seed_namespace_is_disjoint_from_original_for_all_roles(self):
        # Derive only immutable identity strings. Never instantiate episodes.
        for role,count in gate.ROLES.items():
            for family in gate.FAMILIES:
                for index in (0,count//2,count-1):
                    old=f"forge-q21-v1:{role}:{family}:{index}".encode()
                    new=f"forge-q21n01-v1:{role}:{family}:{index}".encode()
                    self.assertNotEqual(hashlib.sha256(old).digest(),
                                        hashlib.sha256(new).digest())
                    self.assertNotEqual(old,new)

    def test_original_protocol_preserved_with_closed_original_science(self):
        self.assertEqual(self.original["state"],"FROZEN_DESIGN_ONLY_NOT_EXECUTED")
        self.assertEqual(self.original["source_parent"],
                         "ecbd672f0b3bba34d6e92d2f1475ea6dc80f605f")
        self.assertEqual(self.frozen["predecessor"]["protocol_blob_sha"],
                         gate.LEGACY_PROTOCOL_BLOB)
        self.assertEqual(self.frozen["predecessor"]["negative_q20"],
                         "DEV_NO_GO_RETAIN_NEGATIVE_NO_HELD")

    def test_exact_mutated_scientific_contracts_refused(self):
        mutations=[
            ("identity",lambda x:x.update(scientific_identity="Q21")),
            ("owner",lambda x:x.update(owner="OTHER_AUTHORITY")),
            ("parent",lambda x:x.update(source_parent="0"*40)),
            ("prior",lambda x:x["predecessor"].update(protocol_blob_sha="0"*40)),
            ("legacy_reinterpretation",lambda x:x["predecessor"].update(disposition="EXECUTED")),
            ("seed_reuse",lambda x:x["generator"].update(seed_namespace="forge-q21-v1")),
            ("seed_spec",lambda x:x["generator"].update(initial_seed_spec="unknown")),
            ("sensor_noise",lambda x:x["generator"]["families"][0]["fixed_generator"].update(noise="1/2")),
            ("additional_family",lambda x:x["generator"]["families"].append({"id":"EXTRA"})),
            ("leakage",lambda x:x["roles"].update(training_on_dev="ALLOWED")),
            ("budget",lambda x:x["roles"].update(DEV=129)),
            ("current_control",lambda x:x["comparators"].update(full_current=[])),
            ("epochs",lambda x:x["comparators"]["training"].update(rnn_epochs=61)),
            ("gain_threshold",lambda x:x["development_decision"].update(history_gain_min_each_real_family=0.0)),
            ("null_threshold",lambda x:x["development_decision"].update(null_max_apparent_history_gain=0.2)),
            ("cross_os",lambda x:x["development_decision"].update(cross_os_native_required=["Linux"])),
            ("admission",lambda x:x["admission"].update(current_authorization="APPROVED")),
            ("paid_model",lambda x:x["admission"].update(no_external_paid_models=False)),
            ("extra_controller",lambda x:x["admission"].update(controller="UNQUALIFIED_CONTROLLER")),
            ("separate_repo",lambda x:x["admission"].update(no_cross_project_private_dependencies=False)),
            ("model_claim",lambda x:x["development_decision"].update(not_evidence_of="TRANSFER_PROVEN")),
        ]
        for name,mutation in mutations:
            with self.subTest(name=name):
                item=copy.deepcopy(self.frozen)
                mutation(item)
                with self.assertRaises(gate.ProtocolRefused):
                    gate.validate(item,self.original)

    def test_no_generated_cohorts_or_executable_side_effects(self):
        files=list(Path(gate.HERE).glob("*"))
        self.assertTrue(all(p.suffix in (".json",".py") for p in files))
        code=(gate.HERE/"prereg_guard.py").read_text(encoding="utf-8")
        self.assertNotIn("execute_development(",code)
        self.assertNotIn("generate(",code)
        self.assertNotIn("workflow_dispatch",code)


if __name__=="__main__":
    unittest.main()
