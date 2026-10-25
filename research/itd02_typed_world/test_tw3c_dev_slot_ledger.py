#!/usr/bin/env python3
"""TW3C DEV-only falsifiers for source-shaped slot reservation and cold replay."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tw3c_dev_slot_ledger import DevSlotLedger, ROLE, _canonical


def fresh(total=2):
    return DevSlotLedger("npc:0", frozenset(("location:0", "location:1")),
                         total, "DEV-TW3C-SOURCE-FREE")


def intent(dest="location:1"):
    return {"actor": "npc:0", "destination": dest}


def recorded(kind="travel.departed"):
    return {"id": 17, "tick": 11, "type": kind, "actors": ["npc:0"],
            "data": {"traveller": "npc:0", "at": "location:0",
                     "arrivesAt": 900, "route": ["location:SECRET"]},
            "causes": [333], "location": "location:0"}


def noop():
    return {"started": False, "reason": "already-there",
            "hidden_seed": "PRIVATE", "future_route": ["location:4"]}


class TW3CSlots(unittest.TestCase):
    def rejects(self, code, callback):
        with self.assertRaisesRegex(ValueError, code):
            callback()

    def test_01_source_free_role(self):
        self.assertEqual(ROLE, "TW3C_HANDCRAFTED_DEV_NO_REAL_DISPATCH")

    def test_02_reserve_one_slot(self):
        x = fresh()
        r = x.reserve(intent())
        self.assertEqual(r["slot"], 1)
        self.assertEqual(x.issued, 1)
        self.assertEqual(r["remaining"], 1)
        self.assertFalse(r["source_executed"])

    def test_03_cannot_reserve_second_in_flight(self):
        x = fresh()
        x.reserve(intent())
        self.rejects("IN_FLIGHT_OR_UNKNOWN", lambda: x.reserve(intent()))
        self.assertEqual(x.issued, 1)

    def test_04_no_event_already_there_is_settled(self):
        x = fresh()
        token = x.reserve(intent("location:0"))["token"]
        r = x.settle(token, noop(), [])
        self.assertEqual(r["slot"], 1)
        self.assertEqual(x.completed, [1])
        self.assertIsNone(x.inflight)

    def test_05_no_event_consumes_slot_without_refund(self):
        x = fresh(1)
        token = x.reserve(intent("location:0"))["token"]
        x.settle(token, noop(), ())
        self.assertEqual(x.issued, 1)
        self.rejects("FINITE_ACTION_BUDGET", lambda: x.reserve(intent()))

    def test_06_started_result_matches_departure(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        r = x.settle(token, {"started": True, "journey": {
            "path": ["location:0", "location:1"], "cost": 123}},
            [recorded()])
        self.assertEqual(r["revealed_private_fields"], 0)
        self.assertFalse(r["event_attribution_authenticated"])

    def test_07_blocked_requires_recorded_block_event(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        r = x.settle(token, {"started": False, "reason": "forbidden",
                             "details": {"capacity": 1}},
                     [recorded("travel.blocked")])
        self.assertEqual(r["slot"], 1)

    def test_08_public_receipt_same_on_all_outcomes(self):
        answers = []
        for source_result, events in (
            (noop(), ()),
            ({"started": False, "reason": "full",
              "details": {"secret": "PRIVATE"}}, (recorded("travel.blocked"),)),
            ({"started": True, "journey": {"secret": "PRIVATE"}}, (recorded(),)),
        ):
            x = fresh()
            token = x.reserve(intent())["token"]
            answers.append(x.settle(token, source_result, events))
        self.assertEqual(answers[0], answers[1])
        self.assertEqual(answers[1], answers[2])
        self.assertNotIn("PRIVATE", str(answers))

    def test_09_started_without_event_denied_atomically(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        self.rejects("DEPARTED_EVENT_REQUIRED",
                     lambda: x.settle(token, {"started": True}, []))
        self.assertEqual(x.completed, [])
        self.assertIsNotNone(x.inflight)

    def test_10_blocked_without_event_denied(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        self.rejects("BLOCKED_EVENT_REQUIRED",
                     lambda: x.settle(token, {"started": False,
                                              "reason": "no-route"}, []))
        self.assertEqual(x.completed, [])

    def test_11_noop_with_fake_event_denied(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        self.rejects("NO_EVENT_EXPECTED",
                     lambda: x.settle(token, noop(), [recorded()]))
        self.assertEqual(x.completed, [])

    def test_12_second_settlement_replay_denied(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        x.settle(token, noop(), ())
        self.rejects("NO_PENDING_SLOT", lambda: x.settle(token, noop(), []))

    def test_13_wrong_token_denied_without_mutation(self):
        x = fresh()
        x.reserve(intent())
        self.rejects("TOKEN_MISMATCH", lambda: x.settle("forged", noop(), []))
        self.assertEqual(x.issued, 1)
        self.assertEqual(x.completed, [])

    def test_14_other_actor_event_denied(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        e = recorded()
        e["actors"] = ["npc:1"]
        self.rejects("SOURCE_SHAPED_EVENT_MISMATCH",
                     lambda: x.settle(token, {"started": True}, [e]))

    def test_15_wrong_event_type_denied(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        self.rejects("SOURCE_SHAPED_EVENT_MISMATCH",
                     lambda: x.settle(token, {"started": True},
                                      [recorded("travel.arrived")]))

    def test_16_bool_event_id_denied(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        e = recorded()
        e["id"] = True
        self.rejects("SOURCE_SHAPED_EVENT_MISMATCH",
                     lambda: x.settle(token, {"started": True}, [e]))

    def test_17_negative_tick_denied(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        e = recorded()
        e["tick"] = -1
        self.rejects("SOURCE_SHAPED_EVENT_MISMATCH",
                     lambda: x.settle(token, {"started": True}, [e]))

    def test_18_invalid_result_denied(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        self.rejects("OUTCOME_SCHEMA", lambda: x.settle(token, {}, ()))

    def test_19_extra_action_fields_do_not_consume_slot(self):
        x = fresh()
        bad = dict(intent(), seed="hidden")
        self.rejects("EXACT_REQUEST_FIELDS", lambda: x.reserve(bad))
        self.assertEqual(x.issued, 0)

    def test_20_unknown_public_destination_does_not_consume(self):
        x = fresh()
        self.rejects("DESTINATION_NOT_PUBLIC",
                     lambda: x.reserve(intent("location:999")))
        self.assertEqual(x.issued, 0)

    def test_21_full_budget_multiple_distinct_tokens(self):
        x = fresh(2)
        first = x.reserve(intent())["token"]
        x.settle(first, noop(), [])
        second = x.reserve(intent("location:0"))["token"]
        self.assertNotEqual(first, second)
        self.assertEqual(x.issued, 2)
        x.settle(second, noop(), [])
        self.rejects("FINITE_ACTION_BUDGET", lambda: x.reserve(intent()))

    def test_22_restore_pending_cannot_issue_again(self):
        x = fresh()
        x.reserve(intent())
        y = DevSlotLedger.restore(x.snapshot())
        self.rejects("IN_FLIGHT_OR_UNKNOWN", lambda: y.reserve(intent()))

    def test_23_restore_completed_preserves_consumption(self):
        x = fresh(1)
        x.settle(x.reserve(intent())["token"], noop(), [])
        y = DevSlotLedger.restore(x.snapshot())
        self.assertEqual((y.issued, y.completed), (1, [1]))
        self.rejects("FINITE_ACTION_BUDGET", lambda: y.reserve(intent()))

    def test_24_reject_corrupted_checksum(self):
        x = fresh()
        serialized = x.snapshot()
        self.rejects("SNAPSHOT_CHECKSUM",
                     lambda: DevSlotLedger.restore(serialized.replace(
                         '"issued":0', '"issued":1')))

    def test_25_reject_forged_pending_even_with_new_checksum(self):
        x = fresh()
        e = json.loads(x.snapshot())
        e["state"]["issued"] = 1
        e["sha256"] = hashlib.sha256(
            _canonical(e["state"]).encode("utf-8")).hexdigest()
        self.rejects("SNAPSHOT_PENDING_MISSING",
                     lambda: DevSlotLedger.restore(_canonical(e)))

    def test_26_reject_duplicated_json_key(self):
        x = fresh()
        text = x.snapshot().replace('"sha256":', '"sha256":"fake","sha256":')
        self.rejects("SNAPSHOT_JSON", lambda: DevSlotLedger.restore(text))

    def test_27_reject_invalid_pending_token_after_new_checksum(self):
        x = fresh()
        x.reserve(intent())
        e = json.loads(x.snapshot())
        e["state"]["inflight"]["token"] = "fake"
        e["sha256"] = hashlib.sha256(
            _canonical(e["state"]).encode("utf-8")).hexdigest()
        self.rejects("SNAPSHOT_PENDING",
                     lambda: DevSlotLedger.restore(_canonical(e)))

    def test_28_no_raw_journey_in_checkpoint(self):
        x = fresh()
        x.reserve(intent())
        s = x.snapshot()
        self.assertNotIn("arrival", s)
        self.assertNotIn("route", s)
        self.assertNotIn("SECRET", s)
        self.assertNotIn("PRIVATE", s)

    def test_29_raw_result_does_not_escape_through_checkpoint(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        x.settle(token, {"started": False, "reason": "already-there",
                         "secret": "PRIVATE"}, [])
        self.assertNotIn("PRIVATE", x.snapshot())
        self.assertNotIn("already-there", x.snapshot())

    def test_30_no_dispatched_source_claim(self):
        x = fresh()
        r = x.reserve(intent())
        self.assertFalse(r["source_executed"])
        self.assertFalse(r["owner_authorized"])
        self.assertFalse(x.settle(r["token"], noop(), [])["scientific_go"])

    def test_31_cold_separate_process_resume_noop(self):
        x = fresh(1)
        token = x.reserve(intent("location:0"))["token"]
        with tempfile.TemporaryDirectory(prefix="tw3c_dev_") as directory:
            path = Path(directory) / "checkpoint.json"
            path.write_text(x.snapshot(), encoding="utf-8")
            code = (
                "import json,sys; from pathlib import Path; "
                "from tw3c_dev_slot_ledger import DevSlotLedger; "
                "p=Path(sys.argv[1]); x=DevSlotLedger.restore(p.read_text()); "
                "r=x.settle(sys.argv[2],"
                "{'started':False,'reason':'already-there'},[]); "
                "p.write_text(x.snapshot()); print(json.dumps(r))"
            )
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       PYTHONNOUSERSITE="1",
                       PYTHONPATH=str(Path(__file__).resolve().parent))
            child = subprocess.run(
                [sys.executable, "-B", "-c", code, str(path), token],
                capture_output=True, text=True, env=env,
                cwd=directory, check=False)
            self.assertEqual(child.returncode, 0, child.stderr)
            result = json.loads(child.stdout)
            self.assertEqual(result["slot"], 1)
            resumed = DevSlotLedger.restore(path.read_text(encoding="utf-8"))
            self.assertEqual(resumed.completed, [1])
            self.rejects("FINITE_ACTION_BUDGET",
                         lambda: resumed.reserve(intent()))

    def test_32_pending_destination_preserved_across_restart(self):
        x = fresh()
        x.reserve(intent("location:1"))
        y = DevSlotLedger.restore(x.snapshot())
        self.assertEqual(y.inflight["destination"], "location:1")

    def test_33_no_refund_even_if_already_there_zero_event(self):
        x = fresh(1)
        token = x.reserve(intent("location:0"))["token"]
        x.settle(token, noop(), [])
        self.assertEqual(x.issued, x.total)
        self.assertEqual(x.completed, [1])

    def test_34_failed_event_match_does_not_release_slot(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        self.rejects("SOURCE_SHAPED_EVENT_MISMATCH",
                     lambda: x.settle(token, {"started": True},
                                      [recorded("travel.blocked")]))
        self.assertEqual(x.inflight["token"], token)

    def test_35_final_receipt_never_contains_token(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        r = x.settle(token, noop(), [])
        self.assertNotIn(token, json.dumps(r))

    def test_36_invalid_run_id_denied(self):
        self.rejects("DEV_RUN_ID",
                     lambda: DevSlotLedger("npc:0",
                         frozenset(("location:0",)), 1, "PRODUCTION"))

    def test_37_no_private_outcome_in_completed_receipt(self):
        x = fresh()
        token = x.reserve(intent())["token"]
        r = x.settle(token, {"started":False,"reason":"blocked",
                             "details":{"seed":"SECRET_GENERATOR"}}, 
                     [recorded("travel.blocked")])
        self.assertNotIn("SECRET_GENERATOR", str(r))
        self.assertEqual(r["revealed_private_fields"], 0)


if __name__ == "__main__":
    unittest.main()
