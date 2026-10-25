"""Adversarial DEV-only action budget, no-event reply and cold restart tests."""
import copy
import json
import subprocess
import sys
import unittest
from tw3b_dev_action_slots import DevActionSlots, canonical, digest


def ledger(budget=3):
    return DevActionSlots(session="dev:test-01", actor="npc:0",
                          public_catalog=frozenset({"location:0","location:1"}),
                          action_budget=budget)


def request(destination="location:1"):
    return {"actor":"npc:0","destination":destination}


SILENT = {"started":False,"reason":"already-there"}
STARTED = {"started":True,"journey":{"path":["location:0","SECRET_ROUTE"],
                                        "arrivesAt":999,"seed":"PRIVATE_SEED"}}
BLOCKED = {"started":False,"reason":"full",
           "details":{"capacity":23,"owner":"SECRET_OWNER"}}


class SourceFreeActionBudget(unittest.TestCase):
    def denied(self, reason, fn):
        with self.assertRaisesRegex(ValueError, reason):
            fn()

    def test_01_last_slot_spent_without_event(self):
        x=ledger(1)
        slot=x.reserve(request("location:0"))
        r=x.settle(slot["action_id"],SILENT)
        self.assertEqual(x.used,1)
        self.assertEqual(r["status"],"DEV_SLOT_SETTLED_NOT_DISPATCHED")
        self.denied("FINITE_ACTION_BUDGET",lambda:x.reserve(request()))

    def test_02_private_results_have_identical_public_receipts(self):
        out=[]
        for raw in (SILENT,STARTED,BLOCKED):
            x=ledger(1)
            slot=x.reserve(request())
            out.append(x.settle(slot["action_id"],raw))
        self.assertEqual(out[0],out[1])
        self.assertEqual(out[1],out[2])
        for secret in ("PRIVATE_","SECRET_","already-there","full","path","capacity"):
            self.assertNotIn(secret,str(out))

    def test_03_second_inflight_rejected_without_additional_spend(self):
        x=ledger()
        x.reserve(request())
        before=x.checkpoint()
        self.denied("IN_FLIGHT_OR_UNKNOWN",lambda:x.reserve(request()))
        self.assertEqual(before,x.checkpoint())

    def test_04_wrong_action_id_does_not_clear_pending(self):
        x=ledger()
        r=x.reserve(request())
        before=x.checkpoint()
        self.denied("WRONG_ACTION_ID",lambda:x.settle("0"*64,SILENT))
        self.assertEqual(before,x.checkpoint())
        x.settle(r["action_id"],SILENT)

    def test_05_double_settle_rejected_without_refund(self):
        x=ledger()
        r=x.reserve(request())
        x.settle(r["action_id"],SILENT)
        before=x.checkpoint()
        self.denied("NO_PENDING_ACTION",lambda:x.settle(r["action_id"],SILENT))
        self.assertEqual(before,x.checkpoint())

    def test_06_next_slot_has_different_dev_correlation_id(self):
        x=ledger(2)
        a=x.reserve(request())
        x.settle(a["action_id"],SILENT)
        b=x.reserve(request())
        self.assertNotEqual(a["action_id"],b["action_id"])
        self.assertEqual([a["slot"],b["slot"]],[1,2])

    def test_07_malformed_authored_reply_does_not_modify_state(self):
        x=ledger()
        a=x.reserve(request())
        before=x.checkpoint()
        for raw in (True,{},{"started":"no"}):
            with self.subTest(raw=raw):
                self.denied("SOURCE_RESULT_",lambda:x.settle(a["action_id"],raw))
                self.assertEqual(x.checkpoint(),before)

    def test_08_unknown_catalog_place_or_actor_cannot_reserve(self):
        x=ledger()
        self.denied("DESTINATION_NOT_PUBLIC",lambda:x.reserve(request("location:2")))
        self.denied("ACTOR_CUSTODY",lambda:x.reserve(
            {"actor":"npc:2","destination":"location:1"}))
        self.assertEqual(x.used,0)

    def test_09_actual_new_python_process_recovers_pending_silent_noop(self):
        x=ledger(1)
        first=x.reserve(request("location:0"))
        cmd=("import sys,json; from tw3b_dev_action_slots import DevActionSlots; "
             "v=DevActionSlots.restore(sys.stdin.buffer.read()); "
             "p=v.pending; r=v.settle(p['action_id'], "
             "{'started':False,'reason':'already-there'}); "
             "print(json.dumps({'pending':p,'receipt':r,"
             "'checkpoint':v.checkpoint().decode()},sort_keys=True))")
        outputs=[]
        for _ in range(2):
            child=subprocess.run([sys.executable,"-B","-c",cmd],
                    input=x.checkpoint(),capture_output=True,check=True,timeout=20)
            outputs.append(json.loads(child.stdout))
        self.assertEqual(outputs[0],outputs[1])
        self.assertEqual(outputs[0]["pending"]["action_id"],first["action_id"])
        y=DevActionSlots.restore(outputs[0]["checkpoint"].encode())
        self.assertEqual(y.used,1)
        self.assertIsNone(y.pending)
        self.denied("FINITE_ACTION_BUDGET",lambda:y.reserve(request()))

    def test_10_single_byte_checkpoint_corruption_rejected(self):
        x=ledger()
        x.reserve(request())
        b=bytearray(x.checkpoint())
        i=b.index(b"location:1")
        b[i]=ord("X")
        self.denied("CHECKPOINT_DIGEST",lambda:DevActionSlots.restore(bytes(b)))

    def test_11_recomputed_checksum_does_not_grant_science_authority(self):
        x=ledger()
        data=json.loads(x.checkpoint())
        body=data["body"]
        body["fsa_first_use_admitted"]=True
        forged=canonical({"kind":data["kind"],"body":body,"sha256":digest(body)})
        self.denied("CHECKPOINT_ROLE",lambda:DevActionSlots.restore(forged))

    def test_12_recomputed_checksum_cannot_skip_slot_or_change_destination(self):
        x=ledger()
        x.reserve(request())
        original=json.loads(x.checkpoint())
        for field,value in (("used",2),("pending",{
            "slot":1,"destination":"location:0",
            "action_id":x.pending["action_id"]})):
            body=copy.deepcopy(original["body"])
            body[field]=value
            forged=canonical({"kind":original["kind"],"body":body,
                              "sha256":digest(body)})
            self.denied("CHECKPOINT_",lambda:DevActionSlots.restore(forged))

    def test_13_untrusted_catalog_and_boolean_budget_fail(self):
        for catalog in (frozenset(),frozenset({"loc:market"}),{"location:0"}):
            self.denied("CALLER_SUPPLIED_CATALOG",lambda:DevActionSlots(
                session="dev:example",actor="npc:0",
                public_catalog=catalog,action_budget=2))
        self.denied("ACTION_BUDGET",lambda:ledger(True))

    def test_14_extra_private_or_original_source_fields_fail_closed(self):
        x=ledger()
        snapshot=json.loads(x.checkpoint())
        for key,value in (("source_executed",True),("role","SOURCE_OWNER"),
                          ("source_seed","SECRET")):
            body=copy.deepcopy(snapshot["body"])
            body[key]=value
            forged=canonical({"kind":snapshot["kind"],"body":body,
                               "sha256":digest(body)})
            self.denied("CHECKPOINT_",lambda:DevActionSlots.restore(forged))

    def test_15_cold_restored_exhausted_budget_stays_exhausted(self):
        x=ledger(2)
        for _ in range(2):
            r=x.reserve(request())
            x.settle(r["action_id"],SILENT)
        y=DevActionSlots.restore(x.checkpoint())
        self.assertEqual(y.used,2)
        self.assertEqual(len(y.completed),2)
        self.denied("FINITE_ACTION_BUDGET",lambda:y.reserve(request()))

    def test_16_duplicate_json_fields_fail_closed(self):
        self.denied("CHECKPOINT_JSON",lambda:DevActionSlots.restore(
            b'{"kind":"X","kind":"Y"}'))


if __name__=="__main__":
    unittest.main()
