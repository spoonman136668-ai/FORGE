"""P14 public development scorer calibration, not model evaluation.

Calibrates the source-pinned official LongMemEval-V2 evaluator using known
correct reference answers as POSITIVE CONTROLS and intentionally incorrect
answers as NEGATIVE CONTROLS. Same frozen 16 P9 public development questions
as P10/P13. Neither selects evidence nor alters prior accuracy scores.
Does not open trajectories, run models, invoke LLM judges or write memory.
"""
from __future__ import annotations
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
import tempfile

import mpai05_p9_dataset_freeze as p9
import mpai05_p10_public_development as p10

COHORT_SHA="103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52"
OFFICIAL_BLOB="6197efa64d1d47bff73c2523f4728c41ec78fd74"
EXPECTED_PURE_CASES=11
EXPECTED_UNSCORABLE_CASES=5
STAGE="INITIAL"

def require(cond,code):
    if not cond:raise RuntimeError("MPAI05_P14_"+code)

def reference_control(scorer,spec:str,gold:str):
    """Return official scorer's TRUE/FALSE against known gold (not a model)."""
    require(type(spec) is str and type(gold) is str,"SOURCE_SCHEMA")
    name=scorer.eval_name(spec)
    if name not in p10.SCORER_ALLOWED:
        return {"kind":"UNSCORABLE","positive":None,"negative":None,
                "boxed_identity":None}
    # Ensure the same extraction path as original P10/P13 generated text.
    boxed="\\boxed{"+gold+"}"
    parsed=scorer.extract_boxed_answer(boxed)
    same=parsed==gold
    positive, positive_reason=p10.official_grade(scorer,spec,parsed,gold)
    wrong="P14_DELIBERATELY_INCORRECT_9F2C6B"
    require(wrong not in gold,"NEGATIVE_COLLISION")
    negative,negative_reason=p10.official_grade(scorer,spec,wrong,gold)
    require(positive_reason=="OFFICIAL_PURE_SCORER" and
            negative_reason=="OFFICIAL_PURE_SCORER","SCORER_ADAPTER_ROUTING")
    require(type(positive) is bool and type(negative) is bool,
            "BINARY_SCORE_REQUIRED")
    return {"kind":name,"positive":positive,"negative":negative,
            "boxed_identity":same}

def summarize(rows,scorer,cohort):
    byid={r["id"]:r for r in rows}
    require(len(cohort)==16,"FROZEN_COHORT_COUNT")
    totals=Counter()
    functions=Counter()
    for case in cohort:
        row=byid[case["id"]]
        gold=row.get("answer")
        spec=row.get("eval_function")
        require(type(spec) is str and type(gold) is str,"BAD_OFFICIAL_ITEM")
        test=reference_control(scorer,spec,gold)
        totals["cases"]+=1
        functions[scorer.eval_name(spec)]+=1
        if test["kind"]=="UNSCORABLE":
            totals["intentionally_unscorable"]+=1
            continue
        totals["official_pure_cases"]+=1
        totals["reference_box_parse_identity"]+=int(test["boxed_identity"])
        totals["known_correct_accepted"]+=int(test["positive"])
        totals["obviously_wrong_rejected"]+=int(not test["negative"])
        if not test["positive"]:totals["positive_control_failures"]+=1
        if test["negative"]:totals["negative_control_failures"]+=1
    require(totals["cases"]==16 and
            totals["official_pure_cases"]==EXPECTED_PURE_CASES and
            totals["intentionally_unscorable"]==EXPECTED_UNSCORABLE_CASES,
            "SCORER_DENOMINATOR_DRIFT")
    return totals,functions

def main():
    global STAGE
    require(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE" and
            os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE",
            "ORIGINAL_RUNNER_ONLY")
    require(not os.getenv("OPENAI_API_KEY"),"PAID_API_FORBIDDEN")
    root=Path(os.environ["MPAI05_P14_SCRATCH"])
    require(not root.exists(),"SCRATCH_COLLISION")
    root.mkdir()
    STAGE="OFFICIAL_SCORER"
    scorer,official=p10.official_scorer(root)
    STAGE="PUBLISHED_COHORT"
    metadata={name:p9.download(name) for name in (
        "checksums.sha256","SCHEMA.md","questions.jsonl",
        "haystacks/lme_v2_small.json")}
    received=p9.freeze(metadata["questions.jsonl"],
        metadata["haystacks/lme_v2_small.json"],
        metadata["SCHEMA.md"],metadata["checksums.sha256"])
    require(received["cohort_sha256"]==COHORT_SHA,"COHORT_HASH_DRIFT")
    rows=[json.loads(line) for line in
          metadata["questions.jsonl"].decode("utf-8").splitlines()
          if line.strip()]
    small=json.loads(metadata["haystacks/lme_v2_small.json"])
    selected=p9.choose(rows,small)["cohort"]
    STAGE="OFFICIAL_POSITIVE_NEGATIVE_CONTROLS"
    summary,functions=summarize(rows,scorer,selected)
    require(not p10.run(["git","status","--porcelain","--untracked-files=all"],official),
            "UPSTREAM_SOURCE_MUTATED")
    print("MPAI05_P14_OFFICIAL_SOURCE_PIN=PASS")
    print("MPAI05_P14_PUBLIC_DATA_PIN=PASS")
    print("MPAI05_P14_FROZEN_COHORT_SHA256="+COHORT_SHA)
    for key in ("cases","official_pure_cases","intentionally_unscorable",
                "reference_box_parse_identity","known_correct_accepted",
                "obviously_wrong_rejected","positive_control_failures",
                "negative_control_failures"):
        print("MPAI05_P14_"+key.upper()+"="+str(summary[key]))
    for name,count in sorted(functions.items()):
        if re.fullmatch(r"[a-z_]{3,48}",name):
            print("MPAI05_P14_OFFICIAL_FUNCTION_"+name.upper()+"="+str(count))
    print("MPAI05_P14_REFERENCE_USED_ONLY_AS_CONTROL=TRUE")
    print("MPAI05_P14_PREVIOUS_MODEL_SCORES_UNCHANGED=TRUE")
    print("MPAI05_P14_FIRST_USE=FALSE")
    print("MPAI05_P14_MODEL_CALLS=0")
    print("MPAI05_P14_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI05_P14_PRODUCTION_WRITES=0")
    if summary["known_correct_accepted"]!=11 or
       summary["reference_box_parse_identity"]!=11 or
       summary["obviously_wrong_rejected"]!=11:
        raise RuntimeError("MPAI05_P14_POSITIVE_OR_NEGATIVE_CONTROL_MISMATCH")

if __name__=="__main__":
    try:main()
    except Exception as e:
        msg=str(e)
        print("MPAI05_P14_SAFE_FAILURE="+
              (msg if re.fullmatch(r"MPAI05_P14_[A-Z0-9_]+",msg)
               else "PRIVATE_EXCEPTION"),flush=True)
        print("MPAI05_P14_SAFE_PHASE="+STAGE,flush=True)
        print("MPAI05_P14_SAFE_ERROR_TYPE="+type(e).__name__,flush=True)
        sys.exit(2)
