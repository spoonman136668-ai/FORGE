"""ACC-102 interacting local cells; development-only deterministic mechanism.

No protected TEST, rule IDs supplied to learner, global gradient or label sharing.
Message bytes are counted; CPU/RSS and scientific acceptance remain unverified.
"""
from __future__ import annotations
import hashlib
import json
import math
from switching import SCHEMA, TOTAL_STEPS, PRE_STEPS, ADAPT_STEPS

FAST, SLOW, BETA = 0.3, 0.02, 0.25
MODEL_SCHEMA = "forge.acc102.u24.interacting-cells.v1"

def idx(bits):
    if len(bits) != 3 or any(type(v) is not int or v not in (0,1) for v in bits):
        raise ValueError("INVALID_INPUT")
    return 4*bits[0]+2*bits[1]+bits[2]

def encode(value):
    return max(-127,min(127,int(math.floor(max(-1.,min(1.,value))*127+0.5))))

class InteractingCells:
    def __init__(self, mode="connected"):
        if mode not in ("connected","disabled","shuffled"):
            raise ValueError("INVALID_ABLATION")
        self.mode = mode
        self.fast = [0.5]*8
        self.slow = [0.5]*8
        self.count = [0]*8
        self.incoming = [(0,0)]*8
        self.sent_payload_bytes = 0
        self.delivered_payload_bytes = 0
        # Hamming-cube neighbors; shuffled ablation permutes sender endpoints.
        self.edges = tuple(((i ^ 1),(i ^ 4)) for i in range(8))
        if mode == "shuffled":
            self.edges = tuple(((i+1)%8,(i+3)%8) for i in range(8))

    def predict(self,bits):
        i=idx(bits)
        msg=0 if self.mode=="disabled" else sum(self.incoming[i])/254.0
        return int(self.fast[i]+BETA*math.tanh(msg)>0.5)

    def observe(self,visible):
        for bits,target in visible:
            if type(target) is not int or target not in (0,1):
                raise ValueError("INVALID_TARGET")
            i=idx(bits)
            self.fast[i]=(1-FAST)*self.fast[i]+FAST*target
            self.slow[i]=(1-SLOW)*self.slow[i]+SLOW*target
            self.count[i]+=1

    def advance_messages(self):
        """Compute *after* current observations, deliver for next timestep only."""
        if self.mode=="disabled":
            self.incoming=[(0,0)]*8
            return
        flags=[encode(self.fast[i]-self.slow[i]) for i in range(8)]
        self.incoming=[tuple(flags[j] for j in self.edges[i]) for i in range(8)]
        self.sent_payload_bytes+=16
        self.delivered_payload_bytes+=16

    def snapshot(self):
        return json.dumps({"schema":MODEL_SCHEMA,"mode":self.mode,"fast":self.fast,
                           "slow":self.slow,"count":self.count,"incoming":self.incoming,
                           "sent":self.sent_payload_bytes,"delivered":self.delivered_payload_bytes},
                          sort_keys=True,separators=(",",":"),allow_nan=False)

    @classmethod
    def restore(cls,payload):
        obj=json.loads(payload)
        if set(obj)!={"schema","mode","fast","slow","count","incoming","sent","delivered"} or obj["schema"]!=MODEL_SCHEMA:
            raise ValueError("INVALID_STATE")
        model=cls(obj["mode"])
        for field in ("fast","slow"):
            v=obj[field]
            if not isinstance(v,list) or len(v)!=8 or any(type(x) is not float or not 0<=x<=1 for x in v):
                raise ValueError("INVALID_STATE")
            setattr(model,field,v)
        cnt=obj["count"]
        if not isinstance(cnt,list) or len(cnt)!=8 or any(type(x) is not int or x<0 for x in cnt):
            raise ValueError("INVALID_STATE")
        model.count=cnt
        inc=obj["incoming"]
        if not isinstance(inc,list) or len(inc)!=8 or any(not isinstance(pair,list) or len(pair)!=2 or any(type(x) is not int or not -127<=x<=127 for x in pair) for pair in inc):
            raise ValueError("INVALID_STATE")
        model.incoming=[tuple(pair) for pair in inc]
        for name,field in (("sent","sent_payload_bytes"),("delivered","delivered_payload_bytes")):
            val=obj[name]
            if type(val) is not int or val<0: raise ValueError("INVALID_STATE")
            setattr(model,field,val)
        return model

def evaluate(trace,mode="connected"):
    if (trace.get("schema")!=SCHEMA or trace.get("split") not in ("FIT","DEV") or
        trace.get("reserved_test_used") is not False or len(trace.get("records",[]))!=TOTAL_STEPS):
        raise ValueError("UNQUALIFIED_TRACE")
    learner=InteractingCells(mode)
    hits=[0,0,0]; totals=[0,0,0]; restart=False
    for step,row in enumerate(trace["records"]):
        if row.get("step")!=step: raise ValueError("STEP_DRIFT")
        phase=0 if step<PRE_STEPS else (1 if step<PRE_STEPS+ADAPT_STEPS else 2)
        for bits,target in row["queries"]:
            hits[phase]+=learner.predict(bits)==target
            totals[phase]+=1
        learner.observe(row["visible"])
        learner.advance_messages()
        if step==PRE_STEPS+ADAPT_STEPS-1:
            before=learner.snapshot()
            learner=InteractingCells.restore(before)
            restart=learner.snapshot()==before
    return {"schema":MODEL_SCHEMA,"mode":mode,
            "phase_accuracy":[x/y for x,y in zip(hits,totals)],
            "phase_queries":totals,"adapt_error":totals[1]-hits[1],
            "cold_restore_exact":restart,
            "payload_bytes_sent":learner.sent_payload_bytes,
            "payload_bytes_delivered":learner.delivered_payload_bytes,
            "state_sha256":hashlib.sha256(learner.snapshot().encode()).hexdigest(),
            "communication_and_resource_qualified":False,
            "scientific_acceptance":"NOT_GRANTED"}
