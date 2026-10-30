#!/usr/bin/env python3
"""NR-M1O. Reanalyse ONLY an existing MG56 original-world ZIP; never reset/step."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import zipfile

ZIP_SHA = "25575d33723017be52ed57f014c6cea8baaa34bb9bc1616ad876f372d66b2a2c"
SOURCE_SHA = "69dbc08751f65013874eec1c1e32c108fb51fb356820474b1702bf08bae6e019"
ROLES = ("wingless_mg19_unchanged", "yggdrasil_mg19_unchanged")
FAMILIES = ("MiniGrid-KeyCorridorS3R2-v0", "MiniGrid-KeyCorridorS4R3-v0", "MiniGrid-ObstructedMaze-1Dl-v0")

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()

def file_hash(path):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def key(public):
    if set(public)!= {"image","direction","mission"}: raise ValueError("PUBLIC_SHAPE")
    image=public["image"]
    if (len(image)!=7 or any(len(row)!=7 for row in image)
        or not isinstance(public["mission"],str) or not public["mission"]
        or not 0<=public["direction"]<=3): raise ValueError("PUBLIC_INVALID")
    front=image[3][5]
    if len(front)!=3: raise ValueError("FRONT_PUBLIC_INVALID")
    return public["mission"],public["direction"],*front

def native_choice(row,parent):
    # Exact MG28 source-pinned integer Laplace score; hypothetical parent scan.
    n,changed=row[parent]
    parent_score=10000*(changed+1)//(n+2)
    best=None
    high=0
    for a,(count,delta) in enumerate(row):
        if count<3:continue
        score=10000*(delta+1)//(count+2)
        if score>=7500 and score>=parent_score+1000 and score>high:
            best=a
            high=score
    return best if best!=parent else None

def census(receipt):
    source=receipt["source"]
    if (digest(source)!=SOURCE_SHA or receipt["canonical_source_sha256"]!=SOURCE_SHA
        or len(source["original_234_episodes"])!=234
        or source["scientific_first_use"] is not False
        or source["zero_external_actions"] is not True):
        raise ValueError("ORIGINAL_SOURCE_IDENTITY_DRIFT")
    episodes=source["original_234_episodes"]
    records=[]
    for role in ROLES:
        for family in FAMILIES:
            subset=sorted((e for e in episodes if e["role"]==role and e["family"]==family),
                          key=lambda e:e["seed_dev_exposed"])
            if len(subset)!=3 or len({e["seed_dev_exposed"] for e in subset})!=3:
                raise ValueError("SOURCE_ROLE_SEEDS_MISSING")
            memory=defaultdict(lambda:[[0,0] for _ in range(7)])
            m=Counter()
            actions=defaultdict(Counter)
            seen_positive=False
            for episode in subset:
                events=episode["source_events"]
                if (len(events)>192 or len(events)!=episode["original_source_actions"]
                    or digest(events)!=episode["source_events_sha256"]):
                    raise ValueError("SOURCE_EPISODE_DRIFT")
                for t,e in enumerate(events,1):
                    if (e["index"]!=t or e["external_actions"]!=0
                        or e["mission"]!=episode["original_public_mission"]
                        or e["before"]["mission"]!=e["after"]["mission"] or e["before"]["mission"]!=e["mission"]
                        or e["before_sha256"]!=digest(e["before"])
                        or e["after_sha256"]!=digest(e["after"])):
                        raise ValueError("SOURCE_SELECTED_PUBLIC_TAMPER")
                    a=e["action"]
                    reward=e["reward"]
                    if (type(a) is not int or a not in range(7)
                        or type(reward) not in (int,float) or not math.isfinite(reward)
                        or not -1<=reward<=1):
                        raise ValueError("INVALID_SOURCE_SELECTED_REWARD")
                    context=key(e["before"])
                    key(e["after"])
                    stats=memory[context]
                    options={p:native_choice(stats,p) for p in range(7)}
                    supported={p:s for p,s in options.items() if s is not None}
                    if supported:
                        m["eligible_all"]+=1
                        if not seen_positive:m["eligible_before_positive"]+=1
                        alternatives=set(supported.values())
                        m["only_turn_alternatives"]+=int(alternatives.issubset({0,1}))
                        m["nonturn_alternative"]+=int(bool(alternatives-{0,1}))
                        m["historical_selected_matches_alternative"]+=int(a in alternatives)
                        for alt in alternatives:actions[alt]["opportunity"]+=1
                    change=e["before_sha256"]!=e["after_sha256"]
                    actions[a]["selected"]+=1
                    actions[a]["changed"]+=int(change)
                    m["actions"]+=1
                    m["public_changes"]+=int(change)
                    if reward>0:
                        m["positive_rewards"]+=1
                        m["positive_terminal"]+=int(e["terminated"])
                        m["positive_nonterminal"]+=int(not(e["terminated"] or e["truncated"]))
                        seen_positive=True
                    stats[a][0]+=1
                    stats[a][1]+=int(change)
                m["episodes"]+=1
            m["distinct_contexts"]=len(memory)
            records.append({"role":role,"family":family,"seeds":[e["seed_dev_exposed"] for e in subset],
                            **dict(m),"by_action":{str(a):dict(x) for a,x in sorted(actions.items())}})
    return records

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("existing_mg56_original_zip")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    if file_hash(args.existing_mg56_original_zip)!=ZIP_SHA:
        raise ValueError("MG56_ORIGINAL_ARCHIVE_TAMPER")
    with zipfile.ZipFile(args.existing_mg56_original_zip) as archive:
        if not {"first.json","second.json","comparison.log"}.issubset(archive.namelist()):
            raise ValueError("MG56_MISSING_ORIGINAL_PROCESS")
        try:
            import orjson
            loads=orjson.loads
        except ImportError:
            loads=json.loads
        a=loads(archive.read("first.json"))
        rows=census(a)
        del a
        b=loads(archive.read("second.json"))
        if census(b)!=rows:raise ValueError("MG56_INDEPENDENT_SOURCE_DIVERGED")
    result={
      "schema":"nr-m1o-original-native-change-support-v1",
      "classification":"SOURCE_EXPOSED_DEV_HISTORICAL_UPPER_BOUND_NOT_NATIVE_MG28_RETURN",
      "artifact_zip_sha256":ZIP_SHA,"source_canonical_sha256":SOURCE_SHA,
      "both_independent_source_processes_matched":True,
      "rules":"seven hypothetical native parent actions; same public context; >=3 own selected action samples; Laplace >=0.75 and +0.1 margin",
      "no_original_world_actions_executed":True,
      "rows":rows,
      "totals":{k:sum(x.get(k,0) for x in rows) for k in
                ("actions","public_changes","eligible_all","eligible_before_positive",
                 "only_turn_alternatives","nonturn_alternative","positive_rewards","episodes")}
    }
    with open(args.output,"w",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2)
        f.write("\n")
    print(json.dumps(result["totals"],sort_keys=True))
if __name__=="__main__":
    main()
