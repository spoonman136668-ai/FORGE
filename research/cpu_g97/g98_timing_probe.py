#!/usr/bin/env python3
"""G98 development-only timing probe for the frozen G96/G97 execution path.

Wraps call boundaries, never edits the cache policy, prompts, tokens or model.
The probe is opt-in and its timings are diagnostic, NOT comparable to frozen
G97 performance thresholds. Do not use for protected held-out cohorts.
"""
import copy
import functools
import time
from contextlib import contextmanager
from pathlib import Path
import sys
from types import SimpleNamespace

G96=Path(__file__).resolve().parents[1]/"cpu_g96"
if str(G96) not in sys.path:sys.path.insert(0,str(G96))
import g96_original_adapter as frozen
from g97_overflow_bypass import OverflowBypassCache
ORIGINAL_ADMISSION_CACHE=frozen.AdmissionCache

PHASES=("prefix_concatenation","cache_request_inclusive","kv_build",
        "kv_clone","cached_decode","fallback_decode")

class Probe:
    def __init__(self,clock=None):
        self.clock=clock or time.perf_counter_ns
        self.events={k:[] for k in PHASES}
        self.cache_policy="lru"
        self.active_cache=None
    def wrap(self,phase,fn):
        @functools.wraps(fn)
        def timed(*args,**kwargs):
            start=self.clock()
            try:return fn(*args,**kwargs)
            finally:self.events[phase].append(self.clock()-start)
        return timed
    def cache_factory(self,policy,calibration=None):
        cache=(OverflowBypassCache() if self.cache_policy=="g97_overflow_bypass"
               else ORIGINAL_ADMISSION_CACHE(policy,calibration=calibration))
        self.active_cache=cache
        original=cache.request
        def request(key,bytes_,build):
            return self.wrap("cache_request_inclusive",original)(
                key,bytes_,self.wrap("kv_build",build))
        cache.request=request
        return cache
    def kv_deepcopy(self,original):
        """Record only copies of the active cache\'s resident KV snapshots."""
        @functools.wraps(original)
        def measured(obj,*args,**kwargs):
            cache=self.active_cache
            if cache is not None and any(
                obj is entry["value"]["past"] for entry in cache.entries.values()):
                return self.wrap("kv_clone",original)(obj,*args,**kwargs)
            return original(obj,*args,**kwargs)
        return measured
    def receipt(self):
        return {"schema":"forge.cpu-g98.timing-probe.v1",
                "phase":"DEVELOPMENT_ONLY","heldout_executed":False,
                "promotion_allowed":False,
                "timing_caveat":"instrumented wall timings include wrapper overhead; nested kv_build is included in cache_request_inclusive",
                "durations_ns":self.events}

@contextmanager
def patched(obj,name,value):
    old=getattr(obj,name)
    setattr(obj,name,value)
    try:yield
    finally:setattr(obj,name,old)

def run_instrumented(model,stream,prefixes,keys,torch,proc,*,probe=None,cache_policy="lru"):
    """Execute the original path, restore all monkeypatches even on exception.

    Caller must use frozen development-only cohort and independently assert
    exact output parity against uninstrumented original-model results.
    """
    from contextlib import ExitStack
    probe=probe or Probe()
    if cache_policy not in ("lru","g97_overflow_bypass"):
        raise ValueError("G98_UNKNOWN_CACHE_POLICY")
    probe.cache_policy=cache_policy
    original_g95=frozen._g95
    g95=SimpleNamespace(**vars(original_g95()))
    g95.baseline_request=probe.wrap("fallback_decode",g95.baseline_request)
    g95.request_decode=probe.wrap("cached_decode",g95.request_decode)
    original_cat = torch.cat
    prefix_ids = {id(p) for p in prefixes}
    suffix_ids = {id(req["suffix"]) for req in stream}
    timed_cat = probe.wrap("prefix_concatenation", original_cat)
    def request_cat(tensors, *args, **kwargs):
        if len(tensors) == 2 and id(tensors[0]) in prefix_ids and id(tensors[1]) in suffix_ids:
            return timed_cat(tensors, *args, **kwargs)
        return original_cat(tensors, *args, **kwargs)
    with ExitStack() as stack:
        stack.enter_context(patched(frozen,"AdmissionCache",probe.cache_factory))
        stack.enter_context(patched(frozen,"_g95",lambda:g95))
        stack.enter_context(patched(torch,"cat",request_cat))
        stack.enter_context(patched(copy,"deepcopy",probe.kv_deepcopy(copy.deepcopy)))
        outputs,metrics=frozen.run_policy(model,stream,prefixes,keys,"lru",torch,proc)
    if len(probe.events["cache_request_inclusive"])!=len(stream):
        raise RuntimeError("G98_INCOMPLETE_CACHE_TIMING")
    if len(probe.events["prefix_concatenation"])!=len(stream):
        raise RuntimeError("G98_INCOMPLETE_PREFIX_TIMING")
    if len(probe.events["cached_decode"])+len(probe.events["fallback_decode"])!=len(stream):
        raise RuntimeError("G98_INCOMPLETE_DECODE_TIMING")
    return outputs,metrics,probe.receipt()
