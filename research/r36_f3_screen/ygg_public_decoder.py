"""F3 development-only public-read-aware decoder adapter.

The pinned Y060 decoder reads only fixed physical public cells 2/4.
Candidate F3 policies reallocate public reads, so their observations
cannot influence the pinned decoder unless the adapter consumes the
ACTUAL observed public addresses. This module observes only the
ten public scalars and never transposition truth, onset or evaluator state.
Not admitted as a new scientific original or winner.
"""
from contextlib import contextmanager

def decode_public(observed,episode):
    b0=observed[0]["0"]
    a=(observed[0]["1"]-b0)%16
    d=(observed[1]["0"]-b0)%16
    if a%2!=1 or observed[1]["1"]!=(b0+d+a)%16:
        raise ValueError("F3_PUBLIC_CALIBRATION_DRIFT")
    inverse=pow(a,-1,16)
    detected={}
    first=None
    for t in (5,7):
        if t>episode:break
        for label,value in observed[t].items():
            address=int(label)
            if address in (0,1):
                continue
            inferred=(inverse*(value-(b0+t*d)))%16
            if inferred==address:
                continue
            if inferred in (0,1):
                raise ValueError("F3_NONANCHOR_PUBLIC_INFERRED_ANCHOR")
            proposal={address:inferred,inferred:address}
            if detected and detected!=proposal:
                raise ValueError("F3_SECOND_INDEPENDENT_SWAP")
            detected=proposal
            if first is None:first=t
    return {"a":a,"b0":b0,"d":d,"inverse":inverse,
            "detected_pair":detected,"first_detection_episode":first}

@contextmanager
def install_public_decoder(y070):
    m=y070.m
    native=m.y61.y60.public_decoder
    try:
        m.y61.y60.public_decoder=decode_public
        yield
    finally:
        m.y61.y60.public_decoder=native
