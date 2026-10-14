"""F6 train-only decision rule derived from PUBLIC sensing and used-F3 labels.

No F6 cohort access. At inference the policy receives ONLY earlier public
reads and a frozen integer threshold. It receives neither the evaluator's
true pair, seed, family, regime, reward nor future observations. Historical
training labels (F5 COVERAGE vs MEMORY errors) are used strictly during fit.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"f5_native_coverage"))
from policy import choose as f5_choose,validate,calibration,PROBES

TRAIN_SEEDS=(67204,67205)
CHECK_SEEDS=(67206,67207)
THRESHOLDS=tuple(range(1,10))
NEXT_ID="Y-FORGE-F6-UNCERTAINTY-CALIBRATION-PROPOSAL"
PARENT="5797a257a75fe139313e8486cd1a1ae79c44b148"

def must(ok,why):
    if not ok:raise ValueError("F6_PUBLIC_"+why)

def residual_strength(history):
    # At episode 7 only observations from 0,1,3,5 are available.
    validate(history,7)
    b0,a,d=calibration(history)
    inv=pow(a,-1,16)
    scores=[]
    for cell,value in history[5].items():
        actual=(inv*(value-(b0+5*d)))%16
        residual=(actual-cell)%16
        scores.append(min(residual,16-residual))
    must(len(scores)==2,"PAIR")
    return max(scores)

def choose_f6(episode,history,threshold):
    must(type(threshold) is int and threshold in THRESHOLDS,"FROZEN_THRESHOLD")
    if episode in (0,1,3,5):
        return f5_choose("F5-COVERAGE",episode,history)
    must(episode==7,"UNKNOWN_EPISODE")
    fresh=f5_choose("F5-COVERAGE",episode,history)
    strength=residual_strength(history)
    if strength>0 and strength>=threshold:
        return tuple(sorted(history[5]))
    return fresh

def parent_records(record):
    must(record.get("schema")=="forge.f5.historical-adaptive-coverage-engineering.v1"
         and record.get("status")=="F3_USED_DATA_ONLY_NOT_PROSPECTIVE_SCIENCE"
         and record.get("source_commit")==PARENT
         and record.get("arms")==["F5-FIXED","F5-COVERAGE","F5-MINIMAX","F5-MEMORY"]
         and record.get("historical_seeds")==list(TRAIN_SEEDS+CHECK_SEEDS)
         and record.get("historical_pairs")==[[8,10],[11,13]]
         and record.get("first_use_claims_consumed")==0
         and record.get("new_f5_dev_cohort_accesses")==0
         and record.get("new_f5_sealed_cohort_accesses")==0
         and record.get("scientific_originals_executed")==0
         and record.get("scientific_authority") is False,"PARENT_IDENTITY")
    rows=record.get("records")
    must(type(rows) is list and len(rows)==768,"PARENT_CASE_COUNT")
    paired={}
    for row in rows:
        if row.get("arm") not in ("F5-COVERAGE","F5-MEMORY"):continue
        must(row.get("seed") in TRAIN_SEEDS+CHECK_SEEDS,"SEED")
        key=(row["seed"],tuple(row["pair"]),row["regime"],
             tuple(row["family"]),row["matching_policy"])
        paired.setdefault(key,{})
        must(row["arm"] not in paired[key],"DUPLICATE_RECORD")
        paired[key][row["arm"]]=row
    must(len(paired)==192 and all(len(v)==2 for v in paired.values()),"PAIR_BALANCE")
    return paired

def training_feature(source,key):
    # Simulator reads for *already used* F3 seeds. The true pair and onset
    # are available only to this development-only training evaluator.
    seed,pair,regime,family,_=key
    must(seed in TRAIN_SEEDS,"TRAIN_ONLY")
    must(pair in ((8,10),(11,13)) and regime in ("steady","onset1"),"PAIR")
    m=source.m
    m.y58.install_transposition(None if regime=="steady" else 1,pair,
                                {"anchor_pair_checks":0})
    try:
        history={}
        for episode in (0,1,3,5):
            addresses=f5_choose("F5-COVERAGE",episode,history)
            history[episode]={cell:m.y64.y46.coordinate(
                cell,seed,episode,family,"late_shock") for cell in addresses}
        return residual_strength(history)
    finally:
        m.y49.restore_environment()

def fit(parent,successor,source):
    must(successor.get("schema")=="forge.f5.automatic-evidence-to-successor-proposal.v1"
         and successor.get("disposition")=="SUCCESSOR_PREPARED_CUSTODY_BLOCKED_NO_ORIGINAL"
         and successor.get("selected",{}).get("proposal_id")==NEXT_ID
         and successor.get("selection_rule")=="PUBLIC_MEMORY_RECHECK_NO_GAIN"
         and successor.get("scientific_dispatch_authorized") is False
         and successor.get("new_seed_allocations")==0
         and successor.get("new_first_use_claims")==0,"UNAUTHORIZED_SUCCESSOR")
    paired=parent_records(parent)
    examples=[]
    for key,arms in sorted(paired.items()):
        if key[0] not in TRAIN_SEEDS:continue
        strength=training_feature(source,key)
        cover=arms["F5-COVERAGE"];memory=arms["F5-MEMORY"]
        actually_rechecked=set(memory["sample_trace"]["addresses"][3])==set(
                           memory["sample_trace"]["addresses"][4])
        must(actually_rechecked==(strength>0),"MECHANISM_FIDELITY")
        must(cover["sample_trace"]["addresses"][3]==
             memory["sample_trace"]["addresses"][3],"SAME_EARLY_SENSORS")
        examples.append({"public_strength":strength,
            "coverage_total":cover["pre_mismatch"]+cover["post_mismatch"],
            "recheck_total":memory["pre_mismatch"]+memory["post_mismatch"]})
    must(len(examples)==96,"TRAINING_COUNT")
    ranking=[]
    for threshold in THRESHOLDS:
        total=0
        count=0
        for e in examples:
            recheck=e["public_strength"]>=threshold and e["public_strength"]>0
            total+=e["recheck_total"] if recheck else e["coverage_total"]
            count+=int(recheck)
        ranking.append((total,count,threshold))
    minimum=min(ranking)
    model={
      "schema":"forge.f6.public-only.calibrated-memory-threshold.v1",
      "status":"TRAINED_ON_PREVIOUSLY_USED_F3_DEVELOPMENT_ONLY",
      "hypothesis_id":NEXT_ID,
      "parent_y070_commit":PARENT,
      "feature":"max_circular_calibrated_public_residual_episode5",
      "objective":"historical_training_total_mismatches_then_minimize_rechecks",
      "frozen_threshold":minimum[2],
      "training_seed_ids":list(TRAIN_SEEDS),
      "untouched_validation_seed_ids":list(CHECK_SEEDS),
      "evaluated_thresholds":list(THRESHOLDS),
      "threshold_scores":[{"threshold":t,"training_mismatches":score,
                           "training_rechecks":rechecks}
                          for score,rechecks,t in ranking],
      "training_cases":len(examples),
      "training_objective_mismatches":minimum[0],
      "training_recheck_count":minimum[1],
      "public_scalar_reads":10,
      "retained_capacity":9,
      "new_f6_cohort_accesses":0,
      "new_first_use_claims":0,
      "scientific_originals":0,
      "scientific_dispatch_authorized":False
    }
    return model
