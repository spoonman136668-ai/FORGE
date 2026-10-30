"""NR-M2C: source-free public-goal planning and eight-step forecast comparison.

An OFFLINE synthetic development task, not an original environment benchmark.
Goal-public states are constructed by evaluator truth but only PUBLIC goal
and start are passed into the unchanged, common-budget BFS planner.
"""
from collections import deque
import argparse
import hashlib
import json
from pathlib import Path
import time
import tracemalloc

from nr_m1z_pinned_r7 import NonlinearLocalLearner
from nr_m2b_factor_cells import PersistentFactorCells
from test_nr_m2b_factor_cells import (
    public_effect, source_samples, source_selected_training,
    trained_original_r7, held_states, true_chain,
)

GOAL_SEQUENCES=((0,1,2,0,1),(2,1,0,2,1))
EIGHT_ACTIONS=(0,2,1,0,1,2,0,2)
EXPANSION_LIMIT=364
PLANNING_HORIZON=5
PUBLIC_START_COUNT=16
SOURCE_SEEDS=(11,12)

class ExactPublicTable:
    """Conventional same-source exact observation store; never guess unseen."""
    def __init__(self, seed):
        self.seen={}
        for episode in source_samples(seed):
            for state in episode:
                for action in range(3):
                    key=(state,action)
                    value=public_effect(seed,action,state)
                    if key in self.seen and self.seen[key]!=value:
                        raise AssertionError("NRM2C_BASELINE_CONTRADICTORY_PUBLIC_SOURCE")
                    self.seen[key]=value
    def step(self,state,action):
        if (state,action) in self.seen:
            return self.seen[state,action],True
        return None,False

class NoMemory:
    def step(self,state,action):
        return None,False

def plan(transition, start, goal):
    """Same deterministic breadth-first planner, no evaluator transitions."""
    if type(start) is not int or type(goal) is not int or not 0<=start<256 or not 0<=goal<256:
        raise ValueError("NRM2C_NONPUBLIC_GOAL")
    if start==goal:
        return (),0
    frontier=deque([(start,())])
    seen={start}
    expanded=0
    while frontier:
        state,path=frontier.popleft()
        if len(path)>=PLANNING_HORIZON:
            continue
        expanded+=1
        if expanded>EXPANSION_LIMIT:
            return None,expanded
        for action in (0,1,2):
            after,known=transition(state,action)
            if not known:
                continue
            new_path=path+(action,)
            if after==goal:
                return new_path,expanded
            if after not in seen:
                seen.add(after)
                frontier.append((after,new_path))
    return None,expanded

def original_r7_step(model):
    return lambda state,action:(model.step("one-source-public-world",action,state),True)

def synthetically_execute(seed, public_start, path):
    # Evaluation ONLY: true authored afters are never passed into plan().
    state=public_start
    for selected in path:
        state=public_effect(seed,selected,state)
    return state

def evaluate_arm(arm, transition, seed, tasks, held):
    metrics={"tasks":len(tasks),"plans":0,"goals_reached":0,
             "synthetic_selected_actions":0,"expanded_nodes":0,
             "plan_lengths":[],"eight_step_trials":len(held),
             "eight_step_correct":0,"eight_step_abstentions":0,
             "per_task_action_sequences":[]}
    for start,goal in tasks:
        sequence,expanded=plan(transition,start,goal)
        metrics["expanded_nodes"]+=expanded
        if sequence is None:
            metrics["per_task_action_sequences"].append(None)
            continue
        metrics["plans"]+=1
        metrics["synthetic_selected_actions"]+=len(sequence)
        metrics["plan_lengths"].append(len(sequence))
        metrics["per_task_action_sequences"].append(list(sequence))
        if synthetically_execute(seed,start,sequence)==goal:
            metrics["goals_reached"]+=1
    for start in held:
        current=start
        known=True
        for action in EIGHT_ACTIONS:
            current,step_known=transition(current,action)
            if not step_known:
                known=False
                break
        if not known:
            metrics["eight_step_abstentions"]+=1
        elif current==true_chain(seed,start,EIGHT_ACTIONS):
            metrics["eight_step_correct"]+=1
    if metrics["plans"]>0:
        metrics["mean_selected_actions_per_plan"]=(
            sum(metrics["plan_lengths"])/metrics["plans"])
    else:
        metrics["mean_selected_actions_per_plan"]=None
    return metrics

def track(work):
    tracemalloc.start()
    cpu=time.process_time_ns()
    wall=time.perf_counter_ns()
    result=work()
    result_cpu=time.process_time_ns()-cpu
    result_wall=time.perf_counter_ns()-wall
    current,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    # A short control evaluation may legitimately consume zero *measured* CPU\n    # ticks on Windows. Preserve the raw zero; never fabricate a speedup.\n    return result,{"cpu_ns":result_cpu,"wall_ns":result_wall,\n                   "cpu_timer_quantized":result_cpu==0 and result_wall>0,\n                   "tracemalloc_peak_bytes":peak}

