"""Pure source-only R8 heldout episode contract. No environment imports or execution."""
import json
from pathlib import Path
from itd02_r8_original_world_preflight import preflight

PROTOCOL=Path(__file__).with_name("itd02_r8_frozen_original_minigrid_01.json")
METHODS=("wingless_r8_online_beliefs","wingless_r5_cost_frontier")

def validate_episode_request(family, seed, method):
    preflight()
    p=json.loads(PROTOCOL.read_text())
    if family not in ("empty","fourrooms") or method not in METHODS:
        raise ValueError("R8_EPISODE_FAMILY_OR_METHOD_UNREGISTERED")
    if type(seed) is not int:
        raise ValueError("R8_EPISODE_SEED_TYPE")
    allowed=set()
    for name in ("check_seeds","development_seeds"):
        cohort=p["cohorts"][name]
        allowed.update(range(cohort["start"],cohort["start"]+cohort["count"]))
    if seed not in allowed:
        raise ValueError("R8_EPISODE_SEED_NOT_HELDOUT")
    return {"family":family,"seed":seed,"method":method,"protocol_id":p["protocol_id"]}
