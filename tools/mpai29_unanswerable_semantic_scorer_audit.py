"""MP-AI29: original-category unanswerable rubric and semantic scorer falsification.

Use exactly frozen MP-AI28 public source/task identities; NEVER modify or
cherry-pick frozen 12-task set. Upstream LoCoMo evaluation.py category 5 scores
phrase occurrence ('no information available' / 'not mentioned'), which can
credit self-contradictory outputs. This gate validates a STRICT abstention
rubric for that source category and exposes weak substring-match controls.

No agent/model requests, no gold/question publication, no memory writes,
no unauthorized scientific acceptance, no claim that paraphrase grading works.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import string

import mpai28_external_task_freeze_and_scorer as p28

FROZEN_SHA = "6ddf3d30019f102f2d2f820be69c1b0478a71f8e7cd1ea6733c5ee07ab29bb85"
LOCOMO_ORIGINAL = (
    "https://github.com/snap-research/locomo/blob/"
    "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/"
    "task_eval/evaluation.py#L260"
)
SOURCE_CODE_SHA = "ca58a30dbe0a5c062aeec2866f8038b93a47797a"
FAMILIES = ("LOCOMO","MAB_CR","MAB_TTL")
PHASE = "INIT"

def require(ok, label):
    if not ok:
        raise RuntimeError("MPAI29_" + label)

def source_category5(output):
    return ("no information available" in output.lower() or
            "not mentioned" in output.lower())

# Exact, case-insensitive allowed messages only. This stricter local scorer
# is intentionally NOT represented as the unchanged LoCoMo official metric.
ABSTAIN_TEXT = ("NO INFORMATION AVAILABLE", "NOT MENTIONED", "UNKNOWN")
def conservative_abstain(text):
    if not isinstance(text,str):
        return False
    return text.strip().upper() in ABSTAIN_TEXT

def scorer_defense(rule, pred, gold):
    # Strict acceptance before substring metrics: disallow explicitly
    # falsifying/disclaiming a copied reference even when it contains gold.
    # This does NOT solve semantic entailment, pronouns or negation generally.
    lower = pred.lower()
    if any(x in lower for x in ("not the answer:", "is not the answer:",
                               "not correct:", "false answer:")):
        return False
    return p28.score(pred, gold, rule)

def semantic_canaries():
    # Self-contained authored fixtures, NOT real benchmark gold. This
    # calibrates rejection and deferral only: a scorer that cannot credit
    # a paraphrase MUST NOT claim a qualified semantic grade.
    gold=("The researcher lives in New York City",)
    exact="The researcher lives in New York City"
    para="The scientist resides in NYC"
    contradiction="The researcher does not live in New York City"
    require(p28.score(exact,gold,"strict"),"CANARY_POSITIVE")
    require(not p28.score(contradiction,gold,"strict"),"CANARY_CONTRADICTION")
    require(not p28.score(para,gold,"strict"),"CANARY_PARAPHRASE_NOT_TRUSTED")
    print("MPAI29_SYNTHETIC_CONTRADICTION_CONTROL=PASS",flush=True)
    print("MPAI29_SYNTHETIC_PARAPHRASE_SEMANTIC_CREDIT=NOT_QUALIFIED",flush=True)

def protocol_sha():
    return hashlib.sha256(json.dumps({
     "schema":"mpai29-conservative-abstention-unanswerable-and-risk-audit.v1",
     "source_identity":FROZEN_SHA,
     "p28_git_blob":SOURCE_CODE_SHA,
     "locomo_category5_official":{"accept_if_contains":
          ["no information available","not mentioned"]},
     "conservative_abstentions":sorted(ABSTAIN_TEXT),
     "adversarial":["not the answer:","not correct:","false answer:"],
     "frozen_sample_change":False,
     "model_exposure":False,
     "semantic_full_credit":False,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

def audit(files,selected):
    import pyarrow.parquet as pq
    original=json.loads(files["LOCOMO"][1].read_text("utf-8"))
    others={key:pq.read_table(files[key][1],
             columns=["answers"]).to_pylist() for key in ("MAB_CR","MAB_TTL")}
    checked=Counter()
    positives=Counter()
    negatives=Counter()
    unanswerable=Counter()
    official_unsafe=Counter()
    strict_guard=Counter()
    para_unqualified=Counter()
    for d in selected:
        fam=d["family"]
        category=str(d.get("category",""))
        if fam=="LOCOMO":
            gold_raw=original[d["row"]]["qa"][d["q"]].get("answer")
            rule="strict"
            if gold_raw is None:
                # Freeze must remain identical: no substitute. Confirm
                # the original independent author assigned adversarial
                # category 5, not an accidental missing label elsewhere.
                require(category=="5","NULL_NOT_ORIGINAL_CATEGORY_5")
                positives_list=ABSTAIN_TEXT
                negs=[
                   "it was in 2019",
                   "the source says not mentioned but it was 2019",
                   "no information available; actual answer is 2019",
                   "UNKNOWN, but definitely it was 2019",
                   "not mentioned except the correct answer is NYC",
                   "", "maybe no", "i do not remember",
                ]
                for z in positives_list:
                    require(conservative_abstain(z),"ABSTAIN_POSITIVE")
                for z in negs:
                    require(not conservative_abstain(z),"ABSTAIN_NEGATIVE")
                # Official category5 matcher is inherently susceptible to
                # self-contradictory "not mentioned ... but X" outputs.
                fp=sum(source_category5(z) for z in negs)
                require(fp>=2,"OFFICIAL_RUBRIC_WEAKNESS_NOT_REPRODUCED")
                # Actual positive upstream phrase controls
                require(all(source_category5(z) for z in ABSTAIN_TEXT[:2]),
                        "LOCOMO_ORIGINAL_PHRASE_CONTROL")
                require(not source_category5("UNKNOWN"),"UPSTREAM_EXTENSION_DECLARATION")
                checked[fam]+=1
                unanswerable[fam]+=1
                positives[fam]+=len(positives_list)
                negatives[fam]+=len(negs)
                official_unsafe[fam]+=fp
                print("MPAI29_NULL_REFERENCE_ORIGINAL_CATEGORY5=PASS",flush=True)
                continue
        else:
            row=others[fam][d["row"]]
            answer=row["answers"]
            require(isinstance(answer,list) and len(answer)>d["q"],
                    "MAB_ANSWER_PAIR_SCHEMA")
            gold_raw=answer[d["q"]]
            rule="substring" if fam=="MAB_CR" else "exact"
        gold=p28.gold_strings(gold_raw)
        require(len(gold)>0,"OTHER_FROZEN_GOLD_UNSCORABLE")
        require(p28.score(gold[0],gold,rule),"REFERENCE_SELF_TEST")
        require(not p28.score("",gold,rule),"REFERENCE_BLANK")
        deny=p28.wrong_for(gold,rule)
        require(not p28.score(deny,gold,rule),"REFERENCE_WRONG")
        # Original CR substring scorer accepts an explicitly negated
        # assertion that embeds exact reference text. No gold printed.
        contradiction="This is not the answer: "+gold[0]
        unsafe=p28.score(contradiction,gold,rule)
        safe=scorer_defense(rule,contradiction,gold)
        require(not safe,"OBVIOUS_CONTRADICTION_GUARD")
        if fam=="MAB_CR":
            require(unsafe,"OFFICIAL_CR_SUBSTRING_FALSE_POSITIVE")
            official_unsafe[fam]+=1
            strict_guard[fam]+=1
        else:
            if unsafe:official_unsafe[fam]+=1
        checked[fam]+=1
        positives[fam]+=1
        negatives[fam]+=2
        # semantic paraphrases of actual gold are never automatically
        # fabricated from gold, to avoid leaking or pretending they are
        # independent human adjudication.
        para_unqualified[fam]+=1
    require(sum(checked.values())==12,"FROZEN_12_CASE_COVERAGE")
    require(unanswerable["LOCOMO"]==1,"ORIGINAL_UNANSWERABLE_COUNT")
    for key in FAMILIES:
        require(checked[key]==4,"SOURCE_FAMILY_CASE_COUNT")
        print("MPAI29_"+key+"_FROZEN_CASES="+str(checked[key]),flush=True)
        print("MPAI29_"+key+"_SAFE_POSITIVES="+str(positives[key]),flush=True)
        print("MPAI29_"+key+"_SAFE_NEGATIVES="+str(negatives[key]),flush=True)
        print("MPAI29_"+key+"_OFFICIAL_ADVERSARIAL_FALSE_POSITIVES="+
              str(official_unsafe[key]),flush=True)
        print("MPAI29_"+key+"_SEMANTIC_PARAPHRASE_JUDGE=NOT_QUALIFIED",flush=True)
    require(official_unsafe["LOCOMO"]>=2 and
            official_unsafe["MAB_CR"]==4,
            "SOURCE_SCORER_VULNERABILITY_CHECK")
    print("MPAI29_TOTAL_FROZEN_CASES=12",flush=True)
    print("MPAI29_UNANSWERABLE_SOURCE_CATEGORY5_COUNT=1",flush=True)
    print("MPAI29_STRICT_CATEGORY5_ABSTENTION_CONTROLS="+
          str(len(ABSTAIN_TEXT)+8)+"_PASS",flush=True)
    print("MPAI29_OFFICIAL_CR_FALSE_POSITIVE_WITNESSES=4",flush=True)
    print("MPAI29_SCORER_GUARD_REJECTS_OBVIOUS_CONTRADICTION=PASS",flush=True)
    print("MPAI29_SOURCE_FAITHFUL_FULL_SEMANTIC_SCORER=NOT_QUALIFIED",flush=True)
    print("MPAI29_RELEASE_FOR_UNFAMILIAR_MODEL_EVAL=BLOCKED",flush=True)
    print("MPAI29_GOLD_TEXT_EXPOSED=FALSE",flush=True)

def main():
    global PHASE
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=("freeze","audit"),required=True)
    args=p.parse_args()
    require(os.environ.get("GITHUB_REPOSITORY")=="spoonman136668-ai/FORGE",
            "REPOSITORY_ID")
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","RUN_ATTEMPT")
    require(not os.environ.get("OPENAI_API_KEY"),"NO_PAID_API")
    semantic_canaries()
    print("MPAI29_AUDIT_PROTOCOL_SHA256="+protocol_sha(),flush=True)
    print("MPAI29_PREEXISTING_FROZEN_SHA256="+FROZEN_SHA,flush=True)
    with tempfile.TemporaryDirectory(prefix="mpai29-source-private-") as scratch:
        PHASE="AUTHENTIC_UPSTREAM"
        files=p28.source_downloads(Path(scratch))
        PHASE="ORIGINAL_FROZEN_SELECTION"
        selected, frozen=p28.selection(files)
        require(frozen==FROZEN_SHA,"P28_PRECOMMITTED_TASKS_CHANGED")
        print("MPAI29_SOURCE_IDENTITY_RECOMPUTED=PASS",flush=True)
        if args.phase=="freeze":
            print("MPAI29_BEFORE_ORIGINAL_GOLD_INSPECTION=PASS",flush=True)
            print("MPAI29_FROZEN_TASKS_PRESERVED=12",flush=True)
        else:
            PHASE="PRIVATE_SCORER_AUDIT"
            audit(files,selected)
    print("MPAI29_PRIVATE_SOURCE_REMOVED=PASS",flush=True)
    print("MPAI29_MODEL_CALLS=0",flush=True)
    print("MPAI29_ACCEPTED_MEMORY_WRITES=0",flush=True)
    print("MPAI29_INDEPENDENT_FIRST_USE_CUSTODY=NOT_ATTESTED",flush=True)
    print("MPAI29_SCIENTIFIC_ACCEPTANCE=FALSE",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        value=str(e)
        code=value if re.fullmatch(r"MPAI29_[A-Z0-9_]{3,100}",value) else "MPAI29_PRIVATE_EXCEPTION"
        print("MPAI29_SAFE_FAILURE="+code,flush=True)
        print("MPAI29_FAILURE_PHASE="+PHASE,flush=True)
        print("MPAI29_EXCEPTION_TYPE="+type(e).__name__,flush=True)
        sys.exit(2)
