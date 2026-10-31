"""ACC-146 pinned-runtime FIT-only numerical provenance probe.

Reads only the three already-consumed SHA-pinned C35/C37 ZIP archives.
Reconstructs the unchanged ACC-145 C36 fit under the CURRENT interpreter,
captures the actual numpy.linalg.solve input and IEEE-754 output, and
reports the numerical backend identity. It never imports or steps MiniGrid.
It never changes the native policy, scientific thresholds, or source rights.

For owner qualification, run this in the original Python 3.11 / NumPy 1.26.4
environment TWICE in separate clean processes on the SAME immutable archives.
This script's own source-only execution is not original-owner acceptance.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import platform
import struct
from pathlib import Path
import numpy as np
from research.acc145_c37_archive_fit import (
    ZIP_SHA, SHA_FIRST, SHA_SECOND, canonical, fetch, reconstruct, sha256,
)

def capture_model(c35):
    captured = {}
    original = np.linalg.solve
    def witness(matrix, rhs):
        solution = original(matrix, rhs)
        if captured:
            raise AssertionError("UNEXPECTED_EXTRA_LINEAR_SOLVE")
        captured["matrix"] = np.array(matrix, copy=True)
        captured["rhs"] = np.array(rhs, copy=True)
        captured["ridge"] = np.array(solution, copy=True)
        return solution
    np.linalg.solve = witness
    try:
        fitted = reconstruct(c35)
    finally:
        np.linalg.solve = original
    if set(captured) != {"matrix", "rhs", "ridge"}:
        raise AssertionError("NO_NUMPY_SOLVE_CAPTURED")
    return fitted, captured

def software_identity():
    config = io.StringIO()
    with contextlib.redirect_stdout(config):
        np.show_config()
    try:
        from threadpoolctl import threadpool_info
        threads = threadpool_info()
    except ImportError:
        threads = "UNAVAILABLE_NO_THREADPOOLCTL"
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "machine": platform.machine(),
        "processor": platform.processor(),
        "os": platform.system(),
        "openblas_threads_env": os.getenv("OPENBLAS_NUM_THREADS"),
        "pythonhashseed_env": os.getenv("PYTHONHASHSEED"),
        "numpy_config_sha256": sha256(config.getvalue().encode()),
        "numpy_config": config.getvalue(),
        "threadpool_info": threads,
    }

def run(fit, first, second):
    c35 = fetch(fit, "fit")
    a = fetch(first, "first")
    b = fetch(second, "second")
    if a["original_FIT_model_sha256"] != SHA_FIRST or b["original_FIT_model_sha256"] != SHA_SECOND:
        raise AssertionError("ORIGINAL_MODEL_SHA_MISMATCH")
    if a["precommitted_protocol_sha256"] != b["precommitted_protocol_sha256"]:
        raise AssertionError("PREREG_DRIFT")
    if a["FIT_trained_two_action_original_forks"] != 93 or b["FIT_trained_two_action_original_forks"] != 93:
        raise AssertionError("FROZEN_OPTION_COUNT_DRIFT")
    if a["criteria"] != b["criteria"] or a["factorial_source_actor_summaries"] != b["factorial_source_actor_summaries"]:
        raise AssertionError("ORIGINAL_SCIENCE_DRIFT")
    fitted, data = capture_model(c35)
    x, y, coefficients = data["matrix"], data["rhs"], data["ridge"]
    if x.shape != (14, 14) or y.shape != (14,) or coefficients.shape != (14,):
        raise AssertionError("RIDGE_SHAPE_DRIFT")
    ieee = b"".join(struct.pack("<d", float(c)) for c in coefficients)
    equations = x.astype("<f8").tobytes(order="C") + y.astype("<f8").tobytes(order="C")
    return {
        "schema": "forge.acc146.c37.pinned-runtime-FIT-only-numerical-probe.v1",
        "source": "C35 previously consumed original FIT, C37 previously consumed source reports",
        "immutable_archives": ZIP_SHA,
        "original_models": {"first": SHA_FIRST, "second": SHA_SECOND},
        "original_model_lengths_bytes": {"first": 1740, "second": 1743},
        "original_results_unmodified": True,
        "fit_only": fitted,
        "matches_original_first": fitted["model_sha256"] == SHA_FIRST and fitted["model_serialized_bytes"] == 1740,
        "matches_original_second": fitted["model_sha256"] == SHA_SECOND and fitted["model_serialized_bytes"] == 1743,
        "normal_equations_ieee754_sha256": sha256(equations),
        "ridge_ieee754_sha256": sha256(ieee),
        "ridge_coefficient_hex": [float(c).hex() for c in coefficients],
        "software_identity": software_identity(),
        "limitations": [
            "No original-world action, reset, replay or heldout read for training",
            "The original archives do not store the full first-run ridge vector",
            "A matching model digest is one-environment reconstruction, not cross-environment determinism",
            "Floating-point backend/root cause remains unresolved without qualified pinned owner runs",
            "No science acceptance or model promotion, owner source patch, queue or workflow dispatch",
        ],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fit", type=Path, required=True)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("REFUSE_OVERWRITE_EXACT_EVIDENCE_RECEIPT")
    report = run(args.fit, args.first, args.second)
    output = json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    args.out.write_bytes(output)
    print("ACC146_SOURCE_ONLY_CUSTODY=PASS")
    print("ACC146_FITTED_MODEL_SHA256=" + report["fit_only"]["model_sha256"])
    print("ACC146_REPORT_SHA256=" + sha256(output))
    print("ACC146_ORIGINAL_WORLD_ACTIONS=ZERO")

if __name__ == "__main__":
    main()
