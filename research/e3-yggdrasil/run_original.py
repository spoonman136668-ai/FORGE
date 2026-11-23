"""Pinned Y070 real scientific worker, with new FORGE-only preregistered cohorts.

The interrupt proof instruments *after* a real Yggdrasil simulator evaluation has
returned. It does not manufacture a synthetic worker or replay Y070's old cohort.
"""
import argparse,hashlib,importlib.util,json,os,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MANIFEST="c5406b30e45895af9a70c074ae1b5de5b70df1cf"
IDS=("Y-FORGE-E3-ONSET-LATENCY-01",)
def load_frozen(ygg_root):
    path=ygg_root/"research/contrib/chatgpt/20261013-y070-onset1/execute.py"
    spec=importlib.util.spec_from_file_location("y070_forge_pinned",path)
    if not spec or not spec.loader:raise ValueError("YGG_PINNED_SCIENTIFIC_SOURCE_MISSING")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
def evaluate(study,ygg_root,marker=None,parent_review=None):
    root=ROOT/"prereg.json"
    raw=root.read_bytes()
    if blob(raw)!=MANIFEST:raise ValueError("YGG_MANIFEST_BLOB_DRIFT")
    m=json.loads(raw)
    x=next((x for x in m["studies"] if x["experiment_id"]==study),None)
    if x is None or study not in IDS:raise ValueError("YGG_STUDY_ID_DRIFT")
    if len(x["dev_seeds"])!=8 or len(x["sealed_seeds"])!=16 or len(set(x["dev_seeds"]+x["sealed_seeds"]))!=24:raise ValueError("YGG_COHORT_DRIFT")
    if parent_review is None:raise ValueError("YGG_E3_REQUIRES_INDEPENDENT_E2_REVIEW")
    predecessor=json.loads(parent_review)
    if (predecessor.get("schema")!="forge.yggdrasil.parity-independent-review.v1"
        or predecessor.get("experiment_id")!=m["parent"]["experiment_id"]
        or predecessor.get("outcome")!=m["parent"]["required_outcome"]
        or predecessor.get("independently_validated") is not True
        or predecessor.get("original_replay_allowed") is not False):
        raise ValueError("YGG_E3_UNQUALIFIED_SCIENTIFIC_PARENT")
    z=load_frozen(ygg_root)
    z.DEV=tuple(x["dev_seeds"]);z.HELDOUT=tuple(x["sealed_seeds"])
    if marker is not None:
        original=z.m.y50.evaluate
        def counted_evaluate(*args,**kwargs):
            result=original(*args,**kwargs)  # real simulator computes first
            if not marker.exists():
                with marker.open("x") as f:
                    f.write(json.dumps({"schema":"forge.ygg.real-evaluator-entered.v1",
                                         "experiment_id":study,"evaluations_completed":1,
                                         "worker_pid":os.getpid(),"prereg_blob":MANIFEST})+"\n")
                    f.flush();os.fsync(f.fileno())
            return result
        z.m.y50.evaluate=counted_evaluate
    result=z.run()
    if list(result["sealed_heldout_seeds"])!=list(x["sealed_seeds"]) or list(result["development_seeds"])!=list(x["dev_seeds"]):
        raise ValueError("YGG_ORIGINAL_COHORT_DRIFT")
    diagnostic=[]
    for pair in m["pairs"]:
        key=f"{pair[0]}_{pair[1]}:onset1"
        totals=result["groups"][key]["totals"]
        corrected=totals["dual_sentinel_decoder_corrected"]
        control=totals["dual_sentinel_detect_only"]
        pre=corrected["pre_detection_mismatch_episodes"]
        post=corrected["post_detection_mismatch_episodes"]
        baseline=control["post_detection_mismatch_episodes"]
        diagnostic.append({"pair":pair,"pre_detection":pre,"post_detection":post,
                           "control_post":baseline,
                           "post_gain_20pct":baseline>0 and post<=0.8*baseline})
    latency=(all(x["pre_detection"]>x["post_detection"] for x in diagnostic)
             and any(x["post_gain_20pct"] for x in diagnostic))
    residual=all(x["post_detection"]>=x["pre_detection"] for x in diagnostic)
    diagnosis=("LATENCY_DOMINANT_PARTIAL_GAIN" if latency else
               "DECODER_RESIDUAL_DOMINANT" if residual else
               "MIXED_OR_NO_GAIN")
    return {"schema":"forge.yggdrasil.e3-latency-original.v1",
            "experiment_id":study,"prereg_blob":MANIFEST,
            "ygg_source_commit":m["lineage"]["source_commit"],
            "parent_worker_blob":m["lineage"]["y070_worker_blob"],
            "scientific_result":result,"onset_diagnostic":{"pairs":diagnostic,"outcome":diagnosis},"model_calls":0,
            "parent_review_sha256":None if parent_review is None else hashlib.sha256(parent_review).hexdigest(),
            "parent_outcome":None if predecessor is None else predecessor["outcome"],
            "original_replay_allowed":False,"science_production_accepted":False}
def main():
    p=argparse.ArgumentParser()
    for key in ("study","ygg_root","out"):p.add_argument("--"+key.replace("_","-"),required=True)
    p.add_argument("--real-interrupt-marker")
    p.add_argument("--parent-review")
    a=p.parse_args()
    marker=Path(a.real_interrupt_marker) if a.real_interrupt_marker else None
    parent=None if not a.parent_review else Path(a.parent_review).read_bytes()
    report=evaluate(a.study,Path(a.ygg_root),marker,parent)
    if marker is not None:raise ValueError("INTERRUPT_WORKER_UNEXPECTEDLY_COMPLETED")
    raw=(json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(a.out).open("xb") as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    print("YGG_ACTUAL_BOUNDED_ORIGINAL=PASS",flush=True)
    print("YGG_EXPERIMENT="+a.study,flush=True)
    print("YGG_E3_DIAGNOSTIC="+report["onset_diagnostic"]["outcome"],flush=True)
    print("YGG_SCIENTIFIC_OUTCOME="+report["scientific_result"]["classification"],flush=True)
    print("YGG_ORIGINAL_SHA256="+hashlib.sha256(raw).hexdigest(),flush=True)
if __name__=="__main__":main()
