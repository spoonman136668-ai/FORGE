"""F5 nonoracle bounded public-sensor coverage and remembered uncertainty.

Policy sees ONLY earlier public readings. Exact 10 scalar reads across
episodes 0,1,3,5,7: fixed anchor calibration first, 2 nonanchor sensors
at 5 and 2 at 7. No seed, family, hidden swap, evaluator metric or future
observations are passed into the policy. One-trial memory <=4 addresses.
"""
from collections import Counter

PROBES=(0,1,3,5,7)
NONANCHOR=tuple(range(2,16))
BASELINE=((0,1),(0,1),(0,1),(2,4),(2,4))
POLICIES=("F5-FIXED","F5-COVERAGE","F5-MEMORY")
MAX_REMEMBERED=4

def require(value,code):
    if not value:raise ValueError("F5_PUBLIC_"+code)

def validate(history,episode):
    require(type(episode) is int and episode in PROBES,"INVALID_EPISODE")
    require(type(history) is dict,"BAD_HISTORY_TYPE")
    require(set(history).issubset(set(PROBES)),"UNKNOWN_EPISODE")
    require(all(type(t) is int and t<episode for t in history),"FUTURE_OR_CURRENT_LEAK")
    for time,reads in history.items():
        require(type(reads) is dict and len(reads)==2,"READ_COUNT")
        require(all(type(addr) is int and addr in range(16) and type(v) is int and 0<=v<16
                    for addr,v in reads.items()),"PUBLIC_VALUE")
    required=[t for t in PROBES if t<episode]
    require(sorted(history)==required,"INCOMPLETE_PUBLIC_HISTORY")
    for t in required[:3]:
        require(set(history[t])=={0,1},"CALIBRATION_CHANGED")

def calibration(history):
    require(0 in history and 1 in history,"NO_CALIBRATION")
    b0=history[0][0]
    a=(history[0][1]-b0)%16
    d=(history[1][0]-b0)%16
    require(a%2==1 and history[1][1]==(b0+a+d)%16,"INVALID_PUBLIC_CALIBRATION")
    return b0,a,d

def public_start(history):
    # Inferred from 0/1 public calibration only, not from evaluator seed ID.
    b0,a,d=calibration(history)
    return (b0+3*a+5*d)%len(NONANCHOR)

def choose(policy,episode,history):
    require(policy in POLICIES,"POLICY")
    validate(history,episode)
    if episode in (0,1,3):return (0,1)
    if policy=="F5-FIXED":return (2,4)
    start=public_start(history)
    # Minimax geometry over all 91 nonanchor pairs and 14 public start states.
    # It raises worst-case exposure from 5/14 to 7/14; no hidden pair input.
    offsets=(0,1,4,6)
    coords=tuple(NONANCHOR[(start+offset)%14] for offset in offsets)
    if episode==5:return coords[:2]
    require(episode==7,"UNEXPECTED_EPISODE")
    seen=history[5]
    require(set(seen)==set(coords[:2]),"MEMORY_IDENTITY_DRIFT")
    if policy=="F5-COVERAGE":return coords[2:]
    b0,a,d=calibration(history)
    inv=pow(a,-1,16)
    # Public residual only; no swap truth, label or hidden physical address.
    residuals={}
    for cell,value in seen.items():
        physical=(inv*(value-(b0+5*d)))%16
        residuals[cell]=(physical-cell)%16
    if any(residuals.values()):
        # Retained uncertainty: spend late reads confirming observed anomaly.
        return tuple(sorted(seen))
    # No public anomaly yet: scan a fresh pair instead of repeatedly probing
    # an uninformative fixed sentinel.
    return coords[2:]

def sampled_public(history):
    # Recovered remembered addresses are bounded and derived from public inputs.
    addresses=tuple(cell for t in sorted(history) if t in (5,7) for cell in history[t])
    return addresses[:MAX_REMEMBERED]

def audit_trace(policy,observations):
    require(policy in POLICIES,"POLICY")
    require(type(observations) is dict and sorted(observations)==list(PROBES),"TRACE_EPISODES")
    replay={}
    for t in PROBES:
        expected=choose(policy,t,replay)
        actual=observations[t]
        require(tuple(actual)==expected,"CAUSAL_ADDRESS_TRACE")
        replay[t]=actual
    require(sum(len(reads) for reads in replay.values())==10,"TOTAL_READS")
    require(len(sampled_public(replay))<=MAX_REMEMBERED,"MEMORY_BUDGET")
    return {"public_read_budget":10,
            "remembered_addresses":list(sampled_public(replay)),
            "late_unique_addresses":len({x for t in (5,7) for x in replay[t]})}
