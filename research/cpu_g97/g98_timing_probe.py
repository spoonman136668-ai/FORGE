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

G96=Path(__file__).resolve().parents[1]/"cpu_g96"
if str(G96) not in sys.path:sys.path.insert(0,str(G96))
import g96_original_adapter as frozen
from g97_overflow_bypass import OverflowBypassCache

PHASES=("prefix_concatenation","cache_request_inclusive","kv_build",
        "kv_clone","cached_decode","fallback_decode")

class Probe:
    def __init__(self,clock=None):
        self.clock=clock or time.perf_counter_ns
        self.events={k:[] for k in PHASES}
    def wrap(self,phase,fn):
        @functools.wraps(fn)
        def timed(*args,**kwargs):
            start=self.clock()
            try:return fn(*args,**kwargs)
            finally:self.events[phase].append(self.clock()-start)
        return timed
    def cache_factory(self,policy,calibration=None):
        cache=OverflowBypassCache()
        original=cache.request
        def request(key,bytes_,build):
            return self.wrap("cache_request_inclusive",original)(
                key,bytes_,self.wrap("kv_build",build))
        cache.request=request
        return cache
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

def run_instrumented(model,stream,prefixes,keys,torch,proc,*,probe=None):
    """Execute the original path, restore all monkeypatches even on exception.

    Caller must use frozen development-only cohort and independently assert
    exact output parity against uninstrumented original-model results.
    """
    from contextlib import ExitStack
    probe=probe or Probe()
    original_g95=frozen._g95
    g95=original_g95()
    g95.baseline_request=probe.wrap("fallback_decode",g95.baseline_request)
    g95.request_decode=probe.wrap("cached_decode",g95.request_decode)
    with ExitStack() as stack:
        stack.enter_context(patched(frozen,"AdmissionCache",probe.cache_factory))
        stack.enter_context(patched(frozen,"_g95",lambda:g95))
        stack.enter_context(patched(torch,"cat",probe.wrap("prefix_concatenation",torch.cat)))
        stack.enter_context(patched(copy,"deepcopy",probe.wrap("kv_clone",copy.deepcopy)))
        outputs,metrics=frozen.run_policy(model,stream,prefixes,keys,"lru",torch,proc)
    if len(probe.events["cache_request_inclusive"])!=len(stream):
        raise RuntimeError("G98_INCOMPLETE_CACHE_TIMING")
    if len(probe.events["prefix_concatenation"])!=len(stream):
        raise RuntimeError("G98_INCOMPLETE_PREFIX_TIMING")
    if len(probe.events["cached_decode"])+len(probe.events["fallback_decode"])!=len(stream):
        raise RuntimeError("G98_INCOMPLETE_DECODE_TIMING")
    return outputs,metrics,probe.receipt()
