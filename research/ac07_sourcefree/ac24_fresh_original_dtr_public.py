"""AC-24: pre-frozen NEW authentic DTR public development source / frozen controls.

All source interaction is isolated in an external subprocess running pinned
Causal-Gymnasium. Only eight whitelisted public fields survive JSON output.
No private source state, generated stand-in, model-directed action, protected
scientific family, native Ygg modification or first-use claim.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, pathlib, sys, time, tracemalloc
import ac10_upstream_contract as ac10
import ac11_original_dtr as ac11
import ac21_local_temporal_memory as ac21
import ac22_fit_only_retention_diagnostics as ac22
import ac23_local_pulse_reconstruction as ac23

SCHEMA="forge.ac24.fresh-original-dtr-public-development-v1"
SOURCE_SCHEMA="forge.ac24.original-public-only-source-episodes-v1"
FIT=tuple(range(761000,761064))
DEV=tuple(range(761200,761232))
ALLOWED=ac10.PROTO["allowed_event_fields"]
SOURCE_CHILD=r"""
import json,sys
from causal_gym.envs.dtr import DTRPCH
from causal_gym.core.task import Task,LearningRegime
phase=sys.argv[1]
seedsets={"FIT":tuple(range(761000,761064)),"DEV":tuple(range(761200,761232))}
if phase not in seedsets:raise RuntimeError("AC24_UNREGISTERED_SOURCE_PHASE")
expected={"stage","observation","action","next_observation",
          "reward","terminated","truncated","valid_actions"}
