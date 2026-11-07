"""RSI-R5 read-only same-budget proposal-selection A/B development measurement.

No owner integration, candidate execution, original source writes, scientific
first use or training. Only the success-count certificate is ablated for A.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from f139 import nci04_model_free_search as search
from f139 import nci04_prompt_program as prompt
from f139.nci04_genenv_source import source_for_vector
from f139.nci04_native_contract import digest

SCHEMA = "forge.f139.rsi-r5.diversity-impact-dev.v1"
PARENT = "3e83e0ddba0aedd397298a07ef53d1bc6bf301b3"
PROPOSER_BLOB = "7d5a1ebe8860f6ae69dff612cbe8fceb4d3d851c"
FIXTURE_BLOB = "f2fda603fbed965a3b4e7cc28844b2246bf8ac2b"
SPEC = Path(__file__).with_name("fixtures") / "model_free_yggdrasil_992ef.py"
CODE = Path(__file__).with_name("nci04_prompt_program.py")
SCENARIOS = ("legacy_only", "p838_history", "p838_p843_history")
ARMS = ("ablation", "qualified")
HISTORICAL = {
    838: ("rate mul add success success mul success total "
          "add add total zero add zero zero"),
    843: ("rate max mul success success mul success total "
          "add add total zero add zero zero"),
}
ABBA = ("ablation", "qualified", "qualified", "ablation")
TIMEOUT_SECONDS = 20


def need(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError("R5_DIVERSITY_" + code)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def read_pinned(path: Path, expected_blob: str) -> bytes:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    need(git_blob(data) == expected_blob, "PINNED_SOURCE_DRIFT")
    return data


def scenario_source(scenario: str) -> tuple[bytes, ...]:
    need(scenario in SCENARIOS, "SCENARIO_UNAUTHORIZED")
    before = read_pinned(SPEC, FIXTURE_BLOB)
    legacy = tuple(source_for_vector(before, v)[0]
                   for v in itertools.product((0, 1), repeat=3) if any(v))
    chosen = (() if scenario == "legacy_only" else
              (838,) if scenario == "p838_history" else (838, 843))
    history = legacy + tuple(
        prompt.source_for_program(before, HISTORICAL[n]) for n in chosen)
    need(len(legacy) == 7 and len(history) == len(legacy)+len(chosen)
         and len({digest(x) for x in history}) == len(history),
         "HISTORICAL_SOURCE_IDENTITY")
    for n in chosen:
        raw = prompt.source_for_program(before, HISTORICAL[n])
        need(prompt.recover_program(before, raw) == HISTORICAL[n]
             and prompt.public_success_count_order(HISTORICAL[n]),
             "HISTORICAL_PROGRAM_UNVERIFIED")
    return history


def arm_run(scenario: str, arm: str) -> dict:
    need(arm in ARMS, "ARM_UNAUTHORIZED")
    read_pinned(CODE, PROPOSER_BLOB)
    before = read_pinned(SPEC, FIXTURE_BLOB)
    history = scenario_source(scenario)
    known = {digest(x) for x in history}
    cert = prompt.public_success_count_order
    start_cpu = time.process_time()
    start_wall = time.perf_counter()
    # The *only* removed feature is #1549's certificate. All proposal grammar,
    # preflight, source synthesis, history and population budgets remain exact.
    with patch.object(prompt, "public_success_count_order",
                      (lambda _program: False) if arm == "ablation" else cert):
        p = prompt.build_plan(
            before,
            history_sources=history,
            consumed_sha256=set(known),
            historical_ast_sha256={search.normalized(x) for x in history},
            history_sha256="a"*64,
            mechanism_sha256="b"*64,
            max_candidates=16,
            eligible_parent_sha256=set(),
        )
    selection_cpu = time.process_time() - start_cpu
    selection_wall = time.perf_counter() - start_wall
    need(p is not None and 0 < len(p.bindings) <= 16
         and len(p.frozen["operations"]) == len(p.bindings),
         "BUDGET_OR_BATCH_INVALID")
    hashes = [b.source.after_sha256 for b in p.bindings]
    need(len(set(hashes)) == len(hashes)
         and not set(hashes).intersection(known),
         "DUPLICATED_SOURCE_IDENTITY")
    programs = [prompt.recover_program(before, b.source.after)
                for b in p.bindings]
    need(all(x is not None for x in programs),
         "UNRECOVERABLE_GENERATED_SOURCE")
    qualified_class = sum(1 for program in programs if cert(program))
    # This is source provenance, not independent acceptance or RSI.
    result = {
        "schema": SCHEMA, "origin": PARENT,
        "proposer_git_blob": PROPOSER_BLOB,
        "fixture_git_blob": FIXTURE_BLOB,
        "scenario": scenario, "arm": arm,
        "history_count": len(history),
        "batch_count": len(hashes),
        "raw_unique": len(set(hashes)),
        "proven_success_count_class": qualified_class,
        "candidate_identities": hashes,
        "selection_cpu_seconds": round(selection_cpu, 6),
        "selection_wall_seconds": round(selection_wall, 6),
        "owner_executed": False, "independent_qualification": False,
        "scientific_pass": False, "rsi_proven": False,
    }
    try:
        import resource
        result["process_peak_rss_bytes"] = (
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            * (1 if sys.platform == "darwin" else 1024))
    except ImportError:
        result["process_peak_rss_bytes"] = "UNVERIFIED"
    return result


def measure() -> dict:
    receipt = {"schema": SCHEMA, "origin": PARENT,
               "proposer_git_blob": PROPOSER_BLOB,
               "fixture_git_blob": FIXTURE_BLOB, "cases": []}
    env = {k:v for k,v in os.environ.items()
           if not any(s in k.upper() for s in
                      ("TOKEN", "PASSWORD", "SECRET", "API_KEY", "CREDENTIAL"))}
    for scenario in SCENARIOS:
        observations = []
        for arm in ABBA:
            started = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "f139.rsi_r5_diversity_impact",
                 "--arm", arm, "--scenario", scenario],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, timeout=TIMEOUT_SECONDS,
                env=env, cwd=Path(__file__).resolve().parents[1])
            whole = time.perf_counter()-started
            need(proc.returncode == 0, "REPLAY_FAILED_" +
                 scenario + "_" + arm + "_EXIT_" + str(proc.returncode)
                 + "_STDERR_" + proc.stderr[-500:].decode("utf8", "replace"))
            result = json.loads(proc.stdout)
            need(result["arm"] == arm
                 and result["scenario"] == scenario
                 and result["origin"] == PARENT
                 and 0 < result["batch_count"] <= 16,
                 "RECEIPT_DRIFT")
            result["whole_child_wall_seconds"] = round(whole, 6)
            observations.append(result)
        a, b, b2, a2 = observations
        need(a["candidate_identities"] == a2["candidate_identities"]
             and b["candidate_identities"] == b2["candidate_identities"],
             "NONDETERMINISTIC_REPLAY")
        need(b["proven_success_count_class"] <=
             a["proven_success_count_class"],
             "NEW_FILTER_ADDED_KNOWN_DUPLICATE")
        receipt["cases"].append({
            "scenario": scenario,
            "baseline_proven": a["proven_success_count_class"],
            "qualified_proven": b["proven_success_count_class"],
            "baseline_selected": a["batch_count"],
            "qualified_selected": b["batch_count"],
            "functional_bounded": (b["batch_count"] >= a["batch_count"]
                                   and (scenario == "legacy_only" or
                                   b["proven_success_count_class"] == 0)),
            "new_source_sha256": hashlib.sha256(
                "".join(b["candidate_identities"]).encode()).hexdigest(),
            "overlap_source_ids": len(set(a["candidate_identities"]).intersection(
                b["candidate_identities"])),
            "ABBA": [
                {"arm": v["arm"], "cpu_seconds": v["selection_cpu_seconds"],
                 "selection_wall_seconds": v["selection_wall_seconds"],
                 "whole_child_wall_seconds": v["whole_child_wall_seconds"],
                 "process_peak_rss_bytes": v["process_peak_rss_bytes"]}
                for v in observations],
            "paired_whole_wall_speedup_A_over_B": [
                round(a["whole_child_wall_seconds"] /
                      b["whole_child_wall_seconds"], 6),
                round(a2["whole_child_wall_seconds"] /
                      b2["whole_child_wall_seconds"], 6)],
        })
    receipt["development_disposition"] = (
        "MEASURED_PROVEN_DUPLICATE_REDUCTION"
        if any(c["baseline_proven"] > c["qualified_proven"]
               for c in receipt["cases"] if c["scenario"] != "legacy_only")
           and all(c["functional_bounded"] for c in receipt["cases"])
        else "R5_DUPLICATE_SELECTION_NO_GO")
    receipt.update(owner_executed=False, scientific_pass=False, rsi_proven=False)
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "--arm" or sys.argv[3] != "--scenario":
        raise SystemExit("R5_FIXED_ARM_SCENARIO_REQUIRED")
    print(json.dumps(arm_run(sys.argv[4], sys.argv[2]),
                     sort_keys=True, separators=(",", ":")))
