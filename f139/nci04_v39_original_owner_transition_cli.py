"""V39 source-bound successor through the existing original-owner CLI."""
from f139 import nci04_v39_source_transition as contract
from f139.nci04_v38_original_owner_transition_cli import main as shared_main


def main(argv=None):
    return shared_main(argv, _contract=contract)


if __name__ == "__main__":
    main()
