import copy
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import f87_existing_owner_wake as f


class ExistingOwnerWake(unittest.TestCase):
    def setUp(self):
        self.run = {
            "id": f.RUN, "run_attempt": 1,
            "name": "Headless deterministic research loop wake v2",
            "event": "workflow_dispatch", "path": f.PATH,
            "head_branch": "main", "head_sha": f.SOURCE,
            "head_repository": {"full_name": f.REPO},
            "repository": {"full_name": f.REPO},
            "status": "completed", "conclusion": "success"
        }
        steps = [{"number": i, "name": "unrelated step " + str(i),
                  "status": "completed", "conclusion": "success"}
                 for i in range(1, 54)]
        for i, title in enumerate(f.OBSERVED, 38):
            steps[i] = {"number": i + 1, "name": title,
                        "status": "completed", "conclusion": "skipped"}
        self.jobs = {"jobs": [{
            "id": 117064918804, "run_id": f.RUN, "run_attempt": 1,
            "name": "wake", "status": "completed", "conclusion": "success",
            "steps": steps
        }]}

    def test_real_shape_stays_observation_only(self):
        o = f.audit(self.run, self.jobs)
        self.assertEqual(o, f.audit(self.run, self.jobs))
        self.assertEqual(o["run_id"], f.RUN)
        self.assertEqual(len(o["source_steps"]), 7)
        self.assertEqual([s["stage"] for s in o["source_steps"]],
                         list(f.OBSERVED.values()))
        for k in ("complete_owner_lease_history_qualified",
                  "independent_preoutcome_owner_witness_qualified",
                  "current_firstuse_availability_proven",
                  "firstuse_dispatch_authorized",
                  "dream_rsi_pareto_activation_authorized",
                  "cloudflare_written", "controller_mutated"):
            self.assertIs(o[k], False)

    def test_run_identity_drift_fails_closed(self):
        changes = {
            "id": f.RUN + 1, "head_sha": "0" * 40, "path": "other.yml",
            "head_branch": "unqualified", "run_attempt": 2,
            "status": "in_progress", "conclusion": "failure",
            "event": "schedule", "repository": {"full_name": "other/repo"},
            "head_repository": {"full_name": "other/repo"}
        }
        for k, v in changes.items():
            with self.subTest(key=k):
                r = copy.deepcopy(self.run)
                r[k] = v
                with self.assertRaises(f.Blocked):
                    f.audit(r, self.jobs)

    def test_job_and_step_drifts_fail_closed(self):
        tests = [
            lambda j: j["jobs"][0].update(run_id=f.RUN + 1),
            lambda j: j["jobs"][0].update(run_attempt=2),
            lambda j: j["jobs"][0].update(conclusion="failure"),
            lambda j: j["jobs"][0]["steps"].pop(),
            lambda j: j["jobs"][0]["steps"][38].update(conclusion="success"),
            lambda j: j["jobs"][0]["steps"][38].update(name="unknown"),
            lambda j: j["jobs"][0]["steps"][38].update(status="in_progress"),
            lambda j: j["jobs"][0]["steps"][39].update(
                number=j["jobs"][0]["steps"][38]["number"]),
            lambda j: j["jobs"].append(copy.deepcopy(j["jobs"][0]))
        ]
        for i, mutation in enumerate(tests):
            with self.subTest(case=i):
                j = copy.deepcopy(self.jobs)
                mutation(j)
                with self.assertRaises(f.Blocked):
                    f.audit(self.run, j)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[]' + b' '*2000001):
            with self.subTest(raw=raw[:22]):
                with self.assertRaises((f.Blocked, ValueError)):
                    f.strict_json(raw)
        obj = f.strict_json(json.dumps(self.run).encode())
        self.assertEqual(obj["head_sha"], f.SOURCE)


if __name__ == "__main__":
    unittest.main()
