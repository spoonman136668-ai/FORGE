"""Read-only join of assignment claims to authenticated native DEV observations.

The caller must independently establish that the assignment was captured before
outcome access. This module cannot establish event time, independent assignment,
randomization, scientific acceptance, or authority to train/dispatch.
"""
from __future__ import annotations

from f139.nci04_prospective_assignment import validate_assignment


def join_prospective_development(assignment, feedback, *,
                                 expected_eligible_hashes):
    """Fail closed on missing, conflicting, or non-development observations."""
    if not isinstance(feedback, dict):
        raise ValueError("F139_PROSPECTIVE_FEEDBACK_MISSING")
    required = ("ticket", "owner_source_sha", "candidate_sha256",
                "artifact_sha256", "report_sha256", "run_id",
                "original_signed_admission_sha256")
    if any(not isinstance(feedback.get(k), (str, int)) or
           isinstance(feedback.get(k), bool) or not feedback.get(k)
           for k in required):
        raise ValueError("F139_PROSPECTIVE_FEEDBACK_IDENTITY")
    if (feedback.get("schema") != "forge.f139.native-development-feedback.v1"
            or feedback.get("mode") != "OBSERVED_TEST_DIAGNOSTICS_ONLY"
            or feedback.get("development_only") is not True
            or feedback.get("scientific_accepted") is not False
            or feedback.get("optimizer_training_authorized") is not False
            or feedback.get("dispatch_authorized") is not False
            or feedback.get("scientific_first_use") is not False
            or feedback.get("quality_score") is not None
            or feedback.get("selection_probability") is not None
            or feedback.get("decision_time_menu") is not None):
        raise ValueError("F139_PROSPECTIVE_FEEDBACK_AUTHORITY")
    review = validate_assignment(
        assignment, expected_ticket=feedback["ticket"],
        expected_source_sha=feedback["owner_source_sha"],
        expected_candidate_sha256=feedback["candidate_sha256"],
        expected_eligible_hashes=expected_eligible_hashes)
    return {
        "schema": "forge.f139.prospective-feedback-join.v1",
        "mode": "DEVELOPMENT_DIAGNOSTIC_JOIN_ONLY",
        "assignment_sha256": review["assignment_sha256"],
        "native_artifact_sha256": feedback["artifact_sha256"],
        "native_report_sha256": feedback["report_sha256"],
        "original_signed_admission_sha256":
            feedback["original_signed_admission_sha256"],
        "ticket": feedback["ticket"], "run_id": feedback["run_id"],
        "decision_time_independently_proven": False,
        "randomization_independently_proven": False,
        "scientific_accepted": False, "optimizer_training_authorized": False,
        "dispatch_authorized": False,
    }
