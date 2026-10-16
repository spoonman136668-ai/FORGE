"""Verify an actual Yggdrasil F63C once-only held-out FIT artifact, without accepting an original."""
import hashlib, io, json, sys, zipfile

RUN=38885850944
ARTIFACT=12038939609
SOURCE="fd5eafe1417626911bb6a7fb0645377d005b8361"
ARCHIVE="sha256:b6dc0cf9ff47cfb58f6b23507224e5b9ba84fa941bd6921e5e55e4c70a05cd16"
ROWS_SHA="35526a3889da02b8e6e73219240b28818e829a3a745b5a9ae74954cb96ed84b5"
VERDICT_SHA="241a7eff70951d39bf63bb277f6d2535c4d7ac4778bac88838f374b703857167"
METRIC_KEYS=("F58_frontier","F59_deferred","F60_fixed","F61_frozen_no_refit",
 "F62_frozen_no_refit","F63C_no_reliability_ablation",
 "F63C_trained_reliability","fixed_FIFO_hash","fixed_pair_triple_DAG")

class NotQualified(ValueError): pass
def require(ok,label):
 if not ok: raise NotQualified("F83_"+label)

def audit_rows(rows,verdict):
 require(type(rows) is list and len(rows)==32,"ROW_COUNT")
 require(verdict.get("registered_validation_cases")==32 and
  verdict.get("strongest_fair")=="F60_fixed","FROZEN_COMPARATOR")
 seen=set()
 scores={name:0 for name in METRIC_KEYS}
 per_family={str(i):{"strongest_fair":0,"trained":0} for i in range(1540,1544)}
 for row in rows:
  require(type(row) is dict and type(row.get("score")) is dict,"ROW_SHAPE")
  seed=row.get("seed");fam=row.get("family")
  require(type(seed) is int and type(fam) is int and
   801008<=seed<801016 and str(fam) in per_family,"ROW_COHORT")
  key=(seed,fam)
  require(key not in seen,"REPEATED_ROW")
  seen.add(key)
  for name in METRIC_KEYS:
   value=row["score"].get(name)
   require(type(value) is int and value in (0,1),"BINARY_SCORE")
   scores[name]+=value
  per_family[str(fam)]["strongest_fair"]+=row["score"]["F60_fixed"]
  per_family[str(fam)]["trained"]+=row["score"]["F63C_trained_reliability"]
  for audit in ("independent_model_audit","independent_ablation_audit"):
   a=row.get(audit)
   require(type(a) is dict and a.get("source_independent_F3") is False and
    a.get("max_payload_bytes")==144 and a.get("prefixes")==72 and
    a.get("publicly_grounded_question") is True,"AUDIT_BOUNDARY")
 require(len(seen)==32 and len({x[0] for x in seen})==8,"COHORT_COMPLETENESS")
 require(scores==verdict.get("scores") and per_family==verdict.get("per_family"),
  "VERDICT_SCORE_MISMATCH")
 require(scores["F60_fixed"]==verdict.get("strongest_fair_correct")==24 and
  scores["F63C_trained_reliability"]==verdict.get("learned_correct")==11,
  "OBSERVED_OUTCOME_DRIFT")
 require(verdict.get("observed_gain")==-0.40625 and
  (scores["F63C_trained_reliability"]-scores["F60_fixed"])/32==-0.40625,
  "NEGATIVE_MAGNITUDE_DRIFT")
 return scores

def verify(run,meta,raw):
 require(type(run) is dict and run.get("id")==RUN and
  run.get("head_sha")==SOURCE and run.get("status")=="completed" and
  run.get("conclusion")=="success" and run.get("event")=="push","RUN_IDENTITY")
 require(type(meta) is dict and meta.get("id")==ARTIFACT and
  meta.get("name")=="y-f63c-once-prospective-heldout-evidence" and
  meta.get("expired") is False and meta.get("digest")==ARCHIVE,"ARTIFACT_IDENTITY")
 require(type(raw) is bytes and len(raw)<=8*1024*1024 and
  "sha256:"+hashlib.sha256(raw).hexdigest()==ARCHIVE,"ARCHIVE_DIGEST")
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  names=z.namelist()
  require(set(names)=={"exact_head.txt","hashes.txt","heldout_verdict.json","heldout_once_rows.jsonl"} and len(names)==4,"ARCHIVE_CONTENTS")
  for info in z.infolist():
   require(info.file_size<=2*1024*1024 and not info.is_dir(),"ARCHIVE_ENTRY_SIZE")
  require(z.read("exact_head.txt").decode("ascii").strip()==SOURCE,"FROZEN_SOURCE")
  outcome=z.read("heldout_verdict.json")
  rows_raw=z.read("heldout_once_rows.jsonl")
 require(hashlib.sha256(outcome).hexdigest()==VERDICT_SHA and
  hashlib.sha256(rows_raw).hexdigest()==ROWS_SHA,"FILE_DIGESTS")
 verdict=json.loads(outcome)
 rows=[json.loads(line) for line in rows_raw.splitlines()]
 require(verdict.get("schema")=="yggdrasil.f63c.once-authentic-heldout-science.v1" and
  verdict.get("row_sha256")==ROWS_SHA,"VERDICT_SCHEMA")
 scores=audit_rows(rows,verdict)
 require(verdict.get("fit_validate_consumed_once") is True and
  verdict.get("originals_executed") is False and
  verdict.get("independent_F3") is False and
  verdict.get("scientific_qualified") is False and
  verdict.get("policy_promotion") is False and
  verdict.get("accepted_ref_mutation") is False and
  verdict.get("diagnostics_executed") is False and
  verdict.get("source_fit_train_rerun") is False,"FIRST_USE_BOUNDARY")
 thresholds=verdict.get("preregistered_threshold_passes",{})
 require(thresholds.get("gain_over_strongest_fair") is False and
  thresholds.get("per_family_nondegradation") is False,"PREREG_FAILURE")
 return {"schema":"forge.f83.authentic-heldout-negative-review.v1",
  "project":"Yggdrasil","run":RUN,"artifact":ARTIFACT,
  "source_sha":SOURCE,"archive_sha256":ARCHIVE,"cases":32,
  "learned_correct":scores["F63C_trained_reliability"],
  "strongest_fair_correct":scores["F60_fixed"],"gain_pp":-40.625,
  "fit_validation_consumed_once":True,"independently_accepted_original":False,
  "dream_rsi_pareto_policy_gain_qualified":False,
  "first_use_authorized":False,"new_original_dispatched":False,
  "disposition":"AUTHENTIC_PROSPECTIVE_FIT_VALIDATION_NEGATIVE_NOT_ACCEPTED_SCIENCE"}

def main(paths):
 require(len(paths)==3,"ARGS")
 with open(paths[0],encoding="utf-8") as f: run=json.load(f)
 with open(paths[1],encoding="utf-8") as f: meta=json.load(f)
 with open(paths[2],"rb") as f: raw=f.read(8*1024*1024+1)
 print(json.dumps(verify(run,meta,raw),sort_keys=True,separators=(",",":")))
 print("F83_REAL_FIT_HELDOUT_NEGATIVE=VERIFIED")
 print("F83_OPTIMIZER_PROMOTION_AND_ORIGINAL_DISPATCH=DENIED")
if __name__=="__main__":
 try:main(sys.argv[1:])
 except (NotQualified,ValueError,KeyError,TypeError,zipfile.BadZipFile,OSError) as err:
  print("F83_ARCHIVE_AUDIT=BLOCKED",file=sys.stderr)
  raise SystemExit(1)
