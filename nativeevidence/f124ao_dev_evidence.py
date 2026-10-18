"""F124-AO frozen evaluator: TRAIN preflight first; exactly one DEV after clearance.

The source/evaluator alone possesses operator names, inverse and graph truth.
Training-selection JSON is frozen in Git before any DEV case is constructed.
Model scores are always computed before comparing to source-only controls.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys,random,gc,time,statistics,tracemalloc,platform
from pathlib import Path
import f124ao_frozen_source as source
import f124ao_public_relation_learner as learned
import f124ao_packed_ambiguity as newwing
import f124ao_training_evidence as prior
import f124an_calibrated_affine as an_y
import f124am_example_affine_learner as am_y
import f124al_noisy_operator_learner as al_y
import f124ag_transition_models as ag
import f124am_terminal_competition as original_w
import f124al_packed_confidence as al_w
import f124ae_scoring_transfer as aa_w
import f124aa_development_evidence as fixed_module
import f124q_independent_binding as q

SCHEMA="forge.research.f124ao.frozen-first-dev-source-backed-outcome.v1"
SELECTED=Path(__file__).resolve().parents[1]/"reference/research-intake/f124ao-post-train-selected-parameters.json"
SELECTED_BLOB="e30c39911fe9aee5af48c1d94233c5a5402b99bc"
TRAIN_SHA="40d21628aa38ebad9e26f1ebcb4ee918bd60aba58b19fe065eb54bc0062f6217"
FAMILIES=tuple(source.FAMILIES)

def need(ok,tag):source.need(ok,"DEV_"+tag)

def lineage(o,t,an,train):
    source.frozen()
    need(source.witness.blob(SELECTED)==SELECTED_BLOB,
         "IMMUTABLE_SELECTED_PRIOR_TO_DEV")
    frozen=json.loads(SELECTED.read_text(encoding="utf-8"))
    raw=Path(train).read_bytes()
    need(hashlib.sha256(raw).hexdigest()==TRAIN_SHA,
         "AUTHENTIC_TRAIN_RAW_BYTES")
    report=json.loads(raw)
    base,delta,_=prior.identity(o,t,an)
    need(frozen["schema"]=="forge.research.f124ao.frozen-post-train-selected-config.v1"
         and frozen["status"]=="TRAIN_COMPLETE_DEV_UNCONSUMED"
         and frozen["source_blob"]==source.FREEZE_BLOB
         and frozen["train_run_id"]==39121840563
         and frozen["train_head_sha"]=="a9e3d0818f2dc407dfc8857057f932ba0f80bb26"
         and frozen["train_artifact_id"]==12133978388
         and frozen["train_raw_json_sha256"]==TRAIN_SHA
         and frozen["never_tune_on_DEV"]
         and report["schema"]==prior.SCHEMA
         and report["source_blob"]==source.FREEZE_BLOB
         and report["only_train_sources_evaluated"]
         and report["dev_cases_generated"]==0
         and not report["dev_selection_or_retuning"]
         and report["selected"]==frozen["selection"]
         and len(report["grid"]["Yggdrasil"])==24
         and len(report["grid"]["Wingless"])==7
         and all(v is False for v in frozen["acceptance_boundary"].values()),
         "AUTHENTIC_FROZEN_TRAIN_BEFORE_DEV")
    for lane in ("Yggdrasil","Wingless"):
        need(report["original_foundations"][lane]["base_sha256"]==
             q.digest(base[lane]) and
             report["original_foundations"][lane]["delta_sha256"]==
             q.digest(delta[lane]),
             "HISTORICAL_FIXED_MODEL_IDENTITY")
    return base,delta,frozen

def blank():
    return {"pairs":0,"paired":0,"FP":0,"FN":0,
            "by_family":{f:{"pairs":0,"paired":0,"FP":0,"FN":0}
                         for f in FAMILIES},
            "accepted_long_ids":[],"max_active":0,"max_retained":0,
            "max_states_per_node":0,"max_packed_bits_per_state":0,
            "model_bit_operations":0,"model_extra_candidate_inspections":0,
            "abstained_pairs":0,"case_sha256":[]}

def record(row,fam,identity,positive,negative,depth,meta1,meta2,works):
    pair=int(positive and not negative)
    for target in (row,row["by_family"][fam]):
        target["pairs"]+=1
        target["paired"]+=pair
        target["FP"]+=int(negative)
        target["FN"]+=int(not positive)
    if depth>=13 and positive:row["accepted_long_ids"].append(identity)
    row["case_sha256"].append(q.digest([identity,fam,positive,negative]))
    for work in works:
        if work is not None:
            for key in ("max_active","max_retained",
                        "max_states_per_node","max_packed_bits_per_state"):
                row[key]=max(row[key],work.get(key,0))
            row["model_extra_candidate_inspections"]+=work.get(
                "model_extra_candidate_inspections",0)
    for meta in (meta1,meta2):
        if meta:
            row["model_bit_operations"]+=meta.get("model_bit_operations",0)
    row["abstained_pairs"]+=int(bool(meta1 and meta1.get("abstained")))

def score_y(arm,g,base,delta,sel):
    if arm=="AO_selected":
        return learned.ygg(g,base,delta,sel["architecture"],
                           sel["bad_bits"],sel["margin"])
    if arm=="AN_original":
        return an_y.ygg(g,base,delta,3,1)
    if arm=="AM_original":
        return am_y.ygg(g,base,delta,24)
    if arm=="AL_original":
        return al_y.ygg(g,base,delta,24)
    raw={k:g[k] for k in ("start","target","roles","edges")}
    score,_,_,work=ag.ygg_transition(raw,base,delta,.1)
    return score,work,None

def score_w(arm,g,base,delta,sel):
    if arm=="AO_selected":
        return newwing.score(g,base,delta,sel["mode"],sel["alpha"])
    if arm=="AN_gamma0":
        return original_w.terminal_competitive(g,base,delta,0.)
    if arm=="AL_cap02":
        return al_w.competitive_capped(g,base,delta,.2)
    if arm=="AA_one_packed":
        return aa_w.frozen_packed(g,base,delta)
    return aa_w.frozen_three(g,base,delta)

def stage(lane,phase,base,delta,selection,resources=False):
    # Preflight only calls this with TRAIN. DEV is explicitly called one time
    # by the separately admitted first-use workflow.
    need(phase in ("TRAIN","DEV"),"AUTHORIZED_STAGE_NAME")
    ygg=lane=="Yggdrasil"
    names=(("AO_selected","AN_original","AM_original",
            "AL_original","AG_unparsed","source_only_true_inverse_AG")
           if ygg else ("AO_selected","AN_gamma0","AL_cap02",
                        "AA_one_packed","AB_three_packed"))
    tables={name:blank() for name in names}
    checks={"valid_positive":0,"valid_negative":0,
            "three_corruptions":0,"old_literal_positive":0,
            "operator_affine":0,"operator_feistel":0,
            "correct_mapping":0,"confident_wrong_mapping":0,
            "abstained_mapping":0,"oracle_in_model":False,
            "wing_source_only_normalized":not ygg}
    cases=source.pairs(lane,phase)
    need(len(cases)==48,"SOURCE_DENOMINATOR")
    truth=source.parent.am.old.prior.parent.original.parent.prior.parent.routes15
    all_graphs=[]
    for seed,vec,fam,op,nonce,p,n in cases:
        identity=q.digest([seed,list(vec),fam])
        depth=len(p["roles"])
        # Source restore is not handed to Yggdrasil models.
        # Wingless receives source-certified normalized inputs in every arm.
        graphs=(p,n) if ygg else (source.plain(p,op,nonce),
                                   source.plain(n,op,nonce))
        if len(all_graphs)<24:
            all_graphs.append(graphs[0])
        for arm in names:
            if arm=="source_only_true_inverse_AG":
                continue
            decisions=[]
            works=[]
            metas=[]
            for g in graphs:
                if ygg:
                    score,work,meta=score_y(arm,g,base,delta,selection)
                else:
                    score,work=score_w(arm,g,base,delta,selection)
                    meta=None
                need(math.isfinite(score),"MODEL_OUTPUT_FINITE")
                decisions.append(score>=0)
                works.append(work)
                metas.append(meta)
            record(tables[arm],fam,identity,*decisions,depth,*metas,works)
        restored_p=source.plain(p,op,nonce) if ygg else graphs[0]
        restored_n=source.plain(n,op,nonce) if ygg else graphs[1]
        # Model predictions above are already completed for each graph.
        if ygg:
            normalized,diag=learned.normalize(
                p,selection["architecture"],selection["bad_bits"],
                selection["margin"])
            if normalized is None:
                checks["abstained_mapping"]+=1
            elif normalized==restored_p:
                checks["correct_mapping"]+=1
            else:
                checks["confident_wrong_mapping"]+=1
            scores=[]
            works=[]
            for graph in (restored_p,restored_n):
                score,_,_,work=ag.ygg_transition(graph,base,delta,.1)
                scores.append(score>=0);works.append(work)
            record(tables["source_only_true_inverse_AG"],fam,identity,
                   *scores,depth,None,None,works)
        relax=fam=="rotate4_tolerant"
        checks["valid_positive"]+=int(truth(restored_p,relaxed=relax)==1)
        checks["valid_negative"]+=int(truth(restored_n,relaxed=relax)==0)
        checks["old_literal_positive"]+=int(
            truth({k:p[k] for k in ("start","target","roles","edges")},
                  relaxed=True)>0)
        checks["three_corruptions"]+=int(sum(
            source.relation(d["input_bits"],op)!=d["output_bits"]
            for d in p["demos"])==3)
        checks["operator_affine" if op.startswith("affine_")
               else "operator_feistel"]+=1
    need(checks["valid_positive"]==48 and checks["valid_negative"]==48
         and checks["three_corruptions"]==48 and
         checks["old_literal_positive"]==0 and
         checks["operator_affine"]==24 and checks["operator_feistel"]==24,
         "INDEPENDENT_TRUE_GRAPH_LABELS")
    for arm,row in tables.items():
        need(row["pairs"]==48 and len(row["case_sha256"])==48
             and all(f["pairs"]==12 for f in row["by_family"].values()),
             "MODEL_PAIRED_DENOMINATOR")
        if ygg:
            need(row["max_active"]<=7 and row["max_retained"]<=9,
                 "YGG_SEVEN_NINE_CAPACITY")
        elif arm in ("AO_selected","AN_gamma0","AL_cap02",
                     "AA_one_packed"):
            need(row["max_states_per_node"]==1 and
                 row["max_packed_bits_per_state"]==12 and
                 row["max_active"]<=64,
                 "WING_ONE_PACKED_CAPACITY")
    if ygg:
        need(sum(checks[k] for k in ("correct_mapping",
             "confident_wrong_mapping","abstained_mapping"))==48,
             "YGG_MAPPED_OR_ABSTAINED_ACCOUNTING")
    else:
        # Selected gamma0 must be bit-identical to untouched original AN.
        need(tables["AO_selected"]["case_sha256"]==
             tables["AN_gamma0"]["case_sha256"],
             "CONTROL_IDENTITY_PREDICTION")
        # Case digests include only identity, fam and decisions, not arm name.
    return {"phase":phase,"lane":lane,"pairs":48,"models":tables,
            "source_diagnostic":checks,
            "resource_graphs":all_graphs if resources else []}

def measured(lane,graphs,base,delta,selection):
    need(len(graphs)==24,"MATCHED_RESOURCE_GRAPHS")
    arms=(("AO_selected","AN_original") if lane=="Yggdrasil"
          else ("AO_selected","AN_gamma0","AL_cap02","AA_one_packed"))
    summary={}
    for arm in arms:
        times=[];peaks=[]
        for graph in graphs:
            function=(lambda:score_y(arm,graph,base,delta,selection)
                      if lane=="Yggdrasil" else
                      lambda:score_w(arm,graph,base,delta,selection))
            function()
            for _ in range(3):
                t=time.perf_counter_ns()
                function()
                times.append(time.perf_counter_ns()-t)
            gc.collect()
            tracemalloc.start()
            function()
            _,peak=tracemalloc.get_traced_memory()
            tracemalloc.stop()
            peaks.append(peak)
        summary[arm]={"graphs":24,"timed_calls":72,
                      "p50_model_only_ns":int(statistics.median(times)),
                      "p50_python_peak_bytes":int(statistics.median(peaks)),
                      "samples_sha256":q.digest([times,peaks])}
    return {"host":platform.platform(),"python":platform.python_version(),
            "timing_not_hardware_equalized":True,
            "source_truth_inverse_excluded":True,
            "arms":summary}

def evaluate(mode,o,t,an,train):
    base,delta,freeze=lineage(o,t,an,train)
    sel=freeze["selection"]
    period="TRAIN" if mode=="preflight" else "DEV"
    result={"schema":SCHEMA,"mode":mode,"period":period,
            "frozen_selection_blob":SELECTED_BLOB,
            "original_train_raw_sha256":TRAIN_SHA,
            "frozen_source_blob":source.FREEZE_BLOB,
            "selection":sel,
            "source_evaluator_inverse_is_not_learned":True,
            "no_DEV_selection_or_retuning":True,
            "protected_first_use":False,
            "independent_science_acceptance":False,
            "optimizer_promotion":False,
            "production_activation":False,
            "lanes":[]}
    for lane in ("Yggdrasil","Wingless"):
        item=stage(lane,period,base[lane],delta[lane],
                   sel[lane],resources=mode=="dev")
        if mode=="dev":
            item["resources"]=measured(
                lane,item.pop("resource_graphs"),base[lane],
                delta[lane],sel[lane])
        else:item.pop("resource_graphs")
        arms=item["models"]
        if lane=="Yggdrasil":
            novel=arms["AO_selected"]
            control=arms["AN_original"]
            item["strict_scientific_win"]=(
                novel["FP"]==0 and novel["paired"]>control["paired"] and
                any(novel["by_family"][f]["paired"]>0 for f in
                    ("rotate4_dense_13_15","xor16_extended_13_15")))
            item["confident_wrong_inference"] = item[
                "source_diagnostic"]["confident_wrong_mapping"]
        else:
            novel=arms["AO_selected"]
            control=arms["AN_gamma0"]
            item["strict_long_positive_preserved"]=set(
                control["accepted_long_ids"]).issubset(
                    set(novel["accepted_long_ids"]))
            item["strict_scientific_win"]=(
                item["strict_long_positive_preserved"] and
                novel["FP"]<control["FP"])
        result["lanes"].append(item)
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=("preflight","dev"),required=True)
    for key in ("o","t","an","train","output"):
        ap.add_argument("--"+key,required=True)
    a=ap.parse_args()
    path=Path(a.output)
    need(path.parent.is_dir() and not path.exists(),"APPEND_ONLY_OUTPUT")
    report=evaluate(a.mode,a.o,a.t,a.an,a.train)
    raw=json.dumps(report,sort_keys=True,indent=2).encode()+b"\n"
    with path.open("xb") as f:f.write(raw)
    print("F124AO_"+a.mode.upper()+"_RAW_SHA256="+hashlib.sha256(raw).hexdigest())
    for lane in report["lanes"]:
        old="AN_original" if lane["lane"]=="Yggdrasil" else "AN_gamma0"
        print("F124AO_"+a.mode.upper()+"_"+lane["lane"]+
              "=selected:"+str(lane["models"]["AO_selected"]["paired"])+
              "/48;original:"+str(lane["models"][old]["paired"])+
              "/48;FP:"+str(lane["models"]["AO_selected"]["FP"])+
              ";strict:"+str(lane["strict_scientific_win"]))
    print("F124AO_PROTECTED_SCIENCE_ACCEPTED=false")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print("F124AO_DEV_FAIL_CLOSED:"+str(error),file=sys.stderr)
        sys.exit(1)
