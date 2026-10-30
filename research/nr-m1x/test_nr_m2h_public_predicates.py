"""NR-M2H source-only FIT/VAL/CHECK evaluation with independent controls.

Cohort seed sets were prospectively fixed in NR_M2H_PREREG.json *before*
this file and the candidate mechanism were committed. All source outcomes
below are AUTHORED ARTIFICIAL DEV outcomes, NOT original MiniGrid actions.
No CHECK outcome is supplied to any learner, control, or fit selector.
"""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter

from nr_m2d_pinned_original_public import MISSION
from nr_m2e_extended_public import GOAL_MISSION, full_public
from nr_m2h_public_predicates import LearnedPublicPreconditions, feature_vector, public_frame

SPEC = json.loads(Path(__file__).with_name("NR_M2H_PREREG.json").read_text("utf-8"))
SEEDS = SPEC["fixture"]["seeds"]
MISSIONS = (MISSION, GOAL_MISSION, "pick up the red ball")
PIXELS = ((1,0,0), (2,4,0), (4,1,2), (3,2,1))
FIT_SEEDS = tuple(SEEDS["fit"])
VAL_SEEDS = tuple(SEEDS["val"])
CHECK_SEEDS = tuple(SEEDS["check"])
# Authored fixture generator constants are NOT exposed to the candidate or
# comparator: both receive only the same selected source-public transitions.
AUTHOR_FIXTURE_CUE = (1, 2)
AUTHOR_FIXTURE_TARGET = (2, 3)
TARGET_VALUES = tuple((1, a % 6, a) for a in range(7))

