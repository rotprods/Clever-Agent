"""Compile a pinned W02 allocation; never promote parity or execute upstream code.

Default command validates immutable inputs and prints a summary without writing.
--write materializes deterministic derived products. --check compares bytes.
--require-frozen fails closed: this v1 compiler cannot authorize scope approval.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = 'inventory/cp03/w02_scope_policy.json'
INPUT_PATHS = ('ledgers/CAPABILITY_LEDGER.jsonl', 'inventory/surfaces/openjarvis.jsonl',
               'inventory/upstreams/openjarvis.json')
DISPOSITIONS = ('W02_CORE', 'CROSS_WAVE_REVIEW', 'OTHER_CP03_WAVE')
MAX_INPUT = 32 * 1024 * 1024
CANONICAL_PINS = {
    'openjarvis': '72033b8ec288aa067ce4530ff9d96bf231e9c4e5',
    'openclaw': '3ee32fb9c10dcf9d5713c0c4891e55227f5b1f0d',
    'omi': 'e1eca38ff28758d58cde43045691c8ba479063e9',
    'clicky': 'a80fa80721a8aebe51a170a7780705024ebc6e46',
}
SNAPSHOT_BLOBS = dict(zip(INPUT_PATHS, (
    'e401ff4c7ce4a1829b97299b564bd28aa3abb7b1',
    '54697466b6101d09567146225c7fc9f354c5e2f9',
    '72067bc3e90473a9bc791c466338a77c2daa02c8',
)))


class ScopeError(ValueError):
    """Invalid evidence or an unsupported attempt to authorize progress."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ScopeError(message)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ScopeError(f'non-finite JSON value: {value}')


def decode(data: bytes | str) -> Any:
    text = data.decode('utf-8') if isinstance(data, bytes) else data
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       separators=(',', ':')) + '\n').encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def safe_relative(path: Any) -> str:
    require(isinstance(path, str) and bool(path), 'empty/invalid path')
    parsed = PurePosixPath(path)
    require(not parsed.is_absolute() and '..' not in parsed.parts and '\\' not in path
            and parsed.as_posix() == path and not any(ord(c) < 32 for c in path),
            f'unsafe path: {path!r}')
    return path


def local_path(root: Path, relative: str) -> Path:
    path = root / safe_relative(relative)
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink path forbidden')
    require(path.resolve().is_relative_to(root.resolve()), 'path escapes root')
    return path


def read_locked(root: Path, relative: str, expected: dict[str, Any]) -> bytes:
    path = local_path(root, relative)
    require(path.is_file() and path.stat().st_size <= MAX_INPUT, 'input missing/oversized')
    data = path.read_bytes()
    require(len(data) == expected['bytes'] and len(data) <= MAX_INPUT, 'input size drift')
    require(git_blob(data) == expected['git_blob_sha'], f'Git blob drift: {relative}')
    require(digest(data) == expected['sha256'], f'SHA256 drift: {relative}')
    return data


