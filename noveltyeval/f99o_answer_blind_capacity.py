"""F99-O: label-blind, whole-population public MetaQA graph-capacity diagnostic.

Does NOT translate language roles, call F95, score QA, train a model,
verify scientific first-use, or authorize an optimizer/science action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import f98o_public_corpus_audit as f98

SCHEMA = 'forge.optimizer.f99o.answer-blind-public-schema-capacity.v1'
CAP = 128
TOPIC = re.compile(r'\[([^\[\]\t\r\n]+)\]')
IDENTIFIER = re.compile(r'^[a-z0-9_-]{1,48}$')


class CapacityError(ValueError):
    pass


def require(test: bool, message: str) -> None:
    if not test:
        raise CapacityError('FORGE_F99O_SOURCE_OR_SCHEMA_DENIED_' + message)


def canonical(value: str, namespace: str, used: dict[str, str]) -> str:
    require(bool(value) and '\x00' not in value and namespace in ('entity', 'forward', 'reverse'),
            'INVALID_IDENTITY')
    key = 'id_' + hashlib.sha256((namespace + '\x00' + value).encode('utf-8')).hexdigest()[:28]
    identity = namespace + '\x00' + value
    require(key not in used or used[key] == identity, 'OPAQUE_ID_COLLISION')
    used[key] = identity
    require(IDENTIFIER.fullmatch(key) is not None, 'OPAQUE_ID_INVALID')
    return key


def build_graph(lines: list[str]) -> tuple[dict[str, tuple[tuple[str, str], ...]], set[str], dict]:
    require(bool(lines), 'EMPTY_KNOWLEDGE_GRAPH')
    used: dict[str, str] = {}
    adjacency: dict[str, set[tuple[str, str]]] = {}
    nodes: set[str] = set()
    prior: set[tuple[str, str, str]] = set()
    duplicates = 0
    self_edges = 0
    for item in lines:
        parts = item.split('|')
        require(len(parts) == 3 and all(parts), 'MALFORMED_GRAPH_TRIPLE')
        left, relation, right = parts
        require(all('\x00' not in x for x in parts), 'BINARY_GRAPH_FIELD')
        a = canonical(left, 'entity', used)
        b = canonical(right, 'entity', used)
        forward = canonical(relation, 'forward', used)
        reverse = canonical(relation, 'reverse', used)
        nodes.update((left, right))
        triple = (left, relation, right)
        if triple in prior:
            duplicates += 1
            continue
        prior.add(triple)
        if a == b:
            self_edges += 1
        adjacency.setdefault(left, set()).add((forward, right))
        adjacency.setdefault(right, set()).add((reverse, left))
    frozen = {key: tuple(sorted(edges)) for key, edges in adjacency.items()}
    return frozen, nodes, {
        'source_rows': len(lines), 'unique_source_triples': len(prior),
        'duplicate_source_rows_retained_in_denominator': duplicates,
        'self_relation_triples_incompatible_with_f95': self_edges,
        'unique_named_entities': len(nodes),
        'unique_f95_compatible_opaque_identifiers': len(used),
        'canonicalization_collision_detected': False,
    }


def extract_questions(rows: list[str]) -> tuple[list[str], int]:
    require(bool(rows), 'EMPTY_QUESTION_COHORT')
    roots: list[str] = []
    seen: set[str] = set()
    duplicates = 0
    for line in rows:
        # Only question text moves downstream. Answer bytes are never interpreted.
        question, sep, answer_field = line.partition('\t')
        require(sep == '\t' and bool(answer_field) and '\t' not in answer_field,
                'MALFORMED_QUESTION_ROW')
        marks = TOPIC.findall(question)
        require(len(marks) == 1 and question.count('[') == 1 and
                question.count(']') == 1, 'TOPIC_ENTITY_NOT_UNIQUE')
        if question in seen:
            duplicates += 1
        seen.add(question)
        roots.append(marks[0])
    return roots, duplicates


def envelope(root: str, hops: int, adjacency: dict[str, tuple[tuple[str, str], ...]],
             cap: int = CAP) -> str:
    require(hops in (2, 3) and cap == CAP, 'BUDGET_OR_DEPTH_DRIFT')
    if root not in adjacency:
        return 'root_absent'
    current = {root}
    visited = {root}
    arcs: set[tuple[str, str, str]] = set()
    for _ in range(hops):
        following: set[str] = set()
        for node in sorted(current):
            for role, neighbor in adjacency.get(node, ()):
                arcs.add((node, role, neighbor))
                if len(arcs) > cap:
                    return 'over_budget'
                if neighbor not in visited:
                    following.add(neighbor)
        visited.update(following)
        current = following
    return 'bounded'


def cohort(roots: list[str], depth: int,
           adjacency: dict[str, tuple[tuple[str, str], ...]]) -> dict:
    buckets = {'bounded': 0, 'over_budget': 0, 'root_absent': 0}
    cached: dict[str, str] = {}
    for root in roots:
        if root not in cached:
            cached[root] = envelope(root, depth, adjacency)
        buckets[cached[root]] += 1
    require(sum(buckets.values()) == len(roots), 'LOST_QUESTION')
    return {
        'complete_population': len(roots), 'distinct_question_roots': len(cached),
        'fully_bounded_without_role_query': buckets['bounded'],
        'complete_envelope_exceeds_128_arcs': buckets['over_budget'],
        'topic_root_missing': buckets['root_absent'],
        'never_truncated_or_cherry_picked': True,
    }


def assess(kb_lines: list[str], qa2_lines: list[str], qa3_lines: list[str],
           *, denominator2: int, denominator3: int) -> dict:
    # Unit-test-only injection. Never authorizes external source provenance.
    require(denominator2 > 0 and denominator3 > 0, 'EMPTY_DENOMINATOR')
    require(len(qa2_lines) == denominator2 and len(qa3_lines) == denominator3,
            'COHORT_DENOMINATOR_DRIFT')
    graph, _, graph_counts = build_graph(kb_lines)
    qa2, dup2 = extract_questions(qa2_lines)
    qa3, dup3 = extract_questions(qa3_lines)
    return {
        'schema': SCHEMA,
        'source_git_objects_authentic': False,
        'public_only_not_blinded': True,
        'source_graph': graph_counts,
        'two_hop': cohort(qa2, 2, graph) | {'duplicate_question_text_rows': dup2},
        'three_hop': cohort(qa3, 3, graph) | {'duplicate_question_text_rows': dup3},
        'f95_actual_question_to_roles_adapter_exists': False,
        'all_external_test_items_runnable_and_scored': False,
        'f95_accuracy_computed': False,
        'independent_scientific_firstuse': False,
        'scientific_acceptance': False,
        'dream_pareto_promotion': False,
        'thetaevolve_accepted_training': False,
        'science_dispatch_authorized': False,
        'accepted_ref_mutation': False,
        'model_calls': 0,
        'codex_calls': 0,
        'cloudflare_writes': 0,
        'status': 'PUBLIC_PREEXISTING_METAQA_GRAPH_SCHEMA_AND_ENVELOPE_FEASIBILITY_ONLY',
    }


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\x00' + raw).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'REFUSE_OUTPUT_OVERWRITE')
    audit = f98.inspect(args.upstream)
    require(audit['real_git_object_readback_performed'] is True, 'NO_AUTHENTIC_SOURCE')
    contents = []
    for (_, relative, expected_blob, _), source in zip(f98.FILES, audit['source_files'], strict=True):
        raw = args.upstream.joinpath(*relative.split('/')).read_bytes()
        require(len(raw) <= 7_000_000 and git_blob(raw) == expected_blob,
                'WORKTREE_DIFFERS_FROM_PINNED_GIT_BLOB')
        require(hashlib.sha256(raw).hexdigest() == source['source_bytes_sha256'],
                'F98O_SOURCE_AUDIT_DRIFT')
        contents.append(raw.decode('utf-8').splitlines())
    output = assess(contents[0], contents[1], contents[2],
                    denominator2=14872, denominator3=14274)
    output['source_git_objects_authentic'] = True
    output['source_repository'] = f98.UPSTREAM_REPO
    output['source_commit'] = f98.UPSTREAM_HEAD
    output['source_files'] = [{
        'kind': row['kind'], 'path': row['path'],
        'source_git_blob_sha1': row['source_git_blob_sha1'],
        'source_bytes_sha256': row['source_bytes_sha256'],
    } for row in audit['source_files']]
    args.output.write_text(json.dumps(output, sort_keys=True, indent=2) + '\n',
                           encoding='utf-8')
    print('F99O_AUTHENTIC_PUBLIC_QA_ROWS=29146')
    print('F99O_MODEL_INFERENCE_AND_SCIENTIFIC_ORIGINALS=ZERO')


if __name__ == '__main__':
    try:
        main()
    except (CapacityError, f98.Blocked, OSError, UnicodeError) as exc:
        print('F99O_READ_ONLY_COMPATIBILITY_BLOCKED:', exc, file=sys.stderr)
        sys.exit(1)
