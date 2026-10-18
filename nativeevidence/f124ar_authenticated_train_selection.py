"""F124-AR authenticated prospective TRAIN-only comparison and disposition.

This file alone touches fresh TRAIN source/evaluator identities. Learners are
given ONLY public supports or normalized graphs, never source operators,
true inverse, pair labels (except TRAIN-only global Wingless calibration),
or prospective DEV. Keep negative outcomes and full nonfinalist grid.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import sys
import time
import tracemalloc
from pathlib import Path

import f124ar_train_source as source
import f124ar_cross_task_relations as new_y
import f124ar_packed_causal_calibration as new_w
import f124aq_train_selection as earlier
import f124aq_sparse_composition as prior_aq_y
import f124ap_dual_kernel_learner as prior_ap_y
import f124ao_public_relation_learner as prior_ao_y
import f124ag_transition_models as prior_ag
import f124am_terminal_competition as original_w
import f124al_packed_confidence as prior_al_w
import f124q_independent_binding as key
import f124aj_example_operator_learner as public

SCHEMA = "forge.research.f124ar.first-original-train-meta-relations.v1"
AQ_TRAIN_SHA = "d3a3935cc58d0fe69f46a496ae130a434360bee4169dc22bdad72385af3aa5b0"
AQ_DEV_SHA = "0f7a75905ba68851819e10a5e2c308f3955daa84eec0a1fa0184d1b392f2746b"

def need(ok, tag):
    source.need(ok, "AUTHENTIC_TRAIN_" + tag)

def authenticated_parent(o, t, an, ao, ap, aq, aqdev):
    source.frozen()
    base, delta = earlier.ancestry(o, t, an, ao, ap)
    for path, expected, label in (
        (aq, AQ_TRAIN_SHA, "AQ_RAW_TRAIN"),
        (aqdev, AQ_DEV_SHA, "AQ_ORIGINAL_FIRST_DEV")
    ):
        need(hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected,
             label)
    train = json.loads(Path(aq).read_bytes())
    dev = json.loads(Path(aqdev).read_bytes())
    need(train["schema"] == earlier.SCHEMA and
         train["freeze_blob"] == earlier.source.FREEZE_BLOB and
         train["DEV_cases_generated"] == 0 and
         train["DEV_consumed"] is False and
         train["selected"]["Yggdrasil"]["paired"] == 0 and
         train["selected"]["Wingless"]["paired"] == 39 and
         dev["schema"] ==
         "forge.research.f124aq.verified-single-wing-first-dev-evidence.v1" and
         dev["mode"] == "dev" and
         dev["Wingless"]["models"]["AQ_selected"]["paired"] == 33 and
         dev["Wingless"]["models"]["original_gamma0"]["paired"] == 33 and
         dev["Wingless"]["models"]["AQ_selected"]["FP"] == 13 and
         dev["Wingless"]["strict_scientific_candidate_win"] is False and
         not dev["Yggdrasil"]["DEV_consumed"] and
         not dev["independent_science_acceptance"] and
         not dev["optimizer_promotion"], "AUTHENTIC_PARENT_NEGATIVES")
    for lane in ("Yggdrasil", "Wingless"):
        need(train["original_model_identity"][lane]["base_sha256"] ==
             key.digest(base[lane]) and
             train["original_model_identity"][lane]["delta_sha256"] ==
             key.digest(delta[lane]), "FROZEN_MODEL_IDENTITY")
    return base, delta

def source_inventory(rows):
    truth = earlier.source.parent.parent.parent.am.old.prior.parent.original.parent.prior.parent.routes15
    pos_truth = neg_truth = corrupted = no_literal = 0
    fams = {family: 0 for family in source.FAMILIES}
    for seed, vec, family, op, nonce, p, n in rows:
        a = source.plain(p, op, nonce)
        b = source.plain(n, op, nonce)
        pos_truth += int(truth(a, relaxed=family == "rotate4_tolerant") == 1)
        neg_truth += int(truth(b, relaxed=family == "rotate4_tolerant") == 0)
        corrupted += int(sum(
            source.relation(d["input_bits"], op) != d["output_bits"]
            for d in p["demos"]) == 3)
        no_literal += int(truth(
            {k: p[k] for k in ("start", "target", "roles", "edges")},
            relaxed=True) > 0)
        fams[family] += 1
        need(p["demos"] == n["demos"], "MATCHED_PAIR_SUPPORT")
    need(len(rows) == 48 and pos_truth == 48 and neg_truth == 48 and
         corrupted == 48 and no_literal == 0 and
         all(v == 12 for v in fams.values()), "ORIGINAL_GRAPH_TRUTH")
    return {"pairs": 48, "positive_truth": pos_truth,
            "negative_truth": neg_truth, "three_corrupted": corrupted,
            "old_literal_shortcuts": no_literal, "families": fams}

def meter(fn):
    """Whole arm, same-host timing + traced Python heap; OS peak cumulative."""
    tracemalloc.start()
    t = time.perf_counter_ns()
    cpu = time.process_time_ns()
    result = fn()
    elapsed = time.perf_counter_ns() - t
    cpu_ns = time.process_time_ns() - cpu
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return result, {"model_and_eval_wall_ns": elapsed,
                    "model_and_eval_cpu_ns": cpu_ns,
                    "python_traced_peak_bytes": peak,
                    "OS_peak_RSS_per_arm_independently_attributed": False}

def process_rss():
    if os.name != "nt":
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
            1024 if platform.system() == "Linux" else 1)
    # Windows PROCESS_MEMORY_COUNTERS: use 64-bit PEAK_WORKING_SET, no
    # misleading process commit/RSS equivalence across operating systems.
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    value = Counters()
    value.cb = ctypes.sizeof(value)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    if not psapi.GetProcessMemoryInfo(process, ctypes.byref(value), value.cb):
        raise OSError("Windows resource witness unavailable")
    return int(value.PeakWorkingSetSize)

def blanks():
    return {"pairs": 0, "paired": 0, "FP": 0, "FN": 0,
            "accepted_long_ids": [], "case_hashes": [],
            "max_active": 0, "max_retained": 0,
            "max_states_per_node": 0, "max_packed_bits_per_state": 0,
            "extra_hop_ops": 0, "model_parameter_storage_lower": 0}

def tally(result, identity, family, roles, positive_score,
          negative_score, workp, workn, memory_lower=0):
    a, b = positive_score >= 0, negative_score >= 0
    result["pairs"] += 1
    result["paired"] += int(a and not b)
    result["FP"] += int(b)
    result["FN"] += int(not a)
    if len(roles) >= 13 and a:
        result["accepted_long_ids"].append(identity)
    result["case_hashes"].append(key.digest([identity, family, a, b]))
    result["model_parameter_storage_lower"] = max(
        memory_lower, result["model_parameter_storage_lower"])
    for work in (workp, workn):
        if work:
            result["max_active"] = max(
                result["max_active"], work.get("max_active", 0))
            result["max_retained"] = max(
                result["max_retained"], work.get("max_retained", 0))
            result["max_states_per_node"] = max(
                result["max_states_per_node"],
                work.get("max_states_per_node", 0))
            result["max_packed_bits_per_state"] = max(
                result["max_packed_bits_per_state"],
                work.get("max_packed_bits_per_state", 0))
            result["extra_hop_ops"] += work.get("extra_hop_evidence_ops", 0)

def ygg_evaluate(rows, base, delta, mode, width):
    supports = [p["demos"] for _, _, _, _, _, p, _ in rows]
    model = new_y.train_shared(supports, mode, width)
    result = blanks()
    cost = {"total_declared_inference_lower": 0, "abstained_graphs": 0,
            "shared_training_operations_upper": model["training_operations_upper"],
            "train_public_tasks": model["train_public_tasks"],
            "shared_parameters": model["shared_parameters"],
            "shared_parameter_bytes_lower": model["shared_float_storage_bytes_lower"],
            "extra_model_memory_disclosed": True}
    for seed, vec, family, op, nonce, pos, neg in rows:
        a, wa, da = new_y.ygg(pos, base, delta, model)
        b, wb, db = new_y.ygg(neg, base, delta, model)
        tally(result, key.digest([seed, list(vec), family]),
              family, pos["roles"], a, b, wa, wb,
              model["shared_float_storage_bytes_lower"])
        for obs in (da, db):
            cost["abstained_graphs"] += int(obs["abstained"])
            cost["total_declared_inference_lower"] += (
                obs["estimated_inference_mul_add_lower"])
            need(obs["source_oracle_used"] is False and
                 obs["operator_catalog_known"] is False and
                 obs["extra_task_working_storage_disclosed"] and
                 obs["max_original_cognitive_cells"] == 16,
                 "MODEL_CUSTODY_AND_MEMORY")
        need(result["max_active"] <= 7 and result["max_retained"] <= 9,
             "ORIGINAL_7_PLUS_9")
    return {**result, **cost, "mode": mode, "width": width}

def old_ygg(rows, base, delta, name):
    row = blanks()
    for seed, vec, fam, op, nonce, p, n in rows:
        if name == "AQ_sparse":
            f = lambda g: prior_aq_y.ygg(
                g, base, delta, "sparse_xor_basis", 2, 12)
        elif name == "AP_kernel":
            f = lambda g: prior_ap_y.ygg(
                g, base, delta, "dual_linear_kernel_ridge", 1., 4, 0.)
        elif name == "AO_neighbor":
            f = lambda g: prior_ao_y.ygg(
                g, base, delta, "neighbor1", 2, 1)
        else:
            # AG unparsed is a valid weak comparator, not an inverse oracle.
            f = lambda g: prior_ag.ygg_transition(
                public.public_task(g)[0], base, delta, .1)
        a, wa = f(p)[0:2]
        b, wb = f(n)[0:2]
        tally(row, key.digest([seed, list(vec), fam]), fam, p["roles"],
              a, b, None, None)
    return {"name": name, **row, "same_new_TRAIN": True}

def wing_evaluate(normalized, base, delta, mode, alpha, calibration):
    row = blanks()
    for identity, fam, pos, neg in normalized:
        a, wa = new_w.score(pos, base, delta, mode, alpha, calibration)
        b, wb = new_w.score(neg, base, delta, mode, alpha, calibration)
        tally(row, identity, fam, pos["roles"], a, b, wa, wb,
              40 if mode == "train_calibrated_hop_likelihood" else 0)
        for work in (wa, wb):
            need(work["max_states_per_node"] == 1 and
                 work["max_packed_bits_per_state"] == 12 and
                 work["max_active"] <= 64 and
                 work["extra_retained_states"] == 0 and
                 work["source_oracle_in_model"] is False,
                 "ORIGINAL_ONE_PACKED_LIMIT")
    return {"mode": mode, "alpha": alpha, **row}

def run(o, t, an, ao, ap, aq, aqdev):
    base, delta = authenticated_parent(o, t, an, ao, ap, aq, aqdev)
    yrows = source.pairs("Yggdrasil", "TRAIN")
    wrows = source.pairs("Wingless", "TRAIN")
    diagnostic = {"Yggdrasil": source_inventory(yrows),
                  "Wingless": source_inventory(wrows)}
    ygrid = []
    for mode in new_y.MODES:
        for width in new_y.WIDTHS:
            candidate, resources = meter(
                lambda mode=mode, width=width: ygg_evaluate(
                    yrows, base["Yggdrasil"], delta["Yggdrasil"],
                    mode, width))
            ygrid.append({**candidate, "resources": resources})
    ycontrol = {}
    for name in ("AQ_sparse", "AP_kernel", "AO_neighbor", "AG_unparsed"):
        ycontrol[name] = old_ygg(
            yrows, base["Yggdrasil"], delta["Yggdrasil"], name)
    yeligible = [r for r in ygrid if r["FP"] == 0 and r["paired"] > 0 and
                 r["paired"] > max(row["paired"] for row in ycontrol.values())]
    yselected = sorted(
        yeligible if yeligible else ygrid,
        key=lambda x: (x["FP"] != 0, -x["paired"], x["FN"],
                       x["resources"]["model_and_eval_cpu_ns"],
                       x["shared_parameter_bytes_lower"],
                       x["mode"], x["width"]))[0]
    normalized = [
        (key.digest([seed, list(vec), fam]), fam,
         source.plain(p, op, nonce), source.plain(n, op, nonce))
        for seed, vec, fam, op, nonce, p, n in wrows
    ]
    calibration, calibration_cost = meter(
        lambda: new_w.fit_calibration(normalized))
    wgrid = []
    options = [("original_gamma0", 0.)] + [
        (m, a) for m in new_w.MODES[1:] for a in new_w.ALPHAS[1:]]
    for mode, alpha in options:
        candidate, resources = meter(
            lambda mode=mode, alpha=alpha: wing_evaluate(
                normalized, base["Wingless"], delta["Wingless"],
                mode, alpha,
                calibration if mode ==
                "train_calibrated_hop_likelihood" else None))
        wgrid.append({**candidate, "resources": resources})
    baseline = next(x for x in wgrid if x["mode"] == "original_gamma0")
    bset = set(baseline["accepted_long_ids"])
    for x in wgrid:
        x["preserves_individual_original_long_positives"] = bset.issubset(
            x["accepted_long_ids"])
    wvalid = [x for x in wgrid if
              x["mode"] != "original_gamma0" and
              x["preserves_individual_original_long_positives"] and
              x["FP"] < baseline["FP"] and
              x["paired"] >= baseline["paired"]]
    wselected = sorted(
        wvalid if wvalid else [baseline],
        key=lambda x: (-x["paired"], x["FP"],
                       x["extra_hop_ops"],
                       x["resources"]["model_and_eval_cpu_ns"],
                       x["mode"], x["alpha"]))[0]
    need(len(ygrid) == 6 and len(wgrid) == 7 and
         all(x["pairs"] == 48 for x in ygrid + wgrid) and
         all(x["pairs"] == 48 for x in ycontrol.values()) and
         len(normalized) == 48 and
         not any(x["max_active"] > 64 for x in wgrid),
         "PRECOMMITTED_COMPLETE_GRID")
    return {
        "schema": SCHEMA,
        "preregistration_blob": source.FREEZE_BLOB,
        "parent_aq_original_train_sha256": AQ_TRAIN_SHA,
        "parent_aq_original_dev_sha256": AQ_DEV_SHA,
        "original_model_identities": {
            lane: {"base_sha256": key.digest(base[lane]),
                   "delta_sha256": key.digest(delta[lane])}
            for lane in ("Yggdrasil", "Wingless")},
        "source_diagnostics": diagnostic,
        "selected": {"Yggdrasil": yselected, "Wingless": wselected},
        "full_candidate_grid": {"Yggdrasil": ygrid, "Wingless": wgrid},
        "controls": {"Yggdrasil": ycontrol,
                     "Wingless": baseline},
        "calibration": {"TRAIN_only": True,
                        "parameters": calibration,
                        "resources": calibration_cost},
        "eligible_to_consider_DEV": {
            "Yggdrasil": bool(yeligible), "Wingless": bool(wvalid)},
        "resource_provenance": {
            "host": platform.platform(), "python": platform.python_version(),
            "process_peak_RSS_bytes_cumulative": process_rss(),
            "Windows_RSS_not_comparable_to_Linux_RSS": True,
            "per_arm_peak_RSS_attribution": False,
            "source_normalization_outside_timed_inference": True,
            "no_equal_hardware_claim": True},
        "fresh_split": "TRAIN_ONLY", "DEV_cases_generated": 0,
        "DEV_consumed": False, "DEV_source_touched": False,
        "all_candidate_outcomes_retained": True,
        "source_truth_evaluator_only": True,
        "protected_first_use": False,
        "independent_science_acceptance": False,
        "optimizer_promotion": False,
        "production_activation": False,
        "merge": False,
    }

def main():
    p = argparse.ArgumentParser()
    for k in ("o", "t", "an", "ao", "ap", "aq", "aqdev", "output"):
        p.add_argument("--" + k, required=True)
    a = p.parse_args()
    dest = Path(a.output)
    need(dest.parent.is_dir() and not dest.exists(),
         "APPEND_ONLY_FIRST_ORIGINAL_TRAIN")
    data = run(a.o, a.t, a.an, a.ao, a.ap, a.aq, a.aqdev)
    raw = json.dumps(data, sort_keys=True, indent=2).encode() + b"\n"
    with dest.open("xb") as f:
        f.write(raw)
    print("F124AR_TRAIN_RAW_SHA256=" + hashlib.sha256(raw).hexdigest())
    for lane in ("Yggdrasil", "Wingless"):
        x = data["selected"][lane]
        print("F124AR_TRAIN_" + lane + "=" + json.dumps(
            {k: x[k] for k in ("mode", "paired", "FP", "FN")
             if k in x}, sort_keys=True))
        print("F124AR_TRAIN_DEV_ELIGIBLE_" + lane + "=" +
              str(data["eligible_to_consider_DEV"][lane]))
    print("F124AR_DEV_CONSUMED=false")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError,
            AssertionError) as e:
        print("F124AR_FAIL_CLOSED:" + str(e), file=sys.stderr)
        sys.exit(1)
