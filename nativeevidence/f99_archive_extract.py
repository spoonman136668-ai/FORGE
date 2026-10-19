"""F99: exact-archive development-only counterfactual descriptors.

This program independently recomputes historical paired outcomes from actual
pinned ZIP bytes. The extracted information is planning-only, never a
trainable GenEnv record, a policy improvement, or a fresh scientific first use.
"""
import argparse
import collections
import hashlib
import io
import json
import math
import pathlib
import re
import sys
import zipfile

SCHEMA="forge.autonomy.f99.authentic-development-row-advisory.v1"
HEX40=re.compile(r"^[0-9a-f]{40}$")
ZIP_LIMIT=1024*1024
JSON_LIMIT=512*1024
PINS={
 "Wingless":{
  "run":38646170288,"artifact":11932322023,
  "commit":"fab5f094a29203a5ef1d63fb40225a3aa9a7e57f",
  "zip":"cf160c2abe1dcc32425f89eb445a20de47ba01c5b158e4fb9242507554dbaadf",
  "member":"w-f10-original-development.json",
  "json":"f397e0f45b0f1664426bca7d5a196eacc5d131d417c9030cc276aa9342a15d92",
  "schema":"wingless.f10.depth_conditioned_capability_audit.v1",
  "rows":96,"pairs":96,"questions":192,
  "blind":"frozen_learned_composition_depth_blind",
  "control":"coded_depth_aware_oracle",
  "verdict":"DEPTH_CONDITIONING_MISSING_FROM_FROZEN_INPUT_INTERFACE",
  "mechanism":"explicit-query-depth-conditioned-composition"
 },
 "Yggdrasil":{
  "run":38646109265,"artifact":11932008018,
  "commit":"714e10f9df0d036f66e4baea229470ed4fe86f04",
  "zip":"cc20faf2c31607ace820b2a9bd90d334b52902a2f776384f938a91884a99fb9e",
  "member":"y-f9-original-development.json",
  "json":"669c3564d7715621e97aa345ee081912223a91c337a17bd3e7dc1c5e6f38f4af",
  "schema":"yggdrasil.f9.typed-role-identifiability-dev.v1",
  "rows":192,"pairs":192,"questions":384,
  "blind":"frozen_learned_role_blind",
  "control":"typed_role_aware_oracle",
  "verdict":"TYPED_RELATION_AND_VARIABLE_BINDING_INPUT_MISSING",
  "mechanism":"typed-role-aware-relation-composition"
 }
}
class Blocked(ValueError): pass
def require(ok,reason):
 if not ok:raise Blocked("FORGE_F99_"+reason)
def hash256(b):return hashlib.sha256(b).hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:
  require(k not in d,"DUPLICATE_JSON_KEY")
  d[k]=v
 return d
def parse_json(raw):
 require(type(raw) is bytes and 0<len(raw)<=JSON_LIMIT,"JSON_SIZE")
 try:
  x=json.loads(raw.decode("utf-8"),object_pairs_hook=unique,
               parse_constant=lambda _:require(False,"NONFINITE"))
 except (UnicodeError,json.JSONDecodeError) as err:
  raise Blocked("FORGE_F99_INVALID_JSON") from err
 require(type(x) is dict,"JSON_OBJECT")
 return x
def archive_bytes(raw,lane):
 require(lane in PINS and type(raw) is bytes and 0<len(raw)<=ZIP_LIMIT,"ZIP_SIZE")
 p=PINS[lane]
 require(hash256(raw)==p["zip"],"ARCHIVE_ZIP_DIGEST")
 try:
  z=zipfile.ZipFile(io.BytesIO(raw),"r",allowZip64=False)
  members=z.infolist()
  require(len(members)==1,"ARCHIVE_MEMBERS")
  item=members[0]
  require(item.filename==p["member"] and item.is_dir() is False and
          item.file_size>0 and item.file_size<=JSON_LIMIT and
          item.compress_size>0 and item.flag_bits & 1 == 0 and
          item.file_size<=100*item.compress_size,
          "ARCHIVE_MEMBER_IDENTITY_OR_BOMB")
  with z.open(item) as f:
   payload=f.read(JSON_LIMIT+1)
  require(len(payload)==item.file_size and hash256(payload)==p["json"],
          "ARCHIVE_CONTAINED_PAYLOAD_DIGEST")
 except (zipfile.BadZipFile,RuntimeError,OSError,EOFError) as err:
  raise Blocked("FORGE_F99_BAD_ARCHIVE") from err
 finally:
  if 'z' in locals():z.close()
 return parse_json(payload)
