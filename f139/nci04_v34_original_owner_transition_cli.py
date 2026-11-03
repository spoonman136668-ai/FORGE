"""V34 entry point into the existing original-owner custody handoff."""
import argparse
from pathlib import Path

from f139.nci04_native_contract import canonical
from f139.nci04_v32_original_owner_transition_cli import guarded_transition
from f139 import nci04_v34_source_transition as contract


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--event-id", type=int, required=True)
    parser.add_argument("--genenv-executable", type=Path, required=True)
    parser.add_argument("--genenv-toolchain", required=True)
    args = parser.parse_args(argv)
    result = guarded_transition(args.db, args.backup, args.target, args.event_id,
        args.genenv_executable, args.genenv_toolchain, _contract=contract)
    print(canonical(result).decode("ascii"))


if __name__ == "__main__":
    main()
