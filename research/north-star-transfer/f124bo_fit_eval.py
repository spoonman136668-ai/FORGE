"""F124-BO frozen prospective development FIT screen (not protected science).

New independently born 12+12 task sources. Exact original AZ policy versus
task-local learned nonlinear modular inverse with selective causal abstention.
Each same-source original arm written immediately; any failure terminates
without replay and archives only actual observations.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NATIVE=ROOT/"nativeevidence"
COHORTS={"mod":range(920000,920012),"feistel":range(921000,921012)}
SOURCE={"mod":"f124bo_mod_source.py","feistel":"f124bo_feistel_source.py"}
BLOBS={
 "mod":"4c037f55e220b22783d89e3e566b951e0eff618e",
 "feistel":"b934ce6962dc9a1526d82dbdc2736d210f2db57d",
 "learner":"fe1229770fa76185779678fc6155f87d28415cef",
 "AZ":"0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7",
 "native":"94d2ae8266da792d254ac54baf3056bbd9b49412"
}


def need(ok,reason):
    if not ok:raise RuntimeError("F124BO_ORIGINAL_FIT_"+reason)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    need(spec and spec.loader,"PYTHON_MODULE")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def blob(path):
    proc=subprocess.run(["git","rev-parse","HEAD:"+str(path.relative_to(ROOT))
                         .replace("\\","/")],cwd=ROOT,capture_output=True,text=True)
    need(proc.returncode==0,"IDENTITY_LOOKUP")
    return proc.stdout.strip()


def source_identity(case):
    need(type(case) is int,"SOURCE_CASE_ID")
    for family,cohort in COHORTS.items():
        if case in cohort:return family
    raise RuntimeError("F124BO_ORIGINAL_FIT_PROTECTED_OR_REPLAY_SOURCE_ID")


def digest(value):
    return hashlib.sha256(json.dumps(
        value,separators=(",",":"),sort_keys=True).encode()).hexdigest()


def public_bits(x):
    return [(x>>j)&1 for j in range(16)]


def one(case,arm):
    need(sys.platform=="linux" and arm in ("AZ","nonlinear"),"SCOPED_LINUX")
    import resource
    family=source_identity(case)
    file=HERE/SOURCE[family]
    need(blob(file)==BLOBS[family]
         and blob(HERE/"f124bo_nonlinear_learner.py")==BLOBS["learner"]
         and blob(NATIVE/"f124az_joint_public_inverse.py")==BLOBS["AZ"]
         and blob(NATIVE/"f124ag_transition_models.py")==BLOBS["native"],
         "FROZEN_LEARNER_AND_SOURCE")
    tic=time.process_time_ns()
    source=load("bo_new_private_evaluator_source_"+family,file)
    data,truth=source.make(case)
    private_positive=truth.get("private_true_positive_count",
                               truth.get("private_truth_pos"))
    private_negative=truth.get("private_true_negative_count",
                               truth.get("private_truth_neg"))
    need(private_positive==1 and private_negative==0,
         "SYMBOLIC_PRIVATE_LABEL")
    fit,check=data["FIT"],data["CHECK"]
    pos,neg=data["positive"],data["hard_negative"]
    need(len(fit)==40 and len(check)==8
         and pos["demos"]==neg["demos"],"EQUIVALENT_PUBLIC_SUPPORT")
    pub=fit+check
    demos=[{"input_bits":public_bits(x),"output_bits":public_bits(y)}
           for x,y in pub]
    need(demos[:24]==pos["demos"],"GRAPH_FITS_PUBLIC_EXACT")
    sys.path.insert(0,str(NATIVE))
    import f124az_joint_public_inverse as az
    import f124ag_transition_models as native
    import f124aj_example_operator_learner as parser
    base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
    delta=[0.0,0.0]
    if arm=="AZ":
        trained=az.train(demos,"BO-ORIGINAL-IDENTICAL-SOURCE",0)
        positive,pwork,_=az.score(pos,list(base),list(delta),trained,demos)
        negative,nwork,_=az.score(neg,list(base),list(delta),trained,demos)
        details={"original_AZ_scientific_policy":True,
                 "original_route":trained["choice"],
                 "AZ_forced_native_diagnostic":False,
                 "original_native_positive_executed":pwork is not None,
                 "original_native_negative_executed":nwork is not None,
                 "model_bits_lower":trained["extra_task_model_bits_lower"]}
    else:
        learner=load("bo_unchanged_selective_nonlinear",
                     HERE/"f124bo_nonlinear_learner.py")
        model,train,plausible=learner.learn(fit,check)
        if model is None:
            positive=negative=-1e9
            details={"original_AZ_scientific_policy":False,
                     "identifiable":False,"learner_fit":train,
                     "native_calls":0,
                     "confidence_rejection":"FIT_OR_CHECK_NOT_QUALIFIED"}
        else:
            inferred=[]
            reports=[]
            for graph in (pos,neg):
                yes,causal_trace=learner.selective_causal_path(
                    graph,model,plausible)
                normalized,public_demos,nonce=parser.public_task(graph)
                need(public_demos==demos[:24],"NATIVE_PUBLIC_PARSING")
                native.frozen.prior.parent.validate_15(normalized)
                for edge in normalized["edges"]:
                    y=sum(b<<j for j,b in enumerate(edge["src_bits"]))
                    decoded=learner.inverse(y,model)
                    edge["src_bits"]=public_bits(decoded)
                native.frozen.prior.parent.validate_15(normalized)
                score,raw,ratio,work=native.ygg_transition(
                    normalized,list(base),list(delta),.1)
                need(math.isfinite(score)
                     and work["max_active"]<=7
                     and work["max_retained"]<=9,
                     "UNMODIFIED_NATIVE_COGNITION")
                inferred.append(1. if yes else -1.)
                reports.append({"causal_decision":causal_trace,
                                "native_score_diagnostic":score,
                                "native_work":work})
            positive,negative=inferred
            details={"original_AZ_scientific_policy":False,
                     "identifiable":True,"learner_fit":train,
                     "native_calls":2,
                     "positive_trace":reports[0],
                     "hard_trace":reports[1],
                     "model_parameter_bits":48,
                     "source_family_or_oracle_used":False}
    cpu=time.process_time_ns()-tic
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    need(cpu>0 and rss>0,"OS_COST")
    return {"schema":"mass.f124bo.first-prospective-public-development-pair.v1",
            "case":case,"family":family,"arm":arm,
            "pair_sha256":digest({"public":pub,"pos":pos,"neg":neg}),
            "positive_accepted":positive>=0,"hard_FP":negative>=0,
            "positive_score":positive,"hard_score":negative,
            "symbolic_private_evaluator_truth":{"positive":1,"negative":0},
            "model_trace":details,"process_CPU_ns":cpu,
            "whole_process_RSS_bytes":rss,
            "old_BM_BN_cases_used":False,"old_TRAIN_replayed":False,
            "protected_BH_U_R_or_BO_128_used":False,
            "scientific_accepted":False,"optimizer_promoted":False}


def summarize(rows):
    need(len(rows)==48,"EXACT_24_NEW_CASES_TWO_ARMS")
    out={}
    for family,cohort in COHORTS.items():
        pairs=[]
        for case in cohort:
            xs=[r for r in rows if r["case"]==case]
            need(len(xs)==2 and {x["arm"] for x in xs}=={"AZ","nonlinear"}
                 and all(x["family"]==family for x in xs),
                 "SOURCE_IDENTITY_PER_CASE")
            a=next(x for x in xs if x["arm"]=="AZ")
            n=next(x for x in xs if x["arm"]=="nonlinear")
            need(a["pair_sha256"]==n["pair_sha256"],"EQUAL_PUBLIC_GRAPH")
            pairs.append({
                "case":case,"AZ_positive":a["positive_accepted"],
                "AZ_hard_FP":a["hard_FP"],
                "nonlinear_positive":n["positive_accepted"],
                "nonlinear_hard_FP":n["hard_FP"],
                "nonlinear_identifiable":n["model_trace"].get("identifiable",False),
                "AZ_CPU_ns":a["process_CPU_ns"],"nonlinear_CPU_ns":n["process_CPU_ns"],
                "AZ_RSS":a["whole_process_RSS_bytes"],
                "nonlinear_RSS":n["whole_process_RSS_bytes"]})
        losses=[r["case"] for r in pairs if r["AZ_positive"]
                and not r["nonlinear_positive"]]
        fps=[r["case"] for r in pairs if r["nonlinear_hard_FP"]]
        positives={r["case"] for r in pairs if r["nonlinear_positive"] and
                   not r["nonlinear_hard_FP"]}
        baseline_correct={r["case"] for r in pairs if r["AZ_positive"]
                          and not r["AZ_hard_FP"]}
        cost_eligible=all(r["nonlinear_CPU_ns"]<=r["AZ_CPU_ns"] and
                          r["nonlinear_RSS"]<=r["AZ_RSS"] for r in pairs)
        gate=(not losses and not fps and len(positives-baseline_correct)>=2
              and cost_eligible)
        out[family]={"pairs":len(pairs),
          "AZ_positive_count":sum(p["AZ_positive"] for p in pairs),
          "AZ_hard_FP_count":sum(p["AZ_hard_FP"] for p in pairs),
          "learned_positive_count":sum(p["nonlinear_positive"] for p in pairs),
          "learned_false_positive_ids":fps,"baseline_positive_losses":losses,
          "learned_correct_pair_count":len(positives),
          "newly_correct_pair_ids":sorted(positives-baseline_correct),
          "identifiable_cases":sum(p["nonlinear_identifiable"] for p in pairs),
          "equal_or_lower_measured_per_case_CPU_RSS":cost_eligible,
          "frozen_FIT_gate":gate,"per_case":pairs}
    return {"schema":"mass.f124bo.original-24-development-causal-transfer.v1",
            "new_source_pairs":24,"original_arm_records":48,
            "families":out,
            "joint_predeclared_FIT_success":all(v["frozen_FIT_gate"] for v in out.values()),
            "full_scientific_resource_parity":False,
            "original_192_TRAIN_replayed":False,
            "BM_BN_development_replayed":False,
            "old_BH_U_R_protected_used":False,
            "BO_128_case_replication_used":False,
            "independent_external_source_novelty_certified":False,
            "scientific_accepted":False,"optimizer_promoted":False,
            "disposition":"NEW_ORIGINAL_DEVELOPMENT_ONLY"}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--child",action="store_true")
    p.add_argument("--case",type=int)
    p.add_argument("--arm",choices=("AZ","nonlinear"))
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    if args.child:
        need(args.case is not None and args.arm is not None,
             "CHILD_ONLY")
        print(json.dumps(one(args.case,args.arm),sort_keys=True))
        return
    need(args.output is not None,"OUTPUT_REQUIRED")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    samples=[]
    for case in list(COHORTS["mod"])+list(COHORTS["feistel"]):
        for arm in ("AZ","nonlinear"):
            x=subprocess.run([sys.executable,"-B",str(Path(__file__).resolve()),
                              "--child","--case",str(case),"--arm",arm],
                              cwd=ROOT,capture_output=True,text=True,timeout=240)
            need(x.returncode==0,"ORIGINAL_FIRSTUSE_CHILD_"+str(case)+
                 "_"+arm+":"+x.stderr[-2000:])
            result=json.loads(x.stdout)
            with (args.output.parent/("original_"+str(case)+"_"+arm+".json")
                  ).open("x",encoding="utf-8") as f:
                json.dump(result,f,indent=2,sort_keys=True)
                f.write("\n")
            samples.append(result)
    evidence={"summary":summarize(samples)}
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(evidence,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124BO_NEW_DEVELOPMENT_CASES=24")
    print("F124BO_ORIGINAL_PER_ARM_RECORDS=48")
    for family,data in evidence["summary"]["families"].items():
        print("F124BO_"+family.upper()+"_CORRECT_PAIRS="+
              str(data["learned_correct_pair_count"]))
        print("F124BO_"+family.upper()+"_HARD_FP="+
              str(len(data["learned_false_positive_ids"])))
    print("F124BO_JOINT_GATE="+
          str(evidence["summary"]["joint_predeclared_FIT_success"]))
    print("F124BO_PROTECTED_FIRSTUSE=false")


if __name__=="__main__":
    main()
