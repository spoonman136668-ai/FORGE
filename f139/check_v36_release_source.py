"""Bounded V36 source/routing guard. This file confers no release authority."""
from __future__ import annotations
import ast
import fnmatch
import re
import subprocess
from pathlib import Path

BASELINE = '6e0921e58316810676edd734f42c32eef2afebc7'
PATHS = frozenset({
    '.github/workflows/qualify.yml',
    '.github/workflows/forge-f139-source-qualification.yml',
    '.github/workflows/f139-v36-original-owner-release.yml',
    'docs/F139-V36-ORIGINAL-OWNER-CORRECTIVE-RELEASE.md',
    'f139/check_v36_release_source.py',
    'f139/F139OriginalOwnerMutex.cs',
    'f139/test_nci04_original_owner_mutex.py',
    'f139/test_nci04_v36_source_transition.py',
})


def verify(root, *, get=None):
    root = Path(root)
    if get is None:
        def get(*args):
            return subprocess.check_output(['git', '-C', str(root), *args],
                text=True, timeout=30).strip()
    head = get('rev-parse', 'HEAD')
    if re.fullmatch('[a-f0-9]{40}', head) is None or get('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('F139_V36_SOURCE_NOT_EXACT_CLEAN')
    if get('merge-base', BASELINE, head) != BASELINE:
        raise ValueError('F139_V36_ACCEPTED_BASELINE_DRIFT')
    if set(get('diff', '--name-only', BASELINE, head).splitlines()) != PATHS:
        raise ValueError('F139_V36_BOUNDED_MANIFEST_DRIFT')
    release = 'f139-owner-release-' + head
    selected = []
    for path in sorted((root/'.github/workflows').glob('f139-v*-original-owner-release*.yml')):
        rows = re.findall(r'^    branches: (\[.*\])$', path.read_text(), re.M)
        for row in rows:
            patterns = ast.literal_eval(row)
            if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
                raise ValueError('F139_V36_RELEASE_PATTERN_DRIFT')
            if any(fnmatch.fnmatchcase(release, p) for p in patterns):
                selected.append(path.name)
    if selected != ['f139-v36-original-owner-release.yml']:
        raise ValueError('F139_V36_COMPETING_RELEASE_ROUTE')
    return head


if __name__ == '__main__':
    print('F139_V36_EXACT_RELEASE_SOURCE=' + verify(Path(__file__).resolve().parents[1]))
