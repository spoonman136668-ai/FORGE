"""Pinned Y065/Y070 public dual-sentinel sampling seam.

The Y065 candidate wrapper calls y64.dual_public_samples directly. Intercept
that boundary, rather than y59.sample (which Y065 shadows). All hooks are
strictly restored even after exceptions. Exactly ten public coordinates.
"""
from contextlib import contextmanager

READ_EPISODES=(0,1,3,5,7)
PUBLIC_BUDGET=10
BASELINE=((0,1),(0,1),(0,1),(2,4),(2,4))

def validate_schedule(schedule):
    if type(schedule) not in (tuple,list) or len(schedule)!=5:
        raise ValueError("F3_PUBLIC_SCHEDULE_SHAPE")
    for pair in schedule:
        if type(pair) not in (tuple,list) or len(pair)!=2:
            raise ValueError("F3_PUBLIC_READ_BUDGET")
        if any(type(a) is not int or a<0 or a>15 for a in pair):
            raise ValueError("F3_PUBLIC_READ_ADDRESS")
        if pair[0]==pair[1]:raise ValueError("F3_DUPLICATE_EPISODE_READ")
    return tuple(tuple(pair) for pair in schedule)

@contextmanager
def install_public_schedule(y070,schedule):
    pairs=validate_schedule(schedule)
    m=y070.m
    native=m.y64.dual_public_samples
    def sampling(seed,family):
        out={}
        for ep,pair in zip(READ_EPISODES,pairs):
            out[ep]={str(a):m.y64.y46.coordinate(a,seed,ep,family,"late_shock") for a in pair}
        if sum(len(x) for x in out.values())!=PUBLIC_BUDGET:
            raise ValueError("F3_PUBLIC_BUDGET")
        return out
    try:
        m.y64.dual_public_samples=sampling
        yield
    finally:
        m.y64.dual_public_samples=native

@contextmanager
def install_public_policy(y070,method,ranking):
    from ygg_learned_policies import choose
    m=y070.m
    native=m.y64.dual_public_samples
    def sampling(seed,family):
        measurements={}
        for ep in READ_EPISODES:
            pair=choose(method,ranking,ep,measurements)
            measurements[ep]={a:m.y64.y46.coordinate(a,seed,ep,family,"late_shock")
                              for a in pair}
        if sum(len(x) for x in measurements.values())!=PUBLIC_BUDGET:
            raise ValueError("F3_POLICY_PUBLIC_BUDGET")
        return {ep:{str(a):v for a,v in group.items()} for ep,group in measurements.items()}
    try:
        m.y64.dual_public_samples=sampling
        yield
    finally:
        m.y64.dual_public_samples=native
