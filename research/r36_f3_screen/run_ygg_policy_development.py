"""F3 source-pinned real development-only four-policy comparison.

Train on seeds 67200..67203 and evaluate on 67204..67207. The
training examples use only the pinned ten public reads and development
pair labels. No sealed cohort, scientific original, or winner selection.
"""
import argparse,hashlib,json
from pathlib import Path
from run_yggdrasil_development import DEV,PAIRS,ARM,load_pinned,validate_portfolio
from ygg_methods import DevelopmentTrial,METHODS
from ygg_learned_policies import fit_all
from ygg_public_instrument import BASELINE,install_public_schedule,install_public_policy

TRAIN=DEV[:4]
VALIDATION=DEV[4:]

def train_public(z):
    m=z.m
    examples=[]
    try:
        for i,seed in enumerate(TRAIN):
            pair=PAIRS[i%len(PAIRS)]
            m.y58.install_transposition(1,pair,{"anchor_pair_checks":0})
            family=z.FAMILIES[i%len(z.FAMILIES)]
            with install_public_schedule(z,BASELINE):
                # Y065 consumes the Y064 public sampler, not raw Y059.sample.
                readings=m.y64.dual_public_samples(seed,family)
            def state(ep):
                v=[0.0]*16
                for k,x in readings[ep].items():v[int(k)]=float(x)
                return tuple(v)
            examples.append(DevelopmentTrial(seed,state(3),state(1),state(5),pair[0]))
            m.y49.restore_environment()
    finally:m.y49.restore_environment()
    return fit_all(tuple(examples))

def measure(root):
    validate_portfolio()
    z=load_pinned(root);m=z.m
    ranks=train_public(z)
    records=[]
    try:
        for pair in PAIRS:
            for regime,onset in (("steady",None),("onset1",1)):
                m.y58.install_transposition(onset,pair,{"anchor_pair_checks":0})
                for family in z.FAMILIES:
                    for seed in VALIDATION:
                        for policy in z.POLICIES:
                            truth=m.y50.evaluate(seed,policy,"canonical","continue",family)
                            for key in ("CONTROL",)+METHODS:
                                audit=[]
                                if key=="CONTROL":
                                    candidate=m.candidate(seed,family,policy,ARM)
                                else:
                                    with install_public_policy(z,key,ranks[key],audit=audit):
                                        candidate=m.candidate(seed,family,policy,ARM)
                                    if len(audit)!=1:
                                        raise ValueError("F3_POLICY_SENSOR_HOOK_NOT_CALLED")
                                    if len(audit[0])!=5 or any(len(reads)!=2 for reads in audit[0]):
                                        raise ValueError("F3_POLICY_SENSOR_TRACE_DRIFT")
                                if candidate["public_scalar_reads"]!=10:
                                    raise ValueError("F3_POLICY_READ_BUDGET")
                                first=next((r["public_detected_swap_first_episode"]
                                     for r in reversed(candidate["rows"])
                                     if r["public_detected_swap_first_episode"] is not None),None)
                                pre=post=0
                                if len(candidate["rows"])!=len(truth["rows"]):
                                    raise ValueError("F3_POLICY_ROWS")
                                for reference,observed in zip(truth["rows"],candidate["rows"]):
                                    wrong=int(any(reference["physical_assignment"][k]!=observed["physical_assignment_evaluator_only"][k]
                                                  for k in reference["physical_assignment"]))
                                    if first is None or observed["episode"]<first:pre+=wrong
                                    else:post+=wrong
                                    if observed["illegal_physical_assignments"] or observed["candidate_retained_cache_occupancy"]>9:
                                        raise ValueError("F3_POLICY_CAPACITY")
                                records.append({"candidate":key,"pair":list(pair),"regime":regime,
                                                "family":list(family),"seed":seed,"policy":policy,
                                                "first_detection":first,"pre_mismatch":pre,
                                                "post_mismatch":post,"reads":10,
                                                "public_addresses":audit[0] if key!="CONTROL" else
                                                    [[0,1],[0,1],[0,1],[2,4],[2,4]]})
                m.y49.restore_environment()
    finally:m.y49.restore_environment()
    if len(records)!=2*2*4*4*3*5:raise ValueError("F3_POLICY_CASE_COUNT")
    # Rule out the vacuous intervention: passing a policy ID to an untouched sampler.
    baseline=[[0,1],[0,1],[0,1],[2,4],[2,4]]
    for key in METHODS:
        traces=[row["public_addresses"] for row in records if row["candidate"]==key]
        if len(traces)!=192 or all(trace==baseline for trace in traces):
            raise ValueError("F3_POLICY_UNOBSERVED_INTERVENTION")
    return {"schema":"forge.f3.yggdrasil.policy-development.v1",
            "status":"DEVELOPMENT_SCORED_FIDELITY_REVIEW_REQUIRED",
            "source_commit":"5797a257a75fe139313e8486cd1a1ae79c44b148",
            "training_seeds":list(TRAIN),"validation_seeds":list(VALIDATION),
            "rankings":{k:list(v) for k,v in ranks.items()},"records":records,
            "scientific_winners_selected":0,"sealed_first_uses_consumed":0}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--yggdrasil-root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    report=measure(a.yggdrasil_root)
    raw=(json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(a.out).open("xb") as f:f.write(raw)
    print("F3_REAL_FOUR_POLICY_DEV=PASS")
    print("F3_POLICY_DEV_RECORD_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F3_POLICY_DEV_TRIALS="+str(len(report["records"])))
