"""F8 causal timing control: identical physical sensors, different observation order.

A matched six-nonanchor sensor set removes the F7-versus-F5 sensor-count
confound. Both arms use ten public reads, same decoder, same source, same
physical coordinates; only the episode-3/episode-5 address groups exchange.
The choice uses public calibration only. No hidden swaps or evaluator inputs.
"""
import importlib.util
from pathlib import Path

PARENT=Path(__file__).resolve().parents[1]/"f7_early_coverage"/"policy.py"
spec=importlib.util.spec_from_file_location("f8_immutable_f7_policy",PARENT)
f7=importlib.util.module_from_spec(spec)
spec.loader.exec_module(f7)

ARMS=("F8-F7-EARLY-CONTROL","F8-SAME-SET-3-5-SWAP")
EPISODES=(0,1,3,5,7)
OFFSETS=f7.OFFSETS
CALIBRATION=(0,1)

def require(ok,why):
    if not ok:raise ValueError("F8_PUBLIC_"+why)

def choose(arm,episode,history):
    require(arm in ARMS,"UNKNOWN_ARM")
    require(type(episode) is int and episode in EPISODES,"EPISODE")
    require(type(history) is dict and sorted(history)==[t for t in EPISODES if t<episode],
            "FUTURE_OR_UNAVAILABLE_READS")
    for t,reads in history.items():
        require(type(reads) is dict and len(reads)==2 and
                all(type(k) is int and 0<=k<16 and type(v) is int and 0<=v<16
                    for k,v in reads.items()),"PUBLIC_HISTORY")
    if episode in CALIBRATION:
        return (0,1)
    require(set(history[0])=={0,1} and set(history[1])=={0,1},
            "ANCHOR_CALIBRATION")
    f7.calibration(history)
    start=f7.public_start(history)
    six=tuple(f7.SENSORS[(start+offset)%14] for offset in OFFSETS)
    if arm==ARMS[0]:
        group={3:0,5:2,7:4}[episode]
    else:
        group={3:2,5:0,7:4}[episode]
    return six[group:group+2]

def validate_trace(arm,history):
    require(type(history) is dict and sorted(history)==list(EPISODES),
            "TRACE_SHAPE")
    previous={}
    for t in EPISODES:
        expected=choose(arm,t,previous)
        require(tuple(history[t])==expected,"ADDRESS_DECISION_DRIFT")
        previous[t]=history[t]
    count=sum(map(len,previous.values()))
    addresses=[x for t in (3,5,7) for x in previous[t]]
    require(count==10 and len(set(addresses))==6 and
            all(cell in range(2,16) for cell in addresses),"READ_BUDGET")
    return {"public_reads":count,"distinct_nonanchors":6,
            "observed_set":sorted(addresses),
            "episode_3":list(previous[3]),
            "episode_5":list(previous[5]),
            "episode_7":list(previous[7])}

def matched_sets(a,b):
    require(a["observed_set"]==b["observed_set"],
            "SENSOR_SET_MISMATCH")
    require(a["episode_3"]==b["episode_5"] and
            a["episode_5"]==b["episode_3"] and
            a["episode_7"]==b["episode_7"],"ONLY_TIMING_IS_ALLOWED")
    require(a["public_reads"]==b["public_reads"]==10,"COST_DRIFT")
    return True

common_decoder=f7.common_decoder
