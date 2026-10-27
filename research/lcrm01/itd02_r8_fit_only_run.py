#!/usr/bin/env python3
"""FIT-only original-world training, custody and lossless six-field model export.

No CHECK or DEV episodes are invoked. The model is recorded only after the
canonical hash matches the source training function's frozen output.
"""
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from itd02_r8_original_world_preflight import preflight
from itd02_r8_sixfield_fit import train_sixfield_fit


def canonical_model(learned):
    return [(list(k), [(list(a), n) for a, n in sorted(c.items())])
            for k, c in sorted(learned.items())]


def verify_and_serialize(learned, expected_digest):
    canonical = canonical_model(learned)
    payload = json.dumps(canonical, separators=(",", ":")).encode()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_digest:
        raise ValueError("R8_FIT_MODEL_DIGEST_MISMATCH")
    if not canonical or any(
        len(k) != 3 or len(entries) == 0 or
        any(type(n) is not int or n <= 0 for _, n in entries)
        for k, entries in canonical
    ):
        raise ValueError("R8_FIT_MODEL_MALFORMED")
    # Confirm that the saved representation reproduces the trained counters.
    rebuilt = defaultdict(Counter)
    for k, entries in json.loads(payload):
        key = tuple(k)
        if key in rebuilt:
            raise ValueError("R8_FIT_MODEL_DUPLICATE_KEY")
        rebuilt[key] = Counter({tuple(a): n for a, n in entries})
    if rebuilt != learned:
        raise ValueError("R8_FIT_MODEL_ROUNDTRIP_FAILED")
    return payload


def main():
    preflight()
    learned, receipt = train_sixfield_fit()
    if receipt["fit_events"] != 12000 or receipt["fit_seeds"] != [81400, 81423]:
        raise ValueError("R8_FIT_RECEIPT_DRIFT")
    payload = verify_and_serialize(learned, receipt["fit_model_sha256"])
    root = Path(os.environ["RUNNER_TEMP"]) / "itd02-r8-fit"
    root.mkdir(parents=True, exist_ok=True)
    target = root / "fitted-sixfield-model.json"
    if target.exists():
        raise ValueError("R8_FIT_MODEL_REFUSE_OVERWRITE")
    target.write_bytes(payload)
    if hashlib.sha256(target.read_bytes()).hexdigest() != receipt["fit_model_sha256"]:
        raise ValueError("R8_FIT_WRITTEN_MODEL_DIGEST_MISMATCH")
    print(json.dumps({"gate": "ITD02-R8-FIT-ONLY",
                      "result": "FIT_SOURCE_QUALIFIED",
                      **receipt,
                      "model_artifact": target.name,
                      "model_bytes": len(payload),
                      "model_roundtrip": True,
                      "development_episodes": 0,
                      "check_episodes": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
