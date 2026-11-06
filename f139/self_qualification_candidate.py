"""One bounded FORGE engineering proposal primitive; no live-owner authority.

Only module-scope TestCase fixture imports in four exact source files may be
rewritten. This does not extend native research lanes, publish, queue, dispatch,
install code, or decide acceptance. The existing qualification checker is the
only evaluator; it must independently bind source and verify coverage/results.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import math
from pathlib import Path
import re

from f139.check_test_discovery_inventory import fixture_normalized_ast

SCHEMA = 'forge.f139.self-qualification-proposal.v1'
KIND = 'fixture-import-module-aliases'
PROFILE_SOURCE = '24364fb039e32db38ca9d9fd5a6e92e50b66ac88'
PROFILE_RUN = 42304091585
EXPECTED_REPEATED_CASES = 48
MINIMUM_SPEEDUP = 1.03
# Before identities are pinned to accepted main 243707c1, not caller claims.
RULES = {
    'f139/test_nci04_g36_owner_integration.py': (
        '3d8da51994573becb0c5df84dfbf349fb74abafeeaf90dd3949a4706f96e2855',
        (('f139.test_nci04_g32_owner_custody', 'OriginalOwnerG32Tests', 'self_fixture_g32'),)),
    'f139/test_nci04_model_free_search.py': (
        '96be976872bf0b49c202cbbc7c45d906ca6bf77772e111f2e83bc5efe1b86447',
        (('f139.test_nci04_owner_model_free_bootstrap', 'LocalG29OriginalOwnerTests', 'self_fixture_bootstrap'),)),
    'f139/test_nci04_v14_dual_native_owner_publication.py': (
        '9e37504405e5f2f7f12624bd8b3d94be6fa8e4b94ef10d1703a9ed9c9f0fb8a0',
        (('f139.test_nci04_owner_free_reasoner_proposal', 'NativeFreeReasonerCustodyTests', 'self_fixture_reasoner'),)),
    'f139/test_nci04_g32_owner_custody.py': (
        '3084d635ec11b79c3d92385a51e9aa775c5a772f4a3f86bb220f79b0855d42e6',
        (('f139.test_nci04_owner_ledger', 'LedgerTests', 'self_fixture_ledger'),
         ('f139.test_nci04_worker_v2', 'V2ContractTests', 'self_fixture_worker'))),
}


def need(ok, reason):
    if not ok:
        raise ValueError('F139_SELF_QUALIFICATION_'+reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def rewrite(path, before):
    need(path in RULES and type(before) is bytes and 0 < len(before) < 100000,
         'PATH_OR_SOURCE_SIZE')
    identity, rules = RULES[path]
    # Git checkout newline conversion is metadata, not a different recipe.
    # Retain and bind the actual before/after bytes separately in the proposal.
    need(sha(before.replace(b'\r\n',b'\n')) == identity, 'FROZEN_BEFORE_SOURCE_DRIFT')
    source = before.decode('utf-8')
    tree = ast.parse(source)
    lines = before.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1]+len(line))
    def span(node):
        return (offsets[node.lineno-1]+node.col_offset,
                offsets[node.end_lineno-1]+node.end_col_offset)
    changes = []
    for module, name, alias in rules:
        need(not any(isinstance(n, ast.Name) and n.id == alias for n in ast.walk(tree)),
             'FIXTURE_ALIAS_COLLISION')
        nodes = [n for n in tree.body if isinstance(n, ast.ImportFrom) and
                 n.module == module and any(a.name == name and a.asname is None for a in n.names)]
        need(len(nodes) == 1, 'FIXTURE_IMPORT_NOT_EXACT')
        node = nodes[0]
        remaining = [a for a in node.names if a.name != name]
        replacement = ('from '+module+' import '+', '.join(
            a.name+(' as '+a.asname if a.asname else '') for a in remaining)+'\n') if remaining else ''
        replacement += 'import '+module+' as '+alias
        changes.append((*span(node), replacement.encode()))
        uses = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == name]
        need(uses and all(isinstance(n.ctx, ast.Load) for n in uses), 'FIXTURE_REBOUND_OR_UNUSED')
        for use in uses:
            changes.append((*span(use), (alias+'.'+name).encode()))
    ordered = sorted(changes)
    need(all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:])),
         'OVERLAPPING_REWRITE')
    after = before
    for start, end, replacement in reversed(ordered):
        after = after[:start]+replacement+after[end:]
    need(after != before and fixture_normalized_ast(source) ==
         fixture_normalized_ast(after.decode('utf-8')), 'ASSERTION_OR_FIXTURE_SEMANTICS_CHANGED')
    return after


def propose(files, *, source_sha, source_tree):
    need(type(files) is dict and set(files) == set(RULES), 'EXACT_FOUR_PATHS_REQUIRED')
    need(all(type(value) is str and re.fullmatch('[a-f0-9]{40}', value)
             for value in (source_sha, source_tree)), 'INDEPENDENT_SOURCE_REQUIRED')
    changes = []
    for path in sorted(RULES):
        after = rewrite(path, files[path])
        changes.append(dict(path=path, before_sha256=sha(files[path]),
                            before_canonical_sha256=RULES[path][0],
                            after_sha256=sha(after),
                            after_canonical_sha256=sha(after.replace(b'\r\n',b'\n')),
                            after_base64=base64.b64encode(after).decode('ascii')))
    return canonical(dict(schema=SCHEMA, kind=KIND, repository='spoonman136668-ai/FORGE',
        source_sha=source_sha, source_tree=source_tree,
        generator_sha256=sha(Path(__file__).read_bytes()),
        profile_source=PROFILE_SOURCE, profile_run=PROFILE_RUN,
        changes=changes, minimum_speedup=MINIMUM_SPEEDUP,
        live_owner_authorized=False, dispatch_authorized=False,
        accepted_ref_mutations=0, optimizer_reward=False, scientific_first_use=False))


def inspect_proposal(raw, files, *, source_sha, source_tree):
    need(type(raw) is bytes and 0 < len(raw) < 300000, 'PROPOSAL_SIZE')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'DUPLICATE_KEY')
            result[key] = value
        return result
    doc = json.loads(raw, object_pairs_hook=unique,
                     parse_constant=lambda _: need(False, 'NONFINITE_JSON'))
    expected = propose(files, source_sha=source_sha, source_tree=source_tree)
    # Re-derive every byte; a digest, caller signature or supplied patch does
    # not authorize an arbitrary edit, even within one of the four files.
    need(canonical(doc) == expected, 'UNAPPROVED_PATCH_OR_AUTHORITY')
    return {row['path']: base64.b64decode(row['after_base64'], validate=True)
            for row in doc['changes']}


def assess_times(runs):
    need(type(runs) is list and len(runs)==4 and
         [r.get('arm') for r in runs]==['baseline','proposal','proposal','baseline'],
         'FROZEN_ABBA_ORDER_REQUIRED')
    values=[r.get('seconds') for r in runs]
    need(all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in values),
         'TIMING_INVALID')
    ratios=[values[0]/values[1],values[3]/values[2]]
    aggregate=(values[0]+values[3])/(values[1]+values[2])
    return dict(paired_speedups=ratios, aggregate_speedup=aggregate,
                development_threshold_met=aggregate>=MINIMUM_SPEEDUP and all(v>=1.0 for v in ratios))
