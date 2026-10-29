"""MP-AI05 P11 P10 failure diagnosis: source-field and retrieval sufficiency only.

Reads the same 16 public DEVELOPMENT questions and pinned upstream trajectory
bytes, never a holdout, model API or production memory. Source-visible string
matching is an *imperfect diagnostic*, never an independent correctness grade.
"""
from __future__ import annotations
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import sys

import mpai05_p10_public_development as p10
import mpai05_p9_dataset_freeze as p9

P10_SOURCE_BLOB="7bd698e3265cc41ee4d286461980d7586a25ac99"
P9_SOURCE_BLOB="2c2100c53c001d28843bc2da664c3e92d413e2e6"
P10_QUALIFIED_RUN="40852701200"
EXPECTED_COHORT="103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52"
EXPECTED_GRADED=11
EXPECTED_UNSCORABLE=5
KEYS=("action","accessibility_tree","thought")
PHASE="INITIAL"

def strict(test,code):
    if not test:
        raise RuntimeError("MPAI05_P11_"+code)

def has_literal(gold,text):
    """Exact normalized answer phrase only; not a sufficient semantic proof."""
    if type(gold) is not str or type(text) is not str:
        return False
    needle=re.sub(r"\s+"," ",gold.casefold()).strip()
    hay=re.sub(r"\s+"," ",text.casefold())
    return bool(3<=len(needle)<=120 and needle in hay)

def inspect_states(file:Path,wanted:dict[str,str]):
    """Count schema fields and selected text without exporting raw trajectories."""
    present=set()
    metrics=Counter()
    state_keys=Counter()
    unsupported_strings=Counter()
    literal_full={}
    with file.open("r",encoding="utf-8") as fd:
        for line in fd:
            if not line.strip():continue
            row=json.loads(line)
            ident=row.get("id")
            if ident not in wanted:continue
            strict(ident not in present,"DUPLICATE_SELECTED_TRAJECTORY")
            present.add(ident)
            strict(row.get("domain")==wanted[ident],"SELECTED_DOMAIN_DRIFT")
            states=row.get("states")
            strict(type(states) is list,"STATE_ARRAY_DRIFT")
            metrics["selected_trajectories"]+=1
            metrics["total_states"]+=len(states)
            support=[]
            for state in states:
                if type(state) is not dict:
                    metrics["non_object_states"]+=1
                    continue
                metrics["state_objects"]+=1
                for key,value in state.items():
                    if not (type(key) is str and
                            re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,63}",key)):
                        continue
                    state_keys[key]+=1
                    if key in KEYS and type(value) is str and value.strip():
                        metrics["supported_nonempty_fields"]+=1
                        support.append(value[:1200])
                    elif key not in KEYS and key not in ("screenshot","image",
                                                          "image_path","url") and
                         type(value) is str and value.strip():
                        unsupported_strings[key]+=1
            if support:
                metrics["trajectories_with_supported_text"]+=1
            else:
                metrics["trajectories_without_supported_text"]+=1
            literal_full[ident]=support
    strict(present==set(wanted),"SELECTED_TRAJECTORIES_INCOMPLETE")
    return metrics,state_keys,unsupported_strings,literal_full

def summarize(questions,selected,haystacks,mem,structure,raw_strings,scorer):
    by_id={row["id"]:row for row in questions}
    counts=Counter()
    cases=Counter()
    for item in selected:
        row=by_id[item["id"]]
        question=row["question"]
        gold=row["answer"]
        strict(type(question) is str and type(gold) is str,
               "QUESTION_OR_GOLD_TYPE")
        name=scorer.eval_name(row["eval_function"])
        if name in p10.SCORER_ALLOWED:
            counts["official_deterministic_cases"]+=1
        else:
            counts["official_unscorable_cases"]+=1
        ids=haystacks[item["id"]]
        text=p10.retrieve(question,ids,mem)
        full="\n".join(seg for ident in ids for seg in mem[ident])
        rawfull="\n".join(seg for ident in ids for seg in raw_strings[ident])
        case=(has_literal(gold,rawfull),has_literal(gold,full),
              has_literal(gold,text))
        if not text:
            counts["retrieval_empty_cases"]+=1
        else:
            counts["retrieval_nonempty_cases"]+=1
        counts["retrieved_context_chars"]+=len(text)
        counts["full_extracted_evidence_chars"]+=len(full)
        if len(text)>=int(p10.CONTEXT_CHARS*0.90):
            counts["near_context_cap_cases"]+=1
        if case[0]:
            counts["literal_gold_in_selected_supported_fields"]+=1
        if case[1]:
            counts["literal_gold_in_p10_extracted_evidence"]+=1
        if case[2]:
            counts["literal_gold_in_p10_retrieved_context"]+=1
        if case[1] and not case[2]:
            counts["literal_found_upstream_but_lost_in_retrieval"]+=1
        if not case[1]:
            counts["literal_not_found_in_extracted_evidence"]+=1
        if p10.retrieve(question,ids,mem)!=text:
            raise RuntimeError("MPAI05_P11_NONDETERMINISTIC_RETRIEVAL")
        counts["case_count"]+=1
    strict(counts["case_count"]==16,"CASE_COUNT_DRIFT")
    strict(counts["official_deterministic_cases"]==EXPECTED_GRADED and
           counts["official_unscorable_cases"]==EXPECTED_UNSCORABLE,
           "OFFICIAL_SCORE_DENOMINATOR_DRIFT")
    # String overlap cannot establish question answerability. Unknown here.
    return counts

