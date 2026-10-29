"""AC-15: genuine source-owned DTR public events -> unchanged Yggdrasil cells.

Conventional development-only learned-count control, NOT native NCA training,
original science, causal-return evaluation, transfer or scientific admission.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc

import ac10_upstream_contract as ac10
import ac11_original_dtr as ac11
import ac14_ogbench as ac14

SCHEMA="forge.ac15.original-dtr-ygg-public-causal-cells.v1"
SOURCE_SCHEMA="forge.ac15.authentic-original-public-observation.v1"
YGG_COMMIT="992ef142aaa551156749a1de484a971b9a0c092f"
YGG_BLOB="f2fda603fbed965a3b4e7cc28844b2246bf8ac2b"
YGG_PATH="yggdrasil/public_causal_cells.py"
FIT=tuple(range(760000,760008))
VALID=tuple(range(760100,760104))
DEV=tuple(range(760200,760204))
FIELDS=frozenset(ac10.PROTO["allowed_event_fields"])
FORBIDDEN=frozenset(ac10.PROTO["forbidden_to_learner"])

_SOURCE_CHILD=r"""
import json,sys,time
from causal_gym.envs.dtr import DTRPCH
from causal_gym.core.task import Task,LearningRegime
phase=sys.argv[1]
seedsets={"FIT":tuple(range(760000,760008)),
          "DEV":tuple(range(760200,760204))}
if phase not in seedsets: raise RuntimeError("UNDECLARED_SOURCE_PHASE")
allowed={"stage","observation","action","next_observation",
         "reward","terminated","truncated","valid_actions"}
