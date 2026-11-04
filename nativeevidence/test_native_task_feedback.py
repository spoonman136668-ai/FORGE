"""Source-free native receipt boundary and anti-leakage tests."""
import copy
import hashlib
import json
import unittest
from nativeevidence import native_task_feedback as m


def wire(report):
    return json.dumps(report, sort_keys=True, separators=(",", ":")).encode()

def ledger(reward):
    return [{"reward": reward}]

def fixture():
    rows=[]
    for role, reward in (("native", 0.0), ("control", 0.8)):
        events=ledger(reward)
        rows.append(dict(family="fixture", role=role, phase="train", seed=2211101,
            original_selected_actions=1, positive_terminal_rewards=int(reward > 0),
            **{"return": reward}, terminated=True, truncated=False,
            source_ledger=events, source_ledger_sha256=hashlib.sha256(m.canonical(events).removesuffix(b"\n")).hexdigest(),
            elapsed_wall_seconds=0.1))
    return dict(schema="yggdrasil.mg90.empirical-relational-frontier-dev.v1",
                phase="train", scientific_admission="DEV_ONLY_NO_CAUSAL_OR_GENERALIZATION_CLAIM",
                roles=["native", "control"], episodes=rows,
                source_step_counts={"native": 1, "control": 1})

def summary(report, lane="Yggdrasil"):
    raw=wire(report)
    return m.summarize(raw,lane=lane,source_sha="a"*40,
                       expected_sha256=hashlib.sha256(raw).hexdigest())

class TaskFeedbackTests(unittest.TestCase):
    def test_actual_task_failure_and_control_success_remain_distinct(self):
        out=summary(fixture())
        self.assertEqual([r["completed_goals"] for r in out["metrics"]], [0, 1])
        self.assertEqual([r["task_return"] for r in out["metrics"]], [0.0, 0.8])
        self.assertTrue(out["development_training_feedback_available"])
        self.assertFalse(out["optimizer_update_authorized"])
        self.assertFalse(out["all_in_cost_verified"])

    def test_heldout_can_be_reported_but_never_training_feedback(self):
        p=fixture();p["phase"]="heldout"
        for row in p["episodes"]:row["phase"]="heldout"
        self.assertFalse(summary(p)["development_training_feedback_available"])

    def test_source_return_ledger_and_count_must_reconcile(self):
        for mutate in (lambda p:p["episodes"][0].update(source_ledger_sha256="0"*64),
                       lambda p:p["episodes"][0].update(**{"return":1.0}),
                       lambda p:p["source_step_counts"].update(native=2),
                       lambda p:p["episodes"].append(copy.deepcopy(p["episodes"][0])),
                       lambda p:p["episodes"][0].update(positive_terminal_rewards=1)):
            p=fixture();mutate(p)
            with self.assertRaises(m.Rejected):summary(p)

    def test_unknown_schema_identity_bool_and_nonfinite_are_rejected(self):
        p=fixture();raw=wire(p)
        with self.assertRaises(m.Rejected):
            m.summarize(raw,lane="Yggdrasil",source_sha="a"*40,expected_sha256="0"*64)
        for bad in (True, float("inf"), float("nan")):
            p=fixture();p["episodes"][0]["return"]=bad
            with self.assertRaises(ValueError):summary(p)
        p=fixture();p["schema"]="unit-tests-passed"
        with self.assertRaises(m.Rejected):summary(p)
        with self.assertRaises(m.Rejected):summary(fixture(),"Wingless")

    def test_incomplete_wingless_retains_negative_without_fabricated_metrics(self):
        p=dict(schema="wingless.itd02.exact-exposure-incomplete.v1",
            status="INCOMPLETE_SOURCE_EXPOSURE", science="NOT_ACCEPTED",
            comparison_complete=False,evaluation_authorized_by_receipt=False,
            observed_interactions=1,remaining_interactions=255,required_interactions=256,
            completed_episode_records=[{"steps":1}])
        out=summary(p,"Wingless")
        self.assertEqual(out["status"],"INCOMPLETE")
        self.assertEqual(out["metrics"],[])
        self.assertEqual(out["incomplete_exposure"]["remaining"],255)
        self.assertFalse(out["development_training_feedback_available"])
        p["observed_interactions"]=2
        with self.assertRaises(m.Rejected):summary(p,"Wingless")

    def test_wingless_evaluation_outcomes_do_not_enter_training_summary(self):
        p=dict(schema="wingless.itd02.exact-exposure-frozen.v1",science="NOT_ACCEPTED",
            exact_train_interactions_per_arm=2,train={"native":{"episodes":[
                {"steps":2,"return":0,"goal_reached":False}]}},
            evaluation={"native":[{"return":999999,"goal_reached":True}]})
        first=summary(p,"Wingless");p["evaluation"]={"junk":"changed"}
        second=summary(p,"Wingless")
        self.assertEqual(first["metrics"],second["metrics"])
        self.assertEqual(first["metrics"][0]["completed_goals"],0)
        self.assertIsNone(first["metrics"][0]["wall_seconds"])

    def test_duplicate_json_and_oversize_input_are_rejected(self):
        for raw in (b'{"schema":1,"schema":2}', b' '*(m.MAX_BYTES+1)):
            with self.assertRaises(ValueError):
                m.summarize(raw,lane="Wingless",source_sha="a"*40,
                            expected_sha256=hashlib.sha256(raw).hexdigest())

if __name__=="__main__":unittest.main()