def main():
    global PHASE
    strict(os.getenv("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE" and
           os.getenv("RUNNER_NAME")=="FORGE-CODEX-REMOTE",
           "ORIGINAL_RUNNER_IDENTITY")
    strict(not os.getenv("OPENAI_API_KEY"),"PAID_API_PROHIBITED")
    root=Path(os.environ["MPAI05_P11_SCRATCH"])
    strict(not root.exists(),"SCRATCH_COLLISION")
    strict(shutil.disk_usage(root.parent).free>=2_000_000_000,"SCRATCH_CAPACITY")
    root.mkdir()
    PHASE="OFFICIAL_SCORER"
    scorer,official=p10.official_scorer(root)
    PHASE="COHORT"
    meta={k:p9.download(k) for k in
          ("checksums.sha256","SCHEMA.md","questions.jsonl","haystacks/lme_v2_small.json")}
    receipt=p9.freeze(meta["questions.jsonl"],meta["haystacks/lme_v2_small.json"],
           meta["SCHEMA.md"],meta["checksums.sha256"])
    strict(receipt["cohort_sha256"]==EXPECTED_COHORT,"COHORT_DRIFT")
    questions=[json.loads(z) for z in meta["questions.jsonl"].decode("utf-8").splitlines() if z.strip()]
    haystacks=json.loads(meta["haystacks/lme_v2_small.json"])
    selected=p9.choose(questions,haystacks)["cohort"]
    wanted={}
    for item in selected:
        for tid in haystacks[item["id"]]:
            if tid in wanted:strict(wanted[tid]==item["domain"],"CROSS_DOMAIN_TRAJECTORY")
            wanted[tid]=item["domain"]
    PHASE="TRAJECTORY_DOWNLOAD"
    file=root/"trajectories.jsonl"
    p10.download(f"https://huggingface.co/datasets/{p9.REPO}/resolve/"
                 f"{p9.REVISION}/trajectories.jsonl?download=true",
                 file,p10.SHA_TRAJECTORIES,p10.BYTES_TRAJECTORIES)
    PHASE="TRAJECTORY_ANALYSIS"
    mem=p10.get_text_trajectories(file,wanted)
    metrics,keys,unused,raw_strings=inspect_states(file,wanted)
    diagnosis=summarize(questions,selected,haystacks,mem,metrics,raw_strings,scorer)
    strict(not p10.run(["git","status","--porcelain","--untracked-files=all"],official),
           "OFFICIAL_GIT_SOURCE_DIRTY")
    allowed=sorted(k for k in keys if k not in ("screenshot","image","image_path"))
    print("MPAI05_P11_PUBLIC_DEVELOPMENT_ONLY=TRUE")
    print("MPAI05_P11_DATASET_COHORT_SHA256="+EXPECTED_COHORT)
    print("MPAI05_P11_OFFICIAL_SCORE_DENOMINATOR=11")
    print("MPAI05_P11_UNSCORABLE_CASES=5")
    for k,v in sorted(metrics.items()):
        print("MPAI05_P11_STRUCT_"+k.upper()+"="+str(v))
    for k,v in sorted(diagnosis.items()):
        print("MPAI05_P11_DIAG_"+k.upper()+"="+str(v))
    # Source field names and counts are safe metadata, never task data.
    print("MPAI05_P11_STATE_FIELD_COUNTS="+json.dumps({k:keys[k] for k in allowed},
          separators=(",",":"),sort_keys=True))
    print("MPAI05_P11_IGNORED_NONEMPTY_TEXT_KEYS="+json.dumps(
          {k:unused[k] for k in sorted(unused)},separators=(",",":"),sort_keys=True))
    print("MPAI05_P11_IGNORED_NONEMPTY_STRING_FIELD_TOTAL="+str(sum(unused.values())))
    for key,count in sorted(keys.items(),key=lambda x:(-x[1],x[0]))[:24]:
        if key not in ("screenshot","image","image_path"):
            print("MPAI05_P11_FIELD_"+key.upper()+"="+str(count))
    for key,count in sorted(unused.items(),key=lambda x:(-x[1],x[0]))[:16]:
        print("MPAI05_P11_UNUSED_FIELD_"+key.upper()+"="+str(count))
    print("MPAI05_P11_LITERAL_TEST_NOT_SEMANTIC_GRADING=TRUE")
    print("MPAI05_P11_LOCAL_MODEL_CALLS=0")
    print("MPAI05_P11_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI05_P11_PRODUCTION_WRITES=0")
    print("MPAI05_P11_SOURCE_CUSTODY=PASS")

if __name__=="__main__":
    try:main()
    except Exception as e:
        msg=str(e)
        print("MPAI05_P11_SAFE_FAILURE="+
            (msg if re.fullmatch(r"MPAI05_P11_[A-Z0-9_]+",msg) else "PRIVATE_EXCEPTION"),
            flush=True)
        print("MPAI05_P11_SAFE_PHASE="+PHASE,flush=True)
        sys.exit(2)
