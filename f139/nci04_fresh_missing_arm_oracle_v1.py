"""Versioned, inert native-development oracle for F139's missing-arm proposal.

This is a candidate-specific behavioral check, NOT part of the historical V3
receipt and NOT called by the live worker. Future invocation requires exact
source/owner custody, isolated runner, frozen test inventory and a separately
qualified versioned receipt. No new scheduler, queue, owner, or science grant.
"""
from __future__ import annotations

SCHEMA = "forge.f139.nci04.fresh-missing-arm-oracle.v1"
SUCCESS = "F139_FRESH_MISSING_ARM_ORACLE_V1=PASS"

# Fixed, credential-free command to run ONLY in an already-authenticated,
# isolated candidate checkout. Do not accept a command supplied by a candidate.
ORACLE = '''from yggdrasil.public_causal_cells import PublicCausalCells


def require(ok, why):
    if not ok:
        raise SystemExit("F139_FRESH_MISSING_ARM_" + why)


# All sixteen public addresses, both independent memory banks, zero/one/two
# observed arms, both public binary outcomes and an immutable cold checkpoint.
for retained, slots in ((False, 7), (True, 9)):
    for address in range(slots):
        cell = PublicCausalCells()
        pristine = cell.snapshot()
        require(cell.propose_missing_action(address, retained=retained) is None,
                "UNOBSERVED_BOTH_ARMS")
        require(cell.snapshot() == pristine, "EMPTY_PROPOSAL_MUTATED")
        for observed_arm in (0, 1):
            for observed_outcome in (0, 1):
                cell = PublicCausalCells()
                cell.observe(address, observed_arm, observed_outcome,
                             retained=retained)
                before = cell.snapshot()
                missing = 1 - observed_arm
                require(cell.choose(address, retained=retained) is None,
                        "BASELINE_PREMATURE_CHOICE")
                require(cell.propose_missing_action(address, retained=retained)
                        == missing, "WRONG_MISSING_ARM")
                require(cell.snapshot() == before, "PROPOSAL_MUTATED_STATE")
                if address < (9 if not retained else 7):
                    require(cell.propose_missing_action(address, retained=not retained)
                            is None, "BANK_EVIDENCE_LEAK")
                    require(cell.snapshot() == before, "BANK_PROBE_MUTATED_STATE")
                cold = PublicCausalCells.restore(before)
                require(cold.snapshot() == before, "COLD_RESTORE_BYTES")
                require(cold.propose_missing_action(address, retained=retained)
                        == missing, "COLD_RESTORE_PROPOSAL")
                require(cold.snapshot() == before, "COLD_PROPOSAL_MUTATED")
                # After the proposed missing arm is actually observed, the
                # proposal must stop. This does NOT simulate an environment.
                cell.observe(address, missing, 1 - observed_outcome,
                             retained=retained)
                both = cell.snapshot()
                require(cell.propose_missing_action(address, retained=retained)
                        is None, "ALREADY_OBSERVED_BOTH_ARMS")
                require(cell.snapshot() == both, "BOTH_PROPOSAL_MUTATED")
                decided = 0 if observed_outcome else 1
                if observed_arm == 1:
                    decided = 1 - decided
                require(cell.choose(address, retained=retained) == decided,
                        "POST_OBSERVATION_CHOICE")
                resumed = PublicCausalCells.restore(both)
                require(resumed.snapshot() == both and
                        resumed.propose_missing_action(address, retained=retained)
                        is None and resumed.choose(address, retained=retained)
                        == decided and resumed.snapshot() == both,
                        "COLD_BOTH_ARMS_CHANGED")
print("F139_FRESH_MISSING_ARM_ORACLE_V1=PASS")
'''

COMMAND = ("python", "-B", "-c", ORACLE)