def generated_public(seed, task, action, family):
    rng = random.Random(seed * 100003 + task * 1009 + action * 17)
    image = [[list(PIXELS[rng.randrange(4)]) for _ in range(7)] for _ in range(7)]
    # Independently balanced two source-visible conditions in FIT;
    # none of the cue or target positions is passed to the model.
    cue = 2 if task % 2 else 1
    image[AUTHOR_FIXTURE_CUE[0]][AUTHOR_FIXTURE_CUE[1]] = [cue, 4 if cue == 2 else 0, 0]
    if family == "check_b":
        # A previously unobserved condition with a different structural
        # dependency. It is not a random renaming of the fitted cue state.
        image[AUTHOR_FIXTURE_CUE[0]][AUTHOR_FIXTURE_CUE[1]] = [5, 0, 0]
        image[4][1] = [2 if task % 2 else 1, 4 if task % 2 else 0, 0]
    if family.startswith("check"):
        image[6][6] = [8, 5, 17]
    mission = MISSIONS[(seed + task) % len(MISSIONS)]
    direction = (task // 2 + seed) % 4
    return full_public({"image": image, "direction": direction, "mission": mission})

def authored_return(before, action, family):
    returned = json.loads(json.dumps(before))
    if action >= 2:
        if family == "check_b":
            change = before["image"][4][1][0] == 2
            # Changed output conditional on a different unseen cue.
            if change:
                returned["image"][AUTHOR_FIXTURE_TARGET[0]][AUTHOR_FIXTURE_TARGET[1]] = [3, action % 6, action]
        elif before["image"][AUTHOR_FIXTURE_CUE[0]][AUTHOR_FIXTURE_CUE[1]][0] == 2:
            returned["image"][AUTHOR_FIXTURE_TARGET[0]][AUTHOR_FIXTURE_TARGET[1]] = list(TARGET_VALUES[action])
    return full_public(returned)

def fit_pairs():
    for action in range(7):
        for seed in FIT_SEEDS:
            for task in range(16):
                before = generated_public(seed, task, action, "fit")
                yield before, action, authored_return(before, action, "fit")

def val_cases():
    for action in range(7):
        for seed in VAL_SEEDS:
            for task in range(12):
                before = generated_public(seed, task, action, "val")
                yield before, action, authored_return(before, action, "val")

def check_cases(family):
    assert family in ("check_a", "check_b")
    chosen = CHECK_SEEDS[:2] if family == "check_a" else CHECK_SEEDS[2:]
    for action in range(7):
        for seed in chosen:
            for task in range(12):
                before = generated_public(seed, task, action, family)
                yield before, action, authored_return(before, action, family)

class EqualDataExactPublicCount:
    """Independent full-public selected-action table, no unselected oracle."""
    def __init__(self):
        self.fit = {}
        self.seen = 0
    def observe(self, before, action, after):
        key = (action, json.dumps(before, sort_keys=True))
        self.fit.setdefault(key, Counter())[json.dumps(after, sort_keys=True)] += 1
        self.seen += 1
    def predict(self, before, action):
        counts = self.fit.get((action, json.dumps(before, sort_keys=True)), Counter())
        if sum(counts.values()) < 4 or len(counts) != 1:
            return None
        return json.loads(next(iter(counts)))

class IndependentFittedFeatureStump:
    """Separate conventional fitted depth-1 public predicate tree comparator.

    It trains over the same 149 legal components. There are no source cue
    indices, task IDs, fixture labels, or protected science claims here.
    """
    def __init__(self):
        self.fit = [[] for _ in range(7)]
        self._trees = {}
    def observe(self, before, action, after):
        self.fit[action].append((tuple(feature_vector(before)), tuple(feature_vector(after))))
        self._trees.pop(action, None)

    @staticmethod
    def leaf(group, col):
        x = [before[col] for before, _ in group]
        y = [after[col] for _, after in group]
        if all(a == b for a, b in zip(x, y)):
            return ("copy", None) if len(set(x)) >= 2 else ("one-copy", x[0])
        if len(set(y)) == 1:
            return ("write", y[0]) if len(set(x)) >= 2 else ("one-write", (x[0], y[0]))
        return None

    def compile(self, action):
        if action in self._trees:
            return self._trees[action]
        samples = self.fit[action]
        if len(samples) < 4:
            return None
        fitted = []
        for col in range(149):
            plain = self.leaf(samples, col)
            if plain is not None:
                fitted.append((None, plain))
                continue
            selected = None
            # Fit split across ALL public features, not a predetermined front.
            for feature in range(149):
                values = set(obs[feature] for obs, _ in samples)
                if len(values) != 2:
                    continue
                a, b = sorted(values, key=lambda v: (str(type(v)), str(v)))
                left = [pair for pair in samples if pair[0][feature] == a]
                right = [pair for pair in samples if pair[0][feature] == b]
                if len(left) < 4 or len(right) < 4:
                    continue
                lo = self.leaf(left, col)
                hi = self.leaf(right, col)
                if lo is None or hi is None:
                    continue
                changed_l = any(x[col] != y[col] for x, y in left)
                changed_r = any(x[col] != y[col] for x, y in right)
                if changed_l == changed_r:
                    continue
                selected = (feature, a, b, lo, hi)
                break
            fitted.append((selected, None))
        self._trees[action] = fitted
        return fitted

    def predict(self, before, action):
        tree = self.compile(action)
        if tree is None:
            return None
        source = feature_vector(before)
        out = []
        for i, (split, plain) in enumerate(tree):
            if plain is not None:
                typ, v = plain
            elif split is not None:
                feature, a, b, left, right = split
                if source[feature] not in (a, b):
                    return None
                typ, v = left if source[feature] == a else right
            else:
                return None
            if typ == "copy":
                out.append(source[i])
            elif typ == "one-copy" and source[i] == v:
                out.append(source[i])
            elif typ == "write":
                out.append(v)
            elif typ == "one-write" and source[i] == v[0]:
                out.append(v[1])
            else:
                return None
        return full_public(public_frame(out))

def trained():
    candidate = LearnedPublicPreconditions(full_public)
    exact = EqualDataExactPublicCount()
    stump = IndependentFittedFeatureStump()
    fit_cpus = {"candidate": 0, "exact": 0, "stump": 0}
    fitting = list(fit_pairs())
    # All arms receive the exact same 448 source-selected outcomes, in order.
    for before, action, after in fitting:
        start = time.process_time_ns()
        candidate.begin(before); candidate.select(before, action)
        candidate.feedback(before, action, after)
        fit_cpus["candidate"] += time.process_time_ns()-start
        start = time.process_time_ns()
        exact.observe(before, action, after)
        fit_cpus["exact"] += time.process_time_ns()-start
        start = time.process_time_ns()
        stump.observe(before, action, after)
        fit_cpus["stump"] += time.process_time_ns()-start
    return candidate, exact, stump, fitting, fit_cpus

def evaluate(model, cases):
    correct = supported = incorrect = 0
    cpu = 0
    for before, action, after in cases:
        start = time.process_time_ns()
        if isinstance(model, LearnedPublicPreconditions):
            candidate, support = model.predict(before, action)
            predicted = candidate if support["supported"] else None
        else:
            predicted = model.predict(before, action)
        cpu += time.process_time_ns()-start
        if predicted is not None:
            supported += 1
            if predicted == after:
                correct += 1
            else:
                incorrect += 1
    return {"correct": correct, "supported": supported, "incorrect": incorrect,
            "abstained": len(cases) - supported, "cpu_ns": cpu}

class NR_M2HSourceOnly(unittest.TestCase):
    def test_precommitted_train_val_and_custody(self):
        model, exact, stump, data, cpu = trained()
        self.assertEqual(len(data), 448)
        self.assertEqual(model.events, 448)
        self.assertEqual(exact.seen, 448)
        self.assertEqual(sum(map(len, stump.fit)), 448)
        self.assertEqual(len({(a, json.dumps(b, sort_keys=True)) for b, a, _ in data}), 448)
        self.assertEqual(tuple(SEEDS["fit"]), (117011, 117013, 117017, 117019))
        self.assertEqual(tuple(SEEDS["val"]), (119021, 119023))
        self.assertEqual(tuple(SEEDS["check"]), (121031, 121037, 121043, 121049))
        val = list(val_cases())
        self.assertEqual(len(val), 168)
        candidate = evaluate(model, val)
        baseline = evaluate(stump, val)
        self.assertEqual(candidate["incorrect"], 0)
        self.assertEqual(candidate["correct"], 168)
        self.assertEqual(baseline["correct"], 168)
        self.assertEqual(evaluate(exact, val)["supported"], 0)
        self.assertEqual(len(feature_vector(data[0][0])), 149)
        print("NRM2H_SYNTHETIC_FIT_VAL_PASS", json.dumps({"candidate": candidate,
               "strong_stump": baseline, "fit_cpu_ns": cpu}, sort_keys=True))

    def test_frozen_check_no_train_or_candidate_rewrite(self):
        model, exact, stump, fit, fitcpu = trained()
        fitted_frames = {(a, json.dumps(b, sort_keys=True)) for b, a, _ in fit}
        before_checkpoint = model.checkpoint()
        check_a = list(check_cases("check_a"))
        check_b = list(check_cases("check_b"))
        self.assertEqual(len(check_a), 168)
        self.assertEqual(len(check_b), 168)
        for before, action, after in check_a + check_b:
            self.assertNotIn((action, json.dumps(before, sort_keys=True)), fitted_frames)
        scores = {}
        for name, arm in (("candidate", model), ("exact", exact), ("stump", stump)):
            scores[name] = {"check_a": evaluate(arm, check_a),
                            "check_b": evaluate(arm, check_b)}
        self.assertEqual(scores["candidate"]["check_a"]["correct"], 168)
        self.assertEqual(scores["stump"]["check_a"]["correct"], 168)
        self.assertEqual(scores["exact"]["check_a"]["supported"], 0)
        self.assertEqual(scores["candidate"]["check_a"]["incorrect"], 0)
        # Check-B is genuinely changed conditional structure: no claim of
        # source-independent physics. State its raw results without a retrofit.
        self.assertEqual(model.checkpoint(), before_checkpoint)
        self.assertEqual(model.events, 448)
        print("NRM2H_ARTIFICIAL_HELDOUT_SOURCE_ONLY_RESULT", json.dumps(scores, sort_keys=True))
        print("NRM2H_STRONG_CONTROL_PARITY_NO_SCIENTIFIC_ADVANTAGE")

    def test_selected_feedback_negative_and_process_restore(self):
        model, _, _, data, _ = trained()
        raw = model.checkpoint()
        digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(LearnedPublicPreconditions.restore(full_public, raw, digest).checkpoint(), raw)
        with self.assertRaises(ValueError):
            LearnedPublicPreconditions.restore(full_public, raw, "0"*64)
        with self.assertRaises(ValueError):
            LearnedPublicPreconditions.restore(full_public, raw+b" ", hashlib.sha256(raw+b" ").hexdigest())
        b, a, y = data[0]
        fresh = LearnedPublicPreconditions(full_public)
        fresh.begin(b)
        with self.assertRaises(ValueError):
            fresh.feedback(b, a, y)
        with self.assertRaises(ValueError):
            fresh.select(dict(b, world_id=1), a)
        with self.assertRaises(ValueError):
            fresh.select(b, True)
        fresh.select(b, a)
        with self.assertRaises(ValueError):
            fresh.checkpoint()
        with self.assertRaises(ValueError):
            fresh.feedback(b, (a+1)%7, y)
        fresh.feedback(b, a, y)
        with self.assertRaises(ValueError):
            fresh.feedback(b, a, y)
        with tempfile.TemporaryDirectory(prefix="nr-m2h-") as tmp:
            file = Path(tmp) / "source-only-checkpoint.json"
            file.write_bytes(raw)
            program = (
                "import pathlib,sys;"
                "from nr_m2h_public_predicates import LearnedPublicPreconditions;"
                "from nr_m2e_extended_public import full_public;"
                "raw=pathlib.Path(sys.argv[1]).read_bytes();"
                "x=LearnedPublicPreconditions.restore(full_public,raw,sys.argv[2]);"
                "assert x.events==448 and x.checkpoint()==raw"
            )
            result = subprocess.run([sys.executable, "-B", "-c", program, str(file), digest],
                                    cwd=str(Path(__file__).parent),
                                    text=True, capture_output=True, timeout=35)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertLessEqual(len(raw), 5000000)

if __name__ == "__main__":
    unittest.main()