def source_only_report():
    original_base=trained_original_r7(11)
    base_raw=original_base.checkpoint()
    base_sha=hashlib.sha256(base_raw).hexdigest()
    candidate=PersistentFactorCells(original_base)
    regimes=[]
    total_choice_disagreements=0
    for seed in SOURCE_SEEDS:
        # The underlying R7 model is NEVER modified, and candidate keeps its
        # history from the previous authored episode without an oracle ID.
        strong, strong_training=track(lambda:trained_original_r7(seed))
        def train_candidate():
            source_selected_training(candidate,seed)
            return candidate
        _, native_training=track(train_candidate)
        snap=candidate.checkpoint()
        restored=PersistentFactorCells.restore(
            snap,base_sha,hashlib.sha256(snap).hexdigest())
        held=held_states(seed)
        if len(held)!=64 or len(set(held))!=64:
            raise AssertionError("NRM2C_UNEXPECTED_PUBLIC_HELDOUT_ROSTER")
        # Goal recipe is EVALUATOR-ONLY. It creates reachable synthetic
        # public goals but is not included in the planner's inputs.
        tasks=[
            (start,true_chain(seed,start,sequence))
            for start in held[:PUBLIC_START_COUNT] for sequence in GOAL_SEQUENCES
        ]
        if len(tasks)!=32:
            raise AssertionError("NRM2C_TASK_COUNT_DRIFT")
        arms={
          "native_factor":{
            "transition":candidate.step,
            "trained_effect_samples":len(candidate.rows[0])*3,
            "checkpoint_bytes":len(snap),
            "training_cost":native_training
          },
          "strong_fitted_original_r7":{
            "transition":original_r7_step(strong),
            "trained_effect_samples":576,
            "checkpoint_bytes":len(strong.checkpoint()),
            "training_cost":strong_training
          },
          "exact_state_count":{
            "transition":ExactPublicTable(seed).step,
            "trained_effect_samples":576,
            "checkpoint_bytes":None,
            "training_cost":None
          },
          "no_memory":{
            "transition":NoMemory().step,
            "trained_effect_samples":0,
            "checkpoint_bytes":0,
            "training_cost":None
          }
        }
        results={}
        for name,data in arms.items():
            metrics,planning_cost=track(
                lambda: evaluate_arm(name,data["transition"],seed,tasks,held))
            results[name]={**metrics,"training_events_effective":data["trained_effect_samples"],
                           "checkpoint_bytes":data["checkpoint_bytes"],
                           "training_cost":data["training_cost"],
                           "planning_cost":planning_cost}
        same=sum(a!=b for a,b in zip(
            results["native_factor"]["per_task_action_sequences"],
            results["strong_fitted_original_r7"]["per_task_action_sequences"]
        ))
        total_choice_disagreements+=same
        if candidate.episodes!=3*(SOURCE_SEEDS.index(seed)+1) or restored.checkpoint()!=snap:
            raise AssertionError("NRM2C_PERSISTENT_CUSTODY_DRIFT")
        if original_base.checkpoint()!=base_raw:
            raise AssertionError("NRM2C_UNEXPECTED_BASE_DRIFT")
        regimes.append({
            "source_only_regime":seed,
            "own_selected_events_cumulative":candidate.events,
            "sliding_window_evictions":candidate.evictions,
            "explicit_world_identity_given_to_candidate":False,
            "heldout_public_starts":len(held),
            "public_task_starts":PUBLIC_START_COUNT,
            "source_only_reachable_public_goal_tasks":len(tasks),
            "goal_sequence_rules_evaluator_only":True,
            "selected_action_disagreements_with_strong_fitted_R7":same,
            "cold_restore_identical":True,
            "arms":results
        })
    summary={
      "schema":"nr-m2c-source-only-matched-action-planning-v1",
      "actual_original_world_actions":0,
      "original_farama_environment_used":False,
      "original_r7_source_sha":"204ecd993b954b23e66d6d1e8b3568e7c93183c5",
      "same_effective_current_regime_training_per_action":192,
      "same_public_goal_inputs_and_search_budget":True,
      "planning_horizon":PLANNING_HORIZON,
      "expansion_budget":EXPANSION_LIMIT,
      "eight_step_forecast_horizon":len(EIGHT_ACTIONS),
      "predeclared_source_free_public_tasks":64,
      "total_action_choice_disagreements_strong_control":total_choice_disagreements,
      "full_CPU_RSS_assurance":"NOT_MEASURED; process CPU and Python traced allocations are exploratory only",
      "first_use_scientific_authorization":False,
      "native_architecture_integration":False,
      "regimes":regimes
    }
    return summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    x=p.parse_args()
    result=source_only_report()
    if x.output:
        x.output.parent.mkdir(parents=True,exist_ok=True)
        x.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf8")
    short={
      "regimes":[{
        "seed":r["source_only_regime"],
        "native":{"goals":r["arms"]["native_factor"]["goals_reached"],
                  "eight_step":r["arms"]["native_factor"]["eight_step_correct"]},
        "strong_R7":{"goals":r["arms"]["strong_fitted_original_r7"]["goals_reached"],
                     "eight_step":r["arms"]["strong_fitted_original_r7"]["eight_step_correct"]},
        "action_disagreements":r["selected_action_disagreements_with_strong_fitted_R7"]
      } for r in result["regimes"]]
    }
    print("NRM2C_SOURCE_ONLY_ACTION_PLANNING_COMPARISON "+json.dumps(short,sort_keys=True))

if __name__=="__main__":
    main()
