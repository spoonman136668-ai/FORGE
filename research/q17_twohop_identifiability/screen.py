"""Q17A: exact causal-composition identifiability screen, not learned science.

The entire sample space is analytically enumerated with Fraction. Neither
held-out synthetic families nor any real source/engine, network or CKB-plane
state is accessed. This is a prerequisite decision for future learning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import tracemalloc
from fractions import Fraction
from itertools import product
from pathlib import Path

FROZEN_BLOB = "18fcff8607d93b9596cb22e5b190ac9fda8bd61f"
HERE = Path(__file__).resolve().parent
STRUCTURES = ("forward", "reverse")
VALID_DEVELOPMENT = ("C17_dev_a", "C17_dev_b")


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError("Q17_" + code)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def read_protocol() -> dict:
    data = (HERE / "FROZEN_PROTOCOL.json").read_bytes()
    blob = hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()
    require(blob == FROZEN_BLOB, "FROZEN_SOURCE_IDENTITY_DRIFT")
    protocol = json.loads(data)
    require(protocol["schema"] ==
            "forge.nci04.q17.twohop-causal-intervention-identifiability.v1",
            "PROTOCOL_SCHEMA_CHANGED")
    require(tuple(v["id"] for v in protocol["development_families"])
            == VALID_DEVELOPMENT, "DEVELOPMENT_FAMILIES_CHANGED")
    require(protocol["evaluation"]["intervened_samples_per_family"] == 64
            and protocol["evaluation"]["intervention_allocation"] ==
            {"do_X_0": 32, "do_X_1": 32}, "INTERVENTION_BUDGET_CHANGED")
    require(protocol["custody"]["original_source_engine_episodes"] == 0
            and protocol["custody"]["protected_scientific_first_use"] is False,
            "ORIGINAL_SOURCE_SCOPE_CHANGED")
    return protocol


def weights(p: Fraction) -> tuple[Fraction, Fraction]:
    return (1-p, p)


def fixed_families(protocol: dict) -> tuple[tuple[str, Fraction, Fraction], ...]:
    out = []
    for family in protocol["development_families"]:
        name = family["id"]
        require(name in VALID_DEVELOPMENT, "HELD_FAMILY_FORBIDDEN")
        p = Fraction(family["p_num"], family["p_den"])
        q = Fraction(family["q_num"], family["q_den"])
        require(0 < p < Fraction(1, 2) and 0 < q < Fraction(1, 2),
                "IDENTIFIABLE_NOISE_BOUNDS")
        out.append((name, p, q))
    require(len(out) == 2, "FAMILY_CARDINALITY_DRIFT")
    return tuple(out)


def passive_distribution(structure: str, p: Fraction, q: Fraction) -> dict:
    """Separate structural interventions, including all 8 visible triples."""
    require(structure in STRUCTURES, "UNKNOWN_STRUCTURE")
    distribution = {(x, y, z): Fraction(0)
                    for x, y, z in product((0, 1), repeat=3)}
    for root in (0, 1):
        for edge_a, edge_b in product((0, 1), repeat=2):
            if structure == "forward":
                x = root
                y = x ^ edge_a
                z = y ^ edge_b
            else:
                y = root
                x = y ^ edge_a
                z = y ^ edge_b
            mass = Fraction(1, 2) * weights(p)[edge_a] * weights(q)[edge_b]
            distribution[(x, y, z)] += mass
    require(sum(distribution.values()) == 1, "PASSIVE_NOT_NORMALIZED")
    return distribution


def intervention_symbolic(structure: str, action: int, p: Fraction,
                          q: Fraction) -> Fraction:
    """Independent structural-equation enumeration, output only terminal Z."""
    require(structure in STRUCTURES and action in (0, 1),
            "INTERVENTION_UNDEFINED")
    score = Fraction(0)
    if structure == "forward":
        for edge_a, edge_b in product((0, 1), repeat=2):
            x = action
            y = x ^ edge_a
            z = y ^ edge_b
            if z == action:
                score += weights(p)[edge_a] * weights(q)[edge_b]
    else:
        for y, edge_b in product((0, 1), repeat=2):
            z = y ^ edge_b
            if z == action:
                score += Fraction(1, 2) * weights(q)[edge_b]
    require(0 < score < 1, "INTERVENTION_DISTRIBUTION_INVALID")
    return score


def intervention_closed_form(structure: str, p: Fraction,
                             q: Fraction) -> Fraction:
    """Independent algebraic control; must match structural enumeration."""
    require(structure in STRUCTURES, "BAD_STRUCTURE")
    return (1-p)*(1-q)+p*q if structure == "forward" else Fraction(1, 2)


def binomial_mass(n: int, k: int, probability: Fraction) -> Fraction:
    require(type(n) is int and 1 <= n <= 128 and
            type(k) is int and 0 <= k <= n, "BINOMIAL_SCOPE_INVALID")
    return (math.comb(n, k) * probability**k *
            (1-probability)**(n-k))


def exact_equal_prior_bayes_error(n: int, forward: Fraction,
                                  reverse: Fraction) -> tuple[Fraction, float, int]:
    """Exact finite-n Bayes risk, full equal-budget count evidence."""
    pf = [binomial_mass(n, k, forward) for k in range(n+1)]
    pr = [binomial_mass(n, k, reverse) for k in range(n+1)]
    require(sum(pf) == 1 and sum(pr) == 1, "BINOMIAL_NORMALIZATION_FAILED")
    risk = sum((min(a, b) for a, b in zip(pf, pr)), Fraction(0)) / 2
    # I(H;K) = Σ_h,k 1/2 P(k|h) log2(P(k|h) / P(k)); all terms positive.
    mutual_info = 0.0
    strict_decisions = 0
    for a, b in zip(pf, pr):
        mixture = (a+b)/2
        if a != b:
            strict_decisions += 1
        for value in (a, b):
            if value:
                mutual_info += (float(value)/2)*math.log2(
                    float(value/mixture))
    require(Fraction(0) <= risk < Fraction(1, 2)
            and 0 < mutual_info <= 1+1e-10,
            "BAYES_RISK_OR_INFORMATION_INVALID")
    return risk, mutual_info, strict_decisions


def screen(protocol: dict) -> dict:
    start = time.process_time()
    tracemalloc.start()
    cases = []
    n = protocol["evaluation"]["intervened_samples_per_family"]
    for name, p, q in fixed_families(protocol):
        front = passive_distribution("forward", p, q)
        back = passive_distribution("reverse", p, q)
        diff = max(abs(front[x]-back[x]) for x in front)
        require(diff == 0, "PASSIVE_EQUIVALENCE_BROKEN")
        require(all(front[x] > 0 for x in front) and len(front) == 8,
                "PASSIVE_SUPPORT_INVALID")
        positive = intervention_closed_form("forward", p, q)
        negative = intervention_closed_form("reverse", p, q)
        for action in (0, 1):
            require(intervention_symbolic("forward", action, p, q)
                    == positive, "FORWARD_SYMBOLIC_ORACLE_DISAGREEMENT")
            require(intervention_symbolic("reverse", action, p, q)
                    == negative, "REVERSE_SYMBOLIC_ORACLE_DISAGREEMENT")
        risk, mutual_info, decisions = exact_equal_prior_bayes_error(
            n, positive, negative)
        effect = positive-negative
        sufficiency = (effect >= Fraction(3, 20) and
                       risk <= Fraction(3, 20) and
                       diff == 0)
        cases.append({
            "family": name,
            "p": str(p), "q": str(q),
            "passive_mass_discrepancy": str(diff),
            "passive_optimal_direction_error": "1/2",
            "passive_causal_direction_information_bits": 0,
            "forward_do_terminal_match_probability": str(positive),
            "reverse_do_terminal_match_probability": str(negative),
            "causal_terminal_effect": str(effect),
            "interventions_total": n,
            "do_x_zero_trials": n//2,
            "do_x_one_trials": n//2,
            "exact_interventional_bayes_error": str(risk),
            "interventional_bayes_error_float": float(risk),
            "interventional_mutual_information_bits": mutual_info,
            "strict_likelihood_count_outcomes": decisions,
            "exact_symbolic_matches_bayes": True,
            "information_sufficiency_predefined_gate": sufficiency
        })
        print("Q17_DEV_FAMILY="+name+
              " PASSIVE_ERROR=0.5"+
              " EFFECT="+format(float(effect), ".9f")+
              " INTERVENTIONAL_BAYES_ERROR="+format(float(risk), ".9f"),
              flush=True)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    cpu = time.process_time()-start
    passed = len(cases) == 2 and all(
        x["information_sufficiency_predefined_gate"] for x in cases)
    verdict = ("INFORMATION_SUFFICIENT_FOR_FUTURE_LEARNING_DESIGN_ONLY"
               if passed else "INFORMATION_NO_GO")
    return {
        "schema":"forge.nci04.q17.exact-information-screen-result.v1",
        "frozen_protocol_git_blob": FROZEN_BLOB,
        "cases": cases,
        "decision": verdict,
        "measured_screen_cpu_seconds": cpu,
        "measured_tracemalloc_peak_bytes": peak,
        "all_eight_observation_triples_checked": True,
        "equal_prior_passive_optimal_error": "1/2",
        "held_unfamiliar_cases_generated": False,
        "native_learned_cognitive_candidate_trained": False,
        "independent_source_custody_verified": False,
        "original_source_engine_episodes": 0,
        "scientific_first_use": False
    }


def selftest(protocol: dict) -> None:
    test = protocol["development_families"][0]
    p = Fraction(test["p_num"], test["p_den"])
    q = Fraction(test["q_num"], test["q_den"])
    require(passive_distribution("forward",p,q) ==
            passive_distribution("reverse",p,q),
            "PASSIVE_EQUALITY_TEST_FAILED")
    require(intervention_symbolic("forward",1,p,q) !=
            intervention_symbolic("reverse",1,p,q),
            "NO_INTERVENTIONAL_IDENTIFIABILITY")
    require(binomial_mass(2,0,Fraction(1,2)) +
            binomial_mass(2,1,Fraction(1,2)) +
            binomial_mass(2,2,Fraction(1,2)) == 1,
            "BINOMIAL_SELFTEST_FAILED")
    print("Q17_EXACT_PASSIVE_EQUIVALENCE_AND_ACTIVE_DISTINCTION=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True,
                        choices=("selftest", "information-screen"))
    mode = parser.parse_args().mode
    protocol = read_protocol()
    selftest(protocol)
    if mode == "selftest":
        return
    report = screen(protocol)
    print("Q17_RESULT_JSON="+canonical(report).decode(), flush=True)
    print("Q17_INFORMATION_DECISION="+report["decision"], flush=True)
    print("Q17_HELD_AND_ORIGINAL_SOURCE=NOT_GENERATED", flush=True)
    print("Q17_LEARNED_TRANSFER_ACCEPTANCE=NOT_CLAIMED", flush=True)


if __name__ == "__main__":
    main()
