#!/usr/bin/env python3
"""Validate a previously saved R8 FIT artifact; never opens MiniGrid."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from itd02_r8_fit_model_loader import EXPECTED_SHA, load_fit_model


def inspect(zip_path):
    with zipfile.ZipFile(zip_path) as bundle:
        if set(bundle.namelist()) != {"fit-receipt.json", "fitted-sixfield-model.json"}:
            raise ValueError("FIT_ARTIFACT_MEMBERS_MISMATCH")
        model = bundle.read("fitted-sixfield-model.json")
        receipt = bundle.read("fit-receipt.json")
    instance = load_fit_model(model, receipt)
    if len(instance.learned) != 23:
        raise ValueError("FIT_MODEL_RECONSTRUCTION_MISMATCH")
    return {"result": "R8_FIT_MODEL_INTAKE_PASS",
            "model_sha256": hashlib.sha256(model).hexdigest(),
            "model_bytes": len(model),
            "learned_entries": len(instance.learned),
            "fit_events": 12000,
            "check_episodes": 0,
            "development_episodes": 0,
            "scientific_accepted": False}


if __name__ == "__main__":
    print(json.dumps(inspect(Path(sys.argv[1])), sort_keys=True))
