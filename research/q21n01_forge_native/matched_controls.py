"""Q21N-01 seven-arm comparator compatibility, using handwritten toys ONLY.

Original Q21 trained estimators are verified by their immutable Git blobs and
reused as scientific comparators, not as original cohorts or authority.
This module has no generator imports that draw rows, no science admission,
and no API accepting Q21N-01 FIT/VALID/DEV cohorts. A qualified real FSA
worker must separately implement admitted role custody before experiment.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEGACY = ROOT / "research" / "q21_information_budget"
SOURCE_BLOBS = {
    "models.py": "52d539a1faff79a42224effd97805a26a9b11e65",
    "sourcefree.py": "e1779e270dca010ac386896146a6b60cee0a8f11",
    "evaluator.py": "4109e68a4fdc32d928343207eb53ce5be54b9003",
}
ARM_NAMES = (
    "FULL_CURRENT_COUNTS", "TRAINED_CURRENT_LOGISTIC",
    "LAGGED_PUBLIC_COUNTS", "TRAINED_2_STATE_ACTION_RNN",
    "TRAINED_4_STATE_ACTION_RNN", "UNSUPERVISED_2_STATE_ACTION_HMM",
    "UNSUPERVISED_4_STATE_ACTION_HMM",
)


class ComparatorBlocked(RuntimeError):
    pass


def need(ok, code):
    if not ok:
        raise ComparatorBlocked("Q21N01_CONTROLS_" + code)


def git_blob(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def source_guard():
    sys.path.insert(0, str(HERE))
    import prereg_guard as g
    doc, predecessor = g.read_protocol()
    g.validate(doc, predecessor)
    for filename, expected in SOURCE_BLOBS.items():
        path = LEGACY / filename
        need(path.is_file() and git_blob(path.read_bytes()) == expected,
             "QUALIFIED_MODEL_SOURCE_CHANGED_" + filename)
    names = tuple(doc["comparators"]["full_current"]
                  + doc["comparators"]["history"])
    need(names == ARM_NAMES, "FROZEN_ARM_INVENTORY_CHANGED")
    settings = doc["comparators"]["training"]
    need(settings["rnn_epochs"] == 60 and
         settings["rnn_restarts"] == 3 and
         settings["hmm_em_epochs"] == 40 and
         settings["hmm_restarts"] == 3, "FROZEN_TRAINING_BUDGET_CHANGED")
    need(doc["admission"]["current_authorization"] == "NONE",
         "UNEXPECTED_SCIENCE_AUTHORITY")
    return doc


def estimator_api():
    # Import only after source bytes are checked; importing never draws a
    # generator seed, calls a runner, or authenticates a scientific start.
    source_guard()
    sys.path.insert(0, str(LEGACY))
    import sourcefree as public
    import models
    import evaluator
    need(tuple(evaluator.ARM_NAMES) == ARM_NAMES and
         tuple(models.MODEL_NAMES) == (
             ARM_NAMES[1], ARM_NAMES[3], ARM_NAMES[4],
             ARM_NAMES[5], ARM_NAMES[6]), "MODEL_API_DRIFT")
    return public, models, evaluator


def handwritten_examples():
    """Deliberately four transitions, not 32: cannot be study episodes."""
    family = ARM_NAMES  # no sampling or private state
    del family
    name = "A_PERSISTENT_ACTION_FLIP"
    return [
        (name, ((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)),
         (0, 1, 0, 1)),
        (name, ((1, 0), (0, 0), (1, 1), (0, 1), (0, 0)),
         (1, 0, 1, 0)),
        (name, ((0, 1), (1, 0), (1, 1), (0, 0), (1, 0)),
         (1, 1, 0, 0)),
    ]


def compare_toy_only(train, valid):
    """Require exact handwritten fixtures; never accept prospective roles."""
    cases = handwritten_examples()
    need(type(train) is list and type(valid) is list and
         train == cases[:2] and valid == cases[2:],
         "NOT_EXACT_HANDWRITTEN_TOY")
    public, models, evaluator = estimator_api()
    import generator
    for row in train + valid:
        need(row in cases and len(row) == 3 and
             len(row[2]) == 4 and len(row[1]) == 5,
             "COHORT_OR_PRIVILEGED_ROW_REFUSED")
    generator.public_rows(train + valid)
    scores = {}
    model_checks = {}

    for name, history in ((ARM_NAMES[0], False), (ARM_NAMES[2], True)):
        counts = public.fit_counts(train, history)
        forecast = lambda row, model=counts, h=history: public.forecast_counts(model, row, h)
        scores[name] = sum(public.nll(row, forecast(row)) for row in valid) / len(valid)
        model_checks[name] = len(counts)

    for name in models.MODEL_NAMES[:3]:
        fit, receipt = models.fit_gradient(name, train, valid,
                                           epochs=60, restarts=3)
        predictions = models.model_predict(fit, valid[0])
        need(len(predictions) == 4 and
             receipt["selected_restart"] in (0, 1, 2) and
             1 <= receipt["selected_epoch"] <= 60,
             "GRADIENT_FROZEN_TRAINING_INVALID")
        scores[name] = receipt["fit_validation_nll"]
        model_checks[name] = models.checkpoint_sha(fit)

    for hidden, name in ((2, models.MODEL_NAMES[3]), (4, models.MODEL_NAMES[4])):
        fit, receipt = models.fit_hmm(hidden, train, valid,
                                      epochs=40, restarts=3)
        need(len(models.model_predict(fit, valid[0])) == 4 and
             1 <= receipt["selected_epoch"] <= 40 and
             receipt["selected_restart"] in (0, 1, 2),
             "HMM_FROZEN_TRAINING_INVALID")
        scores[name] = receipt["fit_validation_nll"]
        model_checks[name] = models.checkpoint_sha(fit)

    need(set(scores) == set(ARM_NAMES) and
         all(type(score) is float and math.isfinite(score) and score >= 0
             for score in scores.values()), "MISSING_OR_INVALID_ARM")
    # Pre-DEV selection must depend ONLY on FIT_VALID public NLL.
    # The two disjoint groups are selected separately with the old
    # immutable selection helper, never with DEV outcomes.
    arms = {name: {"fit_cost": {"fit_validation_nll": score}}
            for name, score in scores.items()}
    current = evaluator.select_pre_dev_arm(arms, ARM_NAMES[:2])
    history = evaluator.select_pre_dev_arm(arms, ARM_NAMES[2:])
    need(current in ARM_NAMES[:2] and history in ARM_NAMES[2:],
         "ARM_FAMILY_SELECTION_LEAK")
    return {
        "schema": "forge.q21n01.matched-controls-handwritten-preflight.v1",
        "validation_arm_nll": scores,
        "current_fit_valid_winner": current,
        "history_fit_valid_winner": history,
        "seven_frozen_comparators": list(ARM_NAMES),
        "frozen_source_blobs": SOURCE_BLOBS,
        "handwritten_fit_arms": 7,
        "role_cohorts_generated": 0,
        "role_models_trained": 0,
        "protected_first_use": False,
        "fsa_authorization": "NOT_GRANTED",
        "experiment_started": False,
    }


def preflight():
    return compare_toy_only(handwritten_examples()[:2], handwritten_examples()[2:])


if __name__ == "__main__":
    print(json.dumps(preflight(), sort_keys=True, allow_nan=False))
