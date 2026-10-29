"""AC-26 read-only original MG11 public transition persistence analysis.

Replays verified, already consumed, source-selected original Farama traces.
A conventional online public transition-graph observer is a DIAGNOSTIC CONTROL,
not the Wingless/Yggdrasil native learner or a model-selected actor.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
from collections import Counter

SCHEMA="forge.ac26.original-mg11-public-persistence-audit.v1"
CANON_SHA="84e93a1cc86addfc27622ea860eac9ea7c6d4b3cfec02ec3e01e04d56b475ba2"
PARENT_HEAD="933703862228eb7b6b4c72dbb6ab9b2f297e1fdb"
SOURCE_FARAMA="7f5853792ea7f04f75614661006d87fcf949f26d"
ROLES=("wingless_go_dk12","yggdrasil_r16",
       "conventional_regularized_public_effect","conventional_seeded_random")
SEEDS=(71301,71303,71307)
POSITIVE_REQUIRED=("wingless_go_dk12","yggdrasil_r16",
                    "conventional_regularized_public_effect")
FIELDS=frozenset(("image","direction","mission"))
REPORT_FILES=("first.json","second.json","comparison.json")

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("utf-8")
def sha(b):
    return hashlib.sha256(b).hexdigest()
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

class PublicGraphObserver:
    """Conventional *equal-public*, online transition memory; no action choice."""
    def __init__(self,initial):
        self.views={initial}
        self.edges=set()
        self.action_edges=set()
        self.last_edge=None
        self.counts=Counter()
    def learn_selected(self,before,action,after):
        # No future state/reward/door label supplied before the selected step.
        # This method is called only AFTER source action and observation.
        if before not in self.views:
            raise RuntimeError("AC26_PUBLIC_CONTINUITY_STATE_ABSENT")
        changed=before!=after
        revisit=after in self.views
        edge=(before,after)
        reverse=changed and (after,before) in self.edges
        immediate=changed and self.last_edge==(after,before)
        repeated=(before,action,after) in self.action_edges
        novelty=not revisit
        self.counts.update({
          "public_changed":int(changed),
          "novel_public_successor":int(novelty),
          "revisited_successor":int(revisit),
          "changed_successor_already_seen":int(changed and revisit),
          "previously_seen_reverse_edge":int(reverse),
          "immediate_two_step_reversal":int(immediate),
          "repeated_same_selected_public_transition":int(repeated),
        })
        self.views.add(after)
        self.edges.add(edge)
        self.action_edges.add((before,action,after))
        self.last_edge=edge
        return {"changed":changed,"novel":novelty,"revisited":revisit,
                "reverse":reverse,"immediate_reversal":immediate}
def verify_public(v):
    if (type(v) is not dict or set(v)!=FIELDS or
        type(v["direction"]) is not int or not 0<=v["direction"]<=3 or
        type(v["mission"]) is not str or
        type(v["image"]) is not list or len(v["image"])!=7 or
        any(type(row) is not list or len(row)!=7 or
            any(type(pixel) is not list or len(pixel)!=3 or
                any(type(c) is not int or not 0<=c<=255 for c in pixel)
                for pixel in row) for row in v["image"])):
        raise RuntimeError("AC26_INVALID_OR_PRIVILEGED_PUBLIC_VISUAL_INPUT")
    return sha(canonical(v))

def score_trace(record):
    if (type(record) is not dict or
        record.get("role") not in ROLES or record.get("seed_evaluator_only") not in SEEDS
        or record.get("original_live_selected_steps")!=192 or
        record.get("external_actions")!=0 or
        type(record.get("real_source_events")) is not list or
        len(record["real_source_events"])!=192):
        raise RuntimeError("AC26_UNEXPECTED_ROLE_SEED_OR_SOURCE_STEP_COUNT")
    events=record["real_source_events"]
    first=verify_public(events[0]["public_before"])
    if first!=record["original_start_public_sha256"]:
        raise RuntimeError("AC26_ORIGINAL_START_PUBLIC_HASH_MISMATCH")
    observer=PublicGraphObserver(first)
    previous_after=None
    door_open=key_pick=key_drop=front_held=forward_held=0
    real_reward=0.
    action_counts=Counter()
    for idx,event in enumerate(events,1):
        if (type(event) is not dict or event.get("role")!=record["role"] or
            event.get("step")!=idx or
            type(event.get("actual_original_source_action")) is not int or
            not 0<=event["actual_original_source_action"]<=6 or
            event.get("external_live_actions")!=0 or
            type(event.get("source_reward")) not in (float,int) or
            not math.isfinite(event["source_reward"]) or
            event.get("terminated") not in (False,True) or
            event.get("truncated") not in (False,True)):
            raise RuntimeError("AC26_SELECTED_REAL_SOURCE_EVENT_CONTRACT_DRIFT")
        a=event["actual_original_source_action"]
        b=verify_public(event["public_before"])
        nxt=verify_public(event["public_after"])
        if (b!=event.get("original_public_before_sha256") or
            nxt!=event.get("original_public_after_sha256") or
            (previous_after is not None and b!=previous_after)):
            raise RuntimeError("AC26_SOURCE_PUBLIC_HASH_OR_TIMELINE_CHANGED")
        observer.learn_selected(b,a,nxt)
        previous_after=nxt
        action_counts[a]+=1
        # Source-annotated downstream audit ONLY, NEVER fed to observer.
        for name in ("source_visible_door_opened","public_pickup","public_drop",
                     "public_door_front_while_held","public_forward_while_held"):
            if type(event.get(name)) is not bool:
                raise RuntimeError("AC26_SOURCE_AUDIT_FLAG_TYPE_DRIFT")
        door_open+=int(event["source_visible_door_opened"])
        key_pick+=int(event["public_pickup"])
        key_drop+=int(event["public_drop"])
        front_held+=int(event["public_door_front_while_held"])
        forward_held+=int(event["public_forward_while_held"])
        real_reward+=event["source_reward"]
    observed={
      "role":record["role"],
      "seed":record["seed_evaluator_only"],
      "real_original_source_selected_actions":192,
      "distinct_source_action_ids":len(action_counts),
      "source_selected_action_histogram":{str(i):action_counts[i] for i in range(7)},
      "unique_public_visual_states_including_initial":len(observer.views),
      **dict(observer.counts),
      "source_visible_door_openings_retrospective_only":door_open,
      "source_key_pickups_retrospective_only":key_pick,
      "source_key_drops_retrospective_only":key_drop,
      "source_front_door_while_held_retrospective_only":front_held,
      "source_forward_while_held_retrospective_only":forward_held,
      "true_original_source_reward":real_reward,
      "policy_selected_using_future_or_audit_source_labels":False,
    }
    if (observed["public_changed"]!=record["same_heading_scene_change_count"]+
        record["heading_change_count"] and
        # These original counters are feature-specific: changes in camera
        # orientation and scene can overlap; never falsely equate them.
        observed["public_changed"]<record["same_heading_scene_change_count"]):
        raise RuntimeError("AC26_SOURCE_ORIGINAL_VISIBLE_EFFECT_CONTRADICTION")
    if (door_open!=record["source_visible_door_openings"] or
        key_pick!=record["source_key_pickups"] or
        key_drop!=record["source_key_drops"] or
        front_held!=record["front_door_while_held"] or
        forward_held!=record["forward_while_held"] or
        real_reward!=record["source_goal_rewards"]):
        raise RuntimeError("AC26_ORIGINAL_SOURCE_REPORTED_COUNTS_DIVERGED")
    return observed

def verify_two_processes(first,second,comparison):
    if (type(first) is not dict or type(second) is not dict or
        first.get("schema")!="itd02.mg11.authentic-original-public-nonrotational-motion.v1"
        or second.get("schema")!=first["schema"] or
        first.get("classification")!="MG11_ORIGINAL_NATIVE_GOALS_NOT_BOTH_ESTABLISHED__NO_SCIENCE"
        or second.get("classification")!=first["classification"] or
        first.get("original_episode_count")!=12 or second.get("original_episode_count")!=12 or
        first.get("external_live_actions")!=0 or second.get("external_live_actions")!=0 or
        first.get("scientific_first_use") is not False or second.get("scientific_first_use") is not False or
        first.get("accepted_native_model_promoted") is not False):
        raise RuntimeError("AC26_ORIGINAL_MG11_PARENT_NEGATIVE_NOT_QUALIFIED")
    if ("canonical_original_source_evidence" not in first or
        "canonical_original_source_evidence" not in second):
        raise RuntimeError("AC26_TWO_PROCESS_CANONICAL_SOURCE_CUSTODY_FAILED")
    a=first["canonical_original_source_evidence"]
    b=second["canonical_original_source_evidence"]
    if (sha(canonical(a))!=CANON_SHA or sha(canonical(b))!=CANON_SHA or
        a!=b or first.get("canonical_original_source_sha256")!=CANON_SHA or
        second.get("canonical_original_source_sha256")!=CANON_SHA or
        comparison.get("canonical_original_source_sha256")!=CANON_SHA or
        comparison.get("classification")!=first["classification"] or
        comparison.get("two_independent_fresh_original_source_processes") is not True or
        comparison.get("selected_source_actions_not_external") is not True or
        comparison.get("scientific_first_use") is not False or
        a.get("original_upstream_farama")!=SOURCE_FARAMA or
        a.get("original_source_fit_samples_each")!=1664):
        raise RuntimeError("AC26_TWO_PROCESS_CANONICAL_SOURCE_CUSTODY_FAILED")
    return a

def analyze(first,second,comparison):
    parent=verify_two_processes(first,second,comparison)
    records=parent["native_and_conventional_public_source_records"]
    if len(records)!=12 or {(r["role"],r["seed_evaluator_only"]) for r in records}!={
            (role,seed) for role in ROLES for seed in SEEDS}:
        raise RuntimeError("AC26_SOURCE_ROLE_AND_DEVELOPMENT_SEED_SET_DRIFT")
    audits=[score_trace(r) for r in records]
    for role in POSITIVE_REQUIRED:
        row=next(x for x in audits if x["role"]==role and x["seed"]==71303)
        if (row["public_changed"]!=70 or
            row["changed_successor_already_seen"]!=66 or
            row["immediate_two_step_reversal"]!=66 or
            row["source_visible_door_openings_retrospective_only"]!=34 or
            row["true_original_source_reward"]!=0):
            raise RuntimeError("AC26_ORIGINAL_DOOR_TOGGLE_REVERSAL_PREDICTION_FALSIFIED")
        a=next(x for x in audits if x["role"]==role and x["seed"]==71301)
        if (a["unique_public_visual_states_including_initial"]!=3 or
            a["changed_successor_already_seen"]!=27):
            raise RuntimeError("AC26_ORIGINAL_PUBLIC_SOURCE_A_ONLY_REPEAT_DRIFT")
    totals={role:{
        "source_selected_actions":sum(x["real_original_source_selected_actions"] for x in audits if x["role"]==role),
        "changed_views":sum(x["public_changed"] for x in audits if x["role"]==role),
        "new_successor_views":sum(x["novel_public_successor"] for x in audits if x["role"]==role),
        "revisited_changed_views":sum(x["changed_successor_already_seen"] for x in audits if x["role"]==role),
        "immediate_two_step_reversals":sum(x["immediate_two_step_reversal"] for x in audits if x["role"]==role),
        "original_source_goal_rewards":sum(x["true_original_source_reward"] for x in audits if x["role"]==role),
    } for role in ROLES}
    return {
      "schema":SCHEMA,"scope":"ORIGINAL_MG11_REPLAY_ONLY_NOT_NEW_NATIVE_TRAINING",
      "parent_exact_head":PARENT_HEAD,
      "source_original_farama":SOURCE_FARAMA,
      "canonical_independent_original_source_sha256":CANON_SHA,
      "source_original_processes":2,
      "source_owned_original_development_episodes_replayed":12,
      "source_owned_original_selected_steps_replayed":2304,
      "new_source_episodes_or_actions":0,
      "policy_training_or_selection":False,
      "native_wingless_or_ygg_source_modified":False,
      "original_environment_imported_or_reset":False,
      "replay_audit_flags_never_used_by_policy":True,
      "controller_or_accepted_science_changed":False,
      "scientific_first_use":False,"scientific_admission":False,
      "source_role_seed_metrics":audits,
      "role_summary":totals,
      "classification":"AC26_PUBLIC_REVERSAL_AND_NONPERSISTENT_PROGRESS_OBSERVED__NO_SCIENCE"
    }
def run(first,second,comparison,out):
    r=analyze(load(first),load(second),load(comparison))
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return r
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for key in ("first","second","comparison","out"): ap.add_argument("--"+key,type=Path,required=True)
    a=ap.parse_args()
    r=run(a.first,a.second,a.comparison,a.out)
    print("AC26_SOURCE_PERSISTENCE_REPLAY=PASS")
    print("AC26_SOURCE_GOAL_BOTH_NATIVE=ZERO")
    print("AC26_DOOR_REVERSAL_DIAGNOSTIC=VERIFIED")
    print("AC26_SCIENTIFIC_ADMISSION=NO")
