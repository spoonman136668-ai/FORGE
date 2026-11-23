"""Exact bounded V39 successor source; never installation authority."""
from __future__ import annotations
import ast
import fnmatch
from pathlib import Path
import re
import subprocess

BASELINE = '814f917bd43687a4bc5246d8b729f66e05c994ae'
FROM_V38 = '54d556c3fdf1023d650f76c48ffb1bdc5ccc9135'
PATHS = frozenset({
    '.github/workflows/f139-v38-original-owner-release.yml',
    'docs/F139-V39-REDUNDANCY-FILTER-OWNER-SUCCESSOR.md',
    'f139/check_v39_release_source.py',
    'f139/local_controller.py', 'f139/nci04_owner_ledger.py',
    'f139/nci04_genenv_owner_backend.py',
    'f139/nci04_partial_publication_custody.py',
    'f139/nci04_v32_original_owner_transition_cli.py',
    'f139/nci04_v38_original_owner_transition_cli.py',
    'f139/nci04_v39_original_owner_transition_cli.py',
    'f139/nci04_v39_source_transition.py',
    'f139/test_github_command_transport.py',
    'f139/test_nci04_v38_source_transition.py',
    'f139/test_nci04_v39_source_transition.py',
    'f139/test_nci04_genenv_owner_backend.py',
})


def verify(root, *, get=None):
    root = Path(root)
    if get is None:
        def get(*args):
            return subprocess.check_output(['git', '-C', str(root), *args],
                text=True, timeout=30).strip()
    head = get('rev-parse', 'HEAD')
    if re.fullmatch('[a-f0-9]{40}', head) is None or get('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('F139_V39_SOURCE_NOT_EXACT_CLEAN')
    if (get('merge-base', FROM_V38, BASELINE) != FROM_V38 or
            get('merge-base', BASELINE, head) != BASELINE):
        raise ValueError('F139_V39_ACCEPTED_BASELINE_DRIFT')
    if set(get('diff', '--name-only', BASELINE, head).splitlines()) != PATHS:
        raise ValueError('F139_V39_BOUNDED_MANIFEST_DRIFT')
    # The accepted PR1508 filter, source/replay compiler and its controls must
    # remain byte-identical to the qualified baseline. They are not reauthored.
    if get('diff', '--name-only', BASELINE, head, '--',
           'f139/nci04_prompt_program.py', 'f139/test_nci04_prompt_program.py'):
        raise ValueError('F139_V39_ACCEPTED_FILTER_DRIFT')
    release = 'f139-owner-release-' + head
    selected = []
    for path in sorted((root/'.github/workflows').glob('f139-v*-original-owner-release*.yml')):
        source = path.read_text()
        if path.name == 'f139-v37-original-owner-release.yml':
            if "&& github.sha == '3dd63467d649a347692b6b42cd5074ff1038d3de'" not in source:
                raise ValueError('F139_V39_CONSUMED_V37_NOT_SEALED')
            continue
        for row in re.findall(r'^    branches: (\[.*\])$', source, re.M):
            patterns = ast.literal_eval(row)
            if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
                raise ValueError('F139_V39_RELEASE_PATTERN_DRIFT')
            if any(fnmatch.fnmatchcase(release, p) for p in patterns):
                selected.append(path.name)
    if selected != ['f139-v38-original-owner-release.yml']:
        raise ValueError('F139_V39_COMPETING_RELEASE_ROUTE')
    source = (root/'.github/workflows/f139-v38-original-owner-release.yml').read_text()
    install = source.split('  install-v39:', 1)[1].split('  recover-pretransition-v38:', 1)[0]
    if ("$old='"+FROM_V38+"'" not in install or
            'f139.nci04_v39_original_owner_transition_cli' not in install or
            'f139/check_v39_release_source.py' not in install):
        raise ValueError('F139_V39_SUCCESSOR_ROUTE_DRIFT')
    return head


if __name__ == '__main__':
    print('F139_V39_EXACT_RELEASE_SOURCE=' + verify(Path(__file__).resolve().parents[1]))
