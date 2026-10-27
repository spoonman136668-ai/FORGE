#!/usr/bin/env python3
"""Independent R5 FIT checkpoint custody. No world resets or scientific acceptance."""
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path
from k4u_native_minigrid import WingBridge

EXPECTED_SHA = "357acd102b3909c4c27131bdec258b7532f6d1a01b70d67ef4cb01e9ed8e8c56"
EXPECTED = {
    "result": "NATIVE_R5_MATCHED_FIT_SNAPSHOT_COLD_RESTORED",
    "source_wingless_r5_commit": "978825064dd6076058a1a38ae1a9a3d80e28d99e",
    "source_minigrid_commit": "7f5853792ea7f04f75614661006d87fcf949f26d",
    "fit_seed_range": [81400, 81423],
    "fit_public_transitions": 12000,
    "native_fit_updates": 12000,
    "snapshot_bytes": 61082,
    "snapshot_sha256": EXPECTED_SHA,
    "cold_restore_identical": True,
    "check_episodes": 0,
    "development_episodes": 0,
    "scientific_first_use": False,
    "scientific_accepted": False,
}

def verify(artifact, native_bridge):
    with zipfile.ZipFile(artifact) as z:
        if set(z.namelist()) != {"r5-native-fit-snapshot.bin", "r5-native-fit-receipt.json"}:
            raise ValueError("R5_FIT_ARTIFACT_CONTENTS_DRIFT")
        checkpoint = z.read("r5-native-fit-snapshot.bin")
        receipt = json.loads(z.read("r5-native-fit-receipt.json"))
    if hashlib.sha256(checkpoint).hexdigest() != EXPECTED_SHA:
        raise ValueError("R5_FIT_CHECKPOINT_HASH_DRIFT")
    if any(receipt.get(key) != value for key, value in EXPECTED.items()):
        raise ValueError("R5_FIT_RECEIPT_DRIFT")
    bridge = WingBridge(native_bridge)
    try:
        bridge.restore(checkpoint)
        restored = bridge.snapshot()
        if restored != checkpoint:
            raise ValueError("R5_FIT_INDEPENDENT_COLD_RESTORE_DRIFT")
    finally:
        bridge.close()
    return {"gate": "ITD02_R8_R5_INDEPENDENT_FIT_INTAKE",
            "result": "PASS", "snapshot_sha256": EXPECTED_SHA,
            "snapshot_bytes": len(checkpoint),
            "native_fit_updates": receipt["native_fit_updates"],
            "check_episodes": 0, "development_episodes": 0,
            "scientific_first_use": False, "scientific_accepted": False}

if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1]), Path(os.environ["ITD02_R5_BRIDGE"])), sort_keys=True))
