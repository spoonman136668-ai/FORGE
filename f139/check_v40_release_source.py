"""Frozen V40 owner handoff source; never approval or installation authority."""
from pathlib import Path
import hashlib
import re
from f139.nci04_v31_original_owner_transition_cli import git as existing_git_read

BASELINE = 'feb75e7490256a6930698742a43b8d12384fbbca'
PATHS = frozenset({'docs/F139-V40-EXPLICIT-OWNER-HANDOFF.md', 'f139/nci04_v40_guarded_owner_handoff.py', '.github/workflows/f139-v38-original-owner-release.yml', 'f139/test_nci04_v38_source_transition.py', 'f139/nci04_v32_original_owner_transition_cli.py', 'scripts/check_rar_g148_go_cache.py', 'scripts/check_rar_g145_pr_scope.py', 'f139/check_v40_release_source.py', 'scripts/check_rar_g156_dynamic_base_cache.py', 'f139/test_nci04_v40_owner_handoff.py', 'f139/nci04_v40_owner_handoff_approval.py'})
WORKFLOW = '.github/workflows/f139-v38-original-owner-release.yml'
LEGACY_STEPS_SHA256 = '0d2b5c4b774ff66b6151f0b1fa954a58534e9e9bd42da1ffc5b3ebf8e6c61c66'
RECOVERY_SHA256 = '6335107ea111fe303beabfca63954f589a316db28f3e31cbb6119e56e9b8230f'
LEGACY_CONDITION = "github.actor == 'spoonman136668-ai' && github.event.created == true && github.ref == format('refs/heads/f139-owner-release-{0}', github.sha) && github.sha == '42c70d74dd93ef90d0f4618fefefe2206b81eafe'"
HANDOFF_CONDITION = "github.actor == 'spoonman136668-ai' && github.event.created == true && github.ref == format('refs/heads/f139-owner-release-{0}', github.sha) && github.sha != '42c70d74dd93ef90d0f4618fefefe2206b81eafe'"


def verify(root, *, get=None):
    root = Path(root)
    if get is None:
        get = lambda *args: existing_git_read(root,*args)
    head = get('rev-parse','HEAD')
    if re.fullmatch('[a-f0-9]{40}',head) is None or get('status','--porcelain','--untracked-files=all'):
        raise ValueError('F139_V40_SOURCE_NOT_EXACT_CLEAN')
    if get('merge-base',BASELINE,head) != BASELINE:
        raise ValueError('F139_V40_QUALIFIED_BASELINE_DRIFT')
    changed = get('diff','--no-renames','--name-only',BASELINE,head).splitlines()
    if len(changed) != len(PATHS) or set(changed) != PATHS:
        raise ValueError('F139_V40_BOUNDED_MANIFEST_DRIFT')
    if get('diff','--name-only',BASELINE,head,'--','genenv','promptlineage',
           'cmd/f139-genenv-source','go.mod','go.sum',
           '.github/workflows/forge-f139-development-worker.yml','f139/nci04_free_reasoner_provider.py'):
        raise ValueError('F139_V40_ACCEPTED_GENERATOR_WORKER_OR_MODEL_BOUNDARY_DRIFT')
    workflow = (root/WORKFLOW).read_text()
    jobs = workflow.split('jobs:\n',1)[1]
    if set(re.findall(r'^  ([a-z0-9-]+):$',jobs,re.M)) != {'install-v39','recover-pretransition-v38','handoff-v40'}:
        raise ValueError('F139_V40_COMPETING_OWNER_HANDOFF_JOB')
    legacy = workflow.split('  install-v39:',1)[1].split('  recover-pretransition-v38:',1)[0]
    recovery = workflow.split('  recover-pretransition-v38:',1)[1].split('  handoff-v40:',1)[0].rstrip()
    current = workflow.split('  handoff-v40:',1)[1]
    def condition(segment):
        return next(l.strip()[4:] for l in segment.splitlines() if l.strip().startswith('if: '))
    if (condition(legacy) != LEGACY_CONDITION or condition(current) != HANDOFF_CONDITION
            or hashlib.sha256(legacy.split('    steps:',1)[1].encode()).hexdigest() != LEGACY_STEPS_SHA256
            or hashlib.sha256(recovery.encode()).hexdigest() != RECOVERY_SHA256):
        raise ValueError('F139_V40_CONSUMED_RELEASE_OR_RECOVERY_CHANGED')
    for required in ("$old='42c70d74dd93ef90d0f4618fefefe2206b81eafe'",'--plan-only',
                     '-m f139.check_v40_release_source','f139.nci04_v40_guarded_owner_handoff',
                     '--owner-approval-comment ([string]$approval.comment_id)',
                     '--event-id ([string]$approval.comment_id)',
                     'F139_V40_POSTMUTATION_EXISTING_TASK_DISABLED_AND_QUIESCENT'):
        if required not in current:
            raise ValueError('F139_V40_EXPLICIT_SOURCE_OR_AUTHORITY_ROUTE_DRIFT')
    return head


if __name__ == '__main__':
    print('F139_V40_EXACT_RELEASE_SOURCE='+verify(Path(__file__).resolve().parents[1]))
