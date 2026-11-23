"""Exact owner-issued V40 handoff approval; GET-only, never creates approval.

CI/copy success is evidence, not mutation authority. A separate canonical OWNER
comment must explicitly approve the original source/policy/task handoff. This
module does not read keys, mutate state, create refs or grant Hybrid/science.
"""
import json
import os
from pathlib import Path
import re

from f139.nci04_native_contract import canonical, digest
from f139.nci04_autonomy_feed import inspect_policy

REPO = 'spoonman136668-ai/FORGE'
REPO_ID = 1413298198
OWNER = 'spoonman136668-ai'
ISSUE = 807
PREFIX = 'F139-V40-OWNER-HANDOFF '
SCHEMA = 'forge.f139.v40.owner-handoff-approval.v1'
FROM = '42c70d74dd93ef90d0f4618fefefe2206b81eafe'
HEAD = 1462
HEAD_SHA256 = '2e7dd68acd559ebb468ce8e3797e31383f2ab40d805c3c8f988cfc68852f41a5'
BINARY_SHA256 = 'b39ac136662315477bf7176b4058dfaaf16d1975dc58be8e64eb184dbc9fb675'
RULESET = 26049392
KEYS = frozenset({'schema','source_sha','from_source_sha','binary_sha256',
    'expected_original_head_seq','expected_original_head_sha256',
    'qualification_run_id','qualification_artifact_id','qualification_artifact_sha256',
    'owner_source_transition','owner_policy_source_update','pause_resume_existing_task',
    'create_immutable_owner_release_ref','hybrid_admission','scientific_first_use',
    'new_controller','new_scheduler','new_queue','paid_model_calls'})
PUBLIC = (380591943, 'FORGE public Linux and Windows qualification',
    {'linux_f139','linux_native','linux_genenv','windows_f139','windows_native','windows_genenv','linux','windows'})
CONTROLLER = (388529274, 'FORGE F139 native Windows controller qualification',
    {'source (ubuntu-latest)','source (windows-latest)'})
DEVELOPMENT = (388789777, 'FORGE F139-D hosted development rehearsal',
    {'development-rehearsal (ubuntu-latest)','development-rehearsal (windows-latest)'})
ORIGIN = (386521635, 'FORGE F73 protected-main cryptographic origin (no science permission)')


class HandoffDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise HandoffDenied('F139_V40_HANDOFF_' + reason)


def sha(value, size):
    return type(value) is str and re.fullmatch('[a-f0-9]{'+str(size)+'}',value) is not None


def decode_body(body):
    need(type(body) is str and body.startswith(PREFIX) and len(body) <= 4000, 'CANONICAL_OWNER_APPROVAL_REQUIRED')
    try:
        doc = json.loads(body[len(PREFIX):])
    except (ValueError,TypeError) as exc:
        raise HandoffDenied('F139_V40_HANDOFF_APPROVAL_JSON_INVALID') from exc
    need(type(doc) is dict and set(doc) == KEYS and doc['schema'] == SCHEMA
         and body == PREFIX+canonical(doc).decode('ascii'), 'APPROVAL_FIELDS_OR_ENCODING')
    need(sha(doc['source_sha'],40) and doc['from_source_sha'] == FROM
         and doc['source_sha'] != FROM and doc['binary_sha256'] == BINARY_SHA256
         and type(doc['expected_original_head_seq']) is int and doc['expected_original_head_seq'] == HEAD
         and doc['expected_original_head_sha256'] == HEAD_SHA256
         and all(type(doc[k]) is int and doc[k] > 0 for k in ('qualification_run_id','qualification_artifact_id'))
         and sha(doc['qualification_artifact_sha256'],64), 'SOURCE_BINARY_ORIGINAL_CUSTODY_DRIFT')
    need(all(doc[k] is True for k in ('owner_source_transition','owner_policy_source_update',
             'pause_resume_existing_task','create_immutable_owner_release_ref'))
         and all(doc[k] is False for k in ('hybrid_admission','scientific_first_use',
             'new_controller','new_scheduler','new_queue'))
         and type(doc['paid_model_calls']) is int and doc['paid_model_calls'] == 0,
         'EXPLICIT_SCOPED_OPERATOR_AUTHORITY_REQUIRED')
    return doc


