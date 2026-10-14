"""F7: earlier public coverage with the SAME ten-read hardware budget.

F6's historically learned memory policy performed no rechecks. F7 instead
shifts the episode-3 redundant anchor pair to two nonanchor locations,
yielding six distinct late/early observations after sufficient public-only
calibration at 0 and 1. This is hypothesis engineering, NOT new science.
"""
import importlib.util
from pathlib import Path
_f5=Path(__file__).resolve().parents[1]/"f5_native_coverage"/"policy.py"
_spec=importlib.util.spec_from_file_location("f7_frozen_f5_public_policy",_f5)
_parent=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parent)
choose_f5=_parent.choose
calibration=_parent.calibration
public_start=_parent.public_start

POLICIES=("F7-REPLAY-F5-COVERAGE","F7-EARLY-SIX-COVERAGE")
READ_TIMES=(0,1,3,5,7)
SENSORS=tuple(range(2,16))
OFFSETS=(0,1,2,3,5,10)

def must(ok,reason):
    if not ok:raise ValueError("F7_PUBLIC_"+reason)

def select(policy,episode,history):
    must(policy in POLICIES,"POLICY")
    must(type(episode) is int and episode in READ_TIMES,"EPISODE")
    must(type(history) is dict and sorted(history)==
         [t for t in READ_TIMES if t<episode],"CAUSAL_HISTORY")
    for t,reads in history.items():
        must(type(reads) is dict and len(reads)==2 and
             all(type(k) is int and 0<=k<16 and
                 type(v) is int and 0<=v<16 for k,v in reads.items()),
             "PUBLIC_READS")
        must(t<episode,"FUTURE_INPUT")
    if policy=="F7-REPLAY-F5-COVERAGE":
        # Public decoder is common to both arms; exact F5 sampling retained.
        return choose_f5("F5-COVERAGE",episode,history)
    if episode in (0,1):return (0,1)
    must(set(history[0])=={0,1} and set(history[1])=={0,1},
         "CALIBRATION_ADDRESS")
    calibration(history)
    rotation=public_start(history)
    addresses=tuple(SENSORS[(rotation+shift)%14] for shift in OFFSETS)
    index={3:0,5:2,7:4}[episode]
    result=addresses[index:index+2]
    must(len(result)==2 and len(set(result))==2,"DISTINCT_READS")
    return result

def common_decoder(public,episode):
    # Exactly the existing F5 generalized matching decoder but also
    # inspect episode 3 if (and only if) nonanchor measurements exist.
    base=public[0]["0"]
    a=(public[0]["1"]-base)%16
    d=(public[1]["0"]-base)%16
    must(a%2==1 and public[1]["1"]==(base+a+d)%16,
         "DECODER_CALIBRATION")
    inv=pow(a,-1,16)
    found={}
    first=None
    for t in (3,5,7):
        if t>episode:break
        for label,value in public[t].items():
            address=int(label)
            if address<2:continue
            inferred=(inv*(value-(base+t*d)))%16
            if inferred==address:continue
            must(inferred>=2,"DECODER_ANCHOR")
            candidate={address:inferred,inferred:address}
            must(not found or found==candidate,"CONFLICTING_MATCH")
            found=candidate
            if first is None:first=t
    return {"a":a,"b0":base,"d":d,"inverse":inv,
            "detected_pair":found,"first_detection_episode":first}

def verify_observations(policy,readings):
    must(type(readings) is dict and sorted(readings)==list(READ_TIMES),
         "TRACE_TIMES")
    checked={}
    for episode in READ_TIMES:
        decision=select(policy,episode,checked)
        must(tuple(readings[episode])==decision,"SOURCE_OR_ORACLE_DRIFT")
        checked[episode]=readings[episode]
    must(sum(len(v) for v in checked.values())==10,"TEN_SCALARS")
    all_nonanchors=[k for t in (3,5,7) for k in checked[t] if k>=2]
    must(len(set(all_nonanchors))==(6 if policy==POLICIES[1] else 4),
         "COVERAGE_COUNT")
    return {"public_scalar_reads":10,"distinct_nonanchor_addresses":len(set(all_nonanchors)),
            "episode_3":list(checked[3]),"late": [list(checked[t]) for t in (5,7)]}

def geometry_certificate(offsets=OFFSETS):
    must(type(offsets) is tuple and len(offsets)==6 and
         len(set(offsets))==6 and offsets[0]==0 and
         all(type(x) is int and 0<=x<14 for x in offsets),"OFFSETS")
    exposures={}
    for a in range(2,16):
        for b in range(a+1,16):
            count=0
            for start in range(14):
                addresses={(start+x)%14+2 for x in offsets}
                count+=int(a in addresses or b in addresses)
            exposures[f"{a}_{b}"]=count
    return {"pairs":len(exposures),"starts":14,
            "min_visible_starts":min(exposures.values()),
            "max_visible_starts":max(exposures.values()),
            "mean_visible_starts_numerator":sum(exposures.values()),
            "six_early_and_late_nonanchor_reads":6,
            "ten_scalar_reads":10}
