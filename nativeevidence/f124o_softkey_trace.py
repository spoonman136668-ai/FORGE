"""F124-O: source-authenticated optimizer-guided, development-only soft-key trace.

Consumes the exact F124-M optimizer-advisory artifact and F124-N negative,
not fabricated candidates or protected scientific first-use. No package API,
external controller, model inference, network call or reserved source.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124n_novel_structure_source as source

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "reference/research-intake/f124o-frozen-pareto-softkey-trace.json"
PROTOCOL_BLOB = "80dc5a0bb84d13de741eb3e6b1c7499ed8d635b6"
PARENT_HEAD = "59cef2e3e877d8b76e7ac971acca69e5d1ed172b"
PARENT_M_SHA = "1991bab2333b2045e244f9afd851b8c95fb08f8be29c10e88822b6bd982d28e0"
PARENT_N_SHA = "1c03362fcfa44dea72208867cf374b0c196b8bb3c79e6e430ffdb6685ee12739"
SCHEMA = "forge.research.f124o.softkey-trace-train-and-dev.v1"


def require(ok, code):
    if not ok:
        raise source.Quarantined("F124O_" + code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(v):
    return (json.dumps(v, sort_keys=True, separators=(",", ":")) + "\n").encode()


def preregistered():
    raw = PROTOCOL.read_bytes().replace(b"\r\n", b"\n")
    require(source.git_blob(raw) == PROTOCOL_BLOB, "FREEZE_DRIFT")
    p = json.loads(raw)
    require(p["schema"] == "forge.research.f124o.frozen-negative-to-diverse-causal-trace.v1"
            and p["status"] == "PREIMPLEMENTATION_FROZEN"
            and p["parent"]["qualified_f124n_head"] == PARENT_HEAD
            and p["parent"]["f124n_report_sha256"] == PARENT_N_SHA
            and p["parent"]["f124m_report_sha256"] == PARENT_M_SHA
            and p["selection"]["candidate_id"] == "softkey-multipath-trace-v1"
            and p["training"]["fit_epochs"] == 28
            and p["training"]["initial_parameters"] == [1.0, 3.0]
            and p["training"]["finite_difference_epsilon"] == 0.002
            and p["training"]["lr"] == 0.2
            and all(p["authority"].values()),
            "PREDECLARED_METHOD_OR_AUTHORITY_DRIFT")
    return p


def checked(path, digest):
    data = Path(path).read_bytes()
    require(sha(data) == digest, "UNAUTHENTICATED_SOURCE_DIGEST")
    return json.loads(data)


def admission(m, n):
    """Actual prior evoportfolio, Shinka/Pareto, GenEnv and Promptbreeder output
    is an input. No success/promotion/automatic authorisation is inferred.
    """
    require(m["schema"] == "forge.research.f124m.authentic-training-optimizer-advisory.v1"
            and m["f124j_report_sha256"] == "d2e3a3bb89065e5dbb084ff0eb0601bcdef63e44774f330e5135e0728e9a2eda"
            and m["f124i_report_sha256"] == "c97f51a04769caeadeee03889daf056cad38be826d18aada453a07371e71fb1e"
            and m["evidence_kind"] == "AUTHENTIC_ORIGINAL_TRAIN_ONLY_NOT_PROSPECTIVE"
            and not m["scientific_first_use"]
            and m["scientific_acceptances"] == 0
            and m["optimizer_promotions"] == 0
            and m["protected_inputs"] == 0
            and m["accepted_ref_mutations"] == 0
            and n["schema"] == "forge.research.f124n.authenticated-original-weight-new-structure-development.v1"
            and n["freeze_git_blob"] == source.PROTOCOL_BLOB
            and n["development_only"]
            and n["frozen_B_weights_unchanged"]
            and n["forward_code_object_unchanged"]
            and n["protected_examples_generated"] == 0
            and n["scientific_acceptances"] == 0
            and n["optimizer_promotions"] == 0
            and len(m["lanes"]) == len(n["lanes"]) == 2,
            "ORIGINAL_DEVELOPMENT_CUSTODY")
    pairs = []
    for index, lane in enumerate(("Wingless", "Yggdrasil")):
        ml, nl = m["lanes"][index], n["lanes"][index]
        archives = (
            ml["evoportfolio_source_advisory"]["archive"],
            ml["shinka_pareto_historical_advisory"]["archive"],
        )
        env = ml["genenv_untested_advisory"]
        prompts = ml["promptbreeder_untested_advisory"]
        require(ml["lane"] == nl["lane"] == lane
                and all(len(archive) == 5 for archive in archives)
                and len(env["candidates"]) == 2 and len(prompts["candidates"]) == 2
                and env["negative_count"] == 2
                and not ml["shinka_pareto_historical_advisory"]["scientific_accepted"]
                and not ml["evoportfolio_source_advisory"]["scientific_accepted"]
                and not env["scientific_accepted"]
                and not prompts["scientific_accepted"]
                and all(x["classification"] == "UNTESTED_PROPOSAL"
                        for x in env["candidates"])
                and all(x["classification"] == "UNTESTED"
                        for x in prompts["candidates"])
                and {x["id"] for x in env["candidates"]} == {
                    "stress-parallel", "stress-cross"}
                and nl["dev"]["pairs"] == 48
                and nl["dev"]["exact_paired"] == 48
                and nl["dev"]["role_only_paired"] == 0
                and nl["dev"]["B_paired"] < nl["dev"]["fixed_paired"]
                and nl["fit"]["pairs"] == 48
                and not nl["development_verdict"].startswith(
                    "ORIGINAL_B_BEATS_FIXED"),
                "NEGATIVE_OR_DIVERSITY_CONTRACT")
        pairs.append({"lane":lane, "prior_B":nl["dev"]["B_paired"],
                      "prior_fixed":nl["dev"]["fixed_paired"],
                      "prior_B_bit_ops":nl["dev"]["B_bit_ops"],
                      "prior_fixed_bit_ops":nl["dev"]["fixed_bit_ops"],
                      "retained_pareto":len(archives[1]),
                      "genenv_proposal_ids":sorted(x["id"] for x in env["candidates"]),
                      "prompt_count":len(prompts["candidates"])})
    return pairs


def softplus(x):
    return max(0.0, x) + math.log1p(math.exp(-abs(x)))


def logsumexp(vals):
    if not vals:
        return -40.0
    peak = max(vals)
    return peak + math.log(sum(math.exp(x - peak) for x in vals))


def predict(graph, scale, bias):
    """Keep competing keyed hypotheses; infer from public bits/topology only.

    The oracle public_routes and generated labels NEVER enter this function.
    One soft gate per key hand-off, no exact-equality/12-of-16 hard threshold.
    """
    source.validate_public(graph)
    require(0.2 <= scale <= 5 and -3 <= bias <= 12, "PARAMETER_BOUNDS")
    frontier = [(graph["start"], None, 0.0)]
    scans = ops = 0
    for role in graph["roles"]:
        following = []
        for node, carried, energy in frontier:
            for e in graph["edges"]:
                scans += 1
                require(scans <= 25000, "EDGE_BUDGET")
                if e["from"] != node or e["role"] != role:
                    continue
                increment = 0.0
                if carried is not None:
                    matches = sum(a == b for a, b in zip(carried, e["src_bits"]))
                    ops += 16
                    # differentiable, soft compatibility rather than symbolic
                    # equality or the frozen 12-of-16 decision comparator
                    increment = -softplus(-(matches - 12) * scale / 4.0)
                following.append((e["to"], e["dst_bits"], energy + increment))
                require(len(following) <= 256, "PARTIAL_PATH_BUDGET")
        frontier = following
    evidence = logsumexp([energy for node, _, energy in frontier
                          if node == graph["target"]])
    return evidence + bias, {"edge_scans":scans, "raw_bit_ops":ops}


def paired_cases(lane, phase):
    frozen = source.frozen()
    require(len(frozen) == 64, "PARENT_FREEZE_DIGEST")
    for vector in source.VECTORS:
        for seed in source.COHORTS[lane][phase]:
            positive, negative = source.build(lane, seed, vector, phase)
            require(source.paired_admit(positive, negative), "SOURCE_PAIR")
            yield seed, tuple(vector), positive, negative


def objective(cases, scale, bias):
    total = 0.0
    for _, _, pos, neg in cases:
        a, _ = predict(pos, scale, bias)
        b, _ = predict(neg, scale, bias)
        total += softplus(-a) + softplus(b)
    return total / (2 * len(cases))


def fit(lane):
    """Fixed 28-epoch finite-difference optimizer. No DEV observation."""
    fit_cases = list(paired_cases(lane, "FIT"))
    require(len(fit_cases) == 48, "FIT_DENOMINATOR")
    scale, bias = 1.0, 3.0
    for _ in range(28):
        eps = 0.002
        ds = (objective(fit_cases, min(5.0, scale + eps), bias) -
              objective(fit_cases, max(0.2, scale - eps), bias)) / (
                  min(5.0, scale + eps) - max(0.2, scale - eps))
        db = (objective(fit_cases, scale, min(12.0, bias + eps)) -
              objective(fit_cases, scale, max(-3.0, bias - eps))) / (
                  min(12.0, bias + eps) - max(-3.0, bias - eps))
        scale = min(5.0, max(0.2, scale - 0.2 * ds))
        bias = min(12.0, max(-3.0, bias - 0.2 * db))
    return (scale, bias), objective(fit_cases, scale, bias)


def evaluate(lane, phase, params):
    counts = {"pairs":0, "paired_correct":0, "positive_correct":0,
              "negative_correct":0, "edge_scans":0, "raw_bit_ops":0,
              "depth":{str(k):{"pairs":0, "paired":0} for k in (7,8,9)},
              "case_sha256":[]}
    for seed, vector, pos, neg in paired_cases(lane, phase):
        a, wa = predict(pos, *params)
        b, wb = predict(neg, *params)
        positive, negative = a >= 0, b < 0
        good = bool(positive and negative)
        depth = str(len(pos["roles"]))
        counts["pairs"] += 1
        counts["paired_correct"] += int(good)
        counts["positive_correct"] += int(positive)
        counts["negative_correct"] += int(negative)
        counts["depth"][depth]["pairs"] += 1
        counts["depth"][depth]["paired"] += int(good)
        counts["edge_scans"] += wa["edge_scans"] + wb["edge_scans"]
        counts["raw_bit_ops"] += wa["raw_bit_ops"] + wb["raw_bit_ops"]
        counts["case_sha256"].append(sha(canonical({
            "lane":lane, "phase":phase, "seed":seed, "vector":list(vector),
            "positive_logit":round(a, 10), "negative_logit":round(b, 10),
            "paired":good})))
    require(counts["pairs"] == 48 and
            all(row["pairs"] == 16 for row in counts["depth"].values()) and
            len(counts["case_sha256"]) == 48, "DENOMINATOR_OR_DEPTH")
    return counts


def produce(m, n):
    preregistered()
    priors = admission(m, n)
    out = {"schema":SCHEMA, "source_head":PARENT_HEAD,
           "freeze_git_blob":PROTOCOL_BLOB,
           "F124M_sha256":PARENT_M_SHA,"F124N_sha256":PARENT_N_SHA,
           "selected_candidate":"softkey-multipath-trace-v1",
           "selection":"PREDECLARED_DIVERSE_ADVISORY_NO_PROSPECTIVE_PROMOTION",
           "lanes":[], "original_protected_inputs":0,
           "original_first_use":False, "scientific_acceptances":0,
           "accepted_ref_mutations":0,"optimizer_promotions":0,
           "codex_calls":0,"paid_model_api_calls":0,"new_scheduler":False}
    for original in priors:
        lane = original["lane"]
        params, loss = fit(lane)
        fit_row = evaluate(lane, "FIT", params)
        dev = evaluate(lane, "DEV", params)
        out["lanes"].append({
            "lane":lane,"frozen_parameters":["softkey_scale","terminal_bias"],
            "parameters":[round(p, 12) for p in params],
            "fit_loss":round(loss, 12), "fit":fit_row, "dev":dev,
            "prior_source_selection":original,
            "development_verdict":(
                "SOFTKEY_BEATS_FROZEN_APPROX_DEVELOPMENT_ONLY"
                if dev["paired_correct"] > original["prior_fixed"] else
                "SOFTKEY_DOES_NOT_BEAT_FROZEN_APPROX_DEVELOPMENT_ONLY"),
            "resource_matched":False})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--f124m-report", required=True)
    parser.add_argument("--f124n-report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    target = Path(args.output)
    require(target.parent.is_dir() and not target.exists(),
            "OUTPUT_OVERWRITE")
    m = checked(args.f124m_report, PARENT_M_SHA)
    n = checked(args.f124n_report, PARENT_N_SHA)
    report = produce(m, n)
    data = json.dumps(report, sort_keys=True, indent=2).encode() + b"\n"
    with target.open("xb") as stream:
        stream.write(data)
    print("F124O_REPORT_SHA256=" + sha(data))
    for row in report["lanes"]:
        print("F124O_DEV_" + row["lane"] + "=" +
              str(row["dev"]["paired_correct"]) + "/48 versus fixed=" +
              str(row["prior_source_selection"]["prior_fixed"]) + "/48 " +
              row["development_verdict"])


if __name__ == "__main__":
    try:
        main()
    except (source.Quarantined, KeyError, TypeError, ValueError, OSError) as exc:
        print("F124O_QUARANTINED:" + str(exc), file=sys.stderr)
        raise SystemExit(1)
