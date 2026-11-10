"""Pure, non-authorizing development quality assessment of typed public-counter programs.

Exact Bernoulli enumeration, not an original FORGE/Yggdrasil science trial.
This module does not read owner history, select parents, publish, or dispatch.
No synthetic regret number is optimizer reward or acceptance evidence.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
from itertools import product
from math import comb
import re

from f139.nci04_prompt_program import _public_counter_value, parse

SCHEMA = "forge.f139.public-counter-development-quality.v1"
PROBABILITIES = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
TRIAL_COUNTS = (2, 4, 8)
SIGNATURE_MAX_TRIALS = 10
MAX_PROGRAMS = 16


def _decision(rule, success0, trials0, success1, trials1):
    """Compute decisions using nonnegative integers, never execute candidate Python."""
    if rule == "empirical":
        left, right = success0 * trials1, success1 * trials0
    elif rule == "laplace":
        left = (success0 + 1) * (trials1 + 2)
        right = (success1 + 1) * (trials0 + 2)
    else:
        numerator, denominator = rule
        numerator0 = _public_counter_value(numerator, success0, trials0 - success0)
        numerator1 = _public_counter_value(numerator, success1, trials1 - success1)
        denominator0 = _public_counter_value(denominator, success0, trials0 - success0)
        denominator1 = _public_counter_value(denominator, success1, trials1 - success1)
        if denominator0 <= 0 or denominator1 <= 0:
            return None
        left, right = numerator0 * denominator1, numerator1 * denominator0
    return 0 if left > right else 1 if left < right else None


def _binomial(trials, successes, probability):
    return comb(trials, successes) * probability ** successes * (
        1 - probability) ** (trials - successes)


def _loss(rule):
    """Uniform average over 54 fixed scenarios; abstention incurs half regret."""
    total = Fraction()
    n_scenarios = 0
    for p0 in PROBABILITIES:
        for p1 in PROBABILITIES:
            if p0 == p1:
                continue
            optimal = 0 if p0 > p1 else 1
            gap = abs(p0 - p1)
            for n0, n1 in product(TRIAL_COUNTS, repeat=2):
                n_scenarios += 1
                for s0, s1 in product(range(n0 + 1), range(n1 + 1)):
                    selected = _decision(rule, s0, n0, s1, n1)
                    regret = (Fraction(1, 2) if selected is None
                              else Fraction(int(selected != optimal)))
                    total += gap * regret * _binomial(n0, s0, p0) * _binomial(n1, s1, p1)
    assert n_scenarios == 54
    return total / n_scenarios


def _signature_bytes(rule):
    """Complete exact decision vector on the bounded public regression domain.

    The fixed DEV regret world draws trial counts only from (2, 4, 8);
    SIGNATURE_MAX_TRIALS=10 therefore covers EVERY possible public history
    observed by its scoring function. This is an exact domain equality key,
    never a claim of equivalence on unseen training counts or environments.
    """
    outcomes = bytearray()
    for n0 in range(1, SIGNATURE_MAX_TRIALS + 1):
        for n1 in range(1, SIGNATURE_MAX_TRIALS + 1):
            for s0, s1 in product(range(n0 + 1), range(n1 + 1)):
                selection = _decision(rule, s0, n0, s1, n1)
                outcomes.append(2 if selection is None else selection)
    assert len(outcomes) == 4225
    return bytes(outcomes)


def _signature(rule):
    """Finite public-grid fingerprint, NOT a universal equivalence certificate."""
    return sha256(_signature_bytes(rule)).hexdigest()


def _metric(loss):
    return {"exact_fraction": str(loss), "decimal": format(float(loss), ".12f")}


def assess(programs):
    """Compare untrusted typed programs with two competent conventional controls.

    No inference about original tasks, unknown worlds, or scientific benefit.
    Callers must separately authenticate any claimed PR source provenance.
    """
    if (type(programs) is not dict or not 1 <= len(programs) <= MAX_PROGRAMS
            or any(type(name) is not str or not re.fullmatch(r"[a-z0-9_-]{1,48}", name)
                   or type(program) is not str
                   for name, program in programs.items())):
        raise ValueError("F139_DEV_QUALITY_INVALID_INPUT")
    parsed = {name: parse(program) for name, program in programs.items()}
    baseline = {name: _loss(name) for name in ("empirical", "laplace")}
    strongest = min(baseline, key=baseline.get)
    # Cache only inside this explicit fixed development cohort. The key is
    # the COMPLETE decision vector, not its SHA digest or source/AST identity:
    # two different programs can share exactly the same actions/ties on this
    # scoring world, and then their expected regret MUST match for every seed.
    if max(TRIAL_COUNTS) > SIGNATURE_MAX_TRIALS:
        raise ValueError("F139_DEV_QUALITY_SIGNATURE_DOMAIN_TOO_SMALL")
    by_exact_decisions = {}
    results = {}
    for name, tree in parsed.items():
        decisions = _signature_bytes(tree)
        if decisions not in by_exact_decisions:
            by_exact_decisions[decisions] = _loss(tree)
        loss = by_exact_decisions[decisions]
        results[name] = {
            "program_sha256": sha256(programs[name].encode("ascii")).hexdigest(),
            "mean_regret": _metric(loss),
            "finite_public_grid_signature_sha256": sha256(decisions).hexdigest(),
            "beats_strongest_control_on_this_synthetic_dev_grid": loss < baseline[strongest],
        }
    return {
        "schema": SCHEMA,
        "mode": "SYNTHETIC_DEVELOPMENT_DIAGNOSTIC_ONLY",
        "fixed_scenarios": 54,
        "grid_decision_cases": 4225,
        "strongest_control": strongest,
        "controls": {name: _metric(loss) for name, loss in baseline.items()},
        "programs": results,
        "distinct_fixed_dev_decision_behaviors": len(by_exact_decisions),
        "redundant_regret_evaluations_avoided": len(parsed) - len(by_exact_decisions),
        "candidate_source_bytes_and_negative_results_preserved": True,
        "finite_grid_equality_is_global_equivalence_proof": False,
        "independent_source_custody_proven": False,
        "scientific_first_use": False,
        "scientific_accepted": False,
        "optimizer_training_authorized": False,
        "dispatch_authorized": False,
        "owner_policy_modified": False,
    }


FROZEN_DEV_GAIN_FLOOR = Fraction(1, 100)  # Exactly 0.01 expected regret.


def screen_development_candidates(programs):
    """Advisory selection after an exact DEV score, with mandatory abstention.

    This may identify a candidate worth a *new, independent, preregistered*
    evaluation. It never certifies a reward, promotes an optimizer, dispatches
    an owner task, or changes the existing candidate generator's choice.
    """
    report = assess(programs)
    control = report["strongest_control"]
    control_loss = Fraction(report["controls"][control]["exact_fraction"])
    # Tie-breaking is stable across input dictionary order; no outcome access.
    candidate = min(sorted(report["programs"]), key=lambda name: Fraction(
        report["programs"][name]["mean_regret"]["exact_fraction"]))
    candidate_loss = Fraction(
        report["programs"][candidate]["mean_regret"]["exact_fraction"])
    gain = control_loss - candidate_loss
    meets_floor = gain >= FROZEN_DEV_GAIN_FLOOR
    return {
        "schema": "forge.f139.public-counter-development-screen.v1",
        "mode": "NON_AUTHORIZING_SYNTHETIC_DEV_SELECTION",
        "disposition": ("PROMISING_DEV_ONLY_REQUIRES_NEW_INDEPENDENT_EVIDENCE"
                        if meets_floor else "DEV_NO_GO"),
        "candidate": candidate if meets_floor else None,
        "best_observed_candidate_for_diagnostics": candidate,
        "strongest_control": control,
        "candidate_mean_regret_exact": str(candidate_loss),
        "control_mean_regret_exact": str(control_loss),
        "absolute_regret_gain_exact": str(gain),
        "predeclared_absolute_regret_gain_floor_exact": str(FROZEN_DEV_GAIN_FLOOR),
        "equal_evidence_and_complete_cost_independently_proven": False,
        "development_signal_only": True,
        "owner_selection_unchanged": True,
        "scientific_first_use": False,
        "scientific_accepted": False,
        "optimizer_training_authorized": False,
        "dispatch_authorized": False,
        "accepted_ref_mutation_authorized": False,
    }
