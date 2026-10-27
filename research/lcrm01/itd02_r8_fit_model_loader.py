"""Read-only custody gate for a previously trained, externally supplied FIT model."""
import hashlib
import json
from collections import Counter

EXPECTED_SHA = "70eaf88c582ec0fc52255f758b7940589e9ba1576c63aa5b243f64184178c799"

def load_fit_model(model_bytes, receipt_bytes):
    if hashlib.sha256(model_bytes).hexdigest() != EXPECTED_SHA:
        raise ValueError("FIT_MODEL_HASH_MISMATCH")
    receipt = json.loads(receipt_bytes)
    if (receipt.get("fit_model_sha256") != EXPECTED_SHA or
        receipt.get("fit_events") != 12000 or
        receipt.get("fit_seeds") != [81400, 81423] or
        receipt.get("check_episodes") != 0 or
        receipt.get("development_episodes") != 0 or
        receipt.get("scientific_accepted") is not False):
        raise ValueError("FIT_RECEIPT_MISMATCH")
    learned = {}
    for key, outcomes in json.loads(model_bytes):
        index = tuple(key)
        if index in learned:
            raise ValueError("FIT_DUPLICATE_STATE_ACTION")
        learned[index] = Counter({tuple(transition): count for transition, count in outcomes})
    if len(learned) != 23 or sum(sum(v.values()) for v in learned.values()) != 12000:
        raise ValueError("FIT_MODEL_COUNTS_MISMATCH")
    from k4t_f4_sixfield_conventional import SixFieldConventional
    return SixFieldConventional(learned)
