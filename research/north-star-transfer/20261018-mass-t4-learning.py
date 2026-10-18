"""T4 Mass Research: public training vs zero prior on new disjoint open inputs.

Only negative-numbered independent training/open source IDs are generated.
Each task contains a fresh 4-bit permutation composed three times over 16b.
Truths for OPEN inputs and source permutation are evaluator-only. No
original MNS or F124 held source is opened. This does NOT constitute
cross-task meta-transfer: the T3 model always starts from identity.
"""
from __future__ import annotations
import importlib.util,sys,random,time,tracemalloc,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
T3=HERE/"20261018-mass-t3-learned-sbox.py"
FREEZE=HERE/"20261018-mass-t4-frozen-train-only.json"
TRAIN=tuple(range(-947,-939))
OPEN=tuple(range(-953,-949))
def need(x,tag):
    if not x:raise ValueError("MASS_T4_"+tag)
def load():
    spec=importlib.util.spec_from_file_location("mass_t4_model",T3)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    return mod
def born(seed,model):
    need(seed in TRAIN or seed in OPEN,"SOURCE_IDS_ONLY_NEGATIVE_TRAIN_AND_OPEN")
    rng=random.Random(9071321+(-seed)*10007)
    permutation=tuple(rng.sample(range(16),16))
    truth=model.pack(permutation)
    xs=rng.sample(range(65536),64)
    clean=[model.forward(x,truth) for x in xs]
    noise=frozenset(rng.sample(range(48),6))
    public=[(x,clean[i]^(1 if i in noise else 0))
            for i,x in enumerate(xs[:48])]
    evals=tuple(zip(xs[48:],clean[48:]))
    need(len(set(xs))==64 and len(public)==48 and len(evals)==16
         and len(noise)==6,"PUBLIC_EQUAL_INFORMATION")
    return (tuple(public[:40]),tuple(public[40:]),evals),{
       "source_truth_not_model_input":True,"public_noise_count":len(noise),
       "operator_namespace":seed}
def measured(f):
    tracemalloc.start();start=time.process_time_ns()
    out=f()
    d={"cpu_ns":time.process_time_ns()-start,
       "python_peak_bytes":tracemalloc.get_traced_memory()[1]}
    tracemalloc.stop()
    return out,d
def correctness(model,weights,evals):
    return sum(model.forward(x,weights)==truth for x,truth in evals)
def bit_errors(model,weights,evals):
    return sum((model.forward(x,weights)^truth).bit_count() for x,truth in evals)
def main():
    d=json.loads(FREEZE.read_text())
    need(d["schema"]=="research.northstar.t4.train-only-learning-resource-parity.v1"
         and d["frozen_parent_head"]=="dda879b5b5fe2dbf185e2778cfcca8f6c6a403bd"
         and not d["original_protected_holdouts_allowed"],"PRECOMMITTED_SOURCE")
    model=load()
    baseline=model.pack(tuple(range(16)))
    train_examples=[born(seed,model)[0] for seed in TRAIN]
    # TRAIN fits expose whether any SHARED parameter survives task changes:
    # T3 learned weights are discarded at task boundary by design.
    train_receipts=[]
    total_train_cpu=0;total_train_peak=0
    for fit,check,hidden in train_examples:
        (weights,rec),cost=measured(lambda:model.fit_public(fit,check))
        total_train_cpu+=cost["cpu_ns"]
        total_train_peak=max(total_train_peak,cost["python_peak_bytes"])
        train_receipts.append({"different_from_initial_prior":weights!=baseline,
                               "train_fit_errors":rec["FIT_bit_errors"],
                               "public_fit_evaluations":rec["sourceblind_forward_evaluations"]})
    evals=[born(seed,model)[0] for seed in OPEN]
    rows=[]
    for fit,check,hold in evals:
        (weights,rec),fitcost=measured(lambda:model.fit_public(fit,check))
        (after_correct,after_bits),infcost=measured(lambda:(
           correctness(model,weights,hold),bit_errors(model,weights,hold)))
        (prior_correct,prior_bits),priorcost=measured(lambda:(
           correctness(model,baseline,hold),bit_errors(model,baseline,hold)))
        rows.append({"fit_CPU_ns":fitcost["cpu_ns"],
                     "fit_peak_bytes":fitcost["python_peak_bytes"],
                     "inference_CPU_ns":infcost["cpu_ns"],
                     "inference_peak_bytes":infcost["python_peak_bytes"],
                     "prior_CPU_ns":priorcost["cpu_ns"],
                     "learned_open_correct":after_correct,
                     "zero_prior_open_correct":prior_correct,
                     "learned_open_bit_errors":after_bits,
                     "zero_prior_open_bit_errors":prior_bits,
                     "learned_equals_prior":weights==baseline,
                     "fit_public_examples":40,"check_public_examples":8,
                     "original_source_truth_did_not_enter_fit":True,
                     "fit_swaps":rec["FIT_permutation_swaps_evaluated"]})
    assert len(rows)==4 and all(r["fit_swaps"]==240 for r in rows)
    totals=lambda k:sum(r[k] for r in rows)
    out={"schema":"mass.t4.public-fit-learning-diagnostic.v1",
         "train_only_task_count":8,"open_diagnostic_task_count":4,
         "reserved_MNS_and_original_F124_source_used":0,
         "public_responses_per_task":48,"corruptions_per_task":6,
         "held_publicly_unobserved_inputs_per_task":16,
         "learned_train_tasks_nonidentity":sum(x["different_from_initial_prior"]
                   for x in train_receipts),
         "open_task_fit_nonidentity":sum(not r["learned_equals_prior"] for r in rows),
         "learner_has_shared_meta_parameters":False,
         "open_correct_new":totals("learned_open_correct"),
         "open_correct_identity":totals("zero_prior_open_correct"),
         "open_bit_errors_new":totals("learned_open_bit_errors"),
         "open_bit_errors_identity":totals("zero_prior_open_bit_errors"),
         "fit_plus_inference_CPU_ns":totals("fit_CPU_ns")+totals("inference_CPU_ns"),
         "identity_inference_CPU_ns":totals("prior_CPU_ns"),
         "fit_peak_lower_bound":max(r["fit_peak_bytes"] for r in rows),
         "inference_peak_lower_bound":max(r["inference_peak_bytes"] for r in rows),
         "TRAIN_fit_CPU_ns_discarded_not_counted_as_transfer":total_train_cpu,
         "TRAIN_peak_bytes":total_train_peak,
         "task_parameters_bytes":8,"full_training_amortization_qualified":False,
         "strongest_original_AZ_full_graph_score_and_peak_compared":False,
         "strict_transfer_scientifically_accepted":False,
         "all_sealed_sources_untouched":True,
         "rows":rows}
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