def pairbool(p):
 return type(p) is list and len(p)==2 and all(type(v) is bool for v in p)
def graph(edges):
 return type(edges) is list and len(edges)==12 and all(
  type(e) is list and len(e)==2 and all(type(a) is int and a>=0 for a in e)
  for e in edges)
def rescore(rows,names,kind):
 result={}
 for name in names:
  predictions=[r[kind][name] for r in rows]
  truth=[r["truth"] for r in rows]
  if kind=="models":
   negative=sum(int(p[0]==t[0]) for p,t in zip(predictions,truth))
   positive=sum(int(p[1]==t[1]) for p,t in zip(predictions,truth))
   both=sum(int(p==t) for p,t in zip(predictions,truth))
   result[name]={"negative_correct":negative,"positive_correct":positive,
     "paired_correct":both,"accuracy":(negative+positive)/(2*len(rows)),
     "paired_accuracy":both/len(rows)}
  else:
   correct=sum(int(p[i]==t[i]) for p,t in zip(predictions,truth) for i in (0,1))
   both=sum(int(p==t) for p,t in zip(predictions,truth))
   result[name]={"correct":correct,"paired_correct":both,
     "negative_false_positives":sum(int(p[1] and not t[1]) for p,t in zip(predictions,truth)),
     "accuracy":correct/(2*len(rows)),"paired_accuracy":both/len(rows)}
 return result
def audit_scores(recomputed,reported):
 require(type(reported) is dict and set(reported)==set(recomputed),"SCORE_ARM_SET")
 for name,record in recomputed.items():
  values=reported[name]
  require(type(values) is dict and set(values)==set(record),"SCORE_METRICS")
  for k,v in record.items():
   got=values[k]
   if isinstance(v,int):
    require(type(got) is int and got==v,"SCORE_INTEGER_OR_REAGGREGATION")
   else:
    require(type(got) in (int,float) and math.isfinite(got) and
            abs(got-v)<1e-12,"SCORE_FLOAT_OR_REAGGREGATION")
