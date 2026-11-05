#!/usr/bin/env python3
"""G96 deterministic bounded admission-policy engine. No inference or network calls."""
from __future__ import annotations
from collections import OrderedDict, Counter
import hashlib, random

CAPACITY=4
BYTE_LIMIT=86_114_304
POLICIES=("no_cache","lru","second_use","frequency","cost_aware")
MIXED_SEED=int.from_bytes(hashlib.sha256(b"CPU_G96_TRAFFIC_20261031").digest()[:8],"big")
OVERFLOW_MARKERS=tuple(f" [G96_OVERFLOW_{i:02d}]" for i in range(4))
THRESHOLDS={"throughput_min":1.15,"min_paired":0.90,"p95_max":1.10,"cpu_max":1.10,"rss_max":1.15}

def build_traffic(stratum, *, cycles=4):
    """Each cycle contains 48 deterministic requests; no model-derived ordering."""
    if stratum=="round_robin":
        one=[p for _ in range(12) for p in range(4)]
    elif stratum=="bursty":
        one=[p for _ in range(3) for p in range(4) for _ in range(4)]
    elif stratum=="overflow":
        one=[p for _ in range(6) for p in range(8)]
    elif stratum=="mixed":
        rng=random.Random(MIXED_SEED)
        one=[rng.randrange(4) if i%4==0 else (i//4)%4 for i in range(48)]
    else:
        raise ValueError("G96_UNKNOWN_STRATUM")
    assert len(one)==48
    return [{"cycle":c,"index":i,"prefix_id":p} for c in range(cycles) for i,p in enumerate(one)]

def traffic_digest(stream):
    import json
    return hashlib.sha256(json.dumps(stream,sort_keys=True,separators=(",",":")).encode()).hexdigest()

class AdmissionCache:
    """Deterministic policy bookkeeping; caller owns immutable KV and exact-key identity."""
    def __init__(self,policy,capacity=CAPACITY,byte_limit=BYTE_LIMIT,*,calibration=None):
        if policy not in POLICIES:raise ValueError("G96_UNKNOWN_POLICY")
        if capacity!=CAPACITY or byte_limit!=BYTE_LIMIT:raise ValueError("G96_BUDGET_DRIFT")
        self.policy=policy;self.capacity=capacity;self.byte_limit=byte_limit
        self.entries=OrderedDict();self.seen=Counter();self.clock=0
        self.hits=self.misses=self.evictions=self.admissions=self.bypasses=0
        self.calibration=dict(calibration or {})
        if policy=="cost_aware":
            if set(self.calibration)!={"prefix_prefill_ns","clone_ns","expected_reuses"}:
                raise ValueError("G96_CALIBRATION_REQUIRED")
            if any(not isinstance(v,(int,float)) or v<0 for v in self.calibration.values()):
                raise ValueError("G96_INVALID_CALIBRATION")
    def resident_bytes(self):return sum(v["bytes"] for v in self.entries.values())
    def keys(self):return list(self.entries)
    def _admit(self,key,bytes_):
        if self.policy=="no_cache":return False
        if self.policy=="second_use":return self.seen[key]>=2
        if self.policy=="frequency":return self.seen[key]>=2
        if self.policy=="cost_aware":
            c=self.calibration
            return self.seen[key]>=2 and c["expected_reuses"]*c["prefix_prefill_ns"]>c["clone_ns"]
        return True
    def _victim(self):
        if self.policy=="frequency":
            return min(self.entries,key=lambda k:(self.seen[k],self.entries[k]["access"],k))
        return next(iter(self.entries))
    def request(self,key,bytes_,build):
        """Build is a callback invoked only on admitted misses; bypass uses full prompt externally."""
        if not isinstance(key,str) or not key:raise ValueError("G96_INVALID_KEY")
        if not isinstance(bytes_,int) or bytes_<0:raise ValueError("G96_INVALID_BYTES")
        self.clock+=1;self.seen[key]+=1
        if key in self.entries:
            self.hits+=1
            item=self.entries.pop(key);item["access"]=self.clock;self.entries[key]=item
            return item["value"],True,False
        self.misses+=1
        if bytes_>self.byte_limit or not self._admit(key,bytes_):
            self.bypasses+=1
            return None,False,False
        # Never evict before successful build; failures leave existing residency unchanged.
        value=build()
        while self.entries and (len(self.entries)>=self.capacity or self.resident_bytes()+bytes_>self.byte_limit):
            victim=self._victim();self.entries.pop(victim);self.evictions+=1
        if self.resident_bytes()+bytes_>self.byte_limit:raise RuntimeError("G96_BYTE_LIMIT")
        self.entries[key]={"value":value,"bytes":bytes_,"access":self.clock}
        self.admissions+=1
        assert len(self.entries)<=self.capacity and self.resident_bytes()<=self.byte_limit
        return value,False,True
