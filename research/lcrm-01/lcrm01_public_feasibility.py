"""LCRM-01: source-free public-information causal identifiability witness.

No learner, scientific source generator, protected cases, or prospective seeds.
The finite two-SCM version space is a diagnostic witness, not a claimed
complete symbolic causal oracle for arbitrary structural models.
"""
from __future__ import annotations

from itertools import product

MODELS = ("direct_chain", "common_cause")
HORIZON = 8


def observed_episode(latent: tuple[int, ...], model: str) -> tuple[tuple[int, int, int], ...]:
    if model not in MODELS or len(latent) != HORIZON or any(type(u) is not int or u not in (0, 1) for u in latent):
        raise ValueError("PUBLIC_OBSERVATION_CONTRACT")
    # Direct: X=U, Y=X, Z=Y. Confounded: X=U, Y=U, Z=Y.
    # Same public (X,Y,Z) for every U and every sequence length.
    return tuple((u, u, u) for u in latent)


def do_x(baseline_x: int, new_x: int, model: str) -> tuple[int, int, int]:
    if model not in MODELS or type(baseline_x) is not int or type(new_x) is not int or baseline_x not in (0, 1) or new_x not in (0, 1):
        raise ValueError("PUBLIC_INTERVENTION_CONTRACT")
    y = new_x if model == "direct_chain" else baseline_x
    return (new_x, y, y)


def consistent_models(observed: tuple[tuple[int, int, int], ...],
                      interventions: tuple[tuple[int, int, tuple[int, int, int]], ...] = ()) -> tuple[str, ...]:
    """Two-witness-model symbolic consistency check; not full SCM discovery.

    Intervention tuple: (public baseline X, do(X=value), public result X,Y,Z).
    Every intervention must be an explicitly observed public event.
    """
    if not observed or any(len(row) != 3 or any(type(v) is not int or v not in (0, 1) for v in row) for row in observed):
        raise ValueError("PUBLIC_HISTORY_INVALID")
    supported = []
    for model in MODELS:
        if any(x != y or y != z for x, y, z in observed):
            continue
        if all(do_x(x, value, model) == outcome for x, value, outcome in interventions):
            supported.append(model)
    return tuple(supported)


def symbolic_counterfactual(observed: tuple[tuple[int, int, int], ...],
                            baseline_x: int, do_value: int,
                            interventions: tuple[tuple[int, int, tuple[int, int, int]], ...] = ()) -> dict:
    versions = consistent_models(observed, interventions)
    possible = {do_x(baseline_x, do_value, model) for model in versions}
    if len(possible) == 1 and versions:
        return {"admitted": True, "outcome": next(iter(possible)), "models": len(versions)}
    return {"admitted": False, "outcome": None, "models": len(versions)}


def certificate() -> dict:
    checked = 0
    for latent in product((0, 1), repeat=HORIZON):
        a = observed_episode(latent, MODELS[0])
        b = observed_episode(latent, MODELS[1])
        assert a == b
        assert consistent_models(a) == MODELS
        for x in latent:
            assert do_x(x, 1 - x, MODELS[0]) != do_x(x, 1 - x, MODELS[1])
            assert not symbolic_counterfactual(a, x, 1 - x)["admitted"]
        checked += 1
    return {
        "schema": "mass.lcrm01.public-observation-feasibility-certificate.v1",
        "source_scope": "ANALYTIC_TWO_SCM_WITNESS_ONLY",
        "all_binary_latent_histories_length_8": checked,
        "public_observational_event_rows": checked * HORIZON,
        "models_observationally_indistinguishable": True,
        "two_hop_do_counterfactual_distinguishes": True,
        "symbolic_version_space_requires_public_interventions": True,
        "zero_unauthorized_counterfactual_admissions": True,
        "new_scientific_firstuse": 0,
        "protected_case_access": False,
        "learned_relational_transfer_accepted": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(certificate(), sort_keys=True))