def wingless(data):
 require(data.get("schema")==PINS["Wingless"]["schema"] and
         data.get("stage")=="DEVELOPMENT_ONLY" and
         data.get("source_birth_independent") is False and
         data.get("sealed_first_use") is False and
         data.get("accepted_ref_mutation") is False and
         data.get("model_retrained") is False and
         data.get("weights_adjusted") is False and
         data.get("external_llm_calls")==0 and
         data.get("query_depth_is_present_in_frozen_model_interface") is False and
         data.get("explicit_depth_is_only_control_input") is True and
         data.get("same_query_and_edges_per_depth_pair") is True and
         data.get("registered_verdict")==PINS["Wingless"]["verdict"] and
         data.get("graph_states")==96 and data.get("paired_questions")==192 and
         data.get("negative_questions")==96 and
         data.get("exact_chain_lengths")==[4,5,6,7],
         "WINGLESS_FROZEN_PROTOCOL_OR_AUTHORITY")
 rows=data.get("rows")
 require(type(rows) is list and len(rows)==96,"WINGLESS_ROW_COUNT")
 counts=collections.Counter()
 identities=set()
 names={"always_yes_shortcut","coded_depth_aware_oracle",
        "frozen_learned_composition_depth_blind","old_F5_depth_blind"}
 for r in rows:
  require(type(r) is dict and
          pairbool(r.get("truth")) and r["truth"]==[False,True] and
          type(r.get("seed")) is int and 51100<=r["seed"]<51124 and
          type(r.get("path_depth")) is int and 4<=r["path_depth"]<=7 and
          r.get("requested_depths")==[r["path_depth"]-1,r["path_depth"]] and
          graph(r.get("edges")) and type(r.get("query")) is list and
          len(r["query"])==2 and all(type(x) is int for x in r["query"]) and
          type(r.get("models")) is dict and set(r["models"])==names and
          all(pairbool(v) for v in r["models"].values()) and
          type(r.get("frozen_probability")) in (int,float) and
          math.isfinite(r["frozen_probability"]) and
          0<=r["frozen_probability"]<=1,
          "WINGLESS_COUNTERFACTUAL_ROW")
  key=(r["path_depth"],r["seed"])
  require(key not in identities,"WINGLESS_DUPLICATE_PAIR")
  identities.add(key);counts[r["path_depth"]]+=1
 require(counts=={4:24,5:24,6:24,7:24},"WINGLESS_DEPTH_BALANCE")
 result=rescore(rows,names,"models")
 audit_scores(result,data.get("scores"))
 require(result[PINS["Wingless"]["blind"]]["paired_correct"]==0 and
         result[PINS["Wingless"]["control"]]["paired_correct"]==96,
         "WINGLESS_BLIND_VERSUS_CONTROL")
 return result,{"depths":{str(k):counts[k] for k in sorted(counts)},
                "distinct_development_seeds":24}
def yggdrasil(data):
 require(data.get("schema")==PINS["Yggdrasil"]["schema"] and
         data.get("stage")=="DEVELOPMENT_ONLY" and
         data.get("source_birth_independent") is False and
         data.get("sealed_first_use") is False and
         data.get("accepted_ref_mutation") is False and
         data.get("scientific_accepted") is False and
         data.get("model_retrained") is False and
         data.get("external_llm_calls")==0 and
         data.get("candidate_state_contains_role_codes") is False and
         data.get("same_untyped_edges_and_query_per_counterfactual") is True and
         data.get("role_swaps_change_only_relation_types") is True and
         data.get("typed_oracle_must_pass") is True and
         data.get("registered_verdict")==PINS["Yggdrasil"]["verdict"] and
         data.get("graph_pairs")==192 and data.get("question_count")==384 and
         data.get("negative_questions")==192 and
         data.get("families")==[40,41,42,43],
         "YGGDRASIL_FROZEN_PROTOCOL_OR_AUTHORITY")
 rows=data.get("rows")
 require(type(rows) is list and len(rows)==192,"YGGDRASIL_ROW_COUNT")
 counts=collections.Counter()
 identities=set()
 names={"always_yes_shortcut","frozen_learned_role_blind",
        "typed_role_aware_oracle","untyped_coded_reachability"}
 for r in rows:
  p=r.get("roles_positive");s=r.get("roles_swapped")
  require(type(r) is dict and pairbool(r.get("truth")) and
          r["truth"]==[True,False] and
          type(r.get("seed")) is int and 51400<=r["seed"]<51448 and
          type(r.get("family")) is int and r["family"] in (40,41,42,43) and
          graph(r.get("edges")) and
          type(r.get("question")) is list and len(r["question"])==2 and
          all(type(v) is int for v in r["question"]) and
          type(p) is list and type(s) is list and len(p)==12 and len(s)==12 and
          all(type(v) is int and 0<=v<=3 for v in p+s) and
          sum(a!=b for a,b in zip(p,s))==1 and
          type(r.get("requested_role_sequence")) is list and
          len(r["requested_role_sequence"])==4 and
          all(type(v) is int and 0<=v<=3 for v in r["requested_role_sequence"]) and
          type(r.get("predictions")) is dict and set(r["predictions"])==names and
          all(pairbool(v) for v in r["predictions"].values()),
          "YGGDRASIL_COUNTERFACTUAL_ROW")
  key=(r["family"],r["seed"])
  require(key not in identities,"YGGDRASIL_DUPLICATE_PAIR")
  identities.add(key);counts[r["family"]]+=1
 require(counts=={40:48,41:48,42:48,43:48},"YGGDRASIL_FAMILY_BALANCE")
 result=rescore(rows,names,"predictions")
 audit_scores(result,data.get("scores"))
 require(result[PINS["Yggdrasil"]["blind"]]["paired_correct"]==0 and
         result[PINS["Yggdrasil"]["control"]]["paired_correct"]==192,
         "YGGDRASIL_BLIND_VERSUS_CONTROL")
 return result,{"families":{str(k):counts[k] for k in sorted(counts)},
                "distinct_development_seeds":48}
