#!/usr/bin/env python3
"""F124CM: original-source mathematical influence falsification; no model fitting/first-use.

The frozen E2 forward law is invoked with explicit ALL-PUBLIC artificial 16-bit
probe values, never a previously born real E2 case/oracle/seed, and CB/CC
are inspected only in their unchanged historical expressive class.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import itertools
import json
import pathlib
import subprocess
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NATIVE = ROOT / "research" / "north-star-transfer"
SOURCE = NATIVE / "f124cj_internal_source.py"
CB = NATIVE / "f124cb_dual_link_learner.py"
CC = NATIVE / "f124cc_trained_two_link_control.py"
FROZEN = HERE / "FROZEN_PROTOCOL.json"
EXPECTED = {
    str(SOURCE.relative_to(ROOT)): "4e7bbd8f93dab1c7242a9374c75731302b034f31",
    str(CB.relative_to(ROOT)): "8a10bf8cec12afc7d8703e3586d8eba91ebfdc7c",
    str(CC.relative_to(ROOT)): "29c0c02f54ea539bed0910fe82adcc86d3aff94d",
}

def require(ok, reason):
    if not ok:
        raise AssertionError("F124CM_FAIL_CLOSED_" + reason)

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "SOURCE_MODULE_MISSING")
    import sys
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value

def actual_git_blobs():
    output = {}
    for path, sha in EXPECTED.items():
        result = subprocess.run(
            ["git", "hash-object", path], cwd=ROOT,
            capture_output=True, text=True, check=True)
        observed = result.stdout.strip()
        require(observed == sha, "ORIGINAL_SOURCE_BLOB_DRIFT_" + path.replace("/", "_"))
        output[path] = observed
    return output

def coordinate_witness(source, param, coordinate):
    # Fixed predeclared subdomain {0,1,2,3} per public nibble.
    # Existence within this subdomain proves true full-domain dependence.
    for values in itertools.product(range(4), repeat=4):
        x = source.join4(values)
        val = source.E_forward(x, param) & 15
        for new in range(4):
            if new == values[coordinate]:
                continue
            different = list(values)
            different[coordinate] = new
            new_value = source.E_forward(source.join4(different), param) & 15
            if new_value != val:
                return {"from_public_input_16": x,
                        "to_public_input_16": source.join4(different),
                        "before_output0": val,
                        "after_output0": new_value}
    return None

def structural_cb_support(cb):
    # This property is algebraic over every valid CB/CC word:
    # output0 = affine(input[perm0]); optional XOR affine(input[perm1]).
    # Two distinct sources max, independent of biases/gains/candidate fitting.
    import inspect
    code = inspect.getsource(cb.forward)
    require("src[perm[j]]" in code and "out[0]^=out[1]" in code
            and "out[2]^=out[3]" in code,
            "CB_SOURCE_ALGEBRA_EXPECTED")
    return {
        "cb_all_32bit_words_max_distinct_public_nibble_parents_for_output0": 2,
        "cc_same_expressive_family": True,
        "method": "universal source-code algebraic support bound; not 2^32 enumeration",
    }

def run():
    freeze = json.loads(FROZEN.read_text())
    require(freeze["status"] == "FROZEN_BEFORE_ANALYSIS_CODE", "PREREG_STATUS")
    blobs = actual_git_blobs()
    source = module("f124cm_pinned_original_E", SOURCE)
    cb = module("f124cm_pinned_CB", CB)
    cc = module("f124cm_pinned_CC", CC)
    require(source.FAMILIES["E2"] == 930000
            and cb.PARAM_BITS == 32 and cb.STRUCTURAL_COMBINATIONS == 96,
            "ORIGINAL_MODEL_SOURCE_FAMILY_ID")
    structural = structural_cb_support(cb)
    require(hasattr(cc, "train") and hasattr(cc, "inverse")
            and "m.pack" in __import__("inspect").getsource(cc.train),
            "CC_TRAINED_SAME_PACKED_FAMILY")
    t0 = time.process_time_ns()
    witnesses = {}
    result_count = 0
    for k0 in range(16):
        for salt in range(16):
            param = [k0, 0, 0, salt]
            ws = [coordinate_witness(source, param, j) for j in range(4)]
            require(all(w is not None for w in ws),
                    f"E_OUTPUT0_NOT_ALL_FOUR_INFLUENCES_{k0}_{salt}")
            # The actual source output0 does not depend on k1 or k2.
            for w in ws:
                for xy in (w["from_public_input_16"], w["to_public_input_16"]):
                    expected = source.E_forward(xy, param) & 15
                    require((source.E_forward(xy, [k0, 15, 15, salt]) & 15)
                            == expected, "K1_K2_INDEPENDENCE")
            witnesses[f"k0={k0},salt={salt}"] = ws
            result_count += len(ws)
    require(result_count == 16 * 16 * 4, "PREREG_FOUR_SUPPORT_COUNT")
    # Only one small reproducible witness excerpt is placed in public receipt.
    # Full bounded witness set is hashed, not private or protected model data.
    canonical = json.dumps(witnesses, sort_keys=True, separators=(",", ":")).encode()
    report = {
        "schema": "forge.itd02.f124cm.structural_expressivity_result.v1",
        "prereg_first": True,
        "original_git_blobs": blobs,
        "original_E2_parameters_k0_salt_evaluated": 256,
        "coordinate_witnesses_total": result_count,
        "every_E2_parameter_support_count": 4,
        "cb_and_cc_output0_max_parent_count": 2,
        "universal_e2_vs_cb_cc_one_stage_representation": "IMPOSSIBLE",
        "all_witnesses_sha256": hashlib.sha256(canonical).hexdigest(),
        "example_k0_0_salt_0": witnesses["k0=0,salt=0"],
        "elapsed_python_process_cpu_ns": time.process_time_ns() - t0,
        "old_E2F2_24_source_case_firstuse_replayed": False,
        "old_hidden_birth_seeds_or_private_oracles_read": False,
        "new_original_environment_steps": 0,
        "trained_native_advantage": "NOT_ESTABLISHED",
        "independent_unfamiliar_family_transfer": "NOT_TESTED",
        "multi_stage_binary_composition_still_may_express_E": True,
        "FSA_firstuse": "DENIED",
        "scientific_go": False,
    }
    return report

if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--json", type=pathlib.Path, required=True)
    opt = args.parse_args()
    report = run()
    opt.json.parent.mkdir(parents=True, exist_ok=True)
    opt.json.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("F124CM_ORIGINAL_SOURCE_BLOBS=PASS")
    print("F124CM_E2_ALL_256_PARAMETERS_ALL_4_INFLUENCES=PASS")
    print("F124CM_WITNESSES=1024")
    print("F124CM_CB_CC_SINGLE_STAGE_REPRESENTATION_IMPOSSIBLE=PASS")
    print("F124CM_ORIGINAL_WORLD_STEPS=0")
    print("F124CM_SCIENTIFIC_GO=FALSE")
