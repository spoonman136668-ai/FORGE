"""Engineering-only R8 JSON IPC test. No authentic MiniGrid source runs."""
import base64
import json
import os
import subprocess
import unittest

EXE = os.environ.get("ITD02_R8_BRIDGE")
S = {"X":20,"Y":20,"Direction":0,"GoalX":21,"GoalY":22,"FrontBlocked":True}

class Bridge(unittest.TestCase):
    def setUp(self):
        if not EXE:
            self.skipTest("ITD02_R8_BRIDGE unset; requires qualified pinned Go binary")
        self.p = subprocess.Popen([EXE],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    def tearDown(self):
        if hasattr(self,"p"):
            try:
                self.request("quit")
                self.p.communicate(timeout=3)
            except Exception:
                self.p.kill()
                self.p.communicate()
    def request(self,op,**fields):
        self.p.stdin.write(json.dumps({"op":op,**fields},separators=(",",":"))+"\n")
        self.p.stdin.flush()
        line=self.p.stdout.readline()
        self.assertTrue(line,"R8 bridge terminated without response")
        return json.loads(line)
    def test_rejected_load_keeps_active_learner(self):
        before=self.request("snapshot")
        self.assertTrue(before["ok"])
        for bad in ("!bad-base64!",base64.b64encode(b'{"schema":"bad"}').decode()):
            rejected=self.request("load",state=bad)
            self.assertFalse(rejected["ok"])
            self.assertTrue(rejected["error"])
            self.assertEqual(self.request("snapshot")["state"],before["state"])
        chosen=self.request("choose",before=S)
        self.assertTrue(chosen["ok"])
        a=chosen["action"]
        self.assertIn(a,(0,1,2))
        self.assertFalse(self.request("feedback",before=S,action=(a+1)%3,after=S)["ok"])
        after=dict(S)
        if a==0: after["Direction"]=3
        if a==1: after["Direction"]=1
        self.assertTrue(self.request("feedback",before=S,action=a,after=after)["ok"])
        self.assertTrue(self.request("episode_start")["ok"])
        state=self.request("snapshot")
        self.assertTrue(state["ok"])
        self.assertTrue(self.request("load",state=state["state"])["ok"])
        self.assertEqual(self.request("snapshot")["state"],state["state"])
        self.assertTrue(self.request("snapshot_base")["ok"])

if __name__=="__main__":
    unittest.main()
