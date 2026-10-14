"""F3 development-only instrumented public sampler integration seam.

Works on the exact Y070/Y065 simulator chain without mutating its checked-out
source. A caller-provided, pre-frozen per-episode read plan replaces only the
public read schedule. Neither plan generation nor sampling can access the
evaluator's hidden physical assignment or the heldout dataset.
"""
from contextlib import contextmanager

READ_EPISODES=(0,1,3,5,7)
PUBLIC_BUDGET=10
RESERVED_ANCHORS=(0,1)

def validate_schedule(schedule):
    if type(schedule) not in (tuple,list) or len(schedule)!=len(READ_EPISODES):
        raise ValueError("F3_PUBLIC_SCHEDULE_SHAPE")
    for addresses in schedule:
        if type(addresses) not in (tuple,list) or len(addresses)!=2:
            raise ValueError("F3_PUBLIC_READ_BUDGET")
        if any(type(a) is not int or a<0 or a>15 for a in addresses):
            raise ValueError("F3_PUBLIC_READ_ADDRESS")
        if addresses[0]==addresses[1]:
            raise ValueError("F3_DUPLICATE_EPISODE_READ")
    if sum(len(pair) for pair in schedule)!=PUBLIC_BUDGET:
        raise ValueError("F3_PUBLIC_READ_BUDGET")
    return tuple(tuple(pair) for pair in schedule)

@contextmanager
def install_public_schedule(y070,schedule):
    """Patch only the pinned simulator's existing public sample transport."""
    schedule=validate_schedule(schedule)
    m=y070.m
    original=m.y59.sample
    original_chain=m.y61.y59.sample
    def sample(seed,family,instrument):
        if instrument!="fixed_rotating_sentinels":
            return original(seed,family,instrument)
        observations={}
        for episode,addresses in zip(READ_EPISODES,schedule):
            observations[episode]={str(a):m.y64.y46.coordinate(a,seed,episode,family,"late_shock")
                                   for a in addresses}
        if sum(len(readings) for readings in observations.values())!=PUBLIC_BUDGET:
            raise ValueError("F3_PUBLIC_BUDGET_DRIFT")
        return observations
    try:
        m.y59.sample=sample
        m.y61.y59.sample=sample
        yield
    finally:
        m.y59.sample=original
        m.y61.y59.sample=original_chain

# Source-native baseline schedule, used to detect instrumentation drift.
BASELINE=((0,1),(0,1),(0,1),(2,4),(2,4))
