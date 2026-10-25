"""O21-S12 only: exercise authenticated native Go R3 JSONL transport without source environments."""
import base64
import hashlib
import json
import os
import subprocess
import unittest

BIN = os.environ.get("R3_BRIDGE_BINARY")

class NativeBridge:
    def __init__(self):
        if not BIN:
            raise RuntimeError("R3_BRIDGE_BINARY_REQUIRED")
        self.p = subprocess.Popen(
            [BIN],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True,bufsize=1)
    def call(self,**payload):
        assert self.p.poll() is None
        self.p.stdin.write(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n")
        self.p.stdin.flush()
        line=self.p.stdout.readline()
        if not line:
            raise AssertionError("Native process exited before reply")
        return json.loads(line)
    def close(self):
        if self.p.poll() is None:
            result=self.call(op="quit")
            assert result.get("ok") is True, result
            self.p.stdin.close()
            self.p.wait(timeout=10)
        assert self.p.returncode == 0, self.p.stderr.read()
        assert self.p.stdout.read() == ""

def state(x=20,blocked=False):
    return {"x":x,"y":20,"goal_x":22,"goal_y":20,
            "direction":0,"front_blocked":blocked}

class OriginalNativeR3Transport(unittest.TestCase):
    def setUp(self):
        self.b=NativeBridge()
    def tearDown(self):
        self.b.close()

    def teach(self,n=4,terminal=False):
        for k in range(n):
            out=self.b.call(op="learn",before=state(),action=2,after=state(21),
                            reward=0.0,terminal=terminal)
            self.assertEqual((out["ok"],out["updates"]),(True,k+1))

    def test_no_issued_source_actions_and_evidence_threshold(self):
        c=self.b.call(op="choose",before=state())
        self.assertTrue(c["ok"])
        self.assertIn(c["action"],(0,1,2))
        self.assertEqual(c.get("updates"),0)
        p=self.b.call(op="predict",before=state(),action=2)
        self.assertTrue(p["ok"]);self.assertFalse(p["reliable"])
        self.assertNotIn("predicted",p)
        self.teach(3)
        self.assertFalse(self.b.call(op="predict",before=state(),action=2)["reliable"])
        self.b.call(op="learn",before=state(),action=2,after=state(21),reward=0,terminal=False)
        p=self.b.call(op="predict",before=state(),action=2)
        self.assertTrue(p["reliable"])
        self.assertEqual(p["predicted"]["x"],21)
        self.assertEqual(p["updates"],4)

    def test_rejected_updates_and_forged_state_cannot_mutate(self):
        self.teach()
        original=self.b.call(op="snapshot")["state"]
        for bad in [
            {"op":"learn","before":state(),"action":3,"after":state(21),"reward":0,"terminal":False},
            {"op":"learn","before":state(),"action":2,"after":state(25),"reward":0,"terminal":False},
            {"op":"invalid"},
            {"op":"choose","before":{**state(),"x":65}},
            {"op":"load","state":"not base64"},
            {"op":"load","state":base64.b64encode(b'{"schema":"forged"}').decode()}
        ]:
            out=self.b.call(**bad)
            self.assertFalse(out["ok"],bad)
            self.assertTrue(out.get("error"),bad)
            self.assertEqual(self.b.call(op="snapshot")["state"],original)

    def test_real_cold_os_process_restore(self):
        self.teach(4,terminal=False)
        before=self.b.call(op="choose",before=state(20,True))
        save=self.b.call(op="snapshot")
        self.assertTrue(save["ok"])
        self.assertEqual(save["updates"],4)
        raw=base64.b64decode(save["state"],validate=True)
        env=json.loads(raw)
        self.assertEqual(env["schema"],"wingless.itd02.r3.local-action-conditioned-transition-state.v1")
        self.assertEqual(env["data"]["completed_events"],4)
        self.assertEqual(sum(row["samples"] for row in env["data"]["learned_effects"]),4)
        fresh=NativeBridge()
        try:
            self.assertEqual(fresh.call(op="choose",before=state())["updates"],0)
            restored=fresh.call(op="load",state=save["state"])
            self.assertTrue(restored["ok"])
            self.assertEqual(restored["updates"],4)
            self.assertEqual(fresh.call(op="snapshot")["state"],save["state"])
            self.assertEqual(fresh.call(op="choose",before=state(20,True))["action"],before["action"])
        finally:
            fresh.close()

    def test_unknown_fields_and_multiple_json_values_rejected(self):
        self.assertFalse(self.b.call(op="choose",before=state(),private_hidden_goal=42)["ok"])
        self.assertEqual(self.b.call(op="snapshot")["updates"],0)
        self.b.p.stdin.write('{"op":"quit"} {"op":"learn"}\n')
        self.b.p.stdin.flush()
        out=json.loads(self.b.p.stdout.readline())
        self.assertFalse(out["ok"])
        self.assertEqual(self.b.call(op="snapshot")["updates"],0)

if __name__=="__main__":
    unittest.main()
