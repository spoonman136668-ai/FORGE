"""F124: closed-loop model-free research-direction discovery and falsification.

Uses live current-source GenEnv advisory candidates and a bounded set of
preregistered *development challenge directions*. Selected directions become
actual new graph challenges, with train-only calibration, disjoint confirmation,
feedback-driven second round, and optional verified scheduled continuity.

No real scientific hypothesis/implementation discovery, first-use, or promotion.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import f118_autonomy_feedback as f118
import f120_generated_environment as f120

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "reference/research-intake/f124-autonomy-feedback-freeze.json"
FREEZE_BLOB = "96bf614c0e99bc03916530daffb6e52b4f9e5ae5"
F118_BLOB = "9ed9127a06d1a22b5ef8519e67730f3dc90e1c6c"
F120_BLOB = "775c120fb4dfb27baf52240f88c11d8a99478451"
SCHEMA = "forge.autonomy.f124.feedback-directed-development.v1"
DIRECTIONS = ("DEPTH_SHORTCUT", "DISTRACTOR_SHORTCUT", "ROLE_ALIAS_SHORTCUT")
LANES = ("Wingless", "Yggdrasil")
HEX40 = re.compile(r"^[a-f0-9]{40}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")

class Quarantined(ValueError):
    pass

def need(ok, code):
    if not ok:
        raise Quarantined("F124_" + code)

def canonical(obj):
    return f118.canonical(obj)

def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def freeze():
    raw = FREEZE.read_bytes().replace(b"\r\n", b"\n")
    need(f118.gitblob(raw) == FREEZE_BLOB, "FROZEN_PROTOCOL_DRIFT")
    need(f118.gitblob((ROOT/"nativeevidence/f118_autonomy_feedback.py").read_bytes().replace(b"\r\n",b"\n")) == F118_BLOB
         and f118.gitblob((ROOT/"nativeevidence/f120_generated_environment.py").read_bytes().replace(b"\r\n",b"\n")) == F120_BLOB,
         "CACHED_FOUNDATION_IDENTITY_DRIFT")
    p = json.loads(raw)
    need(p["schema"] == "forge.autonomy.f124.frozen-feedback-driven-curriculum.v1"
         and p["parent_main_sha"] == "0eca385586f8d4860a3b0076a880962419bdccc0"
         and tuple(p["directions"]) == DIRECTIONS and p["budget"]["rounds"] == 2
         and p["budget"]["train_cases_per_round"] == 8
         and p["budget"]["confirmation_cases_per_round"] == 16
         and p["schedule"].startswith("Existing forge-integrated")
         and all(p["authority"].values()), "PREREGISTRATION_INVALID")
    return hashlib.sha256(raw).hexdigest()

def mutate(candidate, direction):
    vector = list(candidate["vector"])
    index = DIRECTIONS.index(direction)
    vector[index] = min(3, vector[index] + 1)
    need(vector != candidate["vector"] or vector[index] == 3,
         "UNAUTHORIZED_DELTA")
    return vector

def seeds(lane, round_index, phase):
    need(lane in LANES and round_index in (0,1)
         and phase in ("TRAIN", "CONFIRM"), "INVALID_SOURCE_NAMESPACE")
    base = (112000 if lane == "Wingless" else 113000) + round_index * 1000
    if phase == "CONFIRM":
        return range(base + 100, base + 116)
    return range(base, base + 8)

def run_cases(vector, lane, round_index, phase):
    records = []
    for seed in seeds(lane, round_index, phase):
        graph = f120.graph(seed, vector)
        pos, neg = graph["positive"], graph["negative"]
        exact = f120.readout(graph, f120.binding_solver)
        depth = f120.readout(graph, lambda c,e:f120.binding_solver(c,e,max_hops=2))
        role = f120.readout(graph, f120.role_only)
        need(exact["paired_correct"] and not role["paired_correct"]
             and graph["hops"] == vector[0] + 1,
             "INVALID_GRAPH_FALSIFICATION_OR_ORACLE")
        records.append({"seed":seed,"graph_sha256":f120.sha(graph),
            "hops":graph["hops"], "distractors":vector[1],
            "role_aliases":vector[2],
            "oracle_pair":bool(exact["paired_correct"]),
            "depth2_pair":bool(depth["paired_correct"]),
            "role_only_pair":bool(role["paired_correct"])})
    count=len(records)
    need(count == (8 if phase=="TRAIN" else 16),
         "COHORT_BUDGET_CHANGED")
    oracle=sum(int(x["oracle_pair"]) for x in records)
    depth=sum(int(x["depth2_pair"]) for x in records)
    role=sum(int(x["role_only_pair"]) for x in records)
    return {"cases":count,"sha256":sha(records),
        "oracle_correct":oracle,"depth2_correct":depth,
        "role_only_correct":role,
        "discrimination":oracle-max(depth,role),
        "structural_diversity":vector[1]+vector[2],
        "records":records}

def calibration(candidates,lane,round_index):
    options=[]
    for idx,direction in enumerate(DIRECTIONS):
        # Source-linked bounded mutation from one of the two GenEnv artifacts.
        parent=candidates[idx % len(candidates)]
        new_vector=mutate(parent,direction)
        screen=run_cases(new_vector,lane,round_index,"TRAIN")
        options.append({"direction":direction,
            "source_candidate_sha256":parent["source_candidate_sha256"],
            "source_candidate_index":parent["candidate_index"],
            "vector":new_vector,
            "derived_candidate_sha256":sha({"parent":parent["source_candidate_sha256"],
                                             "direction":direction,"vector":new_vector}),
            "screen":screen})
    need(len({x["derived_candidate_sha256"] for x in options})==3,
         "NONUNIQUE_GENERATED_HYPOTHESES")
    return options

def validate_history(history):
    need(type(history) is dict and len(history)<=6, "HISTORY_SIZE")
    out={}
    for key,row in history.items():
        need(type(key) is str and re.fullmatch(
            r"(Wingless|Yggdrasil):(DEPTH_SHORTCUT|DISTRACTOR_SHORTCUT|ROLE_ALIAS_SHORTCUT)",key)
            and type(row) is dict and set(row)=={"count","total_discrimination","last_discrimination","negatives"}
            and all(type(row[k]) is int for k in row)
            and 0 <= row["count"] <= 100000
            and 0 <= row["total_discrimination"] <= row["count"]*16
            and 0 <= row["last_discrimination"] <= 16
            and 0 <= row["negatives"] <= row["count"],
            "HISTORY_PROVENANCE")
        out[key]=dict(row)
    return out

def previous_state(previous,meta,current_run_id):
    if previous is None:
        need(meta is None,"MISSING_PREVIOUS_METADATA")
        return {},0,None,"BOOTSTRAP_NO_PREVIOUS_F124_SCHEDULE"
    need(type(previous) is dict and type(meta) is dict,
         "UNTRUSTED_PREVIOUS_STATE")
    need(previous.get("schema")==SCHEMA
        and previous.get("event")=="schedule"
        and previous.get("run_id")==meta.get("id")
        and previous.get("source_sha")==meta.get("head_sha")
        and meta.get("event")=="schedule"
        and meta.get("head_branch")=="main"
        and meta.get("run_attempt")==1
        and meta.get("conclusion")=="success"
        and type(meta.get("id")) is int
        and 0<meta["id"]<current_run_id
        and type(meta.get("head_sha")) is str
        and HEX40.fullmatch(meta["head_sha"])
        and previous.get("scientific_originals")==0
        and previous.get("accepted_ref_mutations")==0
        and previous.get("optimizer_promotions")==0
        and previous.get("unattended_two_run_continuity_proven") is False
        and type(previous.get("generation")) is int
        and previous["generation"]>0
        and previous["generation"]<=100000,
        "PREVIOUS_RUN_IDENTITY_OR_AUTHORITY")
    rounds=previous.get("rounds")
    need(type(rounds) is list and len(rounds)==4
         and all(type(x) is dict
                 and x.get("lane") in LANES
                 and x.get("direction") in DIRECTIONS
                 and type(x.get("confirmation")) is dict
                 and x["confirmation"].get("cases")==16
                 and type(x["confirmation"].get("sha256")) is str
                 and HEX64.fullmatch(x["confirmation"]["sha256"])
                 for x in rounds), "PREVIOUS_RUN_RESULT_MISSING")
    return validate_history(previous.get("history")),previous["generation"],sha(previous),"VERIFIED_PREVIOUS_F124_SCHEDULE"

def choose(options,history,lane,exclude=(),recent=None):
    # Decisions use previously *observed* confirmation rewards and current
    # TRAIN-only calibration, not current-round confirmation data.
    preferred=None
    if recent is not None:
        direction, observed=recent
        need(direction in DIRECTIONS and type(observed) is int
             and 0<=observed<=16, "NONOBSERVED_SUCCESSOR_SIGNAL")
        # A failed discrimination and a successful discrimination lead to
        # DIFFERENT successors from the same history; this is an observed
        # feedback-driven choice, not an automatic fixed rotation.
        step=1 if observed>0 else 2
        preferred=DIRECTIONS[(DIRECTIONS.index(direction)+step)%3]
    def key(option):
        d=option["direction"]
        row=history.get(f"{lane}:{d}")
        count=row["count"] if row else 0
        reward=row["total_discrimination"] if row else 0
        negative=row["negatives"] if row else 0
        # Unexplored first; if exhausted, prioritize lowest measured
        # discrimination (open falsification question) and observed negatives.
        # Calibration breaks ties exclusively on training-only graphs.
        return (count, int(preferred is not None and d != preferred),
                reward*100//max(1,count), -negative,
                -option["screen"]["discrimination"],
                -option["screen"]["structural_diversity"],
                DIRECTIONS.index(d))
    eligible=[o for o in options if o["direction"] not in exclude]
    need(bool(eligible),"NO_ELIGIBLE_UNREPEATED_DIRECTION")
    return min(eligible,key=key)

def evolve(history,lane,direction,score):
    need(0<=score<=16,"OUTCOME_NOT_FINITE_OR_BOUNDED")
    key=f"{lane}:{direction}"
    prev=history.get(key,{"count":0,"total_discrimination":0,"last_discrimination":0,"negatives":0})
    next_row={"count":prev["count"]+1,
        "total_discrimination":prev["total_discrimination"]+score,
        "last_discrimination":score,
        "negatives":prev["negatives"]+int(score==0)}
    history[key]=next_row

def execute(advisory,source,run_id,event,previous=None,meta=None):
    frozen_sha=freeze()
    need(type(source) is str and HEX40.fullmatch(source)
         and type(run_id) is int and run_id>0
         and event in ("schedule","push","pull_request","workflow_dispatch")
         and (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
         "CURRENT_RUN_SOURCE_UNPINNED")
    if event!="schedule":
        need(previous is None and meta is None,
             "NON_SCHEDULED_REPLAY_FORBIDDEN")
    candidates=f120.validate(advisory,source)
    history,generation,prior_hash,continuity=previous_state(previous,meta,run_id)
    results=[]
    for round_index in (0,1):
        for lane in LANES:
            pool=calibration(candidates[lane],lane,round_index)
            prior_actions=[r for r in results if r["lane"]==lane]
            executed_this_run={r["direction"] for r in prior_actions}
            recent=(prior_actions[-1]["direction"], prior_actions[-1]["feedback_discrimination"]) if prior_actions else None
            selected=choose(pool,history,lane,exclude=executed_this_run,recent=recent)
            # Current round confirmation is only opened AFTER the direction
            # has been selected by prior feedback + training calibration.
            confirm=run_cases(selected["vector"],lane,round_index,"CONFIRM")
            need(confirm["oracle_correct"]==16,
                 "CONTROLLED_EXPERIMENT_INVALID")
            direction=selected["direction"]
            selected_before=sha(history)
            evolve(history,lane,direction,confirm["discrimination"])
            results.append({"lane":lane,"round":round_index+1,
                "direction":direction,
                "derived_candidate_sha256":selected["derived_candidate_sha256"],
                "source_candidate_sha256":selected["source_candidate_sha256"],
                "source_candidate_index":selected["source_candidate_index"],
                "generated_vector":selected["vector"],
                "selection_history_sha256":selected_before,
                "calibration":[{k:v for k,v in x.items() if k!="screen"}
                               | {"screen_sha256":x["screen"]["sha256"],
                                  "train_discrimination":x["screen"]["discrimination"]}
                               for x in pool],
                "training":selected["screen"],
                "confirmation":confirm,
                "feedback_discrimination":confirm["discrimination"],
                "negative_finding":confirm["discrimination"]==0,
                "accepted_scientific_hypothesis":False})
    need([x["lane"] for x in results]==["Wingless","Yggdrasil"]*2
         and all(results[i]["direction"]!=results[i+2]["direction"]
                 for i in (0,1)), "FEEDBACK_DID_NOT_CHANGE_NEXT_ACTION")
    next_choices={}
    for lane in LANES:
        candidate_pool=calibration(candidates[lane],lane,0)
        next_choices[lane]=choose(candidate_pool,history,lane)["direction"]
    return {"schema":SCHEMA,"source_sha":source,"run_id":run_id,
        "event":event,"freeze_sha256":frozen_sha,
        "advisory_sha256":sha(advisory),"generation":generation+1,
        "continuity":continuity,"prior_record_sha256":prior_hash,
        "rounds":results,"history":history,
        "next_scheduled_development_directions":next_choices,
        "actual_controlled_graph_pairs":2*2*(8+16),
        "feedback_changes_second_round":True,
        "bounded_generated_hypothesis_choices":3,
        "model_free_source_only_challenge_selection":True,
        "scientific_hypothesis_invention_proven":False,
        "unattended_two_run_continuity_proven":False,
        "scientific_originals":0,"accepted_ref_mutations":0,
        "optimizer_promotions":0,"new_schedulers":0,
        "Codex_calls":0,"paid_model_calls":0,
        "ckb_plane_contact":False,"cloudflare_writes":0,
        "mind_palace_writes":0}

def main():
    p=argparse.ArgumentParser()
    for name in ("advisory","source-ref","event","output"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--previous")
    p.add_argument("--previous-meta")
    a=p.parse_args()
    need(bool(a.previous)==bool(a.previous_meta),
         "INCOMPLETE_PREVIOUS_STATE_METADATA")
    previous=f118.load_report(a.previous) if a.previous else None
    meta=f118.load_report(a.previous_meta) if a.previous_meta else None
    proof=execute(f118.load_report(a.advisory),a.source_ref,a.run_id,a.event,
                  previous,meta)
    out=Path(a.output)
    need(out.parent.is_dir() and not out.exists(), "IMMUTABLE_OUTPUT")
    with out.open("xb") as writer:
        writer.write(canonical(proof))

if __name__=="__main__":
    try:main()
    except (Quarantined,f118.Quarantined,f120.Invalid,
            OSError,ValueError,TypeError,KeyError) as e:
        print("F124_AUTONOMY_DEVELOPMENT_QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
