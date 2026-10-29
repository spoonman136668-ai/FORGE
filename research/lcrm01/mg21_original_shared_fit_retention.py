"""MG21 source-original shared experience and cold-retention engineering."""
import argparse,base64,hashlib,json
from pathlib import Path
import gymnasium as gym
import minigrid
from mg17_original_family_source_qual import attest_source,frozen,digest
from mg18_native_mission_boundary_audit import WingBridge
from mg21_native_retention_actors import family_fit,prepare,ROLES
from mg21_native_original_probe import probe
from mg21_original_tabular_control import Tabular
from research.native.itd02.mg19.genuine_mission_cells import MissionCells

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg21_original_source_shared_fit_prereg.json"
SOURCE="7f5853792ea7f04f75614661006d87fcf949f26d"
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
 "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")

def protocol():
 p=json.loads(FROZEN.read_text(encoding="utf-8"))
 w=p["world"]
 if (p["schema"]!="itd02.mg21.original-source-shared-fit-cold-retention-engineering.v1" or
     p["phase"]!="FROZEN_BEFORE_ENGINEERING_EXECUTABLE__NO_SCIENTIFIC_FIRST_USE" or
     p["parent"]["Farama_MiniGrid"]!=SOURCE or
     tuple(w["families"])!=FAMILIES or
     w["quarantined_fit_seed"]!=918301 or w["quarantined_probe_seed"]!=918303 or
     w["original_fit_cap"]!=24 or w["original_eval_cap"]!=24 or
     not w["permanently_disqualify_both_seeds_from_scientific_fit_dev_sealed"] or
     not all(p["authority"].values())):
  raise ValueError("MG21_FROZEN_BEFORE_SOURCE_PROTOCOL_DRIFT")
 return p

