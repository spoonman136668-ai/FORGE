#!/usr/bin/env python3
"""MG49 public-only calibration of immutable original MG48 source; no new env actions."""
from __future__ import annotations
import argparse,collections,gc,hashlib,json,subprocess,zipfile
from pathlib import Path
from mg48_egocentric_topological_frontier_dev import align,DIRECTIONS
HERE=Path(__file__).resolve().parent
PRE=HERE/"mg49_mg48_alignment_calibration_prereg.json"
PARENT="301cc19ce6ddd5a14c506c85a4ded0c34ca9df2e"
FREEZE="f98e3054ae0633c2359a5110e725feac3e4e7241"
SOURCE_SHA="3ffcd7c6bd21ffea04448c324c174fc3bccdf3ff5ec848d8070bfc4d6e792ed6"
ZIP_SHA="260846dd15ffb4c7fffb5ce52d6dc0143cd8b05f5ceae0d6cafb09817ea79148"
FAMILIES=("MiniGrid-KeyCorridorS3R2-v0","MiniGrid-KeyCorridorS4R3-v0","MiniGrid-ObstructedMaze-1Dl-v0")
SEEDS=((1061101,1061103,1061107),(1061201,1061203,1061207),(1061301,1061303,1061307))
class HashSink:
    def __init__(self):self.h=hashlib.sha256()
    def write(self,s):self.h.update(s.encode("utf8"))
def digest(x):
    sink=HashSink()
    json.dump(x,sink,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)
    return sink.h.hexdigest()
def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],capture_output=True,text=True,check=False)
def frozen():
    p=json.loads(PRE.read_text(encoding="utf8"));q=p["parent"]
    if (p["schema"]!="itd02.mg49.source-authenticated-MG48-public-movement-calibration.v1"
        or p["phase"]!="FROZEN_READ_ONLY_METRICS_BEFORE_DIAGNOSTIC_EXECUTABLE"
        or q["head"]!=PARENT or q["original_artifact"]!=12939245997
        or q["original_run"]!=40968017418 or q["original_episodes"]!=180
        or q["original_actions"]!=33493
        or q["canonical_source_sha256"]!=SOURCE_SHA or q["zip_sha256"]!=ZIP_SHA
        or q["original_negative"]!="MG48_EGOCENTRIC_TOPOLOGICAL_FRONTIER_DEV_NOT_SUPPORTED_NO_SCIENCE"
        or tuple(p["families"])!=FAMILIES
        or tuple(map(tuple,p["seeds"]))!=SEEDS
        or len(p["roles"])!=20 or p["metrics"]["source_processes"]!=2
        or not p["metrics"]["zero_new_original_world_actions"]
        or not all(p["prohibitions"].values())):
        raise ValueError("MG49_FROZEN_ORIGINAL_METRIC_OR_SOURCE_PROTOCOL_CHANGED")
    for sha in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",sha,"HEAD").returncode:
            raise ValueError("MG49_PREREG_NOT_ANCESTOR_OF_EXECUTABLE")
    if git("diff","--quiet",PARENT,"HEAD","--","research/lcrm01/mg48_egocentric_topological_frontier_dev.py").returncode:
        raise ValueError("MG49_ORIGINAL_MG48_POLICY_CHANGED")
    return p
def preflight():
    frozen()
    original={"image":[[[2,0,(i+j)%3] for j in range(7)] for i in range(7)],
              "direction":0,"mission":"pick up the red ball"}
    after={"image":[[[0,0,0] if j==0 else list(original["image"][i][j-1])
             for j in range(7)] for i in range(7)],"direction":0,"mission":original["mission"]}
    a,b=align(original,after,0,0)
    if not(b>=8 and b>=a+3 and DIRECTIONS[0]==(1,0)):
        raise ValueError("MG49_PUBLIC_ONLY_SOURCE_ALIGN_SYNTHETIC_TEST_FAILED")
    print("MG49_FROZEN_READONLY_SOURCE_ONLY_DUAL_OS_PREFLIGHT_PASS")
def front_class(c):
    if c[0]==2:return "wall"
    if c[0]==4 and c[2]!=0:return "nonopen_door"
    if c[0] in (5,6,7):return "object"
    if c[0]==4:return "open_door"
    if c[0] in (1,3,8):return "floor_empty_goal"
    return "other"
