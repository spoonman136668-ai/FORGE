"""F124-DK source-neutral, source-free mathematical identifiability preflight.

This module proves a *limited* counterexample: all-zero observations on a
strict subset of the five-nibble input domain are compatible both with a
rotation-equivariant zero function and with a non-equivariant spike function.
It does not inspect original causal source cases, train a learner, or certify
that arbitrary observed labels admit an equivariant completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

NIBBLES = 5
WIDTH = 4
DOMAIN = 1 << (NIBBLES * WIDTH)
NIBBLE_MASK = (1 << WIDTH) - 1


def rotate_nibble(n: int) -> int:
    if not 0 <= n <= NIBBLE_MASK:
        raise ValueError("NIBBLE_OUT_OF_RANGE")
    return ((n << 1) & NIBBLE_MASK) | (n >> (WIDTH - 1))


def rotate_input(x: int) -> int:
    if not 0 <= x < DOMAIN:
        raise ValueError("INPUT_OUT_OF_RANGE")
    return sum(rotate_nibble((x >> (WIDTH * k)) & NIBBLE_MASK) << (WIDTH * k)
               for k in range(NIBBLES))


def all_zero_law(_: int) -> int:
    return 0


def spike_law(x: int, unobserved: int) -> int:
    return 1 if x == unobserved else 0


@dataclass(frozen=True)
class Witness:
    unique_observed_inputs: int
    domain_size: int
    witness_input: int
    equivariant_rhs: int
    modified_lhs: int
    modified_rhs: int

    @property
    def non_equivariance_proved(self) -> bool:
        return self.modified_lhs != self.modified_rhs


def source_neutral_witness(observed_zero_labels: Iterable[int]) -> Witness:
    """Prove ambiguity for a specifically zero-labelled *partial* dataset.

    A first-missing-input witness exists among the first |D|+1 integers by
    pigeonhole principle; no million-element model enumeration is needed.
    """
    observed: set[int] = set()
    for x in observed_zero_labels:
        if not isinstance(x, int) or isinstance(x, bool) or not 0 <= x < DOMAIN:
            raise ValueError("OBSERVED_INPUT_INVALID")
        observed.add(x)
    if len(observed) == DOMAIN:
        raise ValueError("FULL_DOMAIN_NO_UNSEEN_INPUT")
    witness = next(x for x in range(len(observed) + 1) if x not in observed)
    assert witness not in observed
    assert all(all_zero_law(x) == spike_law(x, witness) for x in observed)
    equivariant_rhs = rotate_nibble(all_zero_law(witness))
    modified_lhs = spike_law(rotate_input(witness), witness)
    modified_rhs = rotate_nibble(spike_law(witness, witness))
    assert all_zero_law(rotate_input(witness)) == equivariant_rhs == 0
    assert modified_lhs != modified_rhs
    return Witness(len(observed), DOMAIN, witness,
                   equivariant_rhs, modified_lhs, modified_rhs)


def validate_labeled_observations(rows: Iterable[tuple[int, int]]) -> Witness:
    observed: list[int] = []
    for x, output in rows:
        if output != 0:
            raise ValueError("THIS_WITNESS_REQUIRES_ZERO_LABELS")
        observed.append(x)
    return source_neutral_witness(observed)


def declared_preflight() -> dict[str, int | str | bool]:
    record = source_neutral_witness(range(24 * 8))
    return {
        "schema": "mass.f124dk.identifiability-symbolic-preflight.v1",
        "status": "PARTIAL_ZERO_LABELLED_INPUTS_NOT_IDENTIFYING_UNRESTRICTED_SYMMETRY",
        "input_nibbles": NIBBLES,
        "bits_per_nibble": WIDTH,
        "full_input_space": DOMAIN,
        "maximum_public_FIT_events": 24 * 8,
        "distinct_observed_witness_count": record.unique_observed_inputs,
        "unobserved_input_count_at_least": DOMAIN - record.unique_observed_inputs,
        "first_witness_input": record.witness_input,
        "non_equivariance_witness_lhs": record.modified_lhs,
        "non_equivariance_witness_rhs": record.modified_rhs,
        "unrestricted_symmetry_identifiable_from_this_partial_data": False,
        "arbitrary_nonzero_label_coverage_claim": False,
        "protected_scientific_sources_consumed": 0,
        "F124_DJ_reserved_seeds_consumed": 0,
        "F124_DK_reserved_seeds_consumed": 0,
        "external_original_science_acceptance": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(declared_preflight(), sort_keys=True))
