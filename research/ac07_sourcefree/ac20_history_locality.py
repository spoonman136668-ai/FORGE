"""AC-20 read-only locality/identifiability preflight.

This is a source-free mathematical/interface diagnostic. It does NOT run
Causal-Gymnasium, train a native model, evaluate a policy or use held-out data.
The latent variable used in the AFTER-THE-FACT algebraic witness is NEVER an
input to a candidate model or an authorized source interaction.
"""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import subprocess
import sys

import ac19_typed_original_native_bridge as ac19

SCHEMA = "forge.ac20.sourcefree-public-history-locality.v1"
SOURCE_COMMIT = "c94e9a4cd3641588b6b8507e71ccee5c27032bdf"
SOURCE_BLOB = "6af2371dce21804140ea141ccb7be14e003ba275"
NATIVE_COMMIT = "a39171a76d0d7817e3563682bb139a9d7ecf37c4"
NATIVE_BLOB = "68a1423e0bd7206af511212c14b6ce8534154cc2"

def _binary(x, name):
    if type(x) is not int or x not in (0, 1):
        raise ValueError("AC20_INVALID_PUBLIC_" + name)
    return x

def four_public_history_bits(s1, x1, s2, x2):
    """Represent ONLY two previously public observations and chosen actions.

    This layout is a diagnostic, NOT a learned history transport mechanism.
    """
    bits = [0] * 8
    bits[3], bits[4], bits[5], bits[6] = (
        _binary(s1, "S1"), _binary(x1, "X1"),
        _binary(s2, "S2"), _binary(x2, "X2")
    )
    return bits

def decode_four_public_history(bits):
    if (type(bits) is not list or len(bits) != 8 or
        any(type(x) is not int or x not in (0, 1) for x in bits) or
        bits[:3] != [0, 0, 0] or bits[7] != 0):
        raise ValueError("AC20_INVALID_HISTORY_BITS")
    return tuple(bits[3:7])

def source_equation_audit_only(s1, x1, s2, x2, u):
    """Pinned-source terminal equation; ONLY a posthoc mathematical witness.

    Never pass `u`, this function, its output, or its labels to a learner.
    """
    for name, value in (("S1",s1),("X1",x1),("S2",s2),("X2",x2)):
        _binary(value, name)
    if type(u) is not float or not 0 <= u <= 1:
        raise ValueError("AC20_AUDIT_LATENT_OUTSIDE_FIXED_EXAMPLE")
    z = (3*u - 3*s1 - 3*x1 - 3*s1*x1 +
         3*x2 - 3*s2*x2 + 3*x1*x2)
    return int(z > 0)

def _git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args],
                       capture_output=True, text=True, timeout=15)
    if p.returncode:
        raise RuntimeError("AC20_SOURCE_GIT_PIN_FAILED")
    return p.stdout.strip()

def _verify(root, commit, filename, blob):
    root = Path(root).resolve(strict=True)
    if (_git(root, "rev-parse", "HEAD") != commit or
        _git(root, "hash-object", "--", filename) != blob or
        _git(root, "status", "--porcelain", "--untracked-files=no")):
        raise RuntimeError("AC20_ORIGINAL_SOURCE_IDENTITY_OR_CLEANNESS_DRIFT")
    return root

def diagnose(native_root: Path, source_root: Path):
    native_root = _verify(native_root, NATIVE_COMMIT,
                          "yggdrasil/task_runtime.py", NATIVE_BLOB)
    _verify(source_root, SOURCE_COMMIT, "causal_gym/envs/dtr.py", SOURCE_BLOB)
    sys.path.insert(0, str(native_root))
    from yggdrasil.task_runtime import LocalTaskRuntime
    native = LocalTaskRuntime()
    if native.neighbors[4] != (3, 5) or native.neighbors[5] != (4, 6):
        raise RuntimeError("AC20_NATIVE_NEIGHBORHOOD_NOT_ORIGINAL_RING")
    # These are the 16 PUBLIC possible histories, not observed source samples.
    legacy = set()
    site4 = set()
    site5 = set()
    pair = set()
    reward_groups = {}
    for h in product((0, 1), repeat=4):
        s1, x1, s2, x2 = h
        bits = four_public_history_bits(*h)
        if decode_four_public_history(bits) != h:
            raise RuntimeError("AC20_HISTORY_ENCODING_NONINJECTIVE")
        original_ac19 = tuple(ac19.encode_before(1, s2, x2))
        legacy.add(original_ac19)
        f4 = tuple(native.features(bits, 4))
        f5 = tuple(native.features(bits, 5))
        site4.add(f4)
        site5.add(f5)
        pair.add((f4, f5))
        # The latent u=0.5 is used ONLY for diagnostic source-equation
        # collision analysis, and is never exposed to the model or training.
        reward_groups.setdefault((s2,x2), set()).add(
            source_equation_audit_only(*h, 0.5))
    result = {
        "schema": SCHEMA,
        "source_original_commit": SOURCE_COMMIT,
        "source_original_dtr_blob": SOURCE_BLOB,
        "historical_original_ygg_commit": NATIVE_COMMIT,
        "historical_original_runtime_blob": NATIVE_BLOB,
        "public_history_combinations": 16,
        "ac19_terminal_input_unique_patterns": len(legacy),
        "site4_single_hop_distinct_history_features": len(site4),
        "site5_single_hop_distinct_history_features": len(site5),
        "pair_of_original_sites_4_and_5_distinct_history_features": len(pair),
        "original_site5_neighbors": list(native.neighbors[5]),
        "stage1_ac19_observation_action_buckets_with_conflicting_outcomes_at_audit_u_0_5":
            sum(len(v) > 1 for v in reward_groups.values()),
        "posthoc_latent_audit_not_provided_to_any_model": True,
        "two_site_combined_features_are_not_a_trained_native_memory_mechanism": True,
        "native_original_training_events": native.core.events,
        "original_dtr_source_episodes_or_actions_executed": 0,
        "original_dtr_source_imported": False,
        "fit_or_dev_model_training_performed": False,
        "model_directed_action_or_return_measured": False,
        "scientific_first_use": False,
        "scientific_admission": False,
        "owner_controller_queue_or_native_source_modified": False,
    }
    if not (len(legacy) == 4 and len(site4) == 8 and len(site5) == 8 and
            len(pair) == 16 and result[
            "stage1_ac19_observation_action_buckets_with_conflicting_outcomes_at_audit_u_0_5"
            ] == 4 and native.core.events == 0):
        raise RuntimeError("AC20_ORIGINAL_LOCAL_INFORMATION_BOUND_FAILED")
    return result

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = diagnose(a.native, a.source)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("AC20_ORIGINAL_SOURCE_HISTORY_INFORMATION_BOUND=PASS")
    print("AC20_ONE_HOP_SITE5_HISTORY_CONTEXTS=8_OF_16")
    print("AC20_MULTI_CELL_JOINT_INFORMATION_ONLY=16_OF_16_NOT_NATIVE_LEARNING")
    print("AC20_ORIGINAL_SOURCE_EPISODES_EXECUTED=ZERO")
    print("AC20_SCIENTIFIC_ADMISSION=NO")