def inspect(source,p):
    if (source["classification"]!="MG48_EGOCENTRIC_TOPOLOGICAL_FRONTIER_DEV_NOT_SUPPORTED_NO_SCIENCE"
        or source["original_selected_action_count"]!=33493
        or source["exposed_transfer_DEV_seeds"]!=p["seeds"]
        or source["source_original_Farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or source["scientific_first_use"] is not False
        or source["zero_external_actions"] is not True
        or source["native_models_or_controllers_modified"] is not False):
        raise ValueError("MG49_ORIGINAL_SCIENCE_NEGATIVE_OR_SOURCE_CUSTODY_CHANGED")
    episodes=source["original_180_episodes"]
    roles=p["roles"]
    exp={(f,r,sd) for f,ss in zip(FAMILIES,SEEDS) for r in roles for sd in ss}
    if len(episodes)!=180 or len(exp)!=180:raise ValueError("MG49_ORIGINAL_EPISODES_NOT_180")
    seen=set();out=collections.defaultdict(collections.Counter);selected=[];all_actions=0
    for ep in episodes:
        f=ep["family"];role=ep["role"];sd=ep["seed_dev_exposed"];key=(f,role,sd)
        if key in seen or key not in exp:raise ValueError("MG49_ORIGINAL_ROLE_SEED_MISSING_OR_DUPLICATE")
        seen.add(key);ev=ep["source_events"]
        if (not 1<=len(ev)<=192 or len(ev)!=ep["original_source_actions"]
            or digest(ev)!=ep["source_events_sha256"]
            or digest(ev[0]["before"])!=ep["public_start_sha256"]):
            raise ValueError("MG49_EPISODE_SOURCE_EVENT_DIGEST_NOT_VERIFIED")
        x=y=0;counts=collections.Counter()
        for i,e in enumerate(ev):
            if (e["index"]!=i+1 or e["external_actions"]!=0
                or not 0<=e["action"]<=6 or e["mission"]!=ep["original_public_mission"]
                or digest(e["before"])!=e["before_sha256"]
                or digest(e["after"])!=e["after_sha256"]
                or (i and e["before_sha256"]!=ev[i-1]["after_sha256"])):
                raise ValueError("MG49_UNAUTHENTIC_ORIGINAL_SELECTED_EVENT_CHAIN")
            counts["selected_actions"]+=1
            if e["reward"]>0 and e["terminated"]:counts["positive_goal_steps"]+=1
            if e["action"]!=2:continue
            counts["selected_forward"]+=1
            front=front_class(e["before"]["image"][3][5])
            counts["forward_front_"+front]+=1
            stationary,moved=align(e["before"],e["after"],x,y)
            proxy=(moved>=8 and moved>=stationary+3)
            same=(e["before_sha256"]==e["after_sha256"])
            if same:
                counts["forward_same_entire_public_observation"]+=1
                counts["same_public_front_"+front]+=1
            if front in ("wall","nonopen_door"):counts["forward_public_hard_obstruction"]+=1
            if proxy:
                counts["proxy_grounded"]+=1
                counts["proxy_front_"+front]+=1
                if same:counts["proxy_same_entire_public_observation"]+=1
                if front in ("wall","nonopen_door"):
                    counts["proxy_when_public_hard_obstruction"]+=1
                dx,dy=DIRECTIONS[e["before"]["direction"]];x+=dx;y+=dy
            else:counts["proxy_ambiguous"]+=1
        if (counts["selected_actions"]!=ep["original_source_actions"]
            or counts["positive_goal_steps"]!=ep["original_terminal_goal_rewards"]):
            raise ValueError("MG49_EPISODE_ORIGINAL_ACTION_REWARD_COUNT_DRIFT")
        if role in roles[17:19] and (
            counts["proxy_grounded"]!=ep["source_grounded_forward_alignments"]
            or counts["proxy_ambiguous"]!=ep["source_ambiguous_forward"]):
            raise ValueError("MG49_ORIGINAL_MG48_EGOCENTRIC_ALIGNMENT_REPLAY_NOT_IDENTICAL")
        out[(f,role)].update(counts);all_actions+=counts["selected_actions"]
        if role in (roles[17],roles[18],roles[15],roles[13],roles[0],roles[1]):
            selected.append({"family":f,"role":role,"seed":sd,**dict(counts),
                             "original_topology_overrides":ep.get("source_frontier_overrides",0)})
    if seen!=exp or all_actions!=33493:raise ValueError("MG49_SELECTED_ORIGINAL_ACTION_TOTAL_CHANGED")
    by_family={}
    for family in FAMILIES:
        by_family[family]={}
        for role in roles:
            x=out[(family,role)]
            old=source["per_family_per_role"][family][role]
            if (x["selected_actions"]!=old["actions"] or
                x["positive_goal_steps"]!=old["positive_goal_episodes"]):
                raise ValueError("MG49_ORIGINAL_PER_FAMILY_ROLE_AGGREGATE_DRIFT")
            by_family[family][role]=dict(x)
    return {"episodes":180,"selected_actions":all_actions,
            "per_family_per_role":by_family,"selected_episodes":selected,
            "source_public_only":True,
            "meaning":"Public-image alignment is NOT physical pose; wall/nonopen door before selected forward is source-public obstruction evidence, not privileged inventory."}
def run(archive,out):
    p=preflight()
    with archive.open("rb") as fp:
        if hashlib.file_digest(fp,"sha256").hexdigest()!=ZIP_SHA:
            raise ValueError("MG49_IMMUTABLE_GITHUB_ARCHIVE_SHA_INVALID")
    audit_shas=[];primary=None
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist())!={"comparison.log","first.json","second.json","first.log",
             "second.log","mg33c-synthetic.json","first-resources.json","second-resources.json"}:
            raise ValueError("MG49_ORIGINAL_ARCHIVE_LAYOUT_MISMATCH")
        if SOURCE_SHA not in z.read("comparison.log").decode("utf8"):
            raise ValueError("MG49_ORIGINAL_INDEPENDENT_REPRODUCTION_LOG_MISSING")
        for name in ("first.json","second.json"):
            with z.open(name) as fp:e=json.load(fp)
            if (e["canonical_source_sha256"]!=SOURCE_SHA
                or digest(e["source"])!=SOURCE_SHA):
                raise ValueError("MG49_FULL_ORIGINAL_CANONICAL_PROCESS_HASH_MISMATCH")
            result=inspect(e["source"],p);audit_shas.append(digest(result))
            if primary is None:primary=result
            del e,result;gc.collect()
        if len(set(audit_shas))!=1:
            raise ValueError("MG49_TWO_COMPLETE_SOURCE_REPLAY_AUDITS_NOT_IDENTICAL")
        for name in ("first-resources.json","second-resources.json"):
            with z.open(name) as fp:resource=json.load(fp)
            if (resource["original_source_sha256"]!=SOURCE_SHA
                or len(resource["records"])!=180):
                raise ValueError("MG49_ORIGINAL_RESOURCE_SOURCE_ASSOCIATION_DRIFT")
    result={"schema":"itd02.mg49.readonly-original-MG48-public-calibration.v1",
            "classification":"MG49_MG48_PUBLIC_ALIGNMENT_CALIBRATION_SOURCE_AUDIT_PASS_NO_SCIENCE",
            "original_source_sha256":SOURCE_SHA,"original_zip_sha256":ZIP_SHA,
            "source_processes_independently_verified":2,
            "calibration":primary,"original_world_actions_during_mg49":0,
            "original_MG48_scientific_negative_preserved":True,"scientific_first_use":False}
    result["audit_sha256"]=digest(result)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("MG49_BOTH_ORIGINAL_COMPLETE_SOURCE_PROCESSES_AUTHENTIC",SOURCE_SHA)
    for family in FAMILIES:
        print("MG49_CALIBRATION_CANDIDATE",json.dumps({"family":family,
           **primary["per_family_per_role"][family][p["roles"][17]]},sort_keys=True))
    print("MG49_CANONICAL_CALIBRATION_AUDIT_SHA256",result["audit_sha256"])
    print("MG49_FROZEN_DIAGNOSTIC_CLASSIFICATION",result["classification"])
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--preflight",action="store_true")
    parser.add_argument("--archive",type=Path)
    parser.add_argument("--output",type=Path)
    a=parser.parse_args()
    if a.preflight:preflight();return
    if not a.archive or not a.output:parser.error("--archive and --output required")
    run(a.archive,a.output)
if __name__=="__main__":main()
