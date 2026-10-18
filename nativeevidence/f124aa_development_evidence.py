"""F124-AA original-custody fresh cross-family transfer and packed-resource evidence.

Novel public keys, distractors, noisy causal relation and >9-hop graphs are
scored on independently salted cohorts. Source labels stay in the scorer.
No FIT tuning, source reconstruction inside model, or model-authority change.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,platform,random,statistics,sys,time,tracemalloc,types
from collections import Counter
from pathlib import Path

import f124aa_frozen_source as s
import f124aa_packed_transfer as m
import f124z_sparse_continuity as z
import f124z_development_evidence as prior
import f124q_independent_binding as original_t
import f124w_hop_trace_indexed as original_w

SCHEMA="forge.research.f124aa.frozen-transfer-and-packed-representation-development.v1"
Z_RAW="d6e19c5b9a572eefab5e0927a41abad6d34c3654c80605f7980b6e0908c3e44c"
WING_ARMS=("new_packed_one_state","original_Z_three_states","strong_fixed")
YGG_ARMS=("frozen_Z_continuity_0_5","original_T_rank","strong_fixed")


def need(ok,name):
    s.need(ok,"EVIDENCE_"+name)


def original_custody(o,t,u,w,x,y,z_raw):
    base,delta=prior.original_custody(o,t,u,w,x,y)
    b=Path(z_raw).read_bytes()
    need(hashlib.sha256(b).hexdigest()==Z_RAW,"AUTHENTIC_Z_RAW_SHA256")
    evidence=json.loads(b)
    need(evidence["schema"]=="forge.research.f124z.authentic-sparse-continuity-new-development.v1"
         and evidence["frozen_protocol_blob"]=="83e82ec2d7ffdbd2fdea69c4cd6dbe0f94cd8f05"
         and evidence["independent_science_acceptance"] is False
         and evidence["optimizer_promotions"]==0
         and evidence["protected_cases_generated"]==0
         and evidence["matched_compute_superiority_proven"] is False
         and evidence["ygg_selected_FIT"]["penalty"]==.5
         and evidence["lanes"][1]["dev"]["arms"]["continuity_penalty"]["paired"]==48
         and evidence["lanes"][1]["dev"]["arms"]["original_T"]["paired"]==36
         and evidence["lanes"][0]["dev"]["arms"]["sparse_on_demand"]["paired"]==45,
         "FROZEN_Z_POSITIVE_AND_NEGATIVE_CUSTODY")
    return base,delta


def prior_sparse(graph,base,delta):
    proxy=types.SimpleNamespace(validate_public=s.validate_extended)
    env=dict(z.sparse_wingless.__globals__)
    env["source"]=proxy
    f=types.FunctionType(z.sparse_wingless.__code__,env,
                         z.sparse_wingless.__name__,z.sparse_wingless.__defaults__)
    return f(graph,base,delta)


def original_fixed():
    return prior.preceding.parent.fixed_factory()


def forward(lane,arm,g,base,delta,fixed):
    if arm=="strong_fixed":
        if len(g["roles"])>9:
            return None,None,None
        result,work=fixed(g)
        return bool(result),work,None
    if lane=="Wingless":
        if arm=="new_packed_one_state":
            score,work=m.packed_one_state(g,base,delta)
        else:
            score,work=prior_sparse(g,base,delta)
    else:
        if arm=="frozen_Z_continuity_0_5":
            score,ratio,raw,work=m.ygg_continuity(g,base,delta)
            old_score,original_counters=m.ygg_original(g,base,delta)
            need(raw==old_score and
                 all(work[k]==original_counters[k] for k in original_counters),
                 "UNCHANGED_T_LOGIT_AND_ORIGINAL_COST")
            need(work["max_active"]<=7 and work["max_retained"]<=9,
                 "ORIGINAL_SEVEN_PLUS_NINE")
        else:
            score,work=m.ygg_original(g,base,delta)
        # Require exact original T/Z source function outputs within historic
        # 7-9-hop domain; extended-depth graph uses scoped shape validator.
        if len(g["roles"])<=9:
            old,_=original_t.forward("Yggdrasil",g,base,delta)
            if arm=="original_T_rank":
                need(old==score,"ORIGINAL_T_EXACT_SAME")
            else:
                z_old,ratio_old,original_work=z.continuity_head(g,base,delta)
                need(z_old==raw and ratio_old==ratio and
                     all(work[k]==original_work[k] for k in original_work),
                     "ORIGINAL_Z_EXACT_SAME")
    return bool(score>=0),work,score


def phase(lane,phase,base,delta,fixed):
    arms=WING_ARMS if lane=="Wingless" else YGG_ARMS
    stats={name:{
        "applicable_pairs":0,"unsupported_pairs":0,"paired":0,
        "false_positives":0,"false_negatives":0,
        "per_family":{family:{"pairs":0,"unsupported":0,"paired":0,
                 "false_positives":0,"false_negatives":0,
                 "by_depth":{}} for family in s.FAMILIES},
        "max_active":0,"max_retained":0,"peak_node_slots":0,
        "max_packed_bits":0,"extra_continuity_cells":0,
        "edge_work":0,"raw_bit_work":0,"case_sha256":[]}
        for name in arms}
    cases=s.pairs(lane,phase)
    for seed,vector,family,pos,neg in cases:
        depth=len(pos["roles"])
        outcomes={}
        for arm in arms:
            p,w1,score1=forward(lane,arm,pos,base,delta,fixed)
            n,w2,score2=forward(lane,arm,neg,base,delta,fixed)
            r=stats[arm];f=r["per_family"][family]
            if p is None or n is None:
                need(p is None and n is None and family=="extended_depth"
                     and arm=="strong_fixed","UNSUPPORTED_DOMAIN_ONLY")
                r["unsupported_pairs"]+=1;f["unsupported"]+=1
                continue
            r["applicable_pairs"]+=1;f["pairs"]+=1
            b=bool(p and not n)
            r["paired"]+=int(b);f["paired"]+=int(b)
            r["false_positives"]+=int(n);f["false_positives"]+=int(n)
            r["false_negatives"]+=int(not p);f["false_negatives"]+=int(not p)
            level=f["by_depth"].setdefault(str(depth),{"pairs":0,"paired":0})
            level["pairs"]+=1;level["paired"]+=int(b)
            for work in (w1,w2):
                r["max_active"]=max(r["max_active"],work.get("max_active",0))
                r["max_retained"]=max(r["max_retained"],work.get("max_retained",0))
                r["peak_node_slots"]=max(r["peak_node_slots"],
                    work.get("max_states_per_node",work.get("state_limit",0)))
                r["max_packed_bits"]=max(r["max_packed_bits"],
                    work.get("max_packed_bits_per_state",0))
                r["extra_continuity_cells"]=max(r["extra_continuity_cells"],
                    work.get("continuity_counter_slots_max",0))
                r["edge_work"]+=work.get("edge_inspections",
                    work.get("public_edge_scans",0))
                r["raw_bit_work"]+=work.get("raw_bit_reads",
                    work.get("on_demand_raw_bit_reads",
                    work.get("raw_bit_ops",work.get("bit_comparisons",0))))
            r["case_sha256"].append(original_t.digest({
               "family":family,"phase":phase,"seed":seed,"vector":vector,
               "arm":arm,"positive":p,"negative":n,"paired":b}))
            outcomes[arm]=(score1,score2)
    need(len(cases)==48,"FULL_SOURCE_PAIR_COHORT")
    for arm,row in stats.items():
        expected=36 if arm=="strong_fixed" else 48
        need(row["applicable_pairs"]==expected and
             row["unsupported_pairs"]==(48-expected) and
             len(row["case_sha256"])==expected,"CONTROL_SCOPE_TRANSPARENCY")
        for family in s.FAMILIES:
            f=row["per_family"][family]
            need(f["pairs"]+f["unsupported"]==12 and
                 (f["pairs"]==12 if family!="extended_depth" or
                    arm!="strong_fixed" else f["unsupported"]==12),
                 "FROZEN_FAMILY_DENOMINATORS")
        need(row["max_retained"]<=9 and
             (row["max_active"]<=7 if lane=="Yggdrasil" else row["max_active"]<=192),
             "UNCHANGED_MODEL_MEMORY_GUARD")
        if arm=="new_packed_one_state":
            need(row["peak_node_slots"]==1 and row["max_active"]<=64
                 and row["max_packed_bits"]==12,"ONE_PACKED_SLOT_LIMIT")
        if arm=="frozen_Z_continuity_0_5":
            need(row["extra_continuity_cells"]<=16,"COUNTER_OVERFLOW")
    return {"phase":phase,"pairs":48,"family_census":{f:12 for f in s.FAMILIES},
            "oracle_only_in_scorer":True,
            "reference_relation_by_family":{
                f:("hamming_at_most_one" if f=="one_bit_relaxed_keys"
                   else "exact_key_equality") for f in s.FAMILIES},
            "arms":stats}


def qt(s,p):
    z=sorted(s)
    return z[min(len(z)-1,math.ceil(len(z)*p)-1)]


def bench_wing(base,delta,fixed):
    samples={family:[] for family in s.FAMILIES}
    for _,_,family,pos,neg in s.pairs("Wingless","DEV"):
        if len(samples[family])<6:
            # Exactly 6 public graphs/family: 3 paired examples.
            samples[family].extend((pos,neg))
    need(all(len(v)==6 for v in samples.values()),"FROZEN_BENCHMARK_GRAPH_CENSUS")
    funcs={"new_packed_one_state":lambda g:m.packed_one_state(g,base,delta),
           "original_Z_three_states":lambda g:prior_sparse(g,base,delta),
           "strong_fixed":lambda g:fixed(g)}
    values={name:{"times":[],"peaks":[],"supported_graphs":0} for name in funcs}
    i=0
    for family in s.FAMILIES:
        for graph in samples[family]:
            i+=1
            order=list(funcs)
            random.Random("F124AA/resource/v1/"+family+"/"+str(i)).shuffle(order)
            for name in order:
                if name=="strong_fixed" and len(graph["roles"])>9:
                    continue
                f=funcs[name]
                f(graph)
                for _ in range(3):
                    t=time.perf_counter_ns()
                    f(graph)
                    values[name]["times"].append(time.perf_counter_ns()-t)
                gc.collect()
                tracemalloc.start()
                f(graph)
                _,peak=tracemalloc.get_traced_memory()
                tracemalloc.stop()
                values[name]["peaks"].append(peak)
                values[name]["supported_graphs"]+=1
    summary={}
    for name,rec in values.items():
        needed=18 if name=="strong_fixed" else 24
        need(len(rec["times"])==needed*3 and len(rec["peaks"])==needed,
             "FROZEN_RESOURCE_SAMPLE_DENOMINATOR")
        summary[name]={"measured_public_graphs":needed,"time_calls":needed*3,
           "median_time_ns":int(statistics.median(rec["times"])),
           "p95_time_ns":qt(rec["times"],.95),
           "median_python_peak_bytes":int(statistics.median(rec["peaks"])),
           "p95_python_peak_bytes":qt(rec["peaks"],.95),
           "sample_sha256":original_t.digest(rec)}
    a=summary["new_packed_one_state"];b=summary["original_Z_three_states"]
    return {"runner":os.environ.get("RUNNER_NAME","unspecified"),
            "os":platform.platform(),"python":platform.python_version(),
            "source_families":list(s.FAMILIES),
            "strong_fixed_excluded_extended_depth_explicitly":True,
            "new_vs_Z_scope_24_graphs":True,"new_vs_fixed_scope_not_matched":True,
            "source_graph_input_memory_not_removed":True,
            "results":summary,
            "new_time_le_previous_Z":a["median_time_ns"]<=b["median_time_ns"],
            "new_allocation_le_previous_Z":
                a["median_python_peak_bytes"]<=b["median_python_peak_bytes"],
            "resource_matched_superiority_proven":False}


def run(o,t,u,w,x,y,z_raw):
    s.frozen()
    base,deltas=original_custody(o,t,u,w,x,y,z_raw)
    fixed=original_fixed()
    result={"schema":SCHEMA,"freeze_git_blob":s.FREEZE_BLOB,
            "Z_parent_raw_sha256":Z_RAW,
            "original_models_unmodified":True,"new_source_disjoint":True,
            "protected_cases_generated":0,"training_steps":0,
            "scientific_acceptance":False,"optimizer_promotion":False,
            "accepted_ref_mutations":0,"resource_matched_superiority":False,
            "not_a_learned_generalization_claim":True,"lanes":[]}
    for lane in ("Wingless","Yggdrasil"):
        row={"lane":lane,
             "FIT":phase(lane,"FIT",base[lane],deltas[lane],fixed),
             "DEV":phase(lane,"DEV",base[lane],deltas[lane],fixed),
             "original_delta_sha256":original_t.digest(deltas[lane])}
        if lane=="Wingless":row["resource_observations"]=bench_wing(base[lane],deltas[lane],fixed)
        result["lanes"].append(row)
    return result


def main():
    parser=argparse.ArgumentParser()
    for name in ("o","t","u","w","x","y","z","output"):
        parser.add_argument("--"+name,required=True)
    args=parser.parse_args()
    target=Path(args.output)
    need(target.parent.is_dir() and not target.exists(),"NONOVERWRITE_CUSTODY")
    data=run(args.o,args.t,args.u,args.w,args.x,args.y,args.z)
    raw=json.dumps(data,sort_keys=True,indent=2).encode()+b"\n"
    with target.open("xb") as file:file.write(raw)
    print("F124AA_RECEIPT_SHA256="+hashlib.sha256(raw).hexdigest())
    for row in data["lanes"]:
        r=row["DEV"]["arms"]
        if row["lane"]=="Wingless":
            print("F124AA_WING_DEV=packed="+str(r["new_packed_one_state"]["paired"])+
                  "/48:Z="+str(r["original_Z_three_states"]["paired"])+
                  "/48:fixed="+str(r["strong_fixed"]["paired"])+"/36_supported")
        else:
            print("F124AA_YGG_DEV=key_equality="+str(r["frozen_Z_continuity_0_5"]["paired"])+
                  "/48:T="+str(r["original_T_rank"]["paired"])+
                  "/48:fixed="+str(r["strong_fixed"]["paired"])+"/36_supported")


if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as e:
        print("F124AA_FAIL_CLOSED:"+str(e),file=sys.stderr)
        sys.exit(1)
