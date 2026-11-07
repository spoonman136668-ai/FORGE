"""Bounded RSI-R3 development measurement on authentic FORGE source, not RSI proof."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import time
import tracemalloc
import types

from f139.rsi_r3_source_cycle import generate, fingerprint, source_for, verify

TARGET = "f139/nci04_portfolio_source_boundary.py"
BLOB = "8bb13f14f6039032cde4aca623a38713ea47b4e9"
CACHE = (None, 32, 128, 512)
MIN_GAIN = 1.10
ROUNDS = 7


class RealRSIDenied(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise RealRSIDenied("R3_REAL_" + why)


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def variant(original, operator):
    need(type(original) is bytes and blob(original) == BLOB, "TARGET_DRIFT")
    need(type(operator) is int and operator in range(4), "OPERATOR_UNTRUSTED")
    if not operator:
        return original
    txt = original.decode("utf-8", "strict")
    header = "def _ast_identity(raw: bytes) -> str:\n"
    need(txt.count(header) == txt.count("import hashlib\n") == 1,
         "SOURCE_ANCHOR_DRIFT")
    txt = txt.replace("import hashlib\n", "import hashlib\nfrom functools import lru_cache\n", 1)
    txt = txt.replace(header, f"@lru_cache(maxsize={CACHE[operator]})\n" + header, 1)
    compile(txt, TARGET, "exec")
    return txt.encode()


def reader(source, operator):
    # Only the exact authenticated module or a fixed reviewed decorator can run.
    name = "_forge_r3_source_operator_" + str(operator)
    module = types.ModuleType(name)
    module.__package__ = "f139"
    sys.modules[name] = module
    try:
        exec(compile(source, TARGET, "exec"), module.__dict__)
        return module._ast_identity
    finally:
        sys.modules.pop(name, None)


def cohorts(root):
    root = Path(root).resolve(strict=True)
    original = (root / TARGET).read_bytes().replace(b"\r\n", b"\n")
    need(blob(original) == BLOB, "SOURCE_PREIMAGE_DRIFT")
    groups = {"train": [], "validation": [], "holdout": []}
    for path in sorted((root / "f139").glob("*.py")):
        if (path.is_symlink() or path.name in {"rsi_r3_real_workload.py",
                "test_rsi_r3_real_workload.py"} or not path.is_file()):
            continue
        if not 0 < path.stat().st_size <= 65536:
            continue
        rel = path.relative_to(root).as_posix()
        value = path.read_bytes().replace(b"\r\n", b"\n")
        k = int(hashlib.sha256(rel.encode()).hexdigest()[:8], 16) % 10
        group = "train" if k < 6 else "validation" if k < 8 else "holdout"
        groups[group].append((rel, value))
    for name, values in groups.items():
        groups[name] = tuple(sorted(values, key=lambda v: hashlib.sha256(v[0].encode()).hexdigest())[:120])
        need(len(groups[name]) >= 8, "REAL_COHORT_TOO_SMALL")
    names = [name for group in groups.values() for name, _ in group]
    need(len(names) == len(set(names)), "COHORT_LEAKAGE")
    return original, groups


def measure(original, op, rows):
    oracle = reader(variant(original, 0), 0)
    expected = tuple(oracle(raw) for _, raw in rows)
    tracemalloc.start()
    t0, w0 = time.process_time(), time.perf_counter()
    source = variant(original, op)
    fn = reader(source, op)
    for _ in range(ROUNDS):
        for (_, raw), correct in zip(rows, expected):
            need(fn(raw) == correct, "REAL_AST_PARITY")
    cpu, wall = time.process_time()-t0, time.perf_counter()-w0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return dict(operator=op, cpu=cpu, wall=wall, peak_bytes=peak,
                correct=len(rows)*ROUNDS, source_sha256=fingerprint(source))


def feedback(measured):
    # The first metric is measured source-validation throughput, not a fixed
    # correctness tie or manually selected G1; only TRAIN/VALIDATION enter.
    return tuple((m["operator"], (
        max(1, min(10000, round(0.1*m["correct"]/max(m["cpu"], 1e-9)))),
        min(9999, round(m["cpu"]*1000)), m["correct"], m["correct"]))
        for m in measured)


def run(root):
    """Actual-source development evaluation. No scientific/owner authority."""
    original, groups = cohorts(root)
    first_fit = [measure(original, n, groups["train"]) for n in (1, 2, 3)]
    g1 = generate(parent_source=source_for(0), generation=1,
                  feedback=feedback(first_fit), used_operators=frozenset({0}))
    second_fit = [measure(original, n, groups["validation"])
                  for n in (1, 2, 3) if n != g1.operator]
    g2 = generate(parent_source=g1.source, generation=2,
                  feedback=feedback(second_fit), used_operators=frozenset({0, g1.operator}))
    need(verify((g1, g2)), "PARENT_SOURCE_LINEAGE")
    trials = []
    for ordering in ((0, 1, 2, 3), (3, 2, 1, 0)):
        measured = {n: measure(original, n, groups["holdout"]) for n in ordering}
        strongest = min(measured[0]["cpu"], measured[2]["cpu"])
        a, b = measured[g1.operator], measured[g2.operator]
        trials.append(dict(results=list(measured.values()),
            g1_cpu_ratio=strongest / max(a["cpu"], 1e-9),
            g2_cpu_ratio=a["cpu"] / max(b["cpu"], 1e-9),
            g1_wall_ratio=min(measured[0]["wall"], measured[2]["wall"]) / max(a["wall"], 1e-9),
            g2_wall_ratio=a["wall"] / max(b["wall"], 1e-9)))
    passed = all(t[k] >= MIN_GAIN for t in trials for k in (
        "g1_cpu_ratio", "g2_cpu_ratio", "g1_wall_ratio", "g2_wall_ratio"))
    passed = passed and all(m["peak_bytes"] <= 64*1024*1024
                            for t in trials for m in t["results"])
    return dict(schema="forge.rsi-r3.real-source-workload-development.v1",
        baseline_blob=BLOB, generation_1=g1.operator, generation_2=g2.operator,
        lineage=(g1.source_sha256, g2.source_sha256),
        actual_module_sha256=(fingerprint(variant(original, g1.operator)),
                              fingerprint(variant(original, g2.operator))),
        cohort_sizes={name: len(rows) for name, rows in groups.items()},
        cohort_sha256={name: fingerprint(json.dumps([(n, fingerprint(r)) for n, r in rows],
                            sort_keys=True).encode()) for name, rows in groups.items()},
        trials=trials, frozen_development_target_met=passed,
        classification="DEV_PASS_PENDING_FULL_QUALIFICATION" if passed else "RSI_R3_DEV_NO_GO",
        full_g1_g2_regression_qualified=False, whole_process_cost_qualified=False,
        original_owner_autonomous=False, scientific_first_use=False,
        scientific_accepted=False, rsi_proven=False, owner_mutations=0)
