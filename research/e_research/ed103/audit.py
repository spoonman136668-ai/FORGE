"""E-D103 offline schema preflight: no scientific or execution authority granted."""
import json
import math
import re
import sys

COMMIT = '7f5853792ea7f04f75614661006d87fcf949f26d'
BLOB = '660b0a1b769948034c87bb421759c2b9a4f24548'
REQUIRED = {
    'source': ('commit_sha', 'memory_blob', 'runtime_receipt_uri'),
    'freeze': ('approval_ref', 'split_registry_sha256', 'reviewer_ref'),
    'budget': ('episodes', 'environment_steps', 'cpu_seconds', 'peak_rss_bytes', 'train_updates'),
    'interface': ('observations', 'actions', 'reset_policy', 'termination_policy'),
    'witness': ('independent_run_ref', 'original_logs_sha256'),
}
INTEGER_BUDGETS = {'episodes', 'environment_steps', 'peak_rss_bytes', 'train_updates'}


def audit(m):
    if not isinstance(m, dict):
        return {'verdict': 'NOT_QUALIFIED', 'reasons': ['manifest_not_object']}
    problems = []
    if m.get('status') != 'FROZEN_APPROVED':
        problems.append('status_not_frozen_approved')
    for section, fields in REQUIRED.items():
        obj = m.get(section)
        if not isinstance(obj, dict):
            problems.append('missing_section_' + section)
            continue
        for field in fields:
            value = obj.get(field)
            if value is None or type(value) is bool or isinstance(value, str) and not value.strip() or isinstance(value, (dict, list)) and not value:
                problems.append('missing_' + section + '.' + field)
    source = m.get('source') if isinstance(m.get('source'), dict) else {}
    if source.get('commit_sha') != COMMIT:
        problems.append('unverified_source_commit')
    if source.get('memory_blob') != BLOB:
        problems.append('unverified_memory_blob')
    if m.get('holdout_access') != 'PROHIBITED_UNTIL_INDEPENDENT_APPROVAL':
        problems.append('holdout_guard_missing')
    budget = m.get('budget') if isinstance(m.get('budget'), dict) else {}
    for field in REQUIRED['budget']:
        value = budget.get(field)
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
        if field in INTEGER_BUDGETS:
            valid = valid and type(value) is int
        if not valid:
            problems.append('invalid_budget_' + field)
    for section, field in (('freeze', 'split_registry_sha256'), ('witness', 'original_logs_sha256')):
        obj = m.get(section) if isinstance(m.get(section), dict) else {}
        if not isinstance(obj.get(field), str) or not re.fullmatch('[0-9a-f]{64}', obj[field]):
            problems.append('invalid_digest_' + section + '.' + field)
    return {'verdict': 'NOT_QUALIFIED' if problems else 'SCHEMA_COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION', 'reasons': sorted(set(problems))}


if __name__ == '__main__':
    result = audit(json.load(sys.stdin))
    print(json.dumps(result, sort_keys=True))
    sys.exit(2 if result['verdict'] == 'NOT_QUALIFIED' else 0)
