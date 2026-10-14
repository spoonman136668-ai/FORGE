"""Prepare a next Yggdrasil hypothesis without dispatching another scientific original."""
import argparse,hashlib,json
from pathlib import Path
IDS=("Y-FORGE-PARITY-D1-ONSET1","Y-FORGE-PARITY-D2-ONSET1")
def generate(a_raw,b_raw):
    a=json.loads(a_raw);b=json.loads(b_raw)
    if [a.get("experiment_id"),b.get("experiment_id")]!=list(IDS) or a.get("independently_validated") is not True or b.get("independently_validated") is not True or a.get("original_replay_allowed") is not False or b.get("original_replay_allowed") is not False:
        raise ValueError("YGG_PROPOSAL_PARENT_NOT_INDEPENDENTLY_ACCEPTED")
    gain=a["outcome"]=="EARLY_CAUSAL_GAIN" and b["outcome"]=="EARLY_CAUSAL_GAIN"
    return {"schema":"forge.yggdrasil.parity-successor-proposal.v1",
        "experiment_id":"Y-FORGE-PARITY-D3-CAUSAL-BOUNDARY-01",
        "parent_ids":list(IDS),
        "parent_outcomes":[a["outcome"],b["outcome"]],
        "parent_review_sha256":[hashlib.sha256(a_raw).hexdigest(),hashlib.sha256(b_raw).hexdigest()],
        "hypothesis":("Replicate stable early corrective gain across additional disjoint source generators and shock timing" if gain else "Discriminate unavoidable pre-detection latency from post-detection decoder failure using novel frozen onset timing on fresh cohorts"),
        "new_original_dispatch_authorized":False,"proposal_only":True,
        "new_originals_executed":0,"no_fsa_cutover":True,"ckb_research_authority_unchanged":True}
def main():
    p=argparse.ArgumentParser()
    for x in ("d1_review","d2_review","out"):p.add_argument("--"+x.replace("_","-"),required=True)
    a=p.parse_args()
    x=generate(Path(a.d1_review).read_bytes(),Path(a.d2_review).read_bytes())
    with Path(a.out).open("x") as f:f.write(json.dumps(x,indent=2,sort_keys=True)+"\n")
    print("YGG_AUTONOMOUS_SUCCESSOR_PROPOSAL=PASS",flush=True)
    print("YGG_D3_NEW_SCIENCE_DISPATCH=FALSE",flush=True)
if __name__=="__main__":main()
