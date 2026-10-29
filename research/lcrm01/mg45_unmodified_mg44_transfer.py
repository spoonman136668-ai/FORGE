#!/usr/bin/env python3
"""MG45: unchanged MG44 original-source family transfer, never native promotion.

No candidate code copied, extended, tuned or monkeypatched. Public-domain
Farama original source and previously qualified source-selected actors only.
Fresh DEV transfer, NOT independently sealed heldout scientific acceptance.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math,subprocess,time,traceback
from pathlib import Path

from mg39b_original_affordance_ablation import (
    UPSTREAM,digest,event_metric,mg33_episode,mg34_episode,corrected_class,
    control_episode,original_mg38_episode,ablated_episode)
from mg40_action_precondition_dev import evidence_episode
from mg42_observed_reversal_guard import reversal_episode
from mg43_public_target_action_value import action_value_episode
from mg44_public_precondition_release import (
    PublicSlotRelease,public_release_episode,synthetic_source_preflight
    as original_mg44_preflight)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg45_unmodified_mg44_transfer_prereg.json"
PARENT="45705eab3c82b663dac9045ff762e07dc4b22004"
FREEZE="5106679ab09ec4c6c862600656f9b00a00dcb026"
POLICY_BLOB="2f93b9b5227d97d318cf5c05544f85c303496da7"
REGISTER_BLOB="41b4a731255d19bdf61072b7100e752a759a3ae4"
FAMILIES=("MiniGrid-KeyCorridorS3R2-v0",
          "MiniGrid-KeyCorridorS4R3-v0",
          "MiniGrid-ObstructedMaze-1Dl-v0")
ENTRIES=("minigrid.envs:KeyCorridorEnv","minigrid.envs:KeyCorridorEnv",
         "minigrid.envs:ObstructedMaze_1Dlhb")
SEEDS=((1041101,1041103,1041107),(1041201,1041203,1041207),
       (1041301,1041303,1041307))
ROLES=("wingless_mg19_unchanged","yggdrasil_mg19_unchanged",
 "mg33_public_history_frontier_unchanged",
 "mg34_graph_lookahead_unchanged",
 "mg33c_actiononly_ucb_exact_source",
 "mg33c_actiononly_round_robin_exact_source",
 "mg38_generic_affordance_prior_enabled_exact_source",
 "mg39b_generic_affordance_prior_removed",
 "mg40_precondition_memory_enabled_unchanged",
 "mg40_precondition_memory_ablated_unchanged",
 "mg42_observed_reversal_guard_unchanged",
 "mg43_engineered_target_matcher_plus_learned_action_value_unchanged",
 "mg43_engineered_target_matcher_no_action_value_ablation_unchanged",
 "mg44_public_precondition_release_enabled_UNMODIFIED",
 "mg44_public_precondition_release_disabled_UNMODIFIED",
 "seeded_uniform_random")

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    f=p["transfer"]
    ids=[(x["id"],x["entry"]) for x in f["families"]]
    if (p["schema"]!="itd02.mg45.unchanged-mg44-public-actor-new-original-family-transfer.dev.v1"
        or p["phase"]!="PROSPECTIVE_SOURCE_FAMILY_AND_OUTCOME_FROZEN_BEFORE_EXECUTABLE_OR_NEW_WORLD_ACTIONS"
        or p["parent"]["mg44_head"]!=PARENT
        or p["original_source"]["commit"]!=UPSTREAM
        or p["original_source"]["registration_blob_sha1"]!=REGISTER_BLOB
        or tuple(ids)!=tuple(zip(FAMILIES,ENTRIES))
        or tuple(f["roles"])!=ROLES
        or tuple(map(tuple,f["seeds"]))!=SEEDS
        or f["expected_episodes"]!=144
        or f["source_selected_action_cap"]!=192
        or f["reproduce_full_processes"]!=2
        or p["frozen_dev_filter"]["candidate"]!=ROLES[13]
        or not all(p["prohibitions"].values())):
        raise ValueError("MG45_FROZEN_PROTOCOL_FAMILY_POLICY_DRIFT")
    flat=[v for seedset in SEEDS for v in seedset]
    if len(flat)!=9 or len(set(flat))!=9:
        raise ValueError("MG45_SEED_COHORT_NOT_DISJOINT")
    for h in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",h,"HEAD").returncode:
            raise ValueError("MG45_FREEZE_NOT_ANCESTOR_OF_EVALUATOR")
    for seed in flat:
        q=git("grep","-n","-w",str(seed),PARENT,"--",
              "research/lcrm01","docs/research")
        if q.returncode==0:
            raise ValueError("MG45_PRIOR_SOURCE_EXPOSED_SEED:"+str(seed))
        if q.returncode!=1:
            raise ValueError("MG45_PRIOR_SOURCE_IDENTITY_SCAN_UNAVAILABLE")
    original_policy_blob=git("hash-object","research/lcrm01/mg44_public_precondition_release.py")
    if original_policy_blob.returncode or original_policy_blob.stdout.strip()!=POLICY_BLOB:
        raise ValueError("MG45_MG44_ACTUAL_SOURCE_BLOB_CHANGED")
    return p

def preflight():
    frozen()
    # Exact inherited MG44 prereg and positive synthetic public release FSM
    # qualification; unchanged callable imported from pinned parent.
    original_mg44_preflight()
    if (PublicSlotRelease.__module__!="mg44_public_precondition_release"
        or public_release_episode.__module__!="mg44_public_precondition_release"):
        raise ValueError("MG45_UNQUALIFIED_LOCAL_POLICY_REPLACEMENT")
    print("MG45_UNMODIFIED_MG44_POLICY_AND_NEW_FAMILY_FROZEN_SOURCE_ONLY_PASS")

def metrics(rows):
    result={}
    for family in FAMILIES:
        result[family]={}
        for role in ROLES:
            group=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(group)!=3 or group[0]["prior_selected_source_samples"] not in (None,0):
                raise ValueError("MG45_SOURCE_ROLE_NOT_3_NEW_TRANSFER_EPISODES")
            if role!=ROLES[-1]:
                for a,b in zip(group,group[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG45_WITHIN_FAMILY_SOURCE_MEMORY_NOT_RETAINED")
            counts=collections.Counter()
            hist=[0]*7
            for ep in group:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG45_ORIGINAL_EPISODE_EVENT_HASH_FAILED")
                for i,e in enumerate(ep["source_events"],1):
                    if (e["index"]!=i or e["external_actions"]!=0
                        or digest(e["before"])!=e["before_sha256"]
                        or digest(e["after"])!=e["after_sha256"]):
                        raise ValueError("MG45_ORIGINAL_SOURCE_EVENT_NOT_AUTHENTIC")
                    v=event_metric(e)
                    counts.update(v)
                    hist[e["action"]]+=1
            if sum(hist)!=sum(x["original_source_actions"] for x in group):
                raise ValueError("MG45_SELECTED_ACTION_COUNT_MISMATCH")
            result[family][role]={
                "episodes":3,
                "actions":sum(hist),
                "action_histogram":hist,
                "positive_goal_episodes":sum(
                    int(x["original_terminal_goal_rewards"]>0) for x in group),
                "target_visible_frames":counts["target_any_visible_frames"],
                "target_front_frames":counts["target_front_frames"],
                "selected_target_pickup_attempts":counts["target_front_selected_pickup_attempts"],
                "actual_selected_target_pickup_effects":counts["target_front_selected_effects"],
                "real_door_openings":counts["locked_door_openings"],
                "release_public_triggers":sum(
                    x.get("release_triggers",0) for x in group),
                "release_public_effects":sum(
                    x.get("release_actual_public_effects",0) for x in group)}
    return result

def run_original(source_root,native_go,control_root,p):
    import gymnasium as gym
    import minigrid
    import resource
    from mg17_original_family_source_qual import (
        frozen as original_frozen,attest_source,public,digest as original_digest)
    from mg21_original_development import one_episode,ROLES as native_roles
    preflight()
    if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
        raise ValueError("MG45_NOT_PINNED_FARAMA_IMPORT")
    orig=original_frozen()
    attest_source(source_root,orig)
    if subprocess.run(["git","-C",str(source_root),"hash-object",
                       "minigrid/__init__.py"],capture_output=True,text=True,
                       check=True).stdout.strip()!=REGISTER_BLOB:
        raise ValueError("MG45_ORIGINAL_REGISTRATION_SOURCE_CHANGED")
    entrypoints={}
    for name,expected in zip(FAMILIES,ENTRIES):
        spec=gym.spec(name)
        if spec.entry_point!=expected:
            raise ValueError("MG45_NEW_FAMILY_REGISTRY_NOT_ORIGINAL_SOURCE:"+name)
        # No reset/step until all source/registries verified.
        entrypoints[name]=expected
    exact_control=corrected_class(control_root)
    rows=[]
    costs=[]
    for family,seeds in zip(FAMILIES,SEEDS):
        memory={role:None for role in ROLES}
        for seed in seeds:
            start_hashes=[]
            for role in ROLES:
                wall0=time.perf_counter()
                cpu0=time.process_time()
                child0=resource.getrusage(resource.RUSAGE_CHILDREN)
                if role in (ROLES[0],ROLES[1],ROLES[-1]):
                    native=(native_roles[0] if role==ROLES[0] else
                            native_roles[1] if role==ROLES[1] else native_roles[3])
                    ep,_,state=one_episode(
                        family,seed,native,192,memory[role],
                        native_go,entrypoints[family])
                elif role==ROLES[2]:
                    ep,state=mg33_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role==ROLES[3]:
                    ep,state=mg34_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role in (ROLES[4],ROLES[5]):
                    mode="ucb" if role==ROLES[4] else "round_robin"
                    ep,state=control_episode(
                        gym,entrypoints[family],family,seed,mode,memory[role],
                        192,public,original_digest,exact_control)
                elif role==ROLES[6]:
                    ep,state=original_mg38_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role==ROLES[7]:
                    ep,state=ablated_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role in (ROLES[8],ROLES[9]):
                    ep,state=evidence_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[8])
                elif role==ROLES[10]:
                    ep,state=reversal_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest)
                elif role in (ROLES[11],ROLES[12]):
                    ep,state=action_value_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[11])
                elif role in (ROLES[13],ROLES[14]):
                    ep,state=public_release_episode(
                        gym,entrypoints[family],family,seed,memory[role],
                        192,public,original_digest,role==ROLES[13])
                else:
                    raise ValueError("MG45_UNKNOWN_FROZEN_ORIGINAL_SOURCE_ACTOR")
                child1=resource.getrusage(resource.RUSAGE_CHILDREN)
                costs.append({"family":family,"role":role,"seed":seed,
                    "source_selected_actions":ep["original_source_actions"],
                    "outer_wall_seconds":round(time.perf_counter()-wall0,6),
                    "python_process_cpu_seconds":round(time.process_time()-cpu0,6),
                    "children_cpu_seconds_estimate":round(
                        child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime,6),
                    "note":"Linux outer process plus child deltas, not full per-native parity"})
                ep["role"]=role
                start_hashes.append(ep["public_start_sha256"])
                if role!=ROLES[-1]:
                    memory[role]=state
                rows.append(ep)
            if len(set(start_hashes))!=1:
                raise ValueError("MG45_SOURCE_RESET_SEED_NOT_EQUAL_ACROSS_ROLES")
    if len(rows)!=144 or any(not 1<=x["original_source_actions"]<=192 for x in rows):
        raise ValueError("MG45_NEW_FAMILY_ORIGINAL_SOURCE_EPISODES_MISSING")
    table=metrics(rows)
    candidate=ROLES[13]
    controls=(ROLES[14],ROLES[11],ROLES[12],ROLES[10],ROLES[8],ROLES[9],
              ROLES[6],ROLES[7],ROLES[4],ROLES[5])
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in FAMILIES)
           for role in (candidate,*controls)}
    target_effects=sum(table[f][candidate]["actual_selected_target_pickup_effects"]
                       for f in FAMILIES)
    positive_families=sum(table[f][candidate]["positive_goal_episodes"]>0
                          for f in FAMILIES)
    distinct_family_success=table[FAMILIES[-1]][candidate]["positive_goal_episodes"]>=1
    passed=(distinct_family_success and positive_families>=2
            and target_effects>=1
            and all(goals[candidate]>goals[role] for role in controls))
    outcome=p["frozen_dev_filter"]["pass"] if passed else p["frozen_dev_filter"]["fail"]
    source={
        "schema":"itd02.mg45.unmodified-mg44-transfer-original-family.dev-source.v1",
        "classification":outcome,
        "family_source_registration_blob_sha1":REGISTER_BLOB,
        "unchanged_mg44_source_blob_sha1":POLICY_BLOB,
        "original_144_episodes":rows,
        "original_selected_action_count":sum(x["original_source_actions"] for x in rows),
        "per_family_per_role":table,
        "transfer_filter":{
            "candidate":candidate,"goals":goals,
            "candidate_actual_mission_target_effects":target_effects,
            "candidate_positive_new_families":positive_families,
            "distinct_obstructedmaze_positive_goal":distinct_family_success,
            "supported":passed},
        "exposed_transfer_DEV_seeds":[list(x) for x in SEEDS],
        "source_original_Farama":UPSTREAM,
        "scientific_first_use":False,
        "independent_sealed_scientific_witness":False,
        "zero_external_actions":True,
        "native_models_or_controllers_modified":False,
        "native_full_compute_energy_parity_qualified":False,
        "mg28_native_rollout_permitted":False}
    receipt={"schema":source["schema"],"source":source,
             "canonical_source_sha256":digest(source)}
    resources={"schema":"itd02.mg45.auxiliary-host-episode-resources.v1",
               "note":"Host wall+Python process/child CPU deltas, no native CPU/RSS/energy parity claim",
               "original_source_sha256":receipt["canonical_source_sha256"],
               "records":costs}
    return receipt,resources

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preflight",action="store_true")
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--native-go",type=Path)
    ap.add_argument("--control-root",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--resources",type=Path)
    ap.add_argument("--compare",nargs=2,type=Path)
    a=ap.parse_args()
    p=frozen()
    if a.preflight:
        preflight()
        return
    if a.compare:
        first,second=[json.loads(x.read_text(encoding="utf8")) for x in a.compare]
        if (first.get("source")!=second.get("source")
            or first.get("canonical_source_sha256")!=second.get("canonical_source_sha256")
            or first.get("canonical_source_sha256")!=digest(first["source"])
            or first["source"].get("classification") not in
                 (p["frozen_dev_filter"]["pass"],p["frozen_dev_filter"]["fail"])
            or len(first["source"]["original_144_episodes"])!=144
            or first["source"]["scientific_first_use"] is not False
            or first["source"]["zero_external_actions"] is not True):
            raise ValueError("MG45_INDEPENDENT_ORIGINAL_NEW_FAMILY_PROCESSES_DIVERGED")
        print("MG45_TWO_UNMODIFIED_ORIGINAL_TRANSFER_PROCESSES_IDENTICAL",
              first["canonical_source_sha256"])
        print("MG45_FROZEN_NEW_FAMILY_TRANSFER_CLASSIFICATION",
              first["source"]["classification"])
        print("MG45_TRANSFER_PER_FAMILY_GOALS",json.dumps(
              {k:{role:z["positive_goal_episodes"] for role,z in v.items()
                  if role in (ROLES[0],ROLES[1],ROLES[13],ROLES[14])}
               for k,v in first["source"]["per_family_per_role"].items()},sort_keys=True))
        print("MG45_TRANSFER_FILTER",json.dumps(
              first["source"]["transfer_filter"],sort_keys=True))
        return
    if any(x is None for x in (a.source_root,a.native_go,a.control_root,
                               a.output,a.resources)):
        ap.error("--source-root --native-go --control-root --output --resources required")
    started=time.perf_counter()
    try:
        receipt,resources=run_original(
            a.source_root,a.native_go,a.control_root,p)
    except Exception as e:
        receipt={"schema":"itd02.mg45.new-original-family-transfer-blocked.v1",
                 "classification":p["frozen_dev_filter"]["blocked"],
                 "error_type":type(e).__name__,"error":str(e),
                 "trace_tail":traceback.format_exc().splitlines()[-16:]}
        resources={"schema":"itd02.mg45.resources-blocked.v1","records":[]}
    receipt["host_wall_seconds_outside_canonical_source"]=round(
        time.perf_counter()-started,6)
    a.output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",
                        encoding="utf8")
    a.resources.write_text(json.dumps(resources,indent=2,sort_keys=True)+"\n",
                           encoding="utf8")
    cls=receipt.get("source",{}).get("classification",
                                   receipt.get("classification","MG45_BLOCKED"))
    print("MG45_ORIGINAL_TRANSFER_CLASSIFICATION",cls)
    if "BLOCKED" in cls:
        raise ValueError(receipt.get("error","MG45_UNKNOWN_SOURCE_BLOCKER"))
    print("MG45_ORIGINAL_TRANSFER_SOURCE_SHA256",receipt["canonical_source_sha256"])
if __name__=="__main__":
    main()
