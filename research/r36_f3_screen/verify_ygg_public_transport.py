"""Run exact pinned Y070 public-transport parity on a legal development trial.

No candidate selection or scientific first use. Proves the new sampler seam
matches the existing public sensor transport before any experimental plans.
"""
import argparse
from ygg_public_instrument import BASELINE,install_public_schedule
from run_yggdrasil_development import DEV,PAIRS,load_pinned,validate_portfolio,ARM

def run(root):
    validate_portfolio()
    z=load_pinned(root)
    m=z.m
    seed=DEV[0]
    pair=PAIRS[0]
    family=z.FAMILIES[0]
    policy=z.POLICIES[0]
    try:
        m.y58.install_transposition(1,pair,{"anchor_pair_checks":0})
        original=m.candidate(seed,family,policy,ARM)
        with install_public_schedule(z,BASELINE):
            proposed=m.candidate(seed,family,policy,ARM)
        if original["public_scalar_reads"]!=10 or proposed["public_scalar_reads"]!=10:
            raise ValueError("F3_TRANSPORT_PUBLIC_QUOTA_DRIFT")
        if original["rows"]!=proposed["rows"]:
            raise ValueError("F3_TRANSPORT_BASELINE_NOT_EQUIVALENT")
        if proposed["public_scalar_reads"]!=original["public_scalar_reads"]:
            raise ValueError("F3_TRANSPORT_READ_DRIFT")
        return {"status":"PINNED_DEVELOPMENT_PUBLIC_TRANSPORT_PARITY_PASS",
                "source_commit":"5797a257a75fe139313e8486cd1a1ae79c44b148",
                "seed":seed,"pair":list(pair),"public_reads":10,
                "originals_executed":0,"sealed_first_uses_consumed":0}
    finally:
        m.y49.restore_environment()

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--yggdrasil-root",required=True)
    args=parser.parse_args()
    print(run(args.yggdrasil_root)["status"])
