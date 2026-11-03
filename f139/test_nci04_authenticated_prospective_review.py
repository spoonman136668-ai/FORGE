"""Fail-closed tests for authenticated prospective review composition."""
import unittest
from unittest.mock import patch

from f139.nci04_authenticated_prospective_review import (
    review_authenticated_prospective_development,
)


class AuthenticatedReviewTests(unittest.TestCase):
    def test_missing_signed_admission_denied_before_provider(self):
        with patch("f139.nci04_authenticated_prospective_review.development_feedback_v2") as provider:
            with self.assertRaisesRegex(ValueError, "SIGNED_ADMISSION_REQUIRED"):
                review_authenticated_prospective_development(
                    b"forged", {}, None, {}, expected_eligible_hashes=[])
            provider.assert_not_called()

    def test_forged_dict_cannot_replace_signed_admission(self):
        with self.assertRaises(ValueError):
            review_authenticated_prospective_development(
                b"fake", {}, {"ticket": "fake"}, {}, expected_eligible_hashes=[])

    def test_untrusted_raw_bytes_denied(self):
        # Construct without calling admission validators; provider still rejects
        # an invalid ZIP before any assignment claim is joined.
        from f139.nci04_signed_native import NativeAdmission
        signed = NativeAdmission("ticket", "Wingless", "a"*40, 1, "linux",
                                 1, 1, None, "b"*64)
        with self.assertRaises((ValueError, TypeError)):
            review_authenticated_prospective_development(
                b"not a provider ZIP", {}, signed, {},
                expected_eligible_hashes=[])

    def test_valid_provider_still_cannot_upgrade_authority(self):
        from f139.nci04_signed_native import NativeAdmission
        signed = NativeAdmission("ticket", "Wingless", "a"*40, 1, "linux",
                                 1, 1, None, "b"*64)
        review = {"schema": "forge.f139.prospective-feedback-join.v1",
                  "scientific_accepted": False}
        with patch("f139.nci04_authenticated_prospective_review.development_feedback_v2",
                   return_value={"trusted": "diagnostic"}) as provider:
            with patch("f139.nci04_authenticated_prospective_review.join_prospective_development",
                       return_value=review):
                result = review_authenticated_prospective_development(
                    b"zip", {}, signed, {}, expected_eligible_hashes=[])
        provider.assert_called_once()
        self.assertTrue(result["provider_receipt_checked"])
        self.assertFalse(result["original_owner_custody_independently_proven"])
        self.assertFalse(result["assignment_preoutcome_archive_independently_proven"])
        self.assertFalse(result["scientific_accepted"])
        self.assertFalse(result["optimizer_training_authorized"])
        self.assertFalse(result["dispatch_authorized"])


if __name__ == "__main__":
    unittest.main()
