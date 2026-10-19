"""F124-BW analytical obstruction in the frozen 32-bit two-shear learner.

Proof (universal, not a statistical experiment):
  For fixed input high byte h, the frozen first stage sets output low to
  lo + m mod 256 or lo XOR m, where m=(gain*h+bias) mod 256 is independent
  of lo. Both are bijections of lo. The second stage does not touch output
  low. BYTE_SWAP returns output low=h regardless of input lo, so two inputs
  with the same h and distinct low bytes are a two-point impossibility
  witness for *every* legal BQ parameter program, without enumerating
  the 2^32-state class or training on any protected data.

Three alternating XOR shears express BYTE_SWAP exactly, independent of
parameters, by algebra: L1=L0 XOR H0; H1=H0 XOR L1=L0;
L2=L1 XOR H1=H0.

The complete 16-bit finite-domain execution below checks the second
statement; the universal claim about BQ is the symbolic invariant above.
No scientific first-use, source generator, existing FIT or holdout called.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MODEL=HERE/"f124bq_program_learner.py"
FROZEN_BLOB="91ad02a4f3893e3537dddc2390666e3c2d2db5d1"
FROZEN_BV_BLOB="5a509951aacb3de7cbec0c0e895d3b9c8ce4dce5"


def need(condition,message):
    if not condition:
        raise RuntimeError("F124BW_FROZEN_MODEL_PROOF_"+message)


def git_blob(path):
    cmd=subprocess.run(
        ["git","rev-parse","HEAD:"+str(path.relative_to(ROOT)).replace("\\","/")],
        cwd=ROOT,capture_output=True,text=True)
    need(cmd.returncode==0,"REPO_OBJECT_UNAVAILABLE")
    return cmd.stdout.strip()


def frozen_model():
    need(git_blob(MODEL)==FROZEN_BLOB,"LEARNED_PROGRAM_DRIFT")
    need(git_blob(HERE/"f124bv-frozen-independent-science.json")==
         FROZEN_BV_BLOB,"PROTECTED_BV_ADMISSION_DRIFT")
    spec=importlib.util.spec_from_file_location("f124bw_original_BQ",MODEL)
    need(spec is not None and spec.loader is not None,"MODEL_IMPORT")
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    need(obj.STATE_BITS==32 and obj.MAX_PROGRAMS==16
         and obj.ODD_GAINS==tuple(range(1,128,2)),
         "ORIGINAL_32_BIT_HYPOTHESIS_DRIFT")
    return obj


def byte_swap(x):
    need(type(x) is int and 0<=x<=65535,"SWAP_DOMAIN")
    return ((x&255)<<8)|(x>>8)


def three_shear_xor(x):
    need(type(x) is int and 0<=x<=65535,"SHEAR_DOMAIN")
    lo,hi=x&255,x>>8
    lo^=hi
    hi^=lo
    lo^=hi
    return lo|(hi<<8)


def closed_form_first_low(low,high,parameter):
    need(type(low) is int and type(high) is int
         and 0<=low<256 and 0<=high<256,"BYTE_DOMAIN")
    a,b,_,_,mode1,_=parameter
    mix=(a*high+b)&255
    return (low+mix)&255 if mode1==0 else low^mix


def invariant_for_all_programs():
    """Return proof obligations, not a misleading 2^32 enumeration.

    For any a,b,h in allowed domains, m=(a*h+b)&255 is fixed as low varies.
    Addition by constant m in Z/256 and XOR by m in (Z/2)^8 are bijections;
    cancellation yields ylow0 != ylow1 for low0 != low1. Since the second
    high-byte stage never writes low, result holds for all 32-bit states.
    """
    return {
      "all_possible_model_states_analytically_covered":True,
      "source_formula_bound_by_original_git_blob":FROZEN_BLOB,
      "conditional_low_transform_is_permutation":True,
      "conditional_low_injectivity_uses_addition_or_xor_cancellation":True,
      "second_high_stage_never_updates_low":True,
      "byteswap_conditional_low_output_is_constant":True,
      "two_input_contradiction_for_all_BQ_programs":True,
      "claim_no_model_can_exactly_represent_three_shear_swap":True,
      "proof_is_symbolic_not_parameter_enumeration":True,
      "success_on_novel_relationships_observed":False,
    }


def audit():
    m=frozen_model()
    # Exhaustive check is for one canonical mathematical comparator, not
    # for parameter-class generalization, and uses no original source data.
    count=sum(three_shear_xor(x)==byte_swap(x) for x in range(65536))
    need(count==65536,"THREE_SHEARS_ARE_NOT_FULL_BYTE_SWAP")
    h=0x35
    x0=h<<8
    x1=(h<<8)|1
    need(x0!=x1 and byte_swap(x0)&255==byte_swap(x1)&255==h,
         "TWO_POINT_COUNTEREXAMPLE")
    # Spot-check source binding and injectivity on mixed modes/gains/biases.
    # These checks do not substitute for the symbolic universal reasoning.
    tested=0
    for p in ((1,0,1,0,0,0),(1,0,1,0,1,1),
              (53,37,41,19,0,1),(87,109,9,173,1,0),
              (127,255,127,255,1,1)):
        for high in (0,1,53,127,255):
            xs=[(high<<8)|lo for lo in range(256)]
            lows=[m.forward(x,p)&255 for x in xs]
            need(len(set(lows))==256,"LOW_OUTPUT_NOT_BIJECTIVE")
            need(all(lows[i]==closed_form_first_low(i,high,p)
                     for i in range(256)),"FROZEN_PROGRAM_FIRST_STAGE_MISMATCH")
            tested+=256
        need((m.forward(x0,p)&255)!=(m.forward(x1,p)&255),
             "IMPOSSIBILITY_WITNESS_INVALID")
    theorem=invariant_for_all_programs()
    result={
       "schema":"mass.f124bw.frozen-BQ-expressivity-two-point-theorem.v1",
       "frozen_original_BQ_model_Git_blob":FROZEN_BLOB,
       "frozen_BV_source_admission_Git_blob":FROZEN_BV_BLOB,
       "model_state_bits_unchanged":m.STATE_BITS,
       "three_XOR_shear_byteswap_domain_count":count,
       "fixed_input_high_for_witness":h,
       "two_distinct_input_witnesses":[x0,x1],
       "same_swap_low_output":h,
       "source_code_boundary_injective_checks":tested,
       "universal_analytical_invariant":theorem,
       "old_registered_scientific_source_used":False,
       "new_development_924000_or_925000_cases_born":False,
       "protected_128_case_cohorts_used":False,
       "new_model_implemented_or_fit":False,
       "scientific_transfer_accepted":False,
       "optimizer_policy_promoted":False,
       "disposition":"STRUCTURAL_MODEL_CLASS_NONEXPRESSIVITY_PROVED_NO_SCIENCE_FIRSTUSE"
    }
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=audit()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    print("F124BW_ORIGINAL_32_BIT_BQ_SOURCE_PINNED=PASS")
    print("F124BW_THREE_SHEARS_BYTESWAP_FULL_DOMAIN=65536/65536")
    print("F124BW_TWO_POINT_EXACT_STRUCTURAL_OBSTRUCTION=PASS")
    print("F124BW_PROSPECTIVE_SCIENTIFIC_CASES_USED=0")
    print("F124BW_SCIENTIFIC_ADMISSION=false")


if __name__=="__main__":
    main()
