"""ACC-142 development-only information-channel witness.

No environment source, training, network, hidden state, or first-use access.
An optional source audit checks pinned, unmodified Yggdrasil source files.
This script does not patch their owner, change the R1 interface, or establish
causal benefit from learning or action selection.
"""
import argparse
import ast
from dataclasses import dataclass
from enum import Enum
import hashlib
from pathlib import Path
import unittest

PINNED_BLOBS = {
    'research/native/itd02/r1/native_policy.py': '3aa22b1e418a7f8cd9619c476f02b8c614917b16',
    'research/mass_r7c23/run.py': '42d12c424ff9104a52c7e019b00dff7107cf4295',
    'research/mass_r7c27/run.py': '95f05845655b0d290d9b91ff47556ee8675939d8',
}

class Reading(Enum):
    UNOBSERVED = 'unobserved'
    OBSERVED_CLEAR = 'observed_clear'
    OBSERVED_BLOCKED = 'observed_blocked'


def legacy_masked_value(reading):
    """C27's optimistic-clear projection, never a legal new API."""
    if not isinstance(reading, Reading):
        raise ValueError('invalid reading')
    return reading == Reading.OBSERVED_BLOCKED


def suggested_information_envelope(reading):
    """PROPOSAL ONLY: explicitly preserve presence and value separately."""
    if not isinstance(reading, Reading):
        raise ValueError('invalid reading')
    return (reading != Reading.UNOBSERVED,
            reading == Reading.OBSERVED_BLOCKED if reading != Reading.UNOBSERVED else None)


@dataclass(frozen=True)
class PublicStub:
    x: int = 3
    y: int = 4
    direction: int = 1
    front_blocked: bool = False


class SyntheticEdgeModel:
    """Minimal semantic witness; not the original source-native learner."""
    def __init__(self):
        self.evidence = {}
        self.choices = []

    def choose(self, state):
        assert type(state.front_blocked) is bool
        edge = (state.x, state.y, state.direction)
        # Mirrors C23's public bool->status evidence assignment, NOT full policy.
        self.evidence[edge] = int(state.front_blocked)
        self.choices.append((edge, self.evidence[edge]))
        return self.evidence[edge]


def c27_order_witness(model, state):
    """Literal critical order of C27's fork, not an actual original-world action."""
    edge = (state.x, state.y, state.direction)
    masked = PublicStub(state.x, state.y, state.direction, False)
    chosen = model.choose(masked)   # first, fabricated clear input
    model.evidence.pop(edge, None)  # later, cannot undo chosen action
    return chosen


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def get_method(tree, parent, method):
    cls = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == parent)
    return next(x for x in cls.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == method)


def audit_exact_owner_sources(root):
    """Exact Git-blob verification followed by bounded structural checks."""
    trees = {}
    for relative, expected in PINNED_BLOBS.items():
        path = root / relative
        data = path.read_bytes()
        actual = git_blob(data)
        if actual != expected:
            raise AssertionError(f'ORIGINAL_SOURCE_BLOB_DRIFT {relative}: {actual} != {expected}')
        trees[relative] = ast.parse(data, filename=relative)

    r1 = trees['research/native/itd02/r1/native_policy.py']
    c23 = trees['research/mass_r7c23/run.py']
    c27 = trees['research/mass_r7c27/run.py']
    grid = next(x for x in r1.body if isinstance(x, ast.ClassDef) and x.name == 'PublicGrid')
    typed = [x for x in grid.body if isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name) and x.target.id == 'front_blocked']
    assert len(typed) == 1 and isinstance(typed[0].annotation, ast.Name) and typed[0].annotation.id == 'bool', 'R1_PUBLIC_BOOL_CONTRACT_CHANGED'
    feature = next(x for x in r1.body if isinstance(x, ast.FunctionDef) and x.name == 'features')
    ftext = ast.unparse(feature)
    assert 'type(observation.front_blocked) is not bool' in ftext, 'R1_BOOL_VALIDATION_CHANGED'
    assert 'float(observation.front_blocked)' in ftext, 'R1_BOOL_FEATURE_CHANGED'

    fork = next(x for x in c27.body if isinstance(x, ast.FunctionDef) and x.name == 'fork')
    statements = ast.unparse(fork)
    mask = 'sanitized = PublicGrid(before.x, before.y, before.goal_x, before.goal_y, before.direction, False)'
    predict = 'action = no_probe_choose(kind, model, sanitized)'
    clear = 'model.evidence.pop(exposed_edge, None)'
    assert mask in statements and predict in statements and clear in statements, 'C27_MASK_SOURCE_CHANGED'
    assert statements.index(mask) < statements.index(predict) < statements.index(clear), 'C27_CHOOSE_CLEAR_ORDER_CHANGED'

    native = ast.unparse(get_method(c23, 'NativeSelective', 'choose'))
    conventional = ast.unparse(get_method(c23, 'ConventionalProbabilistic', 'choose'))
    assert 'status = int(st.front_blocked)' in native and 'self.evidence[edge]' in native, 'C23_NATIVE_EVIDENCE_CHANGED'
    assert 'bool(st.front_blocked)' in conventional and 'self.posterior[edge]' in conventional, 'C23_CONVENTIONAL_EVIDENCE_CHANGED'
    return {'pinned_blobs': dict(PINNED_BLOBS),
            'r1_bool_only': True, 'c27_fabricated_clear_before_choice': True,
            'c23_native_and_conventional_update_from_front_bool': True}


class SensorBoundaryWitness(unittest.TestCase):
    def test_three_information_states_require_three_distinct_encodings(self):
        readings = tuple(Reading)
        encoded = [suggested_information_envelope(r) for r in readings]
        self.assertEqual(len(set(encoded)), 3)
        self.assertEqual(encoded[0], (False, None))
        self.assertEqual(encoded[1], (True, False))
        self.assertEqual(encoded[2], (True, True))

    def test_legacy_projection_collapses_unobserved_and_observed_clear(self):
        self.assertIs(legacy_masked_value(Reading.UNOBSERVED), False)
        self.assertIs(legacy_masked_value(Reading.OBSERVED_CLEAR), False)
        self.assertIs(legacy_masked_value(Reading.OBSERVED_BLOCKED), True)
        self.assertEqual(len(set(map(legacy_masked_value, Reading))), 2)

    def test_retrospective_decision_cannot_be_undone_by_later_evidence_removal(self):
        m = SyntheticEdgeModel()
        state = PublicStub(front_blocked=True)
        chosen = c27_order_witness(m, state)
        self.assertEqual(chosen, 0)
        self.assertEqual(m.choices, [((3, 4, 1), 0)])
        self.assertEqual(m.evidence, {})
        # An accurate blocked public value would be a different input.
        true_model = SyntheticEdgeModel()
        self.assertEqual(true_model.choose(state), 1)

    def test_invalid_epistemic_input_rejected(self):
        for wrong in (None, False, 1, 'blocked'):
            with self.assertRaises(ValueError):
                suggested_information_envelope(wrong)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner-root', type=Path, help='Existing exact Yggdrasil PR #521 checkout (read only)')
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SensorBoundaryWitness)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print('ACC142_SEMANTIC_WITNESS_PASS=4; ORIGINAL_OWNER_SOURCE_RUNTIME=NOT_EXECUTED')
    if args.owner_root:
        print('ACC142_PINNED_SOURCE_AUDIT_PASS=', audit_exact_owner_sources(args.owner_root))
    else:
        print('ACC142_PINNED_SOURCE_AUDIT=UNVERIFIED_NO_QUALIFIED_CHECKOUT')


if __name__ == '__main__':
    main()
