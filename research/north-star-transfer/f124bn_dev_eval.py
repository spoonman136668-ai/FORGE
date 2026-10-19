"""F124-BN one original new-development FIT against the eligible frozen AZ.

All tasks are from two independently source-born *new* FIT cohorts.
BM negative examples, prior 192 TRAIN, BH U/R and all holdouts are barred.
Records go to append-only individual files before summary; no reruns on fail.
"""
from __future__ import annotations

import argparse,hashlib,importlib.util,json,math
from pathlib import Path
import platform,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
NATIVE=ROOT/"nativeevidence"
A=range(916000,916012)
B=range(917000,917012)
BLOBS={
 "learner":"fc627c4d8b627cdf7368f1b6c188ed5d2214ee51",
 "mix":"56909261219777cae7e975b80278e9387370b552",
 "word":"450165b2d497d6ac0d923fcbeaccd5a29959f24c",
 "AZ":"0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7",
 "native":"94d2ae8266da792d254ac54baf3056bbd9b49412"
}


def need(ok,msg):
    if not ok:raise RuntimeError("F124BN_FIRSTUSE_"+msg)


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec and spec.loader,"MODULE")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def gitblob(path):
    p=subprocess.run(["git","rev-parse","HEAD:"+str(path.relative_to(ROOT))
                       .replace("\\","/")],cwd=ROOT,text=True,capture_output=True)
    need(p.returncode==0,"GIT_OBJECT_LOOKUP")
    return p.stdout.strip()


def identity(case):
    need(type(case) is int,"PROTECTED_ID")
    if case in A:return "mix",HERE/"f124bn_mix_source.py"
    if case in B:return "word",HERE/"f124bn_word_source.py"
    raise RuntimeError("F124BN_FIRSTUSE_PROTECTED_SOURCE_DENIED")


def bits(n):
    return [(n>>j)&1 for j in range(16)]


