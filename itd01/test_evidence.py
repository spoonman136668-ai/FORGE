"""ITD-01 negative-first external research-evidence comparison qualification."""
import copy
import json
import unittest

from itd01 import evidence as e


def protocol(lane="Wingless"):
    return {
        "schema": e.PROTOCOL, "study_id": "ITD01-development-001",
        "lane": lane, "target_source_commit": "a" * 40,
        "preregistration_sha256": "1" * 64,
        "preregistered_utc": "2026-10-22T13:00:00Z",
        "source_birth_utc": "2026-10-22T14:00:00Z",
        "external_contract_sha256": "2" * 64,
        "training_cohort_sha256": "3" * 64,
        "development_cohort_sha256": "4" * 64,
        "controls": list(e.CONTROLS),
        "scientific_first_use_authorized": False, "paid_model_calls": 0,
    }


def report(p, candidate_score=87, candidate_cpu=10, hard_fp=0):
    metric = lambda correct, cpu: {
        "correct": correct, "total": 100, "hard_false_positives": 0,
        "all_in_cpu_ms": cpu, "peak_rss_bytes": 1000000, "io_bytes": 500,
        "resident_memory_bytes": 4000, "communication_bytes": 100,
        "restart_cost_ms": 8,
    }
    rows = [
        ("candidate", metric(candidate_score, candidate_cpu)),
        ("trained_bayesian", metric(85, 12)),
        ("trained_recurrent", metric(80, 13)),
        ("trained_symbolic", metric(75, 14)),
    ]
    rows[0][1]["hard_false_positives"] = hard_fp
    return {
        "schema": e.RESULT, "study_id": p["study_id"],
        "lane": p["lane"],
        "target_source_commit": p["target_source_commit"],
        "external_contract_sha256": p["external_contract_sha256"],
        "training_cohort_sha256": p["training_cohort_sha256"],
        "development_cohort_sha256": p["development_cohort_sha256"],
        "measured_utc": "2026-10-22T15:00:00Z",
        "arms": [
            {"name": name, "fully_trained": True,
             "training_cohort_sha256": p["training_cohort_sha256"],
             "development_cohort_sha256": p["development_cohort_sha256"],
             "metrics": metrics} for name, metrics in rows
        ],
        "protected_holdouts_accessed": 0, "scientific_first_use": False,
        "paid_model_calls": 0, "cross_lane_state_shared": False,
    }


class ExternalEvidenceTests(unittest.TestCase):
    def test_same_external_contract_independent_lanes_positive_is_not_science(self):
        results = []
        for lane in e.LANES:
            p = protocol(lane)
            r = report(p)
            out = e.compare_development(p, r)
            self.assertEqual(out["disposition"],
                             "DEVELOPMENT_SIGNAL_INDEPENDENT_REVIEW_REQUIRED")
            self.assertEqual(out["gain_correct_vs_best_trained_control"], 2)
            self.assertFalse(out["scientific_acceptance"])
            self.assertFalse(out["provider_source_birth_authenticated"])
            self.assertFalse(out["independent_first_use_qualified"])
            self.assertFalse(out["automated_task_dispatch"])
            self.assertEqual(out["accepted_ref_mutations"], 0)
            results.append((p, r))
        self.assertEqual(results[0][0]["external_contract_sha256"],
                         results[1][0]["external_contract_sha256"])
        self.assertNotEqual(results[0][0]["lane"], results[1][0]["lane"])

    def test_negative_resource_and_false_positive_not_wins(self):
        p = protocol()
        for kwargs in ({"candidate_score": 84}, {"candidate_cpu": 20},
                       {"hard_fp": 1}):
            with self.subTest(kwargs=kwargs):
                out = e.compare_development(p, report(p, **kwargs))
                self.assertEqual(out["disposition"],
                                 "NEGATIVE_OR_INCONCLUSIVE_RETAIN")
                self.assertFalse(out["scientific_acceptance"])

    def test_preregistered_before_source_birth_and_cohort_isolation(self):
        p = protocol()
        for key, value in (
            ("source_birth_utc", "2026-10-22T12:00:00Z"),
            ("development_cohort_sha256", p["training_cohort_sha256"]),
            ("scientific_first_use_authorized", True),
            ("paid_model_calls", 1),
            ("controls", ["trained_bayesian"]),
            ("target_source_commit", "notasha"),
        ):
            bad = copy.deepcopy(p)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(e.EvidenceRejected):
                e.validate_protocol(bad)

    def test_injected_arms_or_roles_cannot_select_favorable_comparators(self):
        p = protocol()
        r = report(p)
        for mutation in (
            lambda x: x["arms"].pop(),
            lambda x: x["arms"][2].update(name="candidate"),
            lambda x: x["arms"][2].update(fully_trained=False),
            lambda x: x["arms"][2].update(training_cohort_sha256="9" * 64),
            lambda x: x["arms"][0]["metrics"].update(total=101),
            lambda x: x["arms"][0]["metrics"].update(correct=True),
            lambda x: x.update(protected_holdouts_accessed=1),
            lambda x: x.update(scientific_first_use=True),
            lambda x: x.update(paid_model_calls=1),
            lambda x: x.update(cross_lane_state_shared=True),
            lambda x: x.update(lane="Yggdrasil"),
        ):
            bad = copy.deepcopy(r)
            mutation(bad)
            with self.subTest(bad=str(bad)[:65]), self.assertRaises(
                    e.EvidenceRejected):
                e.compare_development(p, bad)

    def test_result_cannot_precede_source_birth(self):
        p = protocol()
        r = report(p)
        r["measured_utc"] = p["preregistered_utc"]
        with self.assertRaises(e.EvidenceRejected):
            e.compare_development(p, r)

    def test_duplicate_keys_and_extra_authority_fields_rejected(self):
        with self.assertRaisesRegex(e.EvidenceRejected, "DUPLICATE_JSON_KEY"):
            e.read_json(b'{"lane":"Wingless","lane":"Yggdrasil"}')
        with self.assertRaisesRegex(e.EvidenceRejected, "INPUT_SIZE"):
            e.read_json(b"x" * 20001)
        p = protocol()
        r = report(p)
        r["approve_science"] = True
        with self.assertRaises(e.EvidenceRejected):
            e.compare_development(p, r)

    def test_complete_deterministic_read_only_comparison(self):
        p = protocol()
        r = report(p)
        before = json.dumps([p, r], sort_keys=True)
        a = e.compare_development(p, r)
        b = e.compare_development(p, r)
        self.assertEqual(a, b)
        self.assertEqual(json.dumps([p, r], sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
