"""Pure, fail-closed admission for a future V19-origin owner source release.

No filesystem, GitHub, controller, task, credential, or SQLite mutations.
An admission receipt is NOT authorization to execute a cutover.
"""
import re

_SHA = re.compile(r"^[0-9a-f]{40}$")

class ReleaseAdmissionDenied(ValueError):
    pass

def assess_v19_origin(*, attested_origin_source, installed_source, policy_source, ledger_source,
                      main_source, checkout_source, release_source,
                      immutable_rule_verified, original_owner_verified,
                      no_inflight, cold_restore_verified, scientific_first_use):
    values = (attested_origin_source, installed_source, policy_source, ledger_source, main_source,
              checkout_source, release_source)
    if any(not isinstance(v, str) or not _SHA.fullmatch(v) for v in values):
        raise ReleaseAdmissionDenied("INVALID_EXACT_SOURCE_ID")
    if any(v != attested_origin_source for v in values[1:4]):
        raise ReleaseAdmissionDenied("ORIGINAL_V19_SOURCE_DRIFT")
    if len(set(values[4:])) != 1:
        raise ReleaseAdmissionDenied("TARGET_SOURCE_REF_DRIFT")
    if main_source == attested_origin_source:
        raise ReleaseAdmissionDenied("NO_SOURCE_TRANSITION")
    controls = (immutable_rule_verified, original_owner_verified,
                no_inflight, cold_restore_verified)
    if any(v is not True for v in controls) or scientific_first_use is not False:
        raise ReleaseAdmissionDenied("CUSTODY_OR_SCIENCE_DENIED")
    return {"schema": "forge.f139.v19-origin-admission.v1",
            "origin_sha": attested_origin_source, "target_sha": main_source,
            "status": "READ_ONLY_ADMISSIBLE_NOT_AUTHORIZED",
            "execute_authorized": False, "scientific_first_use": False}