episodes=[]
for i,seed in enumerate(seedsets[phase]):
    original=DTRPCH()
    original.task=Task(learning_regime=LearningRegime.do)
    try: original.ctf_do(lambda *_:0)
    except PermissionError: forbidden=True
    else: raise RuntimeError("AC24_SOURCE_PRIVILEGED_COUNTERFACTUAL_PERMITTED")
    first,first_info=original.reset(seed=seed)
    if type(int(first)) is not int or int(first) not in (0,1) or first_info["stage"]!=0:
        raise RuntimeError("AC24_PUBLIC_SOURCE_STAGE0_INVALID")
    a0=i%2;a1=(i//2)%2
    second,r0,t0,x0,private0=original.do(lambda *_:a0)
    terminal,r1,t1,x1,private1=original.do(lambda *_:a1)
    if (type(int(second)) is not int or int(second) not in (0,1) or
        terminal is not None or int(r0)!=0 or int(r1) not in (0,1) or
        t0 is not False or t1 is not True or x0 is not False or x1 is not False):
        raise RuntimeError("AC24_REAL_SOURCE_PUBLIC_CONSEQUENCE_DRIFT")
    events=[
        {"stage":0,"observation":int(first),"action":a0,
         "next_observation":int(second),"reward":int(r0),
         "terminated":False,"truncated":False,"valid_actions":[0,1]},
        {"stage":1,"observation":int(second),"action":a1,
         "next_observation":None,"reward":int(r1),
         "terminated":True,"truncated":False,"valid_actions":[0,1]}
    ]
    if any(set(e)!=expected for e in events):
        raise RuntimeError("AC24_PUBLIC_SOURCE_FIELD_ALLOWLIST_DRIFT")
    # NEVER put private source info, latent values, callback args or raw
    # environment graph into stdout, file, parent process, or learner.
    episodes.append({"seed":seed,"events":events,
                     "ctf_do_permission_denied":forbidden})
print(json.dumps({
    "schema":"forge.ac24.original-public-only-source-episodes-v1",
    "phase":phase,"source_owned_episodes":len(episodes),
    "source_owned_actions":2*len(episodes),
    "episodes":episodes,
    "learner_received_privileged_info":False,
    "scientific_first_use":False
},sort_keys=True,separators=(",",":")))
"""

def digest(b):return hashlib.sha256(b).hexdigest()

def validate_source(x,phase):
    seeds=FIT if phase=="FIT" else DEV
    if (type(x) is not dict or set(x)!={"schema","phase","source_owned_episodes",
            "source_owned_actions","episodes","learner_received_privileged_info",
            "scientific_first_use"} or x["schema"]!=SOURCE_SCHEMA or
        x["phase"]!=phase or x["source_owned_episodes"]!=len(seeds) or
        x["source_owned_actions"]!=2*len(seeds) or
        x["learner_received_privileged_info"] is not False or
        x["scientific_first_use"] is not False):
        raise RuntimeError("AC24_ORIGINAL_SOURCE_CONTRACT_DRIFT")
    if type(x["episodes"]) is not list or [r["seed"] for r in x["episodes"]]!=list(seeds):
        raise RuntimeError("AC24_SOURCE_SEED_OR_EPISODE_DRIFT")
    for i,row in enumerate(x["episodes"]):
        if (type(row) is not dict or set(row)!={"seed","events","ctf_do_permission_denied"} or
            row["ctf_do_permission_denied"] is not True or
            type(row["events"]) is not list or len(row["events"])!=2):
            raise RuntimeError("AC24_SOURCE_PERMISSIONS_OR_EVENTS_INVALID")
        a,b=row["events"]
        for e,j in ((a,0),(b,1)):
            if (type(e) is not dict or set(e)!=set(ALLOWED) or
                e["stage"]!=j or type(e["observation"]) is not int or
                e["observation"] not in (0,1) or
                type(e["action"]) is not int or
                e["action"]!=(i%2 if j==0 else (i//2)%2) or
                type(e["reward"]) is not int or e["reward"] not in (0,1) or
                e["valid_actions"]!=[0,1] or e["terminated"] is not bool(j) or
                e["truncated"] is not False):
                raise RuntimeError("AC24_PUBLIC_SOURCE_EVENT_FIELD_OR_ACTION_DRIFT")
        if (a["reward"]!=0 or a["next_observation"] not in (0,1) or
            b["next_observation"] is not None or b["observation"]!=a["next_observation"]):
            raise RuntimeError("AC24_ORIGINAL_STAGE_OR_TERMINAL_DRIFT")
    return x

def source_phase(upstream,py,phase):
    env=os.environ.copy()
    env.update({"PYTHONPATH":str(upstream.resolve()),
                "PYTHONDONTWRITEBYTECODE":"1"})
    rc,out,err,ns,timeout=ac11.run_cmd(
        [str(py),"-B","-c",SOURCE_CHILD,phase],
        cwd=upstream,env=env,timeout=150)
    if timeout or rc!=0:
        # A failing subprocess may have produced partial real episodes.
        # Never falsify unknown completion as zero.
        raise RuntimeError("AC24_REAL_SOURCE_"+phase+"_FAILED_PARTIAL_EXECUTION_UNKNOWN:stderr_sha256="+digest(err))
    try:x=json.loads(out.decode("utf-8").strip())
    except (UnicodeError,ValueError) as ex:
        raise RuntimeError("AC24_ORIGINAL_SOURCE_PUBLIC_JSON_INVALID_PARTIAL_UNKNOWN") from ex
    validate_source(x,phase)
    return x,ns,digest(out)

def history(row):
    a,b=row["events"]
    h=(a["observation"],a["action"],b["observation"],b["action"])
    return h,b["reward"]

def conventional(fit,dev):
    tab={};ema={}; prior=sum(y for h,y in fit)/len(fit)
    for h,y in fit:
        yes,n=tab.get(h,(0,0))
        tab[h]=(yes+y,n+1)
        ema[h]=0.5*y+0.5*ema.get(h,prior)
    return {
        "full_history_laplace":[((tab[h][0]+1)/(tab[h][1]+2) if h in tab else prior) for h,y in dev],
        "full_history_ema":[ema.get(h,prior) for h,y in dev],
        "pooled_fit_prior":[prior for h,y in dev]
    }, {str(h):n for h,(yes,n) in tab.items()}

def measure(pred,dev):
    if len(pred)!=len(dev) or any(not math.isfinite(p) or not 0<=p<=1 for p in pred):
        raise RuntimeError("AC24_FROZEN_SCORE_INVALID")
    return {"n":len(dev),"correct_at_half":sum(int(p>=0.5)==y for p,(h,y) in zip(pred,dev)),
            "brier":sum((p-y)**2 for p,(h,y) in zip(pred,dev))/len(dev)}

def evaluate(fit_source,dev_source):
    fit=[history(e) for e in fit_source["episodes"]]
    dev=[history(e) for e in dev_source["episodes"]]
    if len(fit)!=64 or len(dev)!=32:raise RuntimeError("AC24_FROZEN_PUBLIC_COHORT_SIZE_INVALID")
    factories={
        "local_self_reconstruction":ac23.LocalPulseReconstruction,
        "local_reward_modulated":ac21.TemporalRingDev,
        "local_near_unit_fixed_diagnostic":lambda:ac22.FrozenGateTemporal(5.),
        "direct_eight_parameter_logistic":ac21.FullHistoryLogisticControl,
        "direct_ten_parameter_logistic":ac22.TenCoefficientFullHistoryLogistic
    }
    models={};metrics={};preds={};census={}
    for name,factory in factories.items():
        tracemalloc.start();before=time.perf_counter_ns()
        model=ac21.fit(factory(),fit)
        elapsed=time.perf_counter_ns()-before
        peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        if model.updates!=1536:raise RuntimeError("AC24_MODEL_FIT_UPDATE_BUDGET_DRIFT")
        checkpoint=model.snapshot() if hasattr(model,"snapshot") else None
        if checkpoint is not None:
            restored=type(model).restore(checkpoint)
            if restored.snapshot()!=checkpoint:
                raise RuntimeError("AC24_CHECKPOINT_COLD_RESTORE_INVALID")
        fit_identity=(model.snapshot() if checkpoint is not None else tuple(model.weights))
        p=[model.predict(h) for h,y in dev]
        if (model.snapshot() if checkpoint is not None else tuple(model.weights))!=fit_identity:
            raise RuntimeError("AC24_DEV_FROZEN_MODEL_MUTATION")
        if checkpoint is not None and [restored.predict(h) for h,y in dev]!=p:
            raise RuntimeError("AC24_CHECKPOINT_FROZEN_PREDICTION_DRIFT")
        preds[name]=p;metrics[name]=measure(p,dev)
        census[name]={
            "fit_updates":model.updates,
            "trained_parameter_count":10 if name in (
                "local_self_reconstruction","local_reward_modulated",
                "direct_ten_parameter_logistic") else 8,
            "fit_wall_ns":elapsed,
            "peak_tracemalloc_bytes":peak,
            "checkpoint_bytes":len(checkpoint.encode()) if checkpoint else None,
            "checkpoint_sha256":digest(checkpoint.encode()) if checkpoint else None,
            "local_gate_logits":[model.gates[3],model.gates[4]] if hasattr(model,"gates") else None,
            "local_gate_amplitudes":[ac21.sig(model.gates[3]),ac21.sig(model.gates[4])] if hasattr(model,"gates") else None,
            "two_hop_message_deliveries":getattr(model,"messages_delivered",None),
            "local_pulse_update_calls":sum(model.local_pulse_update_calls.values()) if hasattr(model,"local_pulse_update_calls") else 0,
        }
    old,buckets=conventional(fit,dev)
    for name,p in old.items():
        preds[name]=p;metrics[name]=measure(p,dev)
    receipt=[]
    for i,e in enumerate(dev_source["episodes"]):
        h,y=dev[i]
        receipt.append({
            "seed":e["seed"],"public_history":list(h),"actual_source_terminal_reward":y,
            "model_probabilities":{name:p[i] for name,p in preds.items()},
            "full_history_fit_support":buckets.get(str(h),0)})
    return {"metrics":metrics,"prediction_rows":receipt,"resource_and_checkpoint_census":census}

def run(upstream,venv,out):
    identified=ac10.inspect_upstream(upstream)
    py=venv/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if not py.is_file() or py.resolve().is_relative_to(upstream.resolve()):
        raise RuntimeError("AC24_PINNED_ORIGINAL_SOURCE_ENV_MISSING")
    # Freeze original source identity BEFORE and AFTER source use.
    fit,fit_ns,fit_stdout_sha=source_phase(upstream,py,"FIT")
    dev,dev_ns,dev_stdout_sha=source_phase(upstream,py,"DEV")
    if ac10.inspect_upstream(upstream)!=identified:
        raise RuntimeError("AC24_ORIGINAL_SOURCE_CHANGED_DURING_REPLAY")
    scored=evaluate(fit,dev)
    result={
        "schema":SCHEMA,"scope":"NEW_AUTHENTIC_PUBLIC_DTR_DEVELOPMENT_NOT_FIRST_USE",
        "source_original_commit":ac10.SOURCE_COMMIT,
        "source_original_tree":ac10.SOURCE_TREE,
        "source_original_dtr_blob":ac10.BLOBS["causal_gym/envs/dtr.py"],
        "prior_ac23_frozen_commit":"0d7a46142e0a391eb56dd4a4bfe5078620889fb4",
        "fit_seeds":list(FIT),"dev_seeds":list(DEV),
        "fit_source_episode_count":fit["source_owned_episodes"],
        "dev_source_episode_count":dev["source_owned_episodes"],
        "source_owned_public_actions":fit["source_owned_actions"]+dev["source_owned_actions"],
        "source_stdout_sha256":{"FIT":fit_stdout_sha,"DEV":dev_stdout_sha},
        "original_source_wall_ns":{"FIT":fit_ns,"DEV":dev_ns},
        "source_fit":fit,"source_dev":dev,
        "model_actions_source_selected":False,
        "source_private_oracle_fields_admitted":False,
        "source_ctf_do_permission_denied":True,
        "source_native_code_edited":False,
        "native_ygg_or_wingless_code_edited":False,
        "dev_model_updates":0,
        "original_scientific_first_use":False,
        "unfamiliar_family_transfer_tested":False,
        "scientific_admission":False,
        "forge_autonomy_controller_queue_changed":False,
        **scored
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    q=argparse.ArgumentParser()
    q.add_argument("--upstream",type=pathlib.Path,required=True)
    q.add_argument("--venv",type=pathlib.Path,required=True)
    q.add_argument("--out",type=pathlib.Path,required=True)
    a=q.parse_args()
    r=run(a.upstream,a.venv,a.out)
    print("AC24_ORIGINAL_NEW_PUBLIC_FIT_EPISODES="+str(r["fit_source_episode_count"]))
    print("AC24_ORIGINAL_NEW_PUBLIC_DEV_EPISODES="+str(r["dev_source_episode_count"]))
    print("AC24_LOCAL_DEV_BRIER="+str(r["metrics"]["local_self_reconstruction"]["brier"]))
    print("AC24_TEN_PARAMETER_BASELINE_BRIER="+str(r["metrics"]["direct_ten_parameter_logistic"]["brier"]))
    print("AC24_SCIENTIFIC_FIRST_USE=FALSE")
