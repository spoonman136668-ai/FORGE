"""MP-AI05 P17 public development failure-attribution gate.

On P15/P16's fixed disjoint 16-case PUBLIC DEVELOPMENT cohort, audit source
literal overlap and official scorer's positive/negative controls. This is
not semantic evidence sufficiency, nor a reranking/training/accuracy trial.
All gold comparisons occur AFTER P16's unchanged retrieval selects context.
Zero model/API calls, no answer text in logs, no persistent memory updates.
"""
from __future__ import annotations
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

import mpai05_p9_dataset_freeze as p9
import mpai05_p10_public_development as p10
import mpai05_p11_diagnose as p11
import mpai05_p14_scorer_calibration as p14
import mpai05_p15_model_qualification as p15
import mpai05_p16_capacity_vs_memory as p16

COHORT="81be63f61ee45231985c9341419a3abb1f42f40930a95be8337d16375ba1b696"
STAGE="INITIAL"
CONDITIONS=("all_source","p10_extracted","lexical_retrieved","idf_retrieved")
GRADED=("official_gradeable","unscorable")

def require(cond,code):
    if not cond:raise RuntimeError("MPAI05_P17_"+code)

def score_controls(scorer,spec,gold):
    """Official exact reference positive and wrong-answer negative controls."""
    result=p14.reference_control(scorer,spec,gold)
    if result["kind"]=="UNSCORABLE":
        require(result["positive"] is None and result["negative"] is None,
                "JUDGE_ROUTING")
        return "unscorable",result
    require(result["boxed_identity"] is True,"BOXED_ANSWER_EXTRACTION")
    require(result["positive"] is True,"KNOWN_CORRECT_SCORER_REJECTED")
    require(result["negative"] is False,"DELIBERATELY_WRONG_SCORER_ACCEPTED")
    return "official_gradeable",result

def diagnostic(rows,cohort,haystack,memory,source_memory,scorer):
    lookup={r["id"]:r for r in rows}
    totals={name:Counter() for name in GRADED}
    observed=Counter()
    for item in cohort:
        row=lookup[item["id"]]
        q=row.get("question");gold=row.get("answer");spec=row.get("eval_function")
        require(type(q) is str and type(gold) is str and type(spec) is str,
                "OFFICIAL_RECORD_SCHEMA")
        ids=haystack[item["id"]]
        # P16's identical model-independent preselected contexts; gold never
        # influences the original lexical or IDF retriever selection.
        contexts,cpu=p16.make_context(q,ids,memory)
        require(all(len(contexts[k])<=p10.CONTEXT_CHARS+8
                    for k in p16.ARMS),"CONTEXT_CAP")
        full="\n".join(v for tid in ids for v in memory[tid])
        pretrunc="\n".join(v for tid in ids for v in source_memory[tid])
        frozen={
            "all_source":pretrunc,
            "p10_extracted":full,
            "lexical_retrieved":contexts["lexical_memory"],
            "idf_retrieved":contexts["idf_diverse_memory"],
        }
        # Source gold is accessed after all four contexts have been frozen.
        grade_kind,control=score_controls(scorer,spec,gold)
        t=totals[grade_kind]
        t["cases"]+=1
        observed[scorer.eval_name(spec)]+=1
        for method in CONDITIONS:
            present=p11.has_literal(gold,frozen[method])
            t["literal_"+method]+=int(present)
            t["chars_"+method]+=len(frozen[method])
        t["retrieval_lexical_empty"]+=int(not bool(contexts["lexical_memory"]))
        t["retrieval_idf_empty"]+=int(not bool(contexts["idf_diverse_memory"]))
        t["lexical_near_context_cap"]+=int(
            len(contexts["lexical_memory"])>=int(p10.CONTEXT_CHARS*0.9))
        t["idf_near_context_cap"]+=int(
            len(contexts["idf_diverse_memory"])>=int(p10.CONTEXT_CHARS*0.9))
        t["idf_literal_gain_vs_lexical"]+=int(
           not p11.has_literal(gold,contexts["lexical_memory"]) and
           p11.has_literal(gold,contexts["idf_diverse_memory"]))
        t["idf_literal_loss_vs_lexical"]+=int(
           p11.has_literal(gold,contexts["lexical_memory"]) and
           not p11.has_literal(gold,contexts["idf_diverse_memory"]))
        t["lexical_term_coverage_milli"]+=round(1000*len(
           p10.tokenize(q)&p10.tokenize(contexts["lexical_memory"]))/
           max(1,len(p10.tokenize(q))))
        t["idf_term_coverage_milli"]+=round(1000*len(
           p10.tokenize(q)&p10.tokenize(contexts["idf_diverse_memory"]))/
           max(1,len(p10.tokenize(q))))
        t["lexical_cpu_ns"]+=cpu["lexical_memory"]
        t["idf_cpu_ns"]+=cpu["idf_diverse_memory"]
        if control["kind"]=="UNSCORABLE":t["judge_denied"]+=1
        else:t["reference_and_wrong_control_passed"]+=1
    require(sum(a["cases"] for a in totals.values())==16,"TOTAL_CASE_COUNT")
    require(totals["official_gradeable"]["reference_and_wrong_control_passed"]==
            totals["official_gradeable"]["cases"],"OFFICIAL_CONTROL_MISMATCH")
    require(totals["unscorable"]["judge_denied"]==
            totals["unscorable"]["cases"],"JUDGE_COUNT_MISMATCH")
    # Distinct fresh P15 split; gradeability predeclared by published spec.
    require(totals["official_gradeable"]["cases"]==13 and
            totals["unscorable"]["cases"]==3,"P16_GRADED_DENOMINATOR_DRIFT")
    return totals,observed

