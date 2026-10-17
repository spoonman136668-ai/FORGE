"""F108-O: frozen TRAIN-only flat-annotation linker; no answer or DEV/EVAL access."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from f107o_freebase_train_linker import normal_form, link

SRC="d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
TRAIN="FreebaseQA-train.json"
TID="24dc4b13a9c4a0ad734732db094c124d086b7d67"
DEV="FreebaseQA-dev.json"
DID="2e16ac381efb7b9e362cbf9bd0cee90006244ea8"
EVAL="FreebaseQA-eval.json"
EID="d7d06ae721aedca26a0838d0113cddc1aa6774a8"
MAX_ENTRIES=100000

class Denied(Exception):pass
def check(ok,reason):
    if not ok:raise Denied("F108O_ORIGINAL_TRAIN_DENIED_"+reason)

def opaque_mid(value):
    return isinstance(value,str) and 1<=len(value.encode("utf-8"))<=128 and all(
        33<=ord(x)<=126 and x not in "|[]" for x in value)

def chain_band(v):
    if not v.strip():return "empty"
    n=len(v.encode("utf-8"))
    if n<=32:return "length_001_032"
    if n<=128:return "length_033_128"
    if n<=512:return "length_129_512"
    return "length_513_plus"

def build(rows, expected_parses=37306):
    check(isinstance(rows,list) and 0<len(rows)<=25000,"ORIGINAL_ROWS")
    seen=set()
    lex={}
    counts=Counter()
    questions=[]
    for row in rows:
        check(isinstance(row,dict),"ROW_OBJECT")
        rid=row.get("Question-ID")
        q=row.get("RawQuestion")
        parses=row.get("Parses")
        check(isinstance(rid,str) and 0<len(rid.encode("utf-8"))<=256
              and rid not in seen,"SOURCE_QUESTION_ID")
        seen.add(rid)
        check(isinstance(q,str) and 0<len(q.encode("utf-8"))<=2048
              and all(ord(x)>=32 and ord(x)!=127 for x in q),"QUESTION_TEXT")
        check(isinstance(parses,list),"SOURCE_PARSE_ARRAY")
        questions.append(q)
        for parse in parses:
            counts["original_parse_entries"]+=1
            check(isinstance(parse,dict),"SOURCE_PARSE_OBJECT")
            for f in ("TopicEntityMid","TopicEntityName",
                      "PotentialTopicEntityMention","InferentialChain"):
                check(isinstance(parse.get(f),str),"ORIGINAL_FLAT_FIELD_TYPE")
            counts["opaque_chain_"+chain_band(parse["InferentialChain"])]+=1
            mid=parse["TopicEntityMid"]
            if not opaque_mid(mid):
                counts["parse_entries_invalid_opaque_mid"]+=1
                continue
            counts["parse_entries_valid_opaque_mid"]+=1
            aliases=set()
            for name in ("PotentialTopicEntityMention","TopicEntityName"):
                v=normal_form(parse[name],128)
                if v and len(v.split())<=10:aliases.add(v)
            if not aliases:
                counts["parse_entries_no_eligible_mention"]+=1
                continue
            counts["parse_entries_eligible_mention"]+=1
            for alias in aliases:
                if alias not in lex:
                    lex[alias]=set()
                    check(len(lex)<=MAX_ENTRIES,"SOURCE_LEXICON_BUDGET")
                lex[alias].add(mid)
    check(len(seen)==len(rows),"COMPLETE_TRAIN_ROW_IDS")
    check(counts["original_parse_entries"]==expected_parses,"COMPLETE_ORIGINAL_PARSE_POPULATION")
    stats={
        "original_train_rows":len(rows),
        "unique_question_ids":len(seen),
        "original_parse_entries":counts["original_parse_entries"],
        "valid_opaque_mid_parse_entries":counts["parse_entries_valid_opaque_mid"],
        "invalid_opaque_mid_parse_entries":counts["parse_entries_invalid_opaque_mid"],
        "eligible_mention_parse_entries":counts["parse_entries_eligible_mention"],
        "no_eligible_mention_parse_entries":counts["parse_entries_no_eligible_mention"],
        "unique_mentions":sum(len(ids)==1 for ids in lex.values()),
        "ambiguous_mentions":sum(len(ids)>1 for ids in lex.values()),
        "total_mentions":len(lex),
        "opaque_chain_length_bands":{
            k.removeprefix("opaque_chain_"):v for k,v in sorted(counts.items())
            if k.startswith("opaque_chain_")
        },
    }
    check(stats["valid_opaque_mid_parse_entries"]+
          stats["invalid_opaque_mid_parse_entries"]==expected_parses,"SOURCE_MID_DENOMINATOR")
    check(stats["unique_mentions"]+stats["ambiguous_mentions"]==len(lex),
          "LEXICON_COLLISION_DENOMINATOR")
    check(sum(stats["opaque_chain_length_bands"].values())==expected_parses,
          "ORIGINAL_CHAIN_SOURCE_COUNT")
    return {k:frozenset(v) for k,v in lex.items()},stats,questions

def source_id(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+bytes([0])+raw).hexdigest()

def git_meta(root,args):
    check(args in (["rev-parse","HEAD"],["rev-parse","HEAD:"+TRAIN],
                   ["rev-parse","HEAD:"+DEV],["rev-parse","HEAD:"+EVAL]),"GIT_META_SCOPE")
    p=subprocess.run(["git","-C",str(root),*args],stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,check=False,timeout=20)
    check(p.returncode==0,"GIT_META_UNAVAILABLE")
    return p.stdout.decode("ascii","strict").strip()

def train_bytes(root):
    p=subprocess.run(["git","-C",str(root),"show","HEAD:"+TRAIN],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=65)
    check(p.returncode==0 and len(p.stdout)==23888089,"ORIGINAL_TRAIN_BYTES")
    check(source_id(p.stdout)==TID,"ORIGINAL_TRAIN_GIT_BLOB")
    return p.stdout

def audit(root):
    root=root.resolve(strict=True)
    check(git_meta(root,["rev-parse","HEAD"])==SRC,"ORIGINAL_HEAD")
    for path,sha in ((TRAIN,TID),(DEV,DID),(EVAL,EID)):
        check(git_meta(root,["rev-parse","HEAD:"+path])==sha,"ORIGINAL_BLOB")
    check(not (root/DEV).exists() and not (root/EVAL).exists(),"DEV_EVAL_WORKTREE_READ")
    raw=train_bytes(root)
    try:doc=json.loads(raw.decode("utf-8","strict"))
    except (ValueError,UnicodeError) as ex:raise Denied("F108O_ORIGINAL_JSON") from ex
    check(isinstance(doc,dict) and "Dataset" in doc and "Version" in doc
          and isinstance(doc.get("Questions"),list)
          and len(doc["Questions"])==20358,"ORIGINAL_TRAIN_20358")
    lex,stats,questions=build(doc["Questions"])
    outcome=Counter(link(q,lex) for q in questions)
    check(sum(outcome.values())==20358,"ALL_TRAIN_QUESTIONS_ACCOUNTED")
    return {
        "schema":"forge.optimizer.f108o.flat-train-lexical-linker.v1",
        "status":"PUBLIC_FREEBASE_TRAIN_NATIVE_FLAT_SCHEMA_LINKER_DIAGNOSTIC",
        "source_repo":"kelvin-jiang/FreebaseQA","source_commit":SRC,
        "train_git_blob":TID,"train_original_sha256":hashlib.sha256(raw).hexdigest(),
        "train_original_bytes":len(raw),
        "dev_git_blob_metadata_only":DID,"eval_git_blob_metadata_only":EID,
        "source_stats":stats,"question_only_link_status_counts":dict(sorted(outcome.items())),
        "question_only_population":sum(outcome.values()),
        "source_native_opaque_mid":True,"inferential_chain_is_opaque_string":True,
        "answers_used_for_linking":False,"answers_read_or_compared":False,
        "dev_or_eval_qa_read":False,"source_values_published":False,
        "f107_frozen_parser_modified":False,"real_qa_scored":0,
        "independent_linker_accuracy_qualified":False,
        "freebase_graph_qualified":False,"role_translator_qualified":False,
        "independent_scientific_firstuse":False,"accepted_science":False,
        "accepted_ref_mutation":False,"dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,"science_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    check(not a.out.exists(),"OUTPUT_EXISTS")
    data=(json.dumps(audit(a.upstream),indent=2,sort_keys=True,ensure_ascii=True)+"\n").encode("utf-8")
    with a.out.open("xb") as f:f.write(data)
    print("F108O_TRAIN_NATIVE_SCHEMA_20358_QUESTIONS_37306_PARSES_ACCOUNTED")
    print("F108O_TRAIN_ONLY_LINKER_NO_GOLD_SCORE_NO_EVAL_NO_MODEL")

if __name__=="__main__":
    try:main()
    except (Denied,OSError,UnicodeError,ValueError,KeyError,subprocess.SubprocessError) as ex:
        print("F108O_ORIGINAL_TRAIN_NATIVE_SCHEMA_DENIED:",ex,file=sys.stderr)
        sys.exit(1)