def verify_runtime_context(target, env=None, event=None):
    env = os.environ if env is None else env
    need(sha(target,40) and env.get('GITHUB_REPOSITORY') == REPO
         and env.get('GITHUB_ACTOR') == OWNER and env.get('RUNNER_NAME') == 'FORGE-CODEX-REMOTE'
         and env.get('GITHUB_EVENT_NAME') == 'push' and env.get('GITHUB_RUN_ATTEMPT') == '1'
         and env.get('GITHUB_SHA') == target
         and env.get('GITHUB_REF') == 'refs/heads/f139-owner-release-'+target
         and str(env.get('GITHUB_RUN_ID','')).isdigit() and int(env['GITHUB_RUN_ID']) > 0,
         'ORIGINAL_CREATE_ONLY_RELEASE_CONTEXT_REQUIRED')
    if event is None:
        event = json.loads(Path(env['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    need(type(event) is dict and event.get('created') is True and event.get('deleted') is False
         and event.get('forced') is False and event.get('before') == '0'*40 and event.get('after') == target
         and event.get('sender',{}).get('login') == OWNER
         and event.get('repository',{}).get('full_name') == REPO,
         'IMMUTABLE_CREATE_ONLY_OWNER_EVENT_REQUIRED')


def _jobs(get, run, expected, *, native=False):
    data = get('repos/'+REPO+'/actions/runs/'+str(run['id'])+'/jobs?per_page=100')
    need(type(data) is dict and type(data.get('jobs')) is list
         and data.get('total_count') == len(data['jobs']) and len(data['jobs']) <= 100,
         'COMPLETE_JOB_CATALOG_REQUIRED')
    jobs = data['jobs']
    if native:
        selected = [j for j in jobs if j.get('name') in expected]
    else:
        selected = jobs
    need(len(selected) == len(expected) and {j.get('name') for j in selected} == expected
         and len({j.get('id') for j in selected}) == len(expected)
         and all(j.get('status') == 'completed' and j.get('conclusion') == 'success'
                 and j.get('run_id') == run['id'] for j in selected), 'MANDATORY_ORIGINAL_JOBS_NOT_PASSED')
    if native:
        owner = next(j for j in selected if j['name'] == 'v40-owner-readonly')
        need(owner.get('runner_name') == 'FORGE-CODEX-REMOTE'
             and {'self-hosted','Windows','forge-codex-isolated'} <= set(owner.get('labels',[])),
             'ORIGINAL_NATIVE_COPY_RUNNER_REQUIRED')


def _qualified_catalog(get, source, event, specifications):
    data = get('repos/'+REPO+'/actions/runs?head_sha='+source+'&event='+event+'&per_page=30')
    need(type(data) is dict and type(data.get('workflow_runs')) is list
         and data.get('total_count') == len(data['workflow_runs']) and len(data['workflow_runs']) < 30, 'BOUNDED_COMPLETE_QUALIFICATION_CATALOG_REQUIRED')
    found = []
    for spec in specifications:
        rows = [r for r in data['workflow_runs'] if r.get('workflow_id') == spec[0]]
        need(len(rows) == 1, 'UNIQUE_FIRST_ATTEMPT_QUALIFICATION_REQUIRED')
        run = rows[0]
        need(run.get('name') == spec[1] and run.get('head_sha') == source and run.get('event') == event
             and run.get('status') == 'completed' and run.get('conclusion') == 'success'
             and run.get('run_attempt') == 1 and run.get('actor',{}).get('login') == OWNER,
             'SOURCE_QUALIFICATION_DRIFT')
        if len(spec) == 3:
            _jobs(get,run,spec[2])
        found.append(run['id'])
    return found


def verify_source_and_immutable_ref(get, target):
    main = get('repos/'+REPO+'/branches/main')
    need(main.get('protected') is True and main.get('commit',{}).get('sha') == target,
         'EXACT_PROTECTED_MAIN_REQUIRED')
    commit = get('repos/'+REPO+'/git/commits/'+target)
    need(commit.get('sha') == target and len(commit.get('parents',[])) == 2
         and commit.get('verification',{}).get('verified') is True, 'VERIFIED_PROTECTED_MERGE_REQUIRED')
    candidate = commit['parents'][1]['sha']
    parent = get('repos/'+REPO+'/git/commits/'+candidate)
    need(parent.get('sha') == candidate and sha(commit.get('tree',{}).get('sha'),40)
         and parent.get('tree',{}).get('sha') == commit['tree']['sha'], 'QUALIFIED_CANDIDATE_TREE_DRIFT')
    candidate_runs = _qualified_catalog(get,candidate,'pull_request',(PUBLIC,CONTROLLER,DEVELOPMENT))
    main_runs = _qualified_catalog(get,target,'push',(PUBLIC,ORIGIN))
    release = get('repos/'+REPO+'/branches/f139-owner-release-'+target)
    need(release.get('protected') is True and release.get('commit',{}).get('sha') == target,
         'IMMUTABLE_EXACT_RELEASE_REF_REQUIRED')
    rule = get('repos/'+REPO+'/rulesets/'+str(RULESET))
    need(rule.get('id') == RULESET and rule.get('name') == 'FORGE F139 immutable owner release refs'
         and rule.get('target') == 'branch' and rule.get('enforcement') == 'active'
         and rule.get('bypass_actors') == []
         and rule.get('conditions',{}).get('ref_name') == dict(include=['refs/heads/f139-owner-release-*'],exclude=[])
         and len(rule.get('rules',[])) == 2 and {r.get('type') for r in rule['rules']} == {'update','deletion'},
         'ORIGINAL_NO_BYPASS_RELEASE_RULESET_REQUIRED')
    return dict(candidate_sha=candidate,source_tree=commit['tree']['sha'],
                candidate_qualification_runs=candidate_runs,main_qualification_runs=main_runs)


def verify_owner_approval(get, target, binary_sha, event_id, comment_id, *, paused):
    need(callable(get) and type(comment_id) is int and comment_id > 0
         and type(event_id) is int and event_id == comment_id, 'EXACT_OWNER_APPROVAL_EVENT_REQUIRED')
    comment = get('repos/'+REPO+'/issues/comments/'+str(comment_id))
    need(comment.get('id') == comment_id and comment.get('user',{}).get('login') == OWNER
         and comment.get('author_association') == 'OWNER'
         and comment.get('issue_url') == 'https://api.github.com/repos/'+REPO+'/issues/'+str(ISSUE),
         'ORIGINAL_OWNER_POLICY_COMMENT_REQUIRED')
    doc = decode_body(comment.get('body'))
    need(doc['source_sha'] == target and doc['binary_sha256'] == binary_sha, 'APPROVAL_SOURCE_OR_BINARY_CHANGED')
    policy = get('repos/'+REPO+'/issues/'+str(ISSUE))
    data = inspect_policy(policy,FROM)
    need(type(paused) is bool and data['enabled'] is (not paused)
         and data['lanes'] == ['Wingless','Yggdrasil'], 'UNCHANGED_TWO_LANE_POLICY_LEASE_REQUIRED')
    run = get('repos/'+REPO+'/actions/runs/'+str(doc['qualification_run_id']))
    need(run.get('id') == doc['qualification_run_id'] and run.get('head_sha') == target
         and run.get('path') == '.github/workflows/f139-g54-v9-owner-cutover.yml'
         and run.get('event') == 'issue_comment' and run.get('head_branch') == 'main'
         and run.get('status') == 'completed' and run.get('conclusion') == 'success'
         and run.get('run_attempt') == 1 and run.get('actor',{}).get('login') == OWNER,
         'AUTHENTIC_SOURCE_BOUND_COPY_QUALIFICATION_REQUIRED')
    _jobs(get,run,{'v40-invocation-qualification','v40-owner-readonly'},native=True)
    artifact = get('repos/'+REPO+'/actions/artifacts/'+str(doc['qualification_artifact_id']))
    witness = artifact.get('workflow_run',{})
    need(artifact.get('id') == doc['qualification_artifact_id'] and artifact.get('expired') is False
         and artifact.get('name') == 'f139-v40-source-bound-copy-build-'+target+'-r'+str(run['id'])
         and 0 < artifact.get('size_in_bytes',0) <= 16_000_000
         and artifact.get('digest') == 'sha256:'+doc['qualification_artifact_sha256']
         and witness.get('id') == run['id'] and witness.get('head_sha') == target
         and witness.get('repository_id') == REPO_ID and witness.get('head_repository_id') == REPO_ID,
         'COPY_ARTIFACT_SOURCE_CUSTODY_DRIFT')
    source = verify_source_and_immutable_ref(get,target)
    return {**doc,**source,'schema':'forge.f139.v40.owner-handoff-plan.v1',
        'comment_id':comment_id,'approval_body_sha256':digest(comment['body'].encode())}


def find_owner_approval(get, target):
    found, seen = [], set()
    for page in range(1,5):
        rows = get('repos/'+REPO+'/issues/'+str(ISSUE)+'/comments?per_page=100&page='+str(page))
        need(type(rows) is list and len(rows) <= 100, 'OWNER_COMMENT_CATALOG_INVALID')
        for row in rows:
            need(type(row.get('id')) is int and row['id'] > 0 and row['id'] not in seen,
                 'OWNER_COMMENT_CATALOG_DRIFT')
            seen.add(row['id'])
            if row.get('user',{}).get('login') == OWNER and str(row.get('body','')).startswith(PREFIX):
                doc = decode_body(row['body'])
                if doc['source_sha'] == target:
                    found.append(row['id'])
        if len(rows) < 100:
            break
    else:
        raise HandoffDenied('F139_V40_HANDOFF_OWNER_COMMENT_CATALOG_TRUNCATED')
    need(len(found) == 1, 'ONE_EXPLICIT_OWNER_HANDOFF_APPROVAL_REQUIRED')
    return verify_owner_approval(get,target,BINARY_SHA256,found[0],found[0],paused=False)


def verify_original_backup(db, backup, target, approval):
    """Read-only full logical/byte backup proof, before any source event."""
    from contextlib import closing
    from f139.local_controller import Database
    from f139.nci04_v38_original_owner_transition_cli import rollback_view
    backup = Path(backup)
    expected = db.filename.parent/('f139-v40-before-'+os.environ['GITHUB_RUN_ID'])/'state.sqlite'
    need(backup == expected and backup.is_file() and not backup.is_symlink()
         and backup.parent.is_dir() and not backup.parent.is_symlink(), 'CANONICAL_RUN_BACKUP_REQUIRED')
    receipt_path = backup.parent/'v40-backup-receipt.json'
    manifest_path = backup.parent/'manifest.sha256.json'
    need(receipt_path.is_file() and not receipt_path.is_symlink()
         and manifest_path.is_file() and not manifest_path.is_symlink(), 'COLD_BACKUP_RECEIPT_REQUIRED')
    receipt = json.loads(receipt_path.read_bytes())
    need(type(receipt) is dict and set(receipt) == {'schema','source_sha','target_source_sha',
         'expected_original_head_seq','expected_original_head_sha256','sqlite_sha256',
         'logical_view_sha256','archive_manifest_sha256'}
         and receipt['schema'] == 'forge.f139.v40.original-cold-backup.v1'
         and receipt['source_sha'] == FROM and receipt['target_source_sha'] == target
         and receipt['expected_original_head_seq'] == approval['expected_original_head_seq']
         and receipt['expected_original_head_sha256'] == approval['expected_original_head_sha256']
         and receipt['sqlite_sha256'] == digest(backup.read_bytes())
         and receipt['archive_manifest_sha256'] == digest(manifest_path.read_bytes()),
         'ORIGINAL_COLD_BACKUP_BYTES_OR_IDENTITY_DRIFT')
    manifest = json.loads(manifest_path.read_bytes())
    need(type(manifest) is dict and manifest.get('state.sqlite') == receipt['sqlite_sha256'],
         'ORIGINAL_BACKUP_MANIFEST_DRIFT')
    for relative, expected_hash in manifest.items():
        need(type(relative) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._/-]{0,399}',relative) is not None and not relative.startswith('/')
             and '\\' not in relative and all(p not in ('','.','..') for p in relative.split('/'))
             and sha(expected_hash,64), 'BACKUP_MANIFEST_PATH_OR_HASH_INVALID')
        path = backup.parent/relative
        need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(backup.parent.resolve())
             and all(not parent.is_symlink() for parent in path.parents if parent.is_relative_to(backup.parent))
             and digest(path.read_bytes()) == expected_hash,
             'BACKUP_MANIFEST_FILE_DRIFT')
    with closing(Database.open_readonly(backup)) as cold:
        need(cold.meta() == db.meta()
             and digest(canonical(rollback_view(cold.conn))) == receipt['logical_view_sha256']
             and digest(canonical(rollback_view(db.conn))) == receipt['logical_view_sha256'],
             'ORIGINAL_BACKUP_LOGICAL_STATE_DRIFT')
    return receipt
