"""LCRM01-E analytic affine-SCM causal-information ceiling (source only).

Enumerates a fixed, public, 9-bit affine causal hypothesis class. This is a
symbolic ceiling and an information lower-bound certificate, NOT a learned
mechanism, independently born scientific source, or original intervention.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import product

MODELS = tuple(range(512))
TARGETS = ('X', 'Y')
QUERIES = tuple(product((0, 1), TARGETS, (0, 1)))
WITNESS_DIRECT = (1 << 1) | (1 << 4) | (1 << 8)
WITNESS_COMMON = (1 << 1) | (1 << 3) | (1 << 8)


def scm(model: int, u: int, do: tuple[str, int] | None = None) -> tuple[int, int, int]:
    if type(model) is not int or not 0 <= model < 512 or type(u) is not int or u not in (0, 1):
        raise ValueError('INVALID_MODEL_OR_PUBLIC_U')
    if do is not None and (not isinstance(do, tuple) or len(do) != 2 or do[0] not in TARGETS or type(do[1]) is not int or do[1] not in (0, 1)):
        raise ValueError('INVALID_PUBLIC_DO')
    x = ((model >> 0) & 1) ^ (((model >> 1) & 1) & u)
    if do is not None and do[0] == 'X':
        x = do[1]
    y = ((model >> 2) & 1) ^ (((model >> 3) & 1) & u) ^ (((model >> 4) & 1) & x)
    if do is not None and do[0] == 'Y':
        y = do[1]
    z = ((model >> 5) & 1) ^ (((model >> 6) & 1) & u) ^ (((model >> 7) & 1) & x) ^ (((model >> 8) & 1) & y)
    return (x, y, z)


def observations(model: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(scm(model, u) for u in (0, 1))


def versions(public_obs: tuple[tuple[int, int, int], ...],
             public_do: tuple[tuple[int, str, int, tuple[int, int, int]], ...] = ()) -> tuple[int, ...]:
    """All models consistent with complete public u=0,1 observational rows.

    Any intervention passed here must be a witnessed public FIT observation;
    verifying independent origin is outside this analytical function.
    """
    if not isinstance(public_obs, tuple) or len(public_obs) != 2:
        raise ValueError('PUBLIC_OBSERVATION_REQUIRED')
    for row in public_obs:
        if not isinstance(row, tuple) or len(row) != 3 or any(type(v) is not int or v not in (0, 1) for v in row):
            raise ValueError('INVALID_PUBLIC_OBSERVATION')
    for row in public_do:
        if not isinstance(row, tuple) or len(row) != 4 or row[0] not in (0, 1) or type(row[0]) is not int or row[1] not in TARGETS or type(row[2]) is not int or row[2] not in (0, 1) or not isinstance(row[3], tuple) or len(row[3]) != 3 or any(type(v) is not int or v not in (0, 1) for v in row[3]):
            raise ValueError('INVALID_PUBLIC_DO_RECEIPT')
    return tuple(m for m in MODELS if observations(m) == public_obs and all(scm(m, u, (target, value)) == outcome for u, target, value, outcome in public_do))


def predict(public_obs: tuple[tuple[int, int, int], ...], query: tuple[int, str, int],
            public_do: tuple[tuple[int, str, int, tuple[int, int, int]], ...] = ()) -> dict:
    if not isinstance(query, tuple) or len(query) != 3 or type(query[0]) is not int or query[0] not in (0,1) or query[1] not in TARGETS or type(query[2]) is not int or query[2] not in (0,1):
        raise ValueError('INVALID_COUNTERFACTUAL_QUERY')
    compatible = versions(public_obs, public_do)
    outcomes = {scm(m, query[0], (query[1], query[2])) for m in compatible}
    if len(outcomes) == 1:
        return {'admitted': True, 'outcome': next(iter(outcomes)), 'version_count':len(compatible), 'scientific_admitted': False}
    return {'admitted':False, 'outcome':None, 'version_count':len(compatible), 'scientific_admitted':False}


def evaluate() -> dict:
    groups = defaultdict(list)
    for m in MODELS:
        groups[observations(m)].append(m)
    ambiguous = 0
    ambiguous_changed = 0
    informative = 0
    total_changed = 0
    refined_ambiguous = 0
    refined_ambiguous_changed = 0
    refined_groups = defaultdict(list)
    for m in MODELS:
        ob = observations(m)
        effect = scm(m, 0, ('X', 1))
        refined_groups[(ob, effect)].append(m)
    for m in MODELS:
        ob = observations(m)
        compatible = groups[ob]
        refined = refined_groups[(ob, scm(m, 0, ('X', 1)))]
        if len(refined) < len(compatible):
            informative += 1
        for u, target, value in QUERIES:
            changed = value != ob[u][0 if target == 'X' else 1]
            total_changed += int(changed)
            ambiguity = len({scm(k, u, (target, value)) for k in compatible}) > 1
            after = len({scm(k, u, (target, value)) for k in refined}) > 1
            ambiguous += int(ambiguity)
            ambiguous_changed += int(ambiguity and changed)
            refined_ambiguous += int(after)
            refined_ambiguous_changed += int(after and changed)
    result = {
        'schema':'mass.lcrm01.e.affine-public-information-enumeration.v1',
        'scope':'ANALYTIC_FIXED_ORDER_AFFINE_FAMILY_ONLY',
        'public_exogenous_u':True,
        'candidate_scm_count':len(MODELS),
        'observational_signature_count':len(groups),
        'observational_classes_with_multiple_scm':sum(len(g)>1 for g in groups.values()),
        'max_observational_equivalence_class':max(map(len, groups.values())),
        'total_model_query_pairs':len(MODELS)*len(QUERIES),
        'intervention_changes_baseline_pairs':total_changed,
        'ambiguous_observation_only_model_query_pairs':ambiguous,
        'ambiguous_changed_target_pairs':ambiguous_changed,
        'model_cases_whose_compatible_set_shrinks_with_do_X_1_at_U_0':informative,
        'remaining_ambiguous_query_pairs_after_one_public_do':refined_ambiguous,
        'remaining_ambiguous_changed_target_pairs_after_one_public_do':refined_ambiguous_changed,
        'do_sufficient_for_arbitrary_scm':False,
        'independent_real_public_do_witness_present':False,
        'trained_lcrm_model_qualified':False,
        'protected_scientific_first_use':0,
        'scientific_acceptance':False,
    }
    return result


if __name__ == '__main__':
    import json
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
