"""Development-only composition of authenticated provider feedback and assignment claims.

No owner action, randomization proof, scientific acceptance, or training grant.
"""
from __future__ import annotations

from f139.nci04_provider_receipt_v2 import development_feedback_v2
from f139.nci04_prospective_feedback_join import join_prospective_development
from f139.nci04_signed_native import NativeAdmission


def review_authenticated_prospective_development(raw, meta, signed, assignment, *,
                                                  expected_eligible_hashes):
    """Require genuine provider ZIP and previously authenticated native admission.

    Caller must independently authenticate provider metadata, owner admission
    custody, and pre-outcome assignment archival; this module does not.
    """
    if not isinstance(signed, NativeAdmission):
        raise ValueError("F139_PROSPECTIVE_SIGNED_ADMISSION_REQUIRED")
    if not isinstance(assignment, dict) or assignment.get("lane") != signed.lane:
        raise ValueError("F139_PROSPECTIVE_LANE_MISMATCH")
    feedback = development_feedback_v2(raw, meta, signed)
    result = join_prospective_development(
        assignment, feedback, expected_eligible_hashes=expected_eligible_hashes)
    return {
        **result,
        "provider_receipt_checked": True,
        "original_owner_custody_independently_proven": False,
        "assignment_preoutcome_archive_independently_proven": False,
        "scientific_accepted": False,
        "optimizer_training_authorized": False,
        "dispatch_authorized": False,
    }
