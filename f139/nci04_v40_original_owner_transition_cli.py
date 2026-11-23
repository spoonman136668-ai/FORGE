"""V40 read-only/copy qualification; no live application entrypoint enabled."""
import argparse
import subprocess
import sys
from pathlib import Path

from f139 import nci04_v40_source_transition as contract
from f139.local_controller import SingleOwner
from f139.nci04_v38_original_owner_transition_cli import main as shared_main


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # A merged successor contract cannot opt the original owner into migration.
    # The only native entrypoint in this engineering scope is read-only; an
    # optional rehearsal mutates a disposable copy through the existing helper.
    contract.need("--preflight-only" in argv and "--verify-pretransition-rollback" not in argv,
                  "LIVE_MIGRATION_NOT_AUTHORIZED")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--target", required=True)
    parser.add_argument("--db", type=Path, required=True)
    args, _ = parser.parse_known_args(argv)
    root = Path(__file__).resolve().parents[1]
    def git(*parts):
        return subprocess.check_output(["git", "-C", str(root), *parts],
            text=True, timeout=20).strip()
    contract.need(git("rev-parse", "HEAD") == args.target and
                  git("status", "--porcelain", "--untracked-files=all") == "",
                  "EXACT_CLEAN_CANDIDATE_REQUIRED")
    worker = git("rev-parse", "HEAD:.github/workflows/forge-f139-development-worker.yml")
    contract.need(worker == contract.QUALIFIED_WORKER_BLOB, "QUALIFIED_WORKER_SOURCE_REQUIRED")
    contract.need(args.db.is_file() and not args.db.is_symlink(), "ORIGINAL_DATABASE_REQUIRED")
    with SingleOwner(args.db.resolve().with_suffix(".lock")):
        return shared_main(argv, _contract=contract)


if __name__ == "__main__":
    main()
