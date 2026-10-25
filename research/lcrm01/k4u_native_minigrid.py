#!/usr/bin/env python3
"""K4U prospectively frozen original MiniGrid native Wingless/Yggdrasil first use.

No cached/consumed K4R worlds. Authentic source-pinned native policy code is
loaded by the runner; K4R's five original conventional methods remain controls.
Public FullObsWrapper is the only environment input; all FIT feedback is REAL.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

from k4r_minigrid_source import (
    FAMILIES, POLICIES, make_env, public, front_blocked,
    state_key, recorded_fit_transition, fitted, act, canon, sha)

HERE=Path(__file__).parent
FROZEN=HERE/"k4u_frozen_native_minigrid.json"
SCHEMA="mass.lcrm01.k4u.original-native-learning-minigrid-development.v1"
METHODS=("wingless_native","yggdrasil_native")+POLICIES
PHASE_SEEDS={"FIT":range(4100,4124),"CHECK":range(5100,5104),"DEV":range(6100,6108)}


def protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (p.get("schema")!="mass.lcrm01.k4u.frozen-native-learned-minigrid-transfer.v1"
        or p["parents"]["K4R_head"]!="e542b58c33698d10473b891734af15dca46c12d6"
        or p["sources"]["commit"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or p["worlds"]["legal_actions"]!=[0,1,2]
        or p["evaluation"]["methods"]!=list(METHODS)
        or list(PHASE_SEEDS["FIT"])!=list(range(4100,4124))
        or list(PHASE_SEEDS["DEV"])!=list(range(6100,6108))):
        raise ValueError("K4U_FROZEN_SCIENTIFIC_SOURCE_DRIFT")
    return p


def public_grid(st):
    goal=st["goal"]
    return {"X":int(st["x"]),"Y":int(st["y"]),
        "GoalX":int(goal[0]),"GoalY":int(goal[1]),
        "Direction":int(st["dir"]),"FrontBlocked":bool(front_blocked(st))}


def native_from_public(module,st):
    v=public_grid(st)
    return module.PublicGrid(
       v["X"],v["Y"],v["GoalX"],v["GoalY"],v["Direction"],v["FrontBlocked"])


# The native Go r1.PublicGrid JSON tags use snake_case. Preserve the
# historical uppercase public_grid observations for Yggdrasil, FIT records
# and conventional controls; convert only when crossing the Wingless IPC.
_WINGLESS_PUBLIC_FIELDS = ("X", "Y", "GoalX", "GoalY", "Direction", "FrontBlocked")
_WINGLESS_GO_FIELDS = ("x", "y", "goal_x", "goal_y", "direction", "front_blocked")


def wingless_wire_grid(grid):
    """Fail closed rather than silently default missing Go observation fields."""
    if type(grid) is not dict or set(grid) != set(_WINGLESS_PUBLIC_FIELDS):
        raise ValueError("WINGLESS_PUBLIC_OBSERVATION_SCHEMA_DRIFT")
    if any(type(grid[name]) is not int for name in _WINGLESS_PUBLIC_FIELDS[:-1]):
        raise ValueError("WINGLESS_PUBLIC_OBSERVATION_INTEGER_TYPE_DRIFT")
    if type(grid["FrontBlocked"]) is not bool:
        raise ValueError("WINGLESS_PUBLIC_OBSERVATION_BLOCKED_TYPE_DRIFT")
    if (any(not 0 <= grid[name] <= 64 for name in _WINGLESS_PUBLIC_FIELDS[:4])
            or not 0 <= grid["Direction"] <= 3):
        raise ValueError("WINGLESS_PUBLIC_OBSERVATION_VALUE_OUT_OF_RANGE")
    return dict(zip(_WINGLESS_GO_FIELDS,
                    (grid[name] for name in _WINGLESS_PUBLIC_FIELDS)))


class WingBridge:
    def __init__(self,executable):
        self.proc=subprocess.Popen([str(executable)],stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)

    def request(self,op,**parts):
        if self.proc.poll() is not None:
            raise ValueError("WINGLESS_NATIVE_SOURCE_PROCESS_EXITED")
        message={"op":op,**parts}
        self.proc.stdin.write(canon(message)+"\n")
        self.proc.stdin.flush()
        line=self.proc.stdout.readline()
        if not line:
            raise ValueError("WINGLESS_NATIVE_SOURCE_RESPONSE_MISSING")
        item=json.loads(line)
        if item.get("ok") is not True:
            raise ValueError("WINGLESS_NATIVE_SOURCE_REJECTED:"+str(item.get("error")))
        return item

    def choose(self,before):
        a=self.request("choose",before=wingless_wire_grid(before))["action"]
        if type(a) is not int or a not in (0,1,2):
            raise ValueError("WINGLESS_UNLAWFUL_ACTION")
        return a

    def learn(self,before,arm,after,reward,done):
        self.request("learn",before=wingless_wire_grid(before),action=arm,
                     after=wingless_wire_grid(after),
                     reward=float(reward),terminal=bool(done))

    def snapshot(self):
        return base64.b64decode(self.request("snapshot")["state"])

    def restore(self,raw):
        self.request("load",state=base64.b64encode(raw).decode())

    def close(self):
        if self.proc.poll() is None:
            try:self.request("quit")
            except Exception:pass
            self.proc.stdin.close()
            self.proc.stdout.close()
            self.proc.wait(timeout=10)


def train_experiences():
    """Common genuine original FIT stream; no native or control gets more data."""
    import random
    stream=[]; records=[];initial=[]
    start_cpu=time.process_time()
    for fi,family in enumerate(FAMILIES):
        for seed in PHASE_SEEDS["FIT"]:
            env=make_env(family)
            try:
                obs,info=env.reset(seed=seed)
                st=public(obs)
                initial.append({"family":family,"seed":seed,
                    "public_start_sha256":st["grid_sha256"],"public_goal":list(st["goal"])})
                rng=random.Random(810000+1000*fi+seed)
                for _ in range(96 if family=="empty" else 192):
                    action=rng.randrange(3)
                    new_obs,reward,terminated,truncated,_=env.step(action)
                    nxt=public(new_obs,st["goal"])
                    done=bool(terminated or truncated)
                    record=recorded_fit_transition(st,action,nxt,reward,family,seed,done)
                    records.append(record)
                    stream.append({"family":family,"seed":seed,"action":action,
                      "before":public_grid(st),"after":public_grid(nxt),
                      "reward":float(reward),"terminal":done,
                      "start_sha256":st["grid_sha256"],
                      "next_sha256":nxt["grid_sha256"]})
                    st=nxt
                    if done:break
            finally:env.close()
    return stream,records,initial,time.process_time()-start_cpu


def source_hints(stream,initial,model):
    known={family:len({r["public_start_sha256"] for r in initial
                if r["family"]==family}) for family in FAMILIES}
    done={family:{r["action"] for r in stream if r["family"]==family}
                for family in FAMILIES}
    eligibility=bool(model["FIT_source_eligible"] and
      all(known[f]>=16 and done[f]=={0,1,2} for f in FAMILIES))
    return {"qualified":eligibility,"distinct_public_starts":known,
       "seen_actions":{k:sorted(v) for k,v in done.items()},
       "original_empirical_fit_support":model["FIT_support"]}


def train_native(stream,go_exe,ygg_source):
    import native_policy as native
    if str(ygg_source.resolve()) not in [str(Path(x).resolve()) for x in sys.path]:
        raise ValueError("YGG_NATIVE_SOURCE_MODULE_NOT_IN_PINNED_PATH")
    wing=WingBridge(go_exe)
    ygg=native.GridColony()
    win_cpu=time.perf_counter();yg_cpu=time.process_time()
    for e in stream:
        b=e["before"];a=e["action"];n=e["after"]
        wing.learn(b,a,n,e["reward"],e["terminal"])
        ygg.observe(native.PublicGrid(
            b["X"],b["Y"],b["GoalX"],b["GoalY"],b["Direction"],b["FrontBlocked"]),
            a,native.PublicGrid(
            n["X"],n["Y"],n["GoalX"],n["GoalY"],n["Direction"],n["FrontBlocked"]),
            e["reward"],e["terminal"])
    train_elapsed=time.perf_counter()-win_cpu
    wing_raw=wing.snapshot();ygg_raw=ygg.save()
    wing.close()
    # A fresh Go process; no trained state from the original process remains.
    new_wing=WingBridge(go_exe)
    new_wing.restore(wing_raw)
    cold_script="""import native_policy,sys,json