def extract(archives,source):
 require(type(source) is str and HEX40.fullmatch(source),"FORGE_SHA")
 require(type(archives) is dict and set(archives)==set(PINS),"TWO_SOURCE_COHORT")
 rows=[]
 for lane in ("Wingless","Yggdrasil"):
  obj=archive_bytes(archives[lane],lane)
  recomputed,features=(wingless(obj) if lane=="Wingless" else yggdrasil(obj))
  p=PINS[lane]
  rows.append({
   "lane":lane,"source_commit":p["commit"],
   "original_archive_run_id":p["run"],"original_artifact_id":p["artifact"],
   "zip_sha256":p["zip"],"contained_json_sha256":p["json"],
   "historical_development_pair_count":p["pairs"],
   "frozen_blind_paired_correct":recomputed[p["blind"]]["paired_correct"],
   "coded_oracle_paired_correct":recomputed[p["control"]]["paired_correct"],
   "development_only_descriptors":features,
   "historical_negative_mechanism_constraint":p["mechanism"],
   "stage":"AUTHENTIC_HISTORICAL_DEVELOPMENT_ONLY",
   "source_bytes_and_rows_reaudited":True,
   "independent_original_firstuse_qualified":False,
   "train_only_genenv_record_admitted":False,
   "science_accepted":False})
 return {
  "schema":SCHEMA,"forge_source_sha":source,
  "cohort_source":"EXACT_PINNED_GITHUB_ACTIONS_ZIP_AND_CONTAINED_JSON_BYTES",
  "lanes":rows,"distinct_authentic_dev_lane_sources":2,
  "descriptive_development_constraints_verified":2,
  "new_trainable_genenv_records":0,
  "new_scientific_originals":0,"original_first_use_authorized":False,
  "research_selection_promotion_authorized":False,
  "accepted_research_ref_mutation":False,
  "model_invocations":0,"codex_invocations":0,"external_model_api_calls":0,
  "disposition":"REAL_DEV_ROW_REAGGREGATION_ONLY_NO_TRAINING_OR_NOVEL_SCIENCE_AUTHORITY"}
def main(argv):
 parser=argparse.ArgumentParser()
 parser.add_argument("--source-sha",required=True)
 parser.add_argument("--wingless-zip",required=True)
 parser.add_argument("--yggdrasil-zip",required=True)
 p=parser.parse_args(argv)
 files={}
 for lane,path in (("Wingless",p.wingless_zip),("Yggdrasil",p.yggdrasil_zip)):
  q=pathlib.Path(path)
  require(q.is_file() and not q.is_symlink() and q.stat().st_size<=ZIP_LIMIT,
          "INPUT_MISSING_OR_SYMLINK")
  files[lane]=q.read_bytes()
 print(json.dumps(extract(files,p.source_sha),sort_keys=True,separators=(",",":")))
if __name__=="__main__":
 try:main(sys.argv[1:])
 except (Blocked,OSError,TypeError,KeyError,IndexError) as exc:
  print("FORGE_F99_DEVELOPMENT_ARCHIVE=QUARANTINED",file=sys.stderr)
  sys.exit(1)
