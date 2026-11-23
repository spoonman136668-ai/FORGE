"""Explicitly owner-approved V40 entry into the existing original handoff.

Source/copy qualification never calls this live entrypoint. No new owner,
scheduler, queue, signing path or Hybrid admission is introduced.
"""
import argparse
import json
from pathlib import Path

from f139 import nci04_v40_source_transition as contract
from f139.nci04_v40_owner_handoff_approval import (
    find_owner_approval, verify_runtime_context)
from f139.nci04_v32_original_owner_transition_cli import guarded_transition
from f139.local_controller import GitHub


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--target',required=True)
    parser.add_argument('--plan-only',action='store_true')
    parser.add_argument('--db',type=Path)
    parser.add_argument('--backup',type=Path)
    parser.add_argument('--event-id',type=int)
    parser.add_argument('--owner-approval-comment',type=int)
    parser.add_argument('--genenv-executable',type=Path)
    parser.add_argument('--genenv-toolchain')
    args = parser.parse_args(argv)
    verify_runtime_context(args.target)
    if args.plan_only:
        contract.need(all(v is None for v in (args.db,args.backup,args.event_id,
            args.owner_approval_comment,args.genenv_executable,args.genenv_toolchain)),
            'PLAN_CANNOT_HAVE_LIVE_ARGUMENTS')
        print(json.dumps(find_owner_approval(GitHub().native_repo_get,args.target),sort_keys=True))
        return
    contract.need(all(v is not None for v in (args.db,args.backup,args.event_id,
        args.owner_approval_comment,args.genenv_executable,args.genenv_toolchain)),
        'COMPLETE_OWNER_HANDOFF_ARGUMENTS_REQUIRED')
    result = guarded_transition(args.db,args.backup,args.target,args.event_id,
        args.genenv_executable,args.genenv_toolchain,_contract=contract,
        _approval_comment_id=args.owner_approval_comment)
    print(json.dumps(result,sort_keys=True))


if __name__ == '__main__':
    main()
