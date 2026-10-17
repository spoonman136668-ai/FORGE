"""F121 prospective development-only model, counterfactual and authority tests."""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f121_learned_binding as m
from test_f120_generated_environment import advisory

SRC = "a" * 40

class F121Qualification(unittest.TestCase):
    def setUp(self):
        self.before = os.environ.get("GITHUB_SHA")
        os.environ["GITHUB_SHA"] = SRC

    def tearDown(self):
        if self.before is None:
            os.environ.pop("GITHUB_SHA", None)
        else:
            os.environ["GITHUB_SHA"] = self.before

    def test_preimplementation_frozen_contract_has_exact_immutable_parent(self):
        contract, digest = m.frozen()
        self.assertEqual(m.f120.blob(m.FREEZE.read_bytes().replace(b"\r\n", b"\n")),
                         m.FREEZE_BLOB)
        self.assertEqual(contract["parent_main_commit"],
                         "0eca385586f8d4860a3b0076a880962419bdccc0")
        self.assertEqual(len(digest), 64)
        self.assertTrue(all(contract["authority"].values()))
        self.assertEqual(contract["cohorts"]["training_epochs"], 120)

    def test_counterfactual_has_exact_same_topology_and_variable_marginals(self):
        for vector in ([1, 0, 1], [1, 1, 2], [2, 2, 1], [3, 3, 2]):
            for seed in (92000, 92023, 92100, 92147, 93000, 93147):
                graph = m.paired_graph(seed, vector)
                positive, negative = graph["positive"], graph["negative"]
                self.assertEqual(sorted((e[0], e[1], e[2]) for e in positive),
                                 sorted((e[0], e[1], e[2]) for e in negative))
                slots = lambda edges: sorted(v for edge in edges for v in edge[3:])
                self.assertEqual(slots(positive), slots(negative))
                self.assertTrue(m.f120.binding_solver(graph, positive))
                self.assertFalse(m.f120.binding_solver(graph, negative))
                self.assertTrue(m.f120.role_only(graph, positive))
                self.assertTrue(m.f120.role_only(graph, negative))

    def test_no_final_oracle_answer_enters_local_path_features(self):
        graph = m.paired_graph(92000, [2, 2, 1])
        positive = m.local_features(graph, graph["positive"])
        negative = m.local_features(graph, graph["negative"])
        self.assertEqual(positive, [1, 1])
        self.assertEqual(negative.count(0), 1)
        self.assertEqual(len(positive), len(negative))

    def test_frozen_cohorts_disjoint_both_lanes(self):
        for lane in ("Wingless", "Yggdrasil"):
            self.assertFalse(set(m.COHORTS[lane]["TRAIN"]) &
                             set(m.COHORTS[lane]["CONFIRM"]))
            self.assertEqual(len(m.COHORTS[lane]["TRAIN"]), 24)
            self.assertEqual(len(m.COHORTS[lane]["CONFIRM"]), 48)

    def test_both_models_truly_update_and_keep_disclosed_nonlearned_controls(self):
        candidate = m.f120.validate(advisory(), SRC)["Wingless"][1]
        train = m.records_for(candidate, "Wingless", "TRAIN")
        samples = [(bits, label) for r in train
                   for bits, label in ((r["positive_bits"], 1),
                                       (r["negative_bits"], 0))]
        # Full cohort used for training in the real experiment is both
        # environments. Duplicate here only for the isolated optimizer test.
        all_samples = samples + samples
        for arm in ("A", "B"):
            weights, move = m.train(all_samples, arm)
            self.assertEqual(len(weights), 3 if arm == "A" else 5)
            self.assertGreater(move, 0.001)
            s = m.score(train, arm, weights)
            self.assertEqual(s["pairs"], 24)
            self.assertLessEqual(s["paired_correct"], 24)
        self.assertEqual(m.control(train, "CTRL_ORACLE")["paired_correct"], 24)
        self.assertEqual(m.control(train, "CTRL_ROLE")["paired_correct"], 0)

    def test_full_live_source_only_qualification_two_lanes_both_candidate_environments(self):
        report = m.execute(advisory(), SRC, 100, "pull_request")
        self.assertEqual(report["schema"], m.SCHEMA)
        self.assertEqual(report["models_per_lane"], 2)
        self.assertEqual(report["train_pairs_total"], 96)
        self.assertEqual(report["confirmation_pairs_total"], 192)
        self.assertEqual(len(report["lanes"]), 2)
        for lane in report["lanes"]:
            self.assertEqual(set(lane["train_scores"]), {"A", "B"})
            self.assertEqual(set(lane["confirm_scores"]), {"A", "B"})
            self.assertEqual(len(lane["candidate_source_sha256"]), 2)
            self.assertEqual(set(lane["frozen_untrained_controls"]),
                             {"CTRL_DEPTH2", "CTRL_ROLE", "CTRL_CONSTANT", "CTRL_ORACLE"})
            self.assertIn(lane["selected_train_only_model"], ("A", "B"))
            self.assertEqual(len(lane["confirm_scores"]["A"]), 2)
            self.assertTrue(lane["symbolic_equality_sensor_is_engineered_not_learned"])
            self.assertFalse(lane["independent_scientific_transfer_established"])
            self.assertFalse(lane["confirm_was_used_for_model_selection"])
        self.assertEqual(report["scientific_acceptances"], 0)
        self.assertFalse(report["scientific_first_use_authorized"])
        self.assertEqual(report["optimizer_promotions"], 0)
        self.assertEqual(report["Codex_calls"], 0)
        self.assertFalse(report["new_scheduler"])

    def test_training_choice_has_no_confirmation_access(self):
        a = m.execute(advisory(), SRC, 100, "pull_request")
        original = m.records_for
        def tampered(candidate, lane, phase):
            rows = original(candidate, lane, phase)
            if phase == "CONFIRM":
                for row in rows:
                    row["positive_bits"], row["negative_bits"] = (
                        row["negative_bits"], row["positive_bits"])
            return rows
        with mock.patch.object(m, "records_for", side_effect=tampered):
            b = m.execute(advisory(), SRC, 100, "pull_request")
        self.assertEqual(
            [x["selected_train_only_model"] for x in a["lanes"]],
            [x["selected_train_only_model"] for x in b["lanes"]])
        self.assertEqual(
            [x["weights_from_train_only"] for x in a["lanes"]],
            [x["weights_from_train_only"] for x in b["lanes"]])

    def test_github_identity_fail_closed(self):
        with mock.patch.dict(os.environ, {"GITHUB_SHA": "b"*40}):
            with self.assertRaisesRegex(m.Invalid, "CURRENT_SOURCE_OR_RUN_MISMATCH"):
                m.execute(advisory(), SRC, 100, "pull_request")
        bad = advisory()
        bad["lanes"][0]["public_environment_artifacts"][0]["environment_sha256"] = "f"*64
        with self.assertRaises(m.f120.Invalid):
            m.execute(bad, SRC, 100, "pull_request")

if __name__ == "__main__":
    unittest.main()
