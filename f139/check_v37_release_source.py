"""Bounded V37 source/routing guard. This file confers no release authority."""
from __future__ import annotations
import ast
import fnmatch
import re
import subprocess
from pathlib import Path

BASELINE = 'e4fdeb37623f9aa8955fe0aaf6a1223143c94585'
PATHS = frozenset({'f139/nci04_partial_publication_custody.py', 'f139/test_nci04_partial_publication_custody.py', 'f139/nci04_model_owner_publication.py', 'f139/nci04_model_free_search.py', 'f139/test_nci04_v33_source_transition.py', 'f139/test_nci04_v34_source_transition.py', 'f139/local_controller.py', 'f139/check_v37_release_source.py', 'f139/test_nci04_v37_source_transition.py', 'f139/nci04_v37_original_owner_transition_cli.py', '.github/workflows/f139-v37-original-owner-release.yml', '.github/workflows/qualify.yml', 'f139/nci04_v37_source_transition.py', 'f139/nci04_v32_original_owner_transition_cli.py', '.github/workflows/f139-v36-original-owner-release.yml', 'f139/nci04_owner_ledger.py', 'f139/test_nci04_v36_source_transition.py', '.github/workflows/forge-f139-source-qualification.yml', 'f139/nci04_genenv_owner_backend.py', 'docs/F139-V37-PUBLIC-ORDER-OWNER-HANDOFF.md'})


def verify(root, *, get=None):
    root = Path(root)
    if get is None:
        def get(*args):
            return subprocess.check_output(['git', '-C', str(root), *args],
                text=True, timeout=30).strip()
    head = get('rev-parse', 'HEAD')
    if re.fullmatch('[a-f0-9]{40}', head) is None or get('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('F139_V37_SOURCE_NOT_EXACT_CLEAN')
    if get('merge-base', BASELINE, head) != BASELINE:
        raise ValueError('F139_V37_ACCEPTED_BASELINE_DRIFT')
    if set(get('diff', '--name-only', BASELINE, head).splitlines()) != PATHS:
        raise ValueError('F139_V37_BOUNDED_MANIFEST_DRIFT')
    release = 'f139-owner-release-' + head
    selected = []
    for path in sorted((root/'.github/workflows').glob('f139-v*-original-owner-release*.yml')):
        rows = re.findall(r'^    branches: (\[.*\])$', path.read_text(), re.M)
        for row in rows:
            patterns = ast.literal_eval(row)
            if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
                raise ValueError('F139_V37_RELEASE_PATTERN_DRIFT')
            if any(fnmatch.fnmatchcase(release, p) for p in patterns):
                selected.append(path.name)
    if selected != ['f139-v37-original-owner-release.yml']:
        raise ValueError('F139_V37_COMPETING_RELEASE_ROUTE')
    return head


if __name__ == '__main__':
    print('F139_V37_EXACT_RELEASE_SOURCE=' + verify(Path(__file__).resolve().parents[1]))