def unique(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        require(isinstance(row, dict), 'non-object record')
        identity = row.get(key)
        require(isinstance(identity, str) and bool(identity), f'missing {key}')
        require(identity not in result, f'duplicate {key}: {identity}')
        result[identity] = row
    return result


def hex_digest(value: Any, length: int) -> bool:
    return (isinstance(value, str) and len(value) == length
            and all(c in '0123456789abcdef' for c in value))


def validate_policy(policy: dict[str, Any]) -> None:
    require(isinstance(policy, dict), 'policy must be an object')
    require(type(policy.get('schema_version')) is int and policy['schema_version'] == 1,
            'unsupported policy schema')
    require(policy.get('authority') == 'PROVISIONAL_ALLOCATION_NOT_PARITY', 'invalid authority')
    require(policy.get('freeze_authorized') is False and type(policy.get('parity_promotions')) is int
            and policy['parity_promotions'] == 0,
            'allocation cannot authorize freeze or parity')
    require(set(policy.get('inputs', {})) == set(INPUT_PATHS), 'input path set drift')
    require(policy.get('expected_counts') == {'global': 7565, 'openjarvis': 646, 'candidates': 2188},
            'denominator contract drift')
    require(hex_digest(policy.get('base_sha'), 40), 'invalid base SHA')
    require(policy.get('upstream_refs') == CANONICAL_PINS, 'canonical pin drift')
    for path, blob in SNAPSHOT_BLOBS.items():
        require(policy['inputs'][path].get('git_blob_sha') == blob, 'snapshot blob drift')
        require(hex_digest(policy['inputs'][path].get('sha256'),64), 'invalid input digest')
        require(type(policy['inputs'][path].get('bytes')) is int
                and 0 < policy['inputs'][path]['bytes'] <= MAX_INPUT, 'invalid input size')
    for path in policy['supplemental_paths']:
        safe_relative(path)
    for path in policy['supplemental_prefixes']:
        require(path.endswith('/'), 'invalid supplemental prefix')
        safe_relative(path[:-1])
    require(all(hex_digest(v, 40) for v in policy['upstream_refs'].values()), 'invalid pin')
    require(policy.get('fallback_inference') == 'CROSS_WAVE_REVIEW'
            and policy.get('fallback_other') == 'OTHER_CP03_WAVE', 'unsafe fallback')
    unique(policy['rules'], 'id')
    for rule in policy['rules']:
        require(rule.get('disposition') in DISPOSITIONS, 'invalid disposition')
        require(bool(rule.get('reason')), 'missing allocation rationale')
        selectors = {'paths','path_prefixes','routes','names','surface_kinds'}
        require(set(rule) <= selectors | {'id','disposition','reason'}, 'unknown rule field')
        require(bool(set(rule) & selectors), 'unconditional rule forbidden')
        for field in selectors & set(rule):
            require(isinstance(rule[field], list) and bool(rule[field])
                    and all(isinstance(v, str) and v for v in rule[field]), 'invalid selector')
        for p in rule.get('paths', []):
            safe_relative(p)
        for p in rule.get('path_prefixes', []):
            require(p.endswith('/'), 'prefix must end in directory separator')
            safe_relative(p[:-1])


def matches(row: dict[str, Any], rule: dict[str, Any]) -> bool:
    path = row['source_path']
    return (('paths' not in rule or path in rule['paths'])
            and ('path_prefixes' not in rule or any(path.startswith(p) for p in rule['path_prefixes']))
            and ('routes' not in rule or row['interface'].get('path') in rule['routes'])
            and ('names' not in rule or row['name'] in rule['names'])
            and ('surface_kinds' not in rule or row['surface_kind'] in rule['surface_kinds']))


def allocate(row: dict[str, Any], policy: dict[str, Any]) -> tuple[str, list[str]]:
    matched = [r for r in policy['rules'] if matches(row, r)]
    kinds = {r['disposition'] for r in matched}
    require(len(kinds) <= 1, f'conflicting rules: {row["capability_id"]}')
    if matched:
        return next(iter(kinds)), sorted(r['id'] for r in matched)
    return ((policy['fallback_inference'], ['REVIEW_FAMILY_ONLY']) if row['family'] == 'inference'
            else (policy['fallback_other'], ['DEFER_NOT_EXCLUDE']))


def compile_rows(rows: list[dict[str, Any]], surfaces: list[dict[str, Any]],
                 inventory: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Pure semantic compiler; immutable-byte validation happens in compile_root."""
    validate_policy(policy)
    counts = policy['expected_counts']
    caps = unique(rows, 'capability_id')
    require(len(caps) == counts['global'], 'global obligation count drift')
    for r in rows:
        require(r.get('source_repo') in policy['upstream_refs'], 'unknown source repository')
        require(r.get('source_commit') == policy['upstream_refs'][r['source_repo']], 'upstream pin drift')
        require(r.get('promotion_status') == 'BEHAVIOR_MAPPED'
                and r.get('parity_status') == 'UNVERIFIED' and r.get('status') == 'IN_SCOPE',
                'immutable denominator status drift')
    oj = sorted((r for r in rows if r['source_repo'] == 'openjarvis'), key=lambda r:r['capability_id'])
    require(len(oj) == counts['openjarvis'], 'OpenJarvis count drift')
    source = unique(surfaces, 'surface_id')
    pin = policy['upstream_refs']['openjarvis']
    require(inventory.get('source_repo') == 'openjarvis' and inventory.get('source_commit') == pin,
            'inventory identity drift')
    files = unique(inventory['files'], 'path')
    for path, entry in files.items():
        safe_relative(path)
        require(entry.get('object_type') == 'blob' and hex_digest(entry.get('object_id'),40),
                'invalid source tree entry')
    candidates = []
    mapped = set()
    for s in surfaces:
        require(s.get('source_repo') == 'openjarvis' and s.get('source_commit') == pin, 'surface pin drift')
        path = safe_relative(s.get('source_path'))
        require(path in files, f'orphan surface file: {path}')
        require(type(s.get('line')) is int and s['line'] > 0, 'invalid source line')
        require(hex_digest(s.get('provenance', {}).get('source_sha256'), 64), 'missing source digest')
        if s.get('promotion_status') == 'DISCOVERED_CANDIDATE':
            candidates.append(s)
        else:
            require(s.get('promotion_status') == 'BEHAVIOR_MAPPED', 'invalid promotion')
            mapped.add(s['surface_id'])
    require(len(candidates) == counts['candidates'], 'candidate count drift')
    require({r.get('source_surface_id') for r in oj} == mapped
            and len(mapped) == len(oj), 'orphan/duplicated behavior surface mapping')
    allocations = []
    rule_counts: Counter[str] = Counter()
    groups: dict[str, list[str]] = {k: [] for k in DISPOSITIONS}
    for row in oj:
        s = source[row['source_surface_id']]
        pairs = (('source_path','source_path'),('source_line','line'),('family','family'),
                 ('surface_kind','surface_kind'),('name','name'),('interface','interface'),
                 ('evidence_strength','evidence_strength'),('runtime_owner','runtime_owner'))
        require(all(row.get(a) == s.get(b) for a,b in pairs), f'source projection drift: {row["capability_id"]}')
        require(s.get('evidence_strength') in {'REGISTRATION','ROUTE_OR_PROTOCOL','BEHAVIOR_TEST'},
                'weak evidence in denominator')
        disposition, rules = allocate(row, policy)
        rule_counts.update(rules)
        groups[disposition].append(row['capability_id'])
        allocations.append({'capability_id':row['capability_id'],'disposition':disposition,'rules':rules,
            'source_surface_id':s['surface_id'],'source_path':s['source_path'],'source_line':s['line'],
            'source_blob_sha':files[s['source_path']]['object_id'],
            'source_sha256':s['provenance']['source_sha256'],'family_at_cp01':row['family'],
            'name':row['name'],'surface_kind':row['surface_kind'],
            'platform_constraints':s.get('platform_constraints',[]),
            'permission_hints_not_grants':s.get('permissions',[]),'parity_status':'UNVERIFIED'})
    supplemental = sorted((s for s in candidates if s['source_path'] in policy['supplemental_paths']
        or any(s['source_path'].startswith(p) for p in policy['supplemental_prefixes'])), key=lambda s:s['surface_id'])
    inference_ids = {r['capability_id'] for r in oj if r['family'] == 'inference'}
    relevant = set(groups['W02_CORE']) | set(groups['CROSS_WAVE_REVIEW'])
    summary = {'schema_version':1,'status':'COMPILED_PROVISIONAL','scope_frozen':False,
        'scope_approval':'REQUIRES_REVIEW','K_final':None,'K_core_proposed':len(groups['W02_CORE']),
        'cross_wave_review':len(groups['CROSS_WAVE_REVIEW']), 'other_wave_retained':len(groups['OTHER_CP03_WAVE']),
        'global_denominator':len(rows),'openjarvis_obligations':len(oj),'candidate_definitions':len(candidates),
        'supplemental_candidate_definitions':len(supplemental),'source_files':len(files),
        'family_only_filter_count':len(inference_ids),
        'relevant_ids_outside_inference_family':sorted(relevant-inference_ids),
        'inference_family_requires_review':sorted(inference_ids & set(groups['CROSS_WAVE_REVIEW'])),
        'by_rule':dict(sorted(rule_counts.items())), 'parity_promotions':0,'runtime_tests':0,
        'base_sha':policy['base_sha'],'upstream_commit':pin,'policy_sha256':digest(canonical(policy)),
        'input_locks':policy['inputs']}
    # Flat relation projection, not a claim of a complete call graph or behavioral equivalence.
    graph = {'schema_version':1,'plane':'P2_COS20D_DECISION','promotion':'PROVISIONAL',
        'nodes':[{'id':r['capability_id'],'kind':'obligation'} for r in allocations]
                + [{'id':k,'kind':'allocation'} for k in DISPOSITIONS],
        'edges':[{'from':r['capability_id'],'to':r['disposition'],'type':'provisionally_allocated_to',
                  'surface':r['source_surface_id'],'source_blob_sha':r['source_blob_sha'],'rules':r['rules']}
                 for r in allocations]}
    return {'summary':summary,'allocations':allocations,'groups':groups,'graph':graph,
        'supplemental':[{'surface_id':s['surface_id'],'name':s['name'],'source_path':s['source_path'],
                          'line':s['line'],'promotion_status':'DISCOVERED_CANDIDATE'} for s in supplemental]}


def compile_root(root: Path) -> dict[str, Any]:
    policy_file = local_path(root, POLICY_PATH)
    require(policy_file.stat().st_size <= 128 * 1024, 'policy oversized')
    policy = decode(policy_file.read_bytes())
    validate_policy(policy)
    raw = {p: read_locked(root, p, policy['inputs'][p]) for p in INPUT_PATHS}
    ledger = [decode(l) for l in raw[INPUT_PATHS[0]].splitlines() if l.strip()]
    surfaces = [decode(l) for l in raw[INPUT_PATHS[1]].splitlines() if l.strip()]
    return compile_rows(ledger, surfaces, decode(raw[INPUT_PATHS[2]]), policy)


def audit_engine_contract(source: bytes, source_surfaces: list[dict[str, Any]],
                          expected_blob: str) -> dict[str, Any]:
    """Inspect exact source syntax without importing/executing OpenJarvis."""
    require(len(source) <= 128 * 1024 and git_blob(source) == expected_blob, 'engine source blob drift')
    module = ast.parse(source.decode('utf-8'))
    classes = {n.name:n for n in module.body if isinstance(n, ast.ClassDef)}
    require({'InferenceEngine','StreamChunk','ResponseFormat'} <= set(classes), 'missing contract class')
    path = 'src/openjarvis/engine/_stubs.py'
    methods = []
    for node in classes['InferenceEngine'].body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = [n for n in node.body if not (isinstance(n,ast.Expr)
                and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))]
        calls = [n for n in ast.walk(node) if isinstance(n,ast.Call)]
        methods.append({'name':node.name,'line':node.lineno,
            'signature':ast.unparse(node.args),'returns':ast.unparse(node.returns) if node.returns else None,
            'async':isinstance(node,ast.AsyncFunctionDef),
            'abstract':any(ast.unparse(d)=='abstractmethod' for d in node.decorator_list),
            'default_noop':not body or all(isinstance(n,ast.Pass) for n in body),
            'default_returns_true':any(isinstance(n,ast.Return) and isinstance(n.value,ast.Constant)
                                      and n.value.value is True for n in body),
            'delegates_to':sorted({n.func.attr for n in calls if isinstance(n.func,ast.Attribute)
                                  and isinstance(n.func.value,ast.Name) and n.func.value.id=='self'}),
            'emitted_finish_reasons':sorted({k.value.value for n in calls for k in n.keywords
                                      if k.arg=='finish_reason' and isinstance(k.value,ast.Constant)
                                      and isinstance(k.value.value,str)}),
            'cp01_candidate_surface_ids':sorted(s['surface_id'] for s in source_surfaces
                         if s['source_path']==path and s['name']==node.name and s['line']==node.lineno)})
    require({m['name'] for m in methods} == {'generate','stream','stream_full','list_models','health','can_serve','close','prepare'},
            'engine method-set drift')
    fields = {name:[{'name':n.target.id,'annotation':ast.unparse(n.annotation)}
                    for n in classes[name].body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name)]
              for name in ('StreamChunk','ResponseFormat')}
    return {'schema_version':1,'status':'STATIC_CONTRACT_MAPPED_NOT_RUNTIME_VERIFIED',
        'source_commit':CANONICAL_PINS['openjarvis'],'source_path':path,'source_blob_sha':git_blob(source),
        'source_sha256':digest(source),'methods':sorted(methods,key=lambda m:m['name']), 'fields':fields,
        'methods_absent_as_individual_cp01_surfaces':sorted(m['name'] for m in methods if not m['cp01_candidate_surface_ids']),
        'parity_promotions':0,'upstream_execution':False,
        'warning':'A class candidate or engine registration is not method-level parity. New syntax findings do not change the frozen denominator.'}


def products(result: dict[str, Any]) -> dict[str, bytes]:
    base = 'reports/cp03/w02_scope/'
    return {base+'SUMMARY.json':canonical(result['summary']),
            base+'ALLOCATIONS.jsonl':b''.join(canonical(r) for r in result['allocations']),
            base+'SUPPLEMENTAL.jsonl':b''.join(canonical(r) for r in result['supplemental']),
            base+'GROUPS.json':canonical(result['groups']),
            'graphs/cp03/w02_scope/ALLOCATION_GRAPH.json':canonical(result['graph'])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write',action='store_true')
    mode.add_argument('--check',action='store_true')
    parser.add_argument('--require-frozen',action='store_true')
    parser.add_argument('--source-root',type=Path,help='Optional exact OpenJarvis source for static engine contract audit')
    args = parser.parse_args()
    try:
        result = compile_root(args.root)
        # Refuse before any write; no flag or schema field can self-approve a freeze.
        require(not args.require_frozen, 'scope freeze not authorized: review shared facets/candidates first')
        outputs = products(result)
        if args.source_root:
            relative = 'src/openjarvis/engine/_stubs.py'
            source = local_path(args.source_root,relative)
            require(source.stat().st_size <= 128*1024, 'engine source oversized')
            inventory = decode(local_path(args.root,INPUT_PATHS[2]).read_bytes())
            blob = next(r['object_id'] for r in inventory['files'] if r['path']==relative)
            surfaces = [decode(l) for l in local_path(args.root,INPUT_PATHS[1]).read_bytes().splitlines() if l.strip()]
            outputs['reports/cp03/w02_scope/ENGINE_CONTRACT.json'] = canonical(audit_engine_contract(source.read_bytes(),surfaces,blob))
        for relative, data in outputs.items():
            path = local_path(args.root, relative)
            if args.check:
                require(path.is_file() and path.read_bytes() == data, f'generated output drift: {relative}')
            elif args.write:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(data)
        print(json.dumps(result['summary'],sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        print(json.dumps({'status':'FAIL','scope_frozen':False,'error':str(error),'parity_promotions':0}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