def canonical(data):
    return hashlib.sha256(json.dumps(
        data,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def run(case,arm):
    need(arm in ("learned","AZ"),"FROZEN_ARMS")
    family,file=identity(case)
    need(sys.platform=="linux","LINUX_OS_ACCOUNTING")
    import resource
    need(gitblob(file)==BLOBS[family]
         and gitblob(HERE/"f124bn_learned_causal.py")==BLOBS["learner"]
         and gitblob(NATIVE/"f124az_joint_public_inverse.py")==BLOBS["AZ"]
         and gitblob(NATIVE/"f124ag_transition_models.py")==BLOBS["native"],
         "SOURCE_ORIGINALITY_DRIFT")
    t0=time.process_time_ns()
    source=module("bn_model_free_origin_"+family,file)
    issued,private=source.make(case)
    need(private["truth_positive"]==1 and private["truth_negative"]==0,
         "SOURCE_LABEL_UNAMBIGUOUS")
    fit,check=issued["FIT"],issued["CHECK"]
    graph_p,graph_n=issued["positive"],issued["hard_negative"]
    need(len(fit)==40 and len(check)==8 and
         graph_p["demos"]==graph_n["demos"],"IDENTICAL_PUBLIC_SUPPORT")
    pub=fit+check
    payload={"public":pub,"positive":graph_p,"negative":graph_n}
    sys.path.insert(0,str(NATIVE))
    import f124az_joint_public_inverse as original
    import f124ag_transition_models as native
    import f124aj_example_operator_learner as parser
    demos=[{"input_bits":bits(x),"output_bits":bits(y)}
           for x,y in pub]
    need(demos[:24]==graph_p["demos"],"EXACT_NATIVE_SOURCE_SUPPORT")
    base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
    delta=[0.0,0.0]
    if arm=="AZ":
        trained=original.train(demos,"F124BN-PROSPECTIVE-PUBLIC-ONLY",0)
        positive,p_work,p_diag=original.score(graph_p,base,delta,trained,demos)
        negative,n_work,n_diag=original.score(graph_n,base,delta,trained,demos)
        route={"original_scientific_policy":True,
               "original_policy_choice":trained["choice"],
               "positive_native_work":p_work,
               "negative_native_work":n_work,
               "model_bits_lower":trained["extra_task_model_bits_lower"],
               "AZ_forced_diagnostic_used":False}
    else:
        learned=module("bn_frozen_learned_causal",HERE/"f124bn_learned_causal.py")
        try:
            model,learn_info=learned.fit(fit,check)
        except ValueError as err:
            # An unidentifiable mechanism must abstain; never oracle-fallback.
            positive=negative=-1e9
            route={"original_scientific_policy":False,
                   "learned_identifiable":False,
                   "fit_rejection":str(err),
                   "native_graph_calls":0,
                   "trained_model_bits_lower":272}
        else:
            judgments=[]
            native_works=[]
            for g in (graph_p,graph_n):
                consistent,hops=learned.causal_path(g,model)
                decoded,source_support,nonce=parser.public_task(g)
                need(source_support==demos[:24],"PUBLIC_NATIVE_GRAPH_IDENTITY")
                native.frozen.prior.parent.validate_15(decoded)
                for edge in decoded["edges"]:
                    v=sum(bit<<j for j,bit in enumerate(edge["src_bits"]))
                    x=learned.inverse(v,model)
                    edge["src_bits"]=bits(x)
                native.frozen.prior.parent.validate_15(decoded)
                native_score,raw,ratio,work=native.ygg_transition(
                    decoded,list(base),list(delta),.1)
                need(math.isfinite(native_score)
                     and work["max_active"]<=7 and work["max_retained"]<=9,
                     "NATIVE_COGNITION_7_9")
                judgments.append(1. if consistent else -1.)
                native_works.append({"score":native_score,
                                     "native_work":work,"causal_checked_hops":hops})
            positive,negative=judgments
            route={"original_scientific_policy":False,
                   "learned_identifiable":True,
                   "fit_receipt":learn_info,
                   "native_graph_calls":2,
                   "positive_native_work":native_works[0],
                   "negative_native_work":native_works[1],
                   "trained_model_bits_lower":272,
                   "source_oracle_used":False}
    cpu=time.process_time_ns()-t0
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cpu>0 and rss>0,"OS_CPU_RSS")
    return {"schema":"mass.f124bn.new-original-dev-fit-causal-pair.v1",
            "case":case,"family":family,"arm":arm,
            "original_public_pair_and_graph_sha256":canonical(payload),
            "positive_graph_sha256":canonical(graph_p),
            "negative_graph_sha256":canonical(graph_n),
            "positive_accepted":positive>=0,
            "negative_false_positive":negative>=0,
            "positive_score":positive,"negative_score":negative,
            "original_private_symbolic_truth":{"positive":1,"negative":0},
            "model_trace":route,"CPU_ns":cpu,"whole_process_peak_RSS_bytes":rss,
            "old_BM_cases_reused":False,"old_TRAIN_replayed":False,
            "BH_U_R_or_BN_holdout_used":False,
            "scientific_accepted":False,"optimizer_promoted":False}


def summarize(rows):
    need(len(rows)==48,"24_CASES_TIMES_TWO_ARMS")
    families={}
    for family,seeds in (("mix",A),("word",B)):
        paired=[]
        for seed in seeds:
            items=[r for r in rows if r["case"]==seed]
            need(len(items)==2 and {r["arm"] for r in items}=={"AZ","learned"}
                 and all(r["family"]==family for r in items),
                 "EXACT_SOURCE_PAIR")
            original=next(x for x in items if x["arm"]=="AZ")
            proposed=next(x for x in items if x["arm"]=="learned")
            need(original["original_public_pair_and_graph_sha256"]==
                 proposed["original_public_pair_and_graph_sha256"],
                 "UNMATCHED_GRAPH_OR_PUBLIC")
            paired.append({
                "case":seed,"AZ_positive":original["positive_accepted"],
                "AZ_FP":original["negative_false_positive"],
                "learner_positive":proposed["positive_accepted"],
                "learner_FP":proposed["negative_false_positive"],
                "learner_identifiable":proposed["model_trace"].get(
                    "learned_identifiable",False),
                "AZ_CPU_ns":original["CPU_ns"],
                "learner_CPU_ns":proposed["CPU_ns"],
                "AZ_RSS":original["whole_process_peak_RSS_bytes"],
                "learner_RSS":proposed["whole_process_peak_RSS_bytes"],
                "public_task_sha256":original["original_public_pair_and_graph_sha256"]
            })
        lost=[r["case"] for r in paired if r["AZ_positive"]
              and not r["learner_positive"]]
        fp=[r["case"] for r in paired if r["learner_FP"]]
        azcorrect={r["case"] for r in paired if r["AZ_positive"] and not r["AZ_FP"]}
        learnedcorrect={r["case"] for r in paired
                        if r["learner_positive"] and not r["learner_FP"]}
        valid=(not lost and not fp and len(learnedcorrect-azcorrect)>=2)
        families[family]={
            "pairs":len(paired),"AZ_positive_count":sum(r["AZ_positive"] for r in paired),
            "AZ_hard_FP_count":sum(r["AZ_FP"] for r in paired),
            "learner_positive_count":sum(r["learner_positive"] for r in paired),
            "learner_FP_case_ids":fp,"baseline_positive_lost_ids":lost,
            "correctly_classified_learned_pairs":len(learnedcorrect),
            "newly_correct_pairs":sorted(learnedcorrect-azcorrect),
            "learned_identifiable_cases":sum(r["learner_identifiable"] for r in paired),
            "FIT_gate_met":valid,"paired":paired}
    return {"schema":"mass.f124bn.frozen-new-relationship-dev-fit.v1",
            "cases_consumed":24,"original_arm_records":48,
            "families":families,
            "joint_FIT_gate":all(f["FIT_gate_met"] for f in families.values()),
            "original_BM_source_reused":False,
            "original_BH_U_R_holdout_used":False,
            "new_BN_128_holdout_used":False,
            "original_consumed_TRAIN_replayed":False,
            "complete_train_amortized_CPU_memory_scientific_parity":False,
            "independent_external_originality_certified":False,
            "scientific_accepted":False,"optimizer_promotion":False,
            "scientific_disposition":"DEVELOPMENT_ONLY_NO_PROTECTED_FIRSTUSE"}


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--child",action="store_true")
    a.add_argument("--case",type=int)
    a.add_argument("--arm",choices=("learned","AZ"))
    a.add_argument("--output",type=Path)
    args=a.parse_args()
    if args.child:
        need(args.case is not None and args.arm is not None,"ARGS")
        print(json.dumps(run(args.case,args.arm),sort_keys=True))
        return
    need(args.output is not None,"OUTPUT")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for case in list(A)+list(B):
        for arm in ("AZ","learned"):
            p=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                              "--child","--case",str(case),"--arm",arm],
                             cwd=ROOT,capture_output=True,text=True,timeout=180)
            need(p.returncode==0,"ORIGINAL_CASE_CHILD_FAILED_"+
                 str(case)+"_"+arm+":"+p.stderr[-1600:])
            raw=json.loads(p.stdout)
            filename=args.output.parent/("original_"+str(case)+"_"+arm+".json")
            with filename.open("x",encoding="utf-8") as f:
                json.dump(raw,f,sort_keys=True,indent=2)
                f.write("\n")
            rows.append(raw)
    result={"summary":summarize(rows)}
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2)
        f.write("\n")
    print("F124BN_NEW_DEVELOPMENT_CASES=24")
    print("F124BN_NEW_ORIGINAL_MODEL_RECORDS=48")
    print("F124BN_FROZEN_FIT_GATE="+str(result["summary"]["joint_FIT_gate"]))
    print("F124BN_PROTECTED_HOLDOUT_USED=0")
    print("F124BN_SCIENTIFIC_ACCEPTANCE=false")


if __name__=="__main__":
    main()
