"""Bounded V38 source/routing guard. This file confers no release authority."""
from __future__ import annotations
import ast
import fnmatch
import re
import subprocess
from pathlib import Path

BASELINE = '08b2fed1ac8b91fb45f4dbd5704b05d7fc5f6978'
PATHS = frozenset(['f139/local_controller.py','f139/nci04_owner_ledger.py','f139/nci04_v32_original_owner_transition_cli.py','f139/nci04_v38_original_owner_transition_cli.py','f139/nci04_v38_source_transition.py','f139/test_nci04_v38_source_transition.py', 'f139/test_nci04_v37_source_transition.py','f139/check_v38_release_source.py','f139/nci04_partial_publication_custody.py','.github/workflows/f139-v37-original-owner-release.yml','.github/workflows/f139-v38-original-owner-release.yml','docs/F139-V38-DIAGNOSTIC-OWNER-RELEASE.md'])


def verify(root, *, get=None):
    root = Path(root)
    if get is None:
        def get(*args):
            return subprocess.check_output(['git', '-C', str(root), *args],
                text=True, timeout=30).strip()
    head = get('rev-parse', 'HEAD')
    if re.fullmatch('[a-f0-9]{40}', head) is None or get('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('F139_V38_SOURCE_NOT_EXACT_CLEAN')
    if get('merge-base', BASELINE, head) != BASELINE:
        raise ValueError('F139_V38_ACCEPTED_BASELINE_DRIFT')
    if set(get('diff', '--name-only', BASELINE, head).splitlines()) != PATHS:
        raise ValueError('F139_V38_BOUNDED_MANIFEST_DRIFT')
    release = 'f139-owner-release-' + head
    selected = []
    for path in sorted((root/'.github/workflows').glob('f139-v*-original-owner-release*.yml')):
        source = path.read_text()
        if path.name == 'f139-v37-original-owner-release.yml':
            # Existing historical V37 installer must not process V38 releases.
            if "&& github.sha == '3dd63467d649a347692b6b42cd5074ff1038d3de'" not in source:
                raise ValueError('F139_V38_CONSUMED_V37_NOT_SEALED')
            continue
        rows = re.findall(r'^    branches: (\[.*\])$', source, re.M)
        for row in rows:
            patterns = ast.literal_eval(row)
            if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
                raise ValueError('F139_V38_RELEASE_PATTERN_DRIFT')
            if any(fnmatch.fnmatchcase(release, p) for p in patterns):
                selected.append(path.name)
    if selected != ['f139-v38-original-owner-release.yml']:
        raise ValueError('F139_V38_COMPETING_RELEASE_ROUTE')
    return head


if __name__ == '__main__':
    print('F139_V38_EXACT_RELEASE_SOURCE=' + verify(Path(__file__).resolve().parents[1]))