s=native_policy.GridColony.restore(sys.stdin.buffer.read())
ob=native_policy.PublicGrid(3,3,6,5,0,False)
print(json.dumps({"action":s.choose(ob),"updates":s.feedback_updates}))
"""
    cold=subprocess.run([sys.executable,"-B","-c",cold_script],
            input=ygg_raw,capture_output=True,timeout=30)
    if cold.returncode:
        raise ValueError("YGG_COLD_NATIVE_PROCESS_RESTORE_FAILED:"+cold.stderr.decode()[-1000:])
    cold_value=json.loads(cold.stdout)
    probe=native.PublicGrid(3,3,6,5,0,False)
    if cold_value!={"action":ygg.choose(probe),"updates":len(stream)}:
        raise ValueError("YGG_COLD_NATIVE_PREDICTIONS_CHANGED")
    for entry in stream[:8]:
        b=entry["before"]
        if new_wing.choose(b)!=WingBridgeChoiceAfterRaw(wing_raw,go_exe,b):
            raise ValueError("WINGLESS_COLD_RESTART_ACTION_DRIFT")
    if ygg.feedback_updates!=len(stream):
        raise ValueError("YGG_NATIVE_FIT_UPDATE_COUNT_NOT_MATCHED")
    return new_wing,ygg,wing_raw,ygg_raw,{"total_native_fit_wall_seconds":train_elapsed,
      "total_shared_native_fit_python_cpu_seconds":time.process_time()-yg_cpu,
      "native_fit_events_each":len(stream),
      "wingless_checkpoint_bytes":len(wing_raw),"yggdrasil_checkpoint_bytes":len(ygg_raw),
      "wingless_checkpoint_sha256":hashlib.sha256(wing_raw).hexdigest(),
      "yggdrasil_checkpoint_sha256":hashlib.sha256(ygg_raw).hexdigest(),
      "authentic_independent_native_cold_process_restores":True}


def WingBridgeChoiceAfterRaw(raw,go_exe,b):
    """Independent cold process audit on public samples only, no episode use."""
    w=WingBridge(go_exe)
    try:w.restore(raw);return w.choose(b)
    finally:w.close()


def episode(family,seed,method,control,wing,ygg,native):
    cpu=time.process_time();wall=time.perf_counter()
    env=make_env(family)
    nsteps=0;reward_total=0.;first=None;success=False;trace=[]
    try:
        obs,info=env.reset(seed=seed)
        st=public(obs);initial_hash=st["grid_sha256"]
        original_goal=list(st["goal"])
        for t in range(96 if family=="empty" else 192):
            if method=="wingless_native":
                a=wing.choose(public_grid(st))
            elif method=="yggdrasil_native":
                a=ygg.choose(native_from_public(native,st))
            else:
                a=act(family,st,method,control,seed,t)
            if type(a) is not int or a not in (0,1,2):
                raise ValueError("K4U_POLICY_ILLEGAL_PUBLIC_ACTION")
            if first is None:first=a
            new_obs,reward,terminated,truncated,_=env.step(a)
            nxt=public(new_obs,st["goal"])
            trace.append((st["x"],st["y"],st["dir"],a,nxt["x"],nxt["y"],nxt["dir"],float(reward)))
            nsteps+=1;reward_total+=float(reward)
            st=nxt
            if terminated or truncated:
                success=bool(terminated and reward_total>0.)
                break
        return {"family":family,"seed":seed,"policy":method,
          "initial_public_sha256":initial_hash,"public_goal":original_goal,
          "first_action":first,"success":success,"real_reward":reward_total,
          "steps":nsteps,"actual_public_trace_sha256":sha(canon(trace).encode()),
          "process_cpu_seconds":time.process_time()-cpu,
          "wall_seconds":time.perf_counter()-wall}
    finally:env.close()


def phase(name,model,wing,ygg,native):
    outcomes=[]
    for family in FAMILIES:
        for seed in PHASE_SEEDS[name]:
            for method in METHODS:
                outcomes.append(episode(family,seed,method,model,wing,ygg,native))
    return outcomes


def evaluate(dev):
    details={};checks={}
    for family in FAMILIES:
        groups={m:[x for x in dev if x["family"]==family and x["policy"]==m] for m in METHODS}
        if any(len(x)!=8 for x in groups.values()):
            raise ValueError("K4U_CONTROL_EVALUATION_PARITY_DRIFT")
        rates={m:sum(x["success"] for x in group)/8 for m,group in groups.items()}
        returns={m:sum(x["real_reward"] for x in group)/8 for m,group in groups.items()}
        firsts={m:sorted({x["first_action"] for x in group}) for m,group in groups.items()}
        detail={"success_rate":rates,"mean_public_reward":returns,"first_action_ids":firsts}
        details[family]=detail
    for m in ("wingless_native","yggdrasil_native"):
        gate={}
        for family in FAMILIES:
            q=details[family]
            gate[family+"_five_of_eight_real_successes"]=q["success_rate"][m]>=5/8
            gate[family+"_action_diversity"]=len(q["first_action_ids"][m])>=2
            gate[family+"_at_least_75pct_learned_planner_reward"]=(
                  q["mean_public_reward"][m]>=.75*q["mean_public_reward"]["learned_model_bfs"])
        q=details["fourrooms"]
        gate["fourrooms_two_additional_wins_over_tabular_q"]=(
             (q["success_rate"][m]-q["success_rate"]["tabular_q"])>=2/8)
        checks[m]=gate
    passed=all(all(v.values()) for v in checks.values())
    return {"result":"BOTH_INDEPENDENT_NATIVE_MINIGRID_SOURCE_POSITIVE" if passed else
           "NO_QUALIFIED_NATIVE_UNFAMILIAR_WORLD_TRANSFER",
      "family_results":details,"per_candidate_frozen_gates":checks,
      "two_native_candidates_all_gates_pass":passed,"scientific_accepted":False,
      "new_architecture_breakthrough_claim":False}


def execute(p,go_exe,ygg_dir):
    import native_policy as native
    wall=time.perf_counter();cpu=time.process_time()
    train_stream,records,initial,fit_cpu=train_experiences()
    control=fitted(records,initial)
    evidence={"schema":SCHEMA,"gate":"LCRM01-K4U",
      "source_commit":p["sources"]["commit"],
      "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
      "native_Wingless_commit":p["sources"]["wingless"]["commit"],
      "native_Yggdrasil_commit":p["sources"]["yggdrasil"]["commit"],
      "FIT_episodes":len(initial),"FIT_public_experience_count":len(train_stream),
      "FIT_public_experiences":train_stream,"FIT_original_starts":initial,
      "FIT_control_fitted_state_sha256":sha(canon(control).encode()),
      "FIT_control_checkpoint_bytes":len(canon(control).encode()),
      "CHECK_evaluations":0,"DEV_evaluations":0,
      "K4R_original_scientific_benchmark_qualified":True,
      "K4S_original_source_negative_preserved":True,
      "scientific_first_use":False,"scientific_accepted":False}
    info=source_hints(train_stream,initial,control)
    evidence["FIT_source_eligibility"]=info
    if not info["qualified"]:
        evidence["result"]="FIT_NATIVE_SOURCE_UNQUALIFIED_HOLDOUT_NOT_CONSUMED"
        return evidence
    wing,ygg,wraw,yraw,fit_info=train_native(train_stream,go_exe,ygg_dir)
    try:
        evidence["native_FIT_checks"]=fit_info
        check=phase("CHECK",control,wing,ygg,native)
        dev=phase("DEV",control,wing,ygg,native)
        outcome=evaluate(dev)
        evidence.update({"result":"COMPLETE_PROSPECTIVE_NATIVE_MINIGRID_DEVELOPMENT",
             "CHECK_evaluations":len(check),"DEV_evaluations":len(dev),
             "CHECK_public_outcomes":check,"DEV_public_outcomes":dev,
             "native_science":outcome})
        return evidence
    finally:wing.close()


def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--wingless-binary",type=Path,required=True)
    pa.add_argument("--yggdrasil-source-dir",type=Path,required=True)
    pa.add_argument("--output",type=Path,required=True)
    args=pa.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        raise RuntimeError("K4U_ORIGINAL_OUTPUT_NOT_FRESH")
    start_cpu=time.process_time();start_wall=time.perf_counter()
    try:
        p=protocol()
        sys.path.insert(0,str(args.yggdrasil_source_dir.resolve()))
        result=execute(p,args.wingless_binary,args.yggdrasil_source_dir)
    except Exception as e:
        result={"schema":SCHEMA,"gate":"LCRM01-K4U",
            "result":"ORIGINAL_SOURCE_OR_INFRASTRUCTURE_UNQUALIFIED",
            "error_type":type(e).__name__,"error":str(e),
            "traceback_tail":traceback.format_exc().splitlines()[-12:],
            "scientific_first_use":False,"scientific_accepted":False}
    result["resource"]={"whole_python_process_CPU_seconds":time.process_time()-start_cpu,
         "wall_seconds":time.perf_counter()-start_wall,
         "peak_python_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
         "FIT_physics_shared":True,
         "go_bridge_CPU_not_in_python_process_CPU":True}
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("K4U_ORIGINAL_EXECUTION="+result["result"])
    if "native_science" in result:
        print("K4U_SOURCE_SCIENCE="+result["native_science"]["result"])
        print("K4U_DEV_SUCCESS="+canon(result["native_science"]["family_results"]))
        print("K4U_FROZEN_NATIVE_GATES="+canon(result["native_science"]["per_candidate_frozen_gates"]))
    print("K4U_FIT_REAL_EXPERIENCES="+str(result.get("FIT_public_experience_count",0)))
    return 1 if result["result"]=="ORIGINAL_SOURCE_OR_INFRASTRUCTURE_UNQUALIFIED" else 0

if __name__=="__main__":
    sys.exit(main())