runs=[]
started=time.perf_counter_ns()
for i,seed in enumerate(seedsets[phase]):
    original=DTRPCH()
    original.task=Task(learning_regime=LearningRegime.do)
    try:
        original.ctf_do(lambda *_:0)
    except PermissionError:
        forbidden_permission_denied=True
    else:
        raise RuntimeError("PRIVILEGED_COUNTERFACTUAL_WAS_PERMITTED")
    initial,initial_info=original.reset(seed=seed)
    if int(initial) not in (0,1) or initial_info["stage"]!=0:
        raise RuntimeError("SOURCE_PUBLIC_INITIAL_STAGE_CHANGED")
    a0=i%2
    a1=(i//2)%2
    obs1,r0,done0,trunc0,priv0=original.do(lambda *args,a=a0:a)
    obs2,r1,done1,trunc1,priv1=original.do(lambda *args,a=a1:a)
    # Neither original info dictionary nor source/SCM object is serialized.
    assert int(obs1) in (0,1) and obs2 is None
    assert int(r0)==0 and int(r1) in (0,1)
    assert done0 is False and trunc0 is False
    assert done1 is True and trunc1 is False
    events=[
      {"stage":0,"observation":int(initial),"action":a0,
       "next_observation":int(obs1),"reward":int(r0),
       "terminated":False,"truncated":False,"valid_actions":[0,1]},
      {"stage":1,"observation":int(obs1),"action":a1,
       "next_observation":None,"reward":int(r1),
       "terminated":True,"truncated":False,"valid_actions":[0,1]}
    ]
    assert all(set(e)==allowed for e in events)
    runs.append({"seed":seed,"events":events,
                 "ctf_do_permission_denied":forbidden_permission_denied})
print(json.dumps({"schema":"forge.ac15.authentic-original-public-observation.v1",
 "phase":phase,"source_owned_episodes":len(runs),
 "source_owned_actions":2*len(runs),
 "episodes":runs,"source_call_wall_ns":time.perf_counter_ns()-started,
 "learner_received_privileged_info":False,
 "scientific_first_use":False},sort_keys=True))
"""

def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def git(repo:Path,*args:str)->str:
    return ac10.git(repo,*args)

def exact_existing_ygg(root:Path):
    root=root.resolve(strict=True)
    if git(root,"rev-parse","HEAD")!=YGG_COMMIT:
        raise RuntimeError("AC15_YGG_ORIGINAL_COMMIT_DRIFT")
    file=root/YGG_PATH
    if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(root):
        raise RuntimeError("AC15_YGG_CAUSAL_CELLS_FILE_UNSAFE")
    if git(root,"hash-object","--",YGG_PATH)!=YGG_BLOB:
        raise RuntimeError("AC15_YGG_ORIGINAL_BLOB_DRIFT")
    if git(root,"status","--porcelain","--untracked-files=no"):
        raise RuntimeError("AC15_YGG_WORKTREE_MODIFIED")
    spec=importlib.util.spec_from_file_location("ac15_pinned_ygg_original",file)
    if spec is None or spec.loader is None:
        raise RuntimeError("AC15_EXISTING_YGG_IMPORT_FAILED")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cls=mod.PublicCausalCells
    if cls.LEARNED_BYTES!=128 or cls.CHECKPOINT_BYTES!=164 or cls.ACTIVE_SLOTS!=7:
        raise RuntimeError("AC15_YGG_LEARNER_INTERFACE_DRIFT")
    return cls

def validate_source(data:dict,phase:str):
    seeds=FIT if phase=="FIT" else DEV
    if (type(data) is not dict or data.get("schema")!=SOURCE_SCHEMA or
        data.get("phase")!=phase or
        data.get("source_owned_episodes")!=len(seeds) or
        data.get("source_owned_actions")!=2*len(seeds) or
        data.get("scientific_first_use") is not False or
        data.get("learner_received_privileged_info") is not False):
        raise RuntimeError("AC15_EXTERNAL_SOURCE_CONTRACT_DRIFT")
    rows=data.get("episodes")
    if type(rows) is not list or len(rows)!=len(seeds) or [r.get("seed") for r in rows]!=list(seeds):
        raise RuntimeError("AC15_FIT_DEV_SEED_IDENTITY_DRIFT")
    for i,row in enumerate(rows):
        if row.get("ctf_do_permission_denied") is not True:
            raise RuntimeError("AC15_PRIVILEGED_DTR_PERMISSION_MISSING")
        events=row.get("events")
        if type(events) is not list or len(events)!=2:
            raise RuntimeError("AC15_NON_TWO_STAGE_ORIGINAL")
        for stage,event in enumerate(events):
            if type(event) is not dict or set(event)!=FIELDS or set(event)&FORBIDDEN:
                raise RuntimeError("AC15_RAW_ORACLE_INFORMATION_EXPOSURE")
            if event["stage"]!=stage or type(event["observation"]) is not int or event["observation"] not in (0,1):
                raise RuntimeError("AC15_PUBLIC_STAGE_OBSERVATION_INVALID")
            if event["action"]!= (i%2 if stage==0 else (i//2)%2):
                raise RuntimeError("AC15_FIXED_SCRIPT_ACTION_DRIFT")
            if type(event["reward"]) is not int or event["reward"] not in (0,1) or event["valid_actions"]!=[0,1]:
                raise RuntimeError("AC15_PUBLIC_REWARD_OR_RIGHTS_INVALID")
            if event["truncated"] is not False or event["terminated"] is not bool(stage):
                raise RuntimeError("AC15_PUBLIC_TERMINAL_INVALID")
            if stage==0 and (event["next_observation"] not in (0,1) or event["reward"]!=0):
                raise RuntimeError("AC15_ORIGINAL_STAGE0_SOURCE_SEMANTICS_DRIFT")
            if stage==1 and event["next_observation"] is not None:
                raise RuntimeError("AC15_ORIGINAL_TERMINAL_OBSERVATION_DRIFT")
        if events[1]["observation"]!=events[0]["next_observation"]:
            raise RuntimeError("AC15_SOURCE_STAGE_CHAIN_MISMATCH")

def source_phase(root:Path,py:Path,env:dict,phase:str):
    result=ac11.run_cmd([str(py),"-B","-c",_SOURCE_CHILD,phase],
                        cwd=root,env=env,timeout=95)
    rc,out,err,wall,expired=result
    if rc!=0 or expired:
        # Partial original episodes MAY have been executed by the failing
        # subprocess. Never report fabricated zero counts in a failure.
        raise RuntimeError("AC15_ORIGINAL_SOURCE_PHASE_FAILED_UNKNOWN_EXECUTION:"+phase)
    try:
        doc=json.loads(out.decode("utf-8").strip())
        validate_source(doc,phase)
    except (UnicodeError,ValueError,KeyError,TypeError) as ex:
        raise RuntimeError("AC15_ORIGINAL_PUBLIC_JSON_FAILED_UNKNOWN_EXECUTION") from ex
    return doc,wall,digest(out)

def address(event:dict)->int:
    return 2*event["stage"]+event["observation"]

def outcome(event:dict)->int:
    return event["next_observation"] if event["stage"]==0 else event["reward"]

def choose_counts(counter:dict,addr:int):
    a=counter.get((addr,0),[0,0])
    b=counter.get((addr,1),[0,0])
    n0=sum(a);n1=sum(b)
    if n0==0 or n1==0:
        return None
    lhs=a[1]*n1;rhs=b[1]*n0
    if lhs==rhs:
        return None
    return 0 if lhs>rhs else 1

def run(upstream:Path,ygg:Path,venv:Path,ac14_report:Path,out:Path):
    original=ac10.inspect_upstream(upstream)
    cls=exact_existing_ygg(ygg)
    parent=json.loads(ac14_report.read_text(encoding="utf-8"))
    if (parent.get("schema")!=ac14.SCHEMA or
        parent.get("original_commit")!=original["sha"] or
        parent.get("original_tree")!=original["tree"] or
        parent.get("original_dtr_sha256")!=original["dtr_original_git_blob_sha256"] or
        parent.get("state")!="REAL_SOURCE_PUBLIC_SMOKE_PASS" or
        parent.get("source_owned_public_episodes")!=2 or
        parent.get("source_owned_public_actions")!=4 or
        parent.get("scientific_first_use") is not False or
        parent.get("source_files_modified") is not False or
        parent.get("native_model_trained") is not False or
        parent.get("controller_or_f139_queue_changed") is not False):
        raise RuntimeError("AC15_ORIGINAL_AC14_SCIENTIFIC_BOUNDARY_NOT_QUALIFIED")
    if not set(FIT).isdisjoint(DEV) or not set(FIT).isdisjoint(VALID) or not set(DEV).isdisjoint(VALID):
        raise RuntimeError("AC15_PUBLIC_DATASET_SEED_LEAKAGE")
    venv=venv.resolve(strict=True)
    if venv.is_relative_to(upstream.resolve()) or venv.is_relative_to(ygg.resolve()):
        raise RuntimeError("AC15_VENV_INSIDE_PROTECTED_SOURCE")
    py=venv/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if not py.is_file():
        raise RuntimeError("AC15_UPSTREAM_REAL_RUNTIME_MISSING")
    env=os.environ.copy()
    env.update({"PYTHONPATH":str(upstream.resolve()),
                "PYTHONDONTWRITEBYTECODE":"1"})
    fit,fit_wall,fit_hash=source_phase(upstream,py,env,"FIT")
    cell=cls()
    tabular=defaultdict(lambda:[0,0])
    pooled=defaultdict(lambda:[0,0])
    tracemalloc.start()
    t0=time.perf_counter_ns()
    updates=0
    for episode in fit["episodes"]:
        for event in episode["events"]:
            addr=address(event);arm=event["action"];y=outcome(event)
            cell.observe(addr,arm,y)
            tabular[(addr,arm)][y]+=1
            pooled[arm][y]+=1
            updates+=1
    ckpt=cell.snapshot()
    fit_learner_wall=time.perf_counter_ns()-t0
    learner_peak=tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    if len(ckpt)!=164:
        raise RuntimeError("AC15_ORIGINAL_CHECKPOINT_CAPACITY_CHANGED")
    restored=cls.restore(ckpt)
    if restored.snapshot()!=ckpt:
        raise RuntimeError("AC15_COLD_RESTORE_FAILED")
    for addr in range(4):
        for arm in range(2):
            if cell._counts[addr][arm]!=tabular[(addr,arm)]:
                raise RuntimeError("AC15_EQUAL_FIT_COUNTS_MISMATCH")
    frozen=digest(ckpt)
    dev,dev_wall,dev_hash=source_phase(upstream,py,env,"DEV")
    decisions=[]
    observed_matched_action=0
    abstain=0
    for episode in dev["episodes"]:
        for event in episode["events"]:
            addr=address(event)
            chosen=cell.choose(addr)
            ref=choose_counts(tabular,addr)
            cold=restored.choose(addr)
            pool=choose_counts({(0,k):v for k,v in pooled.items()},0)
            if chosen!=ref or chosen!=cold:
                raise RuntimeError("AC15_MATCHED_TABULAR_OR_COLD_PARITY_LOST")
            abstain+=chosen is None
            observed_matched_action+=chosen==event["action"] if chosen is not None else 0
            decisions.append({"seed":episode["seed"],"stage":event["stage"],
                "public_observation":event["observation"],
                "actual_scripted_action":event["action"],
                "actual_source_outcome":outcome(event),
                "learned_cell_recommendation":chosen,
                "matched_fitted_tabular_recommendation":ref,
                "global_fitted_arm_control":pool,
                "cold_restore_recommendation":cold})
    if digest(cell.snapshot())!=frozen or digest(restored.snapshot())!=frozen:
        raise RuntimeError("AC15_DEV_LEARNER_CHANGED_DURING_FROZEN_EVALUATION")
    result={
        "schema":SCHEMA,"scope":"AUTHENTIC_PUBLIC_DEVELOPMENT_LEARNER_CONTROL_ONLY",
        "upstream_sha":original["sha"],
        "upstream_tree_sha":original["tree"],
        "upstream_dtr_sha256":original["dtr_original_git_blob_sha256"],
        "existing_ygg_commit":YGG_COMMIT,
        "existing_ygg_git_blob":YGG_BLOB,
        "source_fit":fit,
        "source_dev":dev,
        "source_fit_stdout_sha256":fit_hash,
        "source_dev_stdout_sha256":dev_hash,
        "source_fit_process_wall_ns":fit_wall,
        "source_dev_process_wall_ns":dev_wall,
        "fit_learner_wall_ns":fit_learner_wall,
        "fit_learner_python_traced_peak_bytes":learner_peak,
        "candidate_name":"EXISTING_YGG_PUBLIC_CAUSAL_CELLS_CONVENTIONAL_DEV_CONTROL",
        "candidate_mutated_original_native_source":False,
        "fit_observed_action_outcome_updates":updates,
        "retained_checkpoint_bytes":len(ckpt),
        "checkpoint_sha256":frozen,
        "cold_restore_identical":True,
        "fully_fitted_tabular_control_parity":True,
        "dev_abstention_count":abstain,
        "dev_recommendations_matching_scripted_action":observed_matched_action,
        "dev_choices":decisions,
        "dev_updates":0,
        "candidate_beats_fully_fitted_control":False,
        "candidate_realized_policy_value_measured":False,
        "independent_unfamiliar_family_transfer_tested":False,
        "reserved_public_valid_used":False,
        "protected_science_family_used":False,
        "scientific_first_use":False,
        "accepted_science_changed":False,
        "native_wingless_or_yggdrasil_source_modified":False,
        "controller_or_queue_changed":False
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",type=Path,required=True)
    p.add_argument("--ygg",type=Path,required=True)
    p.add_argument("--venv",type=Path,required=True)
    p.add_argument("--ac14-report",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    r=run(a.upstream,a.ygg,a.venv,a.ac14_report,a.out)
    print("AC15_ACTUAL_NATIVE_CONTROL_FIT_UPDATES="+str(r["fit_observed_action_outcome_updates"]))
    print("AC15_FITTED_TABULAR_PARITY="+str(r["fully_fitted_tabular_control_parity"]))
    print("AC15_CHECKPOINT_COLD_RESTORE="+str(r["cold_restore_identical"]))
    print("AC15_SOURCE_FIT_EPISODES="+str(r["source_fit"]["source_owned_episodes"]))
    print("AC15_SOURCE_DEV_EPISODES="+str(r["source_dev"]["source_owned_episodes"]))
    print("AC15_SCIENTIFIC_FIRST_USE=FALSE")
