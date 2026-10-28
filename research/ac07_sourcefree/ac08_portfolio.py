"""AC-08: read-only reconciliation of AC-05/06/07 source-free research portfolio.

No new scheduler, research dispatcher, model import, outside network, original
consequence source, scientific admission, privileged state or first-use.
The true scope is precisely 30 bounded original IDs + 6 mechanism IDs.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CASE_PINS={
    "AC05":"9c85db56ef0ff8f478e2d129d7c0a64da49d1a6c",
    "AC06":"d6c6e1ff61ebb3bd75ce35be07fe13c027aff8f9",
    "AC07":"d63640071100dcc6e31030f0a69c07b324eeef47",
}
PR_CHAIN=(1054,1055,1057,1058,1060,1061,1062)
AC06_ORIGINAL=set("U07 U08 U10 U18 U19 U20 U21 U22 U23 U24 U26 U27 U28 U29 U30".split())
AC07_ORIGINAL=set("U01 U02 U03 U04 U05 U06 U09 U11 U12 U13 U14 U15 U16 U17 U25".split())
PHYSICAL_ONLY={"U03","U06"}
ORIGINAL_NAMES=(
    "JIT tensor decompression","grammar/n-gram speculative decoding",
    "software NUMA-as-HBM","distributed micro-LoRA gradients",
    "activation/prompt lookup","analog arithmetic in commodity DRAM",
    "hyperdimensional vector binding","fixed reservoir dynamics",
    "fractal-seed arbitrary weight replacement","holographic associative memory",
    "ternary arithmetic kernels","out-of-core parameter streaming",
    "fixed-size KV sketches","procedural synthesis of arbitrary weights",
    "operator fusion","compiled weights in instruction cache",
    "lossless grammar-history collapse","vector symbolic superposition",
    "finite-state/Tsetlin learning","minimum-description-length program search",
    "chaos-seed infinite cognition","low-rank/tensor-train factorization",
    "spectral one-pass language","cellular-automata local learning",
    "Levin-style bounded program search","hyperbolic infinite memory",
    "typed graph rewriting","number-theoretic-transform semantics",
    "topology to semantic prediction","stabilizer quantum simulation"
)
NATIVE_NAMES=(
    "Causal Delta Cognition","Decision-Sufficient Learning",
    "Counterexample-Driven Memory Fusion","Executable Knowledge",
    "Delayed Causal Credit","Structural Transfer Compilation"
)
# Research screening order only: NOT authorization for native model/first use.
NATIVE_PILOT_ORDER=(
    {"claim_id":"AC-D1","lane":"Wingless",
     "decision":"PREPARE_ONLY",
     "critical_test":"Learn dependencies from FIT, charge every causal probe, include hidden interactions and whole-life amortization; preserve zero false skips."},
    {"claim_id":"AC-D5","lane":"Yggdrasil",
     "decision":"PREPARE_ONLY",
     "critical_test":"Compare strictly local action-to-consequence traces with fully fitted EMA/e-prop, quantify message cost, causal confounds, lesions and unfamiliar shift."},
    {"claim_id":"AC-D3","lane":"Wingless/BIO",
     "decision":"PREPARE_ONLY",
     "critical_test":"Require reversible predictive memory, cold persistence and delayed distinctions, with total provenance bytes and equal-byte replay controls."}
)
# Engineering relevance is separate from scientific evidence. No winner is asserted.
SECONDARY_PILOT_FAMILIES=("U07","U08","U10","U18","U22","U24")
NO_NATIVE_SUPERIORITY=True

def load(path,label):
    spec=importlib.util.spec_from_file_location(label,ROOT/path)
    if spec is None or spec.loader is None:
        raise RuntimeError("AC08_IMPORT_MISSING:"+label)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def report():
    ac05=load(Path("research/ac05_sourcefree/learning.py"),"ac08_ac05")
    ac06=load(Path("research/ac06_sourcefree/restricted.py"),"ac08_ac06")
    ac07=load(Path("research/ac07_sourcefree/remaining.py"),"ac08_ac07")
    a=ac05.run()
    b=ac06.run()
    c=ac07.run()
    originals=set("U%02d"%i for i in range(1,31))
    new=set("AC-D%d"%i for i in range(1,7))
    if set(b["experiment_claim_ids"])!=AC06_ORIGINAL:
        raise RuntimeError("AC06_SOURCE_COVERAGE_DRIFT")
    if set(c["restricted_new_original_ids"])!=AC07_ORIGINAL:
        raise RuntimeError("AC07_SOURCE_COVERAGE_DRIFT")
    if set(a["results"])!=new:
        raise RuntimeError("AC05_SOURCE_COVERAGE_DRIFT")
    if AC06_ORIGINAL&AC07_ORIGINAL or AC06_ORIGINAL|AC07_ORIGINAL!=originals:
        raise RuntimeError("DUPLICATE_OR_OMITTED_ORIGINAL")
    if len(ORIGINAL_NAMES)!=30 or len(NATIVE_NAMES)!=6:
        raise RuntimeError("TITLE_REGISTRY_DRIFT")
    if not (
        a["results"]["AC-D1"]["undercovered_fit_unseen_interaction_failure"] and
        a["results"]["AC-D3"]["unobserved_future_error_count"]>0 and
        a["results"]["AC-D5"]["matched_fitted_ema_parity"] and
        a["results"]["AC-D6"]["verified_unfamiliar_transfer"] is False
    ):
        raise RuntimeError("AC05_NEGATIVE_EVIDENCE_MISSING")
    if set(c["physical_substitute_not_physical_result"])!=PHYSICAL_ONLY:
        raise RuntimeError("HARDWARE_BOUNDARY_LOST")
    # Explicitly preserve negative cases from original methods.
    byfamily={v["family"]:v["result"] for v in b["observations"] if v["seed"]==ac06.SEEDS[0]}
    other={v["family"]:v["result"] for v in c["observations"] if v["seed"]==ac07.SEEDS[0]}
    if not (
        byfamily["graph_program"]["unfamiliar_threehop_correct"] is False and
        byfamily["rank_one_factor"]["fullrank_holdout_mse"]>0 and
        other["verified_speculation"]["draft_mismatch"]>0 and
        other["sketch_bounded_search"]["sketch_overcount_key_count"]>0 and
        other["hardware_substitutes"]["physical_claim_tested"] is False
    ):
        raise RuntimeError("ORIGINAL_NEGATIVES_LOST")
    rows=[]
    for n,title in enumerate(ORIGINAL_NAMES,1):
        ident="U%02d"%n
        source="AC06" if ident in AC06_ORIGINAL else "AC07"
        rows.append({
            "claim_id":ident,"title":title,"origin":"original_uploaded_portfolio",
            "measured_by":source,
            "evidence_scope":("SOFTWARE_SUBSTITUTE_NOT_PHYSICAL_PROOF" if ident in PHYSICAL_ONLY
                               else "RESTRICTED_SYNTHETIC_ONLY"),
            "native_learning_superiority_proven":False,
            "candidate_for_secondary_mechanism_study":ident in SECONDARY_PILOT_FAMILIES,
            "science_admitted":False
        })
    for n,title in enumerate(NATIVE_NAMES,1):
        ident="AC-D%d"%n
        rows.append({
            "claim_id":ident,"title":title,"origin":"six_new_hypotheses",
            "measured_by":"AC05",
            "evidence_scope":"SYNTHETIC_DEVELOPMENT_ONLY",
            "native_learning_superiority_proven":False,
            "candidate_for_secondary_mechanism_study":False,
            "science_admitted":False
        })
    if len(rows)!=36 or len({v["claim_id"] for v in rows})!=36:
        raise RuntimeError("PORTFOLIO_ROW_DUPLICATE")
    sourcefree_all=(
        a["scientific_first_use"] is False and
        b["scientific_first_use"] is False and
        c["scientific_first_use"] is False and
        a["accepted_science"] is False and
        b["accepted_science"] is False and
        c["scientific_admission"] is False
    )
    if not sourcefree_all:
        raise RuntimeError("SCIENTIFIC_SOURCE_BARRIER_BROKEN")
    return {
        "schema":"forge.ac08.portfolio-reconciliation.sourcefree.v1",
        "scope":"READ_ONLY_RECONCILIATION_OF_SYNTHETIC_DEVELOPMENT",
        "original_count":30,"native_hypothesis_count":6,
        "unique_claim_count":len(rows),
        "actual_sourcefree_original_ids":sorted(originals),
        "actual_six_native_ids":sorted(new),
        "physical_substitute_only_ids":sorted(PHYSICAL_ONLY),
        "source_evidence_commit_pins":CASE_PINS,
        "stacked_draft_pr_chain":list(PR_CHAIN),
        "overlapping_active_research_priorities_must_continue":True,
        "independent_itd02_consequence_source_verified":False,
        "native_model_learning_superiority_proven":False,
        "scientific_first_use_authorized":False,
        "scientific_admission_authorized":False,
        "model_promotion_authorized":False,
        "controller_or_queue_changed":False,
        "portfolio_rows":rows,
        "conditional_first_native_pilot_questions":list(NATIVE_PILOT_ORDER),
        "secondary_non-admitted_mechanism_ids":list(SECONDARY_PILOT_FAMILIES),
        "evidence_positives_not_claimed_as_science":True,
        "negative_evidence_preserved":True
    }

if __name__=="__main__":
    print(json.dumps(report(),indent=2,sort_keys=True))
