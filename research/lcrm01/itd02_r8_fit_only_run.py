#!/usr/bin/env python3
"""FIT-only source-authentic qualification. Never invokes DEV or CHECK."""
import json
from pathlib import Path
from itd02_r8_original_world_preflight import preflight
from itd02_r8_sixfield_fit import train_sixfield_fit

def main():
    preflight()
    _,receipt=train_sixfield_fit()
    if receipt["fit_events"]!=12000 or receipt["fit_seeds"]!=[81400,81423]:
        raise ValueError("R8_FIT_RECEIPT_DRIFT")
    print(json.dumps({"gate":"ITD02-R8-FIT-ONLY","result":"FIT_SOURCE_QUALIFIED",
                      **receipt,"development_episodes":0,"check_episodes":0},
                     sort_keys=True))
if __name__=="__main__":main()
