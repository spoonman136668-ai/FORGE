"""Pure research/training/self-improvement steering preview for the existing F139 owner.

This is a decision preview, not an admission, authorization, scheduler,
checkpoint writer, scientific evaluation or worker dispatch. Every readiness
and outcome input must be independently authenticated by a future existing-owner
adapter before it is passed here. No live integration exists in this module.
"""
from __future__ import annotations

from f139.nci04_research_steering import LANES, fair_lane_order

SCHEMA = "forge.f139.research-training-self-phase-preview.v2"
MODES = ("AUTO", "RESEARCH", "TRAIN", "SELF_IMPROVE", "HOLD")
PHASES = ("RESEARCH", "TRAIN", "SELF_IMPROVE")
SELF_SCOPE = "FORGE-self"
OUTCOMES = ("IMPROVED", "NO_GAIN", "REGRESSED", "UNVERIFIED")
MAX_RECENT = 64


class PhaseSteeringDenied(ValueError):
    """Input is not an exact, bounded read-only steering snapshot."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise PhaseSteeringDenied("F139_PHASE_STEERING_" + reason)


def _eligible_lanes(value: tuple[str, ...]) -> tuple[str, ...]:
    require(type(value) is tuple and len(value) <= len(LANES)
            and all(type(lane) is str and lane in LANES for lane in value)
            and len(set(value)) == len(value), "ELIGIBILITY_INVALID")
    return value


def _recent_outcomes(value: tuple[tuple[str, str], ...]) -> dict[str, list[str]]:
    require(type(value) is tuple and len(value) <= MAX_RECENT
            and all(type(pair) is tuple and len(pair) == 2
                    and type(pair[0]) is str and pair[0] in LANES
                    and type(pair[1]) is str and pair[1] in OUTCOMES
                    for pair in value), "OUTCOME_INVALID")
    result = {lane: [] for lane in LANES}
    for lane, outcome in value:
        result[lane].append(outcome)
    return result


def preview(*, mode: str, lane: str | None,
            research_ready: tuple[str, ...],
            training_ready: tuple[str, ...],
            admitted_lanes: tuple[str, ...] = (),
            recent_training_outcomes: tuple[tuple[str, str], ...] = (),
            self_improvement_ready: bool = False,
            admitted_phases: tuple[str, ...] = ()) -> dict:
    """Choose one *advisory* next phase from externally verified ready sets.

    Outcome tuples are chronological and must come from verified independent
    native training evaluation receipts (not developer-only CI). Two consecutive
    NO_GAIN/REGRESSED receipts trigger research-first automatic steering.
    Self-improvement readiness must mean separately authenticated FORGE-self
    development scope, not a claim of RSI success or owner permission.
    An admission history permits AUTO to rotate eligible phases fairly.
    A manual override never makes an unready lane eligible or authorizes work.
    """
    require(type(mode) is str and mode in MODES, "MODE_INVALID")
    require(lane is None or (type(lane) is str and lane in LANES), "LANE_INVALID")
    require(mode != "SELF_IMPROVE" or lane is None, "SELF_SCOPE_INVALID")
    require(type(self_improvement_ready) is bool, "SELF_READINESS_INVALID")
    require(type(admitted_phases) is tuple and len(admitted_phases) <= MAX_RECENT
            and all(type(phase) is str and phase in PHASES
                    for phase in admitted_phases), "PHASE_HISTORY_INVALID")
    research = _eligible_lanes(research_ready)
    training = _eligible_lanes(training_ready)
    require(type(admitted_lanes) is tuple and len(admitted_lanes) <= 100000,
            "ADMISSION_HISTORY_INVALID")
    try:
        order = fair_lane_order(admitted_lanes)
    except ValueError as exc:
        raise PhaseSteeringDenied("F139_PHASE_STEERING_ADMISSION_HISTORY_INVALID") from exc
    outcomes = _recent_outcomes(recent_training_outcomes)

    def result(phase: str | None, selected: str | None, status: str) -> dict:
        return {
            "schema": SCHEMA, "requested_mode": mode, "requested_lane": lane,
            "phase": phase, "selected_lane": selected, "status": status,
            "advisory_only": True, "dispatch_authorized": False,
            "scientific_first_use": False, "checkpoint_mutation": False,
            "accepted_ref_mutation": False, "new_controller": False,
            "self_source_mutation": False, "rsi_proven": False,
            "deployment_authorized": False,
        }

    # HOLD drains future admissions; the original owner must finish and
    # reconcile already-started work. No retroactive cancellation is implied.
    if mode == "HOLD":
        return result(None, None, "HOLD_NEW_ADMISSIONS_ONLY")

    ordered = tuple(x for x in order if lane is None or x == lane)
    if mode == "SELF_IMPROVE":
        if self_improvement_ready:
            return result("SELF_IMPROVE", SELF_SCOPE, "MANUAL_ELIGIBLE_PREVIEW")
        return result(None, None, "MANUAL_NO_ELIGIBLE_SELF_IMPROVE")
    if mode in ("RESEARCH", "TRAIN"):
        eligible = research if mode == "RESEARCH" else training
        for target in ordered:
            if target in eligible:
                return result(mode, target, "MANUAL_ELIGIBLE_PREVIEW")
        return result(None, None, "MANUAL_NO_ELIGIBLE_" + mode)

    # Automatic steering is evidence-responsive without touching the original
    # ledger, reallocating existing tasks, or creating training permits.
    stalled = set()
    for target, history in outcomes.items():
        if len(history) >= 2 and all(
                x in ("NO_GAIN", "REGRESSED") for x in history[-2:]):
            stalled.add(target)
    choices = []
    for target in ordered:
        if target in training and target not in stalled:
            choices.append(("TRAIN", target, "AUTO_TRAINING_READY"))
        if target in research:
            status = ("AUTO_TRAINING_STALLED_RESEARCH_FIRST" if target in stalled
                      else "AUTO_RESEARCH_READY")
            choices.append(("RESEARCH", target, status))
    # A lane-pinned AUTO request must never silently switch to FORGE-self.
    if lane is None and self_improvement_ready:
        choices.append(("SELF_IMPROVE", SELF_SCOPE, "AUTO_SELF_IMPROVEMENT_READY"))
    if choices:
        # Select the phase least recently admitted. This is only a preview:
        # the caller must source-verify original-owner admissions first.
        last = {phase: -1 for phase in PHASES}
        for index, phase in enumerate(admitted_phases):
            last[phase] = index
        _, (phase, selected, status) = min(
            enumerate(choices), key=lambda item: (last[item[1][0]], item[0]))
        return result(phase, selected, status)
    if any(target in training for target in ordered):
        return result(None, None, "AUTO_TRAINING_STALLED_NO_RESEARCH")
    return result(None, None, "AUTO_NO_ELIGIBLE_WORK")