def main():
    global STAGE
    require(os.name=="nt" and os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE"
            and os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
            "WRONG_ORIGINAL_WINDOWS_HOST")
    require(not os.getenv("OPENAI_API_KEY"),"PAID_API_DENIED")
    root=Path(os.environ["MPAI05_P17_SCRATCH"])
    require(not root.exists() and
            shutil.disk_usage(root.parent).free>=2000000000,
            "SCRATCH_COLLISION_OR_DISK")
    root.mkdir()
    STAGE="OFFICIAL_SCORER"
    scorer,official=p10.official_scorer(root)
    STAGE="FROZEN_PUBLIC_METADATA"
    raw={k:p9.download(k) for k in (
        "checksums.sha256","SCHEMA.md","questions.jsonl","haystacks/lme_v2_small.json")}
    receipt=p9.freeze(raw["questions.jsonl"],raw["haystacks/lme_v2_small.json"],
                       raw["SCHEMA.md"],raw["checksums.sha256"])
    require(receipt["cohort_sha256"]==p15.PRIOR_COHORT_SHA,
            "PREVIOUS_COHORT_FROZEN_DRIFT")
    rows=[json.loads(x) for x in raw["questions.jsonl"].decode("utf-8").splitlines()
          if x.strip()]
    small=json.loads(raw["haystacks/lme_v2_small.json"])
    selected=p15.new_cohort(rows,small)
    require(selected["digest"]==COHORT and selected["overlap"]==0,"P15_COHORT_DRIFT")
    wanted={}
    for item in selected["selected"]:
        for tid in small[item["id"]]:
            if tid in wanted:require(wanted[tid]==item["domain"],"CROSS_DOMAIN")
            wanted[tid]=item["domain"]
    STAGE="PUBLIC_TRAJECTORY_SHA"
    path=root/"trajectories.jsonl"
    p10.download(f"https://huggingface.co/datasets/{p9.REPO}/resolve/"
                 f"{p9.REVISION}/trajectories.jsonl?download=true",
                 path,p10.SHA_TRAJECTORIES,p10.BYTES_TRAJECTORIES)
    STAGE="P16_EXTRACTOR_AND_RETRIEVAL"
    memory=p10.get_text_trajectories(path,wanted)
    _,_,_,source_memory=p11.inspect_states(path,wanted)
    require(len(memory)==len(wanted)==len(source_memory)==200,
            "SOURCE_MEMORIES_COUNT")
    measures,names=diagnostic(rows,selected["selected"],small,memory,
                             source_memory,scorer)
    require(not p10.run(["git","status","--porcelain","--untracked-files=all"],official),
            "OFFICIAL_SOURCE_CHECKOUT_CHANGED")
    print("MPAI05_P17_OFFICIAL_SOURCE_SHA=PASS")
    print("MPAI05_P17_PUBLIC_DATA_SHA256=PASS")
    print("MPAI05_P17_FROZEN_COHORT_SHA256="+COHORT)
    for family in GRADED:
        for k,v in sorted(measures[family].items()):
            print("MPAI05_P17_"+family.upper()+"_"+k.upper()+"="+str(v))
    for name,count in sorted(names.items()):
        require(re.fullmatch(r"[a-z_]{3,48}",name) is not None,"OFFICIAL_FUNCTION_NAME")
        print("MPAI05_P17_OFFICIAL_FUNCTION_"+name.upper()+"="+str(count))
    print("MPAI05_P17_REFERENCES_ONLY_POST_FROZEN_RETRIEVAL=TRUE")
    print("MPAI05_P17_LITERAL_PROXY_NOT_SEMANTIC_PROOF=TRUE")
    print("MPAI05_P17_OFFICIAL_REFERENCES_PASS_NEGATIVE_CONTROLS=PASS")
    print("MPAI05_P17_PUBLIC_DEVELOPMENT_ONLY=TRUE")
    print("MPAI05_P17_MODEL_CALLS=0")
    print("MPAI05_P17_INDEPENDENT_FIRST_USE=FALSE")
    print("MPAI05_P17_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI05_P17_PRODUCTION_WRITES=0")

if __name__=="__main__":
    try:main()
    except Exception as error:
        msg=str(error)
        safe=msg if re.fullmatch(r"MPAI05_P17_[A-Z0-9_]{3,100}",msg) else "PRIVATE_EXCEPTION"
        print("MPAI05_P17_SAFE_FAILURE="+safe,flush=True)
        print("MPAI05_P17_SAFE_STAGE="+STAGE,flush=True)
        print("MPAI05_P17_SAFE_ERROR_TYPE="+type(error).__name__,flush=True)
        sys.exit(2)
