"""One-time read-only D1 Time Travel checkpoint validation.
No bookmark values printed, stored in public artifacts, or used for restore.
Actual live restore is destructive and is never attempted.
"""
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class RecoveryCheck:
    supported_backend: bool
    bookmark_shape_verified: bool
    bookmark_readback_qualified: bool
    restore_attempted: bool = False
    full_backup_restore_qualified: bool = False
    live_schema_install_approved: bool = False

def validate_recovery(db_result, bookmark_result):
    # Both inputs must have come from the independently identity-matched
    # account/database read-only APIs, not arbitrary data from D1 itself.
    db=(db_result or {}).get("result") if isinstance(db_result,dict) else None
    version=db.get("version") if isinstance(db,dict) else None
    if version!="production":
        return RecoveryCheck(False,False,False)
    if not isinstance(bookmark_result,dict) or bookmark_result.get("success") is not True:
        return RecoveryCheck(True,False,False)
    item=bookmark_result.get("result")
    value=item.get("bookmark") if isinstance(item,dict) else None
    good=(isinstance(value,str) and 20<=len(value)<=160 and
          re.fullmatch(r"[A-Fa-f0-9-]+",value) is not None and
          value.count("-")>=2)
    return RecoveryCheck(True,good,good)
