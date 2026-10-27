#!/usr/bin/env python3
"""Cold-process intake of frozen native Wingless R8 FIT evidence. No worlds run."""
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path
from k4u_native_minigrid import WingBridge

EXPECTED = "cb873b9371b1a374a213b0dfd19357915c69a44d4fcdd550c5179d4bfa0b9a0a"

def verify(zip_path, executable):
    with zipfile.ZipFile(zip_path) as z:
        if set(z.namelist()) != {"native-fit-receipt.json", "r8-native-fit-snapshot.bin"}:
            raise ValueError("R8_NATIVE_FIT_ARTIFACT_MEMBERS_DRIFT")
        receipt = json.loads(z.read("native-fit-receipt.json"))
        snapshot = z.read("r8-native-fit-snapshot.bin")
    digest = hashlib.sha256(snapshot).hexdigest()
    if digest != EXPECTED or receipt.get("snapshot_sha256") != digest:
        raise ValueError("R8_NATIVE_FIT_SNAPSHOT_HASH_DRIFT")
    required = {"result": "NATIVE_FIT_SNAPSHOT_COLD_RESTORED",
                "native_fit_updates": 12000, "fit_public_transitions": 12000,
                "fit_seed_range": [81400, 81423], "snapshot_bytes": len(snapshot),
                "check_episodes": 0, "development_episodes": 0,
                "cold_restore_identical": True, "scientific_first_use": False,
                "scientific_accepted": False,
                "source_wingless_commit": "9061b256b9d68e4d83b3a10e51fb8b7ef365259f",
                "source_minigrid_commit": "7f5853792ea7f04f75614661006d87fcf949f26d"}
    if any(receipt.get(k) != v for k, v in required.items()):
        raise ValueError("R8_NATIVE_FIT_RECEIPT_DRIFT")
    bridge = WingBridge(executable)
    try:
        bridge.restore(snapshot)
        current = bridge.request("snapshot")
        if current.get("updates") != 12000 or bridge.snapshot() != snapshot:
            raise ValueError("R8_NATIVE_FIT_INDEPENDENT_COLD_RESTORE_DRIFT")
    finally:
        bridge.close()
    return {"gate": "ITD02_R8_NATIVE_FIT_INDEPENDENT_INTAKE",
            "result": "PASS", "native_fit_updates": 12000,
            "snapshot_sha256": digest, "snapshot_bytes": len(snapshot),
            "check_episodes": 0, "development_episodes": 0,
            "scientific_accepted": False, "scientific_first_use": False}

if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1]), Path(os.environ["ITD02_R8_BRIDGE"])), sort_keys=True))
