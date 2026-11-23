"""Execute a NEW bounded Wingless development original on a frozen fresh cohort.

Uses the exact unchanged archived R35 computational method. This is real
scientific compute, not a synthetic controller fixture and not F3 acceptance.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,sys
from protocol import protocol,parent_ok,claim_ok,load,digest,gitblob,reject,STAGES,LEGACY_BLOB,WING_SHA
ROOT=pathlib.Path(__file__).resolve().parent
def module(path,name):
    raw=path.read_bytes()
    if gitblob(raw)!=LEGACY_BLOB:reject("LEGACY_METHOD_BLOB_CHANGED")
    spec=importlib.util.spec_from_file_location(name,path)
    if not spec or not spec.loader:reject("METHOD_UNAVAILABLE")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod
def original(manifest_raw,parent_raw,claim_raw,legacy_root,wingless_root,stage,run_id,head):
    m=protocol(manifest_raw);p=parent_ok(parent_raw,stage)
    claim_ok(claim_raw,manifest_raw,stage,run_id,head)
    if not isinstance(run_id,str) or not run_id.isdecimal() or len(head)!=40:reject("RUN_IDENTITY")
    s=m["stages"][stage]
    legacy=module(legacy_root/"research/r35-wingless/execute.py","r8_pinned_r35_method")
    src=wingless_root/m["source_method_file"]
    if not src.is_file():reject("PINNED_WINGLESS_METHOD_MISSING")
    w52=legacy.load_parent(src)
    plan={"arms":m["fixed_arms"],"development_blocks":s["development_blocks"],
          "sealed_heldout_seeds":s["sealed_heldout_seeds"],"parent_experiment_id":s["parent_experiment_id"]}
    model=legacy.run(plan,w52,p["outcome"])
    if (model.get("classification") not in m["classification_rules"] or
        model.get("model_calls")!=0 or model.get("science_production_accepted") is not False):
        reject("SCIENCE_METHOD_INVALID")
    return {"schema":"forge.r8.real-wingless-development-original.v1",
      "experiment_id":STAGES[stage],"stage_index":stage,
      "parent_experiment_id":s["parent_experiment_id"],
      "parent_outcome":p["outcome"],"parent_review_sha256":digest(parent_raw),
      "frozen_manifest_sha256":digest(manifest_raw),
      "method_legacy_git_blob":LEGACY_BLOB,"wingless_source_commit":WING_SHA,
      "run_id":run_id,"launch_head_sha":head,
      "firstuse_budget_consumed_before_compute":True,
      "original_replay_allowed":False,
      "scientific_accepted":False,"paid_api_calls":0,
      "scientific_development_result":model,"outcome":model["classification"]}
def main():
    a=argparse.ArgumentParser()
    for v in ("manifest","parent_review","claim","legacy_root","wingless_root","stage","run_id","head","out"):
        a.add_argument("--"+v.replace("_","-"),required=True)
    p=a.parse_args()
    i=int(p.stage)
    if i not in (0,1):reject("STAGE")
    args=(pathlib.Path(p.manifest).read_bytes(),pathlib.Path(p.parent_review).read_bytes(),
          pathlib.Path(p.claim).read_bytes(),pathlib.Path(p.legacy_root),
          pathlib.Path(p.wingless_root),i,p.run_id,p.head)
    result=original(*args)
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with pathlib.Path(p.out).open("xb") as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    print("R8_REAL_DEVELOPMENT_ORIGINAL_EXECUTED="+STAGES[i],flush=True)
    print("R8_ORIGINAL_SHA256="+digest(raw),flush=True)
if __name__=="__main__":main()
