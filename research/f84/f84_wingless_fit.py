#!/usr/bin/env python3
"""Read-only F84 source-bound FIT receipt admission. Never scientific authority."""
import hashlib,io,json,re,sys,zipfile
RUN=38878579349
ART=12037005113
SHA="c6abcf0eac723ab44e3fd20563e51b7fab355105"
DIGEST="sha256:e904bb9e7674ee80a34ebca5b629728a4baaa93de3db0c22e9b4a15f7d8b507e"
ARMS=("public_full_exact_joint_posterior_extra_work","strong_structured_MAP","public_top2_role_beam","F60_MAP_algorithm_port_F61_observations","public_local_rolewise","private_oracle_unfair")
NAMES={"f61b-fit.json","independent_audit.txt","hashes.txt","source_identity.txt"}
class Denied(ValueError): pass
def need(v,s):
 if not v:raise Denied("F84_"+s)
def audit(run,meta,blob):
 need(run.get("id")==RUN and run.get("head_sha")==SHA and run.get("run_attempt")==1 and run.get("event")=="push" and run.get("path")==".github/workflows/w-f61b-once-fit-source-20261016.yml" and run.get("status")=="completed" and run.get("conclusion")=="success","RUN_IDENTITY")
 need(meta.get("id")==ART and meta.get("name")=="wingless-f61b-once-fit-receipts" and meta.get("expired") is False and meta.get("digest")==DIGEST and meta.get("workflow_run",{}).get("head_sha")==SHA and meta.get("workflow_run",{}).get("id")==RUN,"ARTIFACT_IDENTITY")
 need(len(blob)<2*1024*1024 and "sha256:"+hashlib.sha256(blob).hexdigest()==DIGEST,"ARCHIVE_DIGEST")
 files={}
 with zipfile.ZipFile(io.BytesIO(blob)) as z:
  for info in z.infolist():
   path=info.filename
   need(path in NAMES or (path.startswith("evidence/") and path[9:] in NAMES),"ARCHIVE_PATH")
   key=path.rsplit("/",1)[-1]
   need(key not in files and not info.is_dir() and info.file_size<1024*1024,"ARCHIVE_DUPLICATE_OR_SIZE")
   files[key]=z.read(info)
 need(set(files)==NAMES,"ARCHIVE_INCOMPLETE")
 need(files["source_identity.txt"].decode().strip().splitlines()==["head="+SHA,"qualified_ancestor=3e4af348b35bd792463c40ddafcad9e953309206"],"SOURCE_WITNESS")
 hashes={}
 for line in files["hashes.txt"].decode().splitlines():
  m=re.fullmatch(r"([0-9a-f]{64})\s+(?:evidence/)?(f61b-fit\.json|independent_audit\.txt)",line.strip())
  need(m is not None and m[2] not in hashes,"HASH_MANIFEST")
  hashes[m[2]]=m[1]
 need(set(hashes)=={"f61b-fit.json","independent_audit.txt"} and all(hashlib.sha256(files[k]).hexdigest()==v for k,v in hashes.items()),"RECEIPT_HASH")
 d=json.loads(files["f61b-fit.json"])
 need(d.get("schema")=="wingless.f61b.counterfactual-binding-FIT-source.v1" and d.get("stage")=="F61B_DISJOINT_FIT_ONLY_SOURCE_NOT_LEARNED" and d.get("fit_seeds")==[771000,771016] and d.get("FIT_families")==[1480,1481,1482,1483] and d.get("cases")==128 and d.get("dependent_query_instances_per_case")==3,"FROZEN_COHORT")
 need(d.get("diagnostic_unconsumed") is True and d.get("originals_unconsumed") is True and d.get("independent_F3") is False and d.get("accepted_refs_unchanged") is True and d.get("native_total_576B_unverified") is True and d.get("abstract_cost_is_not_proven_matched_work") is True and d.get("source_gate_qualified") is False,"FIRST_USE_FENCE")
 rows=d.get("rows");need(type(rows) is list and len(rows)==128,"ROW_COUNT")
 scores={a:0 for a in ARMS};seen=set()
 for row in rows:
  seed,fam,length=row.get("seed"),row.get("family"),row.get("length")
  need(type(seed) is int and type(fam) is int and type(length) is int and 771000<=seed<771016 and 1480<=fam<=1483 and length in (8,10) and (seed,fam,length) not in seen,"ROW_COHORT_OR_REPLAY")
  seen.add((seed,fam,length))
  correct=row.get("correct")
  need(type(correct) is dict and set(correct)==set(ARMS),"ROW_ARM_SET")
  for arm in ARMS:
   value=correct[arm];need(type(value) is int and value in (0,1),"ROW_SCORE_TYPE")
   scores[arm]+=value
 need(len(seen)==128 and d.get("scores")==scores,"ROW_SCORE_RECOUNT")
 strongest=max(ARMS[1:-1],key=lambda a:scores[a]);gain=(scores[ARMS[0]]-scores[strongest])/128
 need(scores[ARMS[0]]==104 and scores[strongest]==102 and gain==0.015625 and d.get("strongest_affordable_structural_control")==strongest and abs(d.get("exact_gain_vs_strongest",-1)-gain)<1e-12 and abs(d.get("exact_public_accuracy",-1)-104/128)<1e-12,"FROZEN_NEGATIVE_DRIFT")
 lines=[x for x in files["independent_audit.txt"].decode().splitlines() if x.startswith("W_F61_SOURCE_AUDIT ")]
 need(len(lines)==1,"INDEPENDENT_AUDIT_MISSING")
 witness=json.loads(lines[0].split(" ",1)[1])
 need(witness.get("correct")==scores and witness.get("qualified") is False and abs(witness.get("headroom",-1)-gain)<1e-12 and abs(witness.get("exact_accuracy",-1)-104/128)<1e-12,"INDEPENDENT_AUDIT_DRIFT")
 return {"schema":"forge.f84.wingless-real-fit-negative.v1","run":RUN,"artifact":ART,"source_sha":SHA,"digest":DIGEST,"fit_cases":128,"exact_correct":104,"strongest_fair_correct":102,"headroom_pp":1.5625,"required_headroom_pp":5,"first_use_authorized":False,"independent_original_accepted":False,"dream_rsi_pareto_policy_gain_qualified":False,"originals_dispatched":0,"disposition":"AUTHENTIC_FIT_NEGATIVE_NOT_ACCEPTED_SCIENCE"}
if __name__=="__main__":
 try:
  need(len(sys.argv)==4,"ARGS")
  with open(sys.argv[1],encoding="utf-8") as f:run=json.load(f)
  with open(sys.argv[2],encoding="utf-8") as f:meta=json.load(f)
  with open(sys.argv[3],"rb") as f:blob=f.read(2*1024*1024+1)
  print(json.dumps(audit(run,meta,blob),sort_keys=True,separators=(",",":")))
  print("F84_REAL_WINGLESS_FIT=VERIFIED_NEGATIVE")
  print("F84_POLICY_PROMOTION_AND_ORIGINAL_DISPATCH=DENIED")
 except (Denied,ValueError,KeyError,TypeError,zipfile.BadZipFile,OSError,UnicodeError):
  print("F84_FIT_ADMISSION=BLOCKED",file=sys.stderr)
  raise SystemExit(1)
