"""Adversarial compiler tests. No test below executes model inference."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('w02_scope', ROOT/'scripts/cp03/w02_scope.py')
assert SPEC and SPEC.loader
scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scope)


class ScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = scope.decode((ROOT/scope.POLICY_PATH).read_bytes())
        cls.rows = [scope.decode(l) for l in (ROOT/scope.INPUT_PATHS[0]).read_bytes().splitlines() if l.strip()]
        cls.surfaces = [scope.decode(l) for l in (ROOT/scope.INPUT_PATHS[1]).read_bytes().splitlines() if l.strip()]
        cls.inventory = scope.decode((ROOT/scope.INPUT_PATHS[2]).read_bytes())
        cls.reference = scope.compile_root(ROOT)

    def data(self):
        return copy.deepcopy((self.rows,self.surfaces,self.inventory,self.policy))

    def test_full_snapshot_partitions_646_without_parity(self):
        r=self.reference
        self.assertEqual(r['summary']['global_denominator'],7565)
        self.assertEqual([len(r['groups'][k]) for k in scope.DISPOSITIONS],[32,52,562])
        ids=[i for group in r['groups'].values() for i in group]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(ids),646)
        self.assertFalse(r['summary']['scope_frozen'])
        self.assertIsNone(r['summary']['K_final'])
        self.assertEqual(r['summary']['parity_promotions'],0)

    def test_candidates_remain_candidates(self):
        self.assertEqual(self.reference['summary']['candidate_definitions'],2188)
        self.assertEqual(len(self.reference['supplemental']),119)
        self.assertTrue(all(r['promotion_status']=='DISCOVERED_CANDIDATE' for r in self.reference['supplemental']))

    def test_chat_route_is_not_silently_lost_by_family_filter(self):
        rows={r['capability_id']:r for r in self.reference['allocations']}
        chat=rows['cap_56358709cbc328e25ed1afff']
        self.assertEqual(chat['family_at_cp01'],'api_protocol')
        self.assertEqual(chat['disposition'],'CROSS_WAVE_REVIEW')
        self.assertEqual(chat['rules'],['S05'])

    def test_connector_family_does_not_become_core(self):
        row=next(r for r in self.reference['allocations'] if r['capability_id']=='cap_1dd24dc8f644a7e229d19450')
        self.assertEqual(row['family_at_cp01'],'inference')
        self.assertEqual(row['disposition'],'CROSS_WAVE_REVIEW')

    def test_all_mounts_require_review(self):
        mounts=[r for r in self.reference['allocations'] if r['surface_kind']=='route_mount']
        self.assertEqual(len(mounts),29)
        self.assertTrue(all(r['disposition']=='CROSS_WAVE_REVIEW' for r in mounts))

    def test_every_obligation_has_source_provenance(self):
        for r in self.reference['allocations']:
            self.assertTrue(scope.hex_digest(r['source_blob_sha'],40))
            self.assertTrue(scope.hex_digest(r['source_sha256'],64))
            self.assertGreater(r['source_line'],0)
            self.assertTrue(r['rules'])

    def test_graph_has_no_orphan_or_missing_allocation(self):
        g=self.reference['graph']; ids={n['id'] for n in g['nodes']}
        self.assertEqual(len(g['edges']),646)
        self.assertEqual(len(g['nodes']),649)
        self.assertTrue(all(e['from'] in ids and e['to'] in ids for e in g['edges']))

    def test_memory_order_does_not_change_semantic_products(self):
        rows,surfaces,inv,policy=self.data()
        random.Random(42).shuffle(rows);random.Random(99).shuffle(surfaces)
        inv['files'].reverse();policy['rules'].reverse()
        got=scope.compile_rows(rows,surfaces,inv,policy)
        # Policy's own byte-order digest intentionally changes with policy ordering.
        got['summary']['policy_sha256']=self.reference['summary']['policy_sha256']
        self.assertEqual(scope.products(got),scope.products(self.reference))

    def test_duplicate_capability_id_rejected(self):
        r,s,i,p=self.data();r[-1]=r[0]
        with self.assertRaisesRegex(scope.ScopeError,'duplicate'):scope.compile_rows(r,s,i,p)

    def test_duplicate_surface_rejected(self):
        r,s,i,p=self.data();s.append(s[0])
        with self.assertRaisesRegex(scope.ScopeError,'duplicate'):scope.compile_rows(r,s,i,p)

    def test_missing_capability_rejected(self):
        r,s,i,p=self.data();r.pop()
        with self.assertRaisesRegex(scope.ScopeError,'count drift'):scope.compile_rows(r,s,i,p)

    def test_wrong_upstream_pin_rejected(self):
        r,s,i,p=self.data();r[0]['source_commit']='0'*40
        with self.assertRaisesRegex(scope.ScopeError,'pin drift'):scope.compile_rows(r,s,i,p)

    def test_policy_cannot_change_canonical_pin(self):
        p=copy.deepcopy(self.policy);p['upstream_refs']['openjarvis']='0'*40
        with self.assertRaises(scope.ScopeError):scope.validate_policy(p)

    def test_source_surface_crosslink_must_match(self):
        r,s,i,p=self.data();row=next(v for v in r if v['source_repo']=='openjarvis');row['name']='invented'
        with self.assertRaisesRegex(scope.ScopeError,'projection drift'):scope.compile_rows(r,s,i,p)

    def test_missing_source_file_rejected(self):
        r,s,i,p=self.data();bad=s[0]['source_path'];i['files']=[v for v in i['files'] if v['path']!=bad]
        with self.assertRaisesRegex(scope.ScopeError,'orphan surface file'):scope.compile_rows(r,s,i,p)

    def test_invalid_source_line_rejected(self):
        for value in (0,-1,True,'10'):
            r,s,i,p=self.data();s[0]['line']=value
            with self.subTest(value=value),self.assertRaisesRegex(scope.ScopeError,'source line'):scope.compile_rows(r,s,i,p)

    def test_candidate_promotion_rejected(self):
        r,s,i,p=self.data();next(v for v in s if v['promotion_status']=='DISCOVERED_CANDIDATE')['promotion_status']='BEHAVIOR_MAPPED'
        with self.assertRaisesRegex(scope.ScopeError,'candidate count'):scope.compile_rows(r,s,i,p)

    def test_weak_evidence_is_not_behavioral_proof(self):
        r,s,i,p=self.data();row=next(v for v in r if v['source_repo']=='openjarvis');surf=next(v for v in s if v['surface_id']==row['source_surface_id'])
        row['evidence_strength']=surf['evidence_strength']='DEFINITION'
        with self.assertRaisesRegex(scope.ScopeError,'weak evidence'):scope.compile_rows(r,s,i,p)

    def test_conflicting_rules_rejected(self):
        r,s,i,p=self.data();q=copy.deepcopy(p['rules'][0]);q['id']='conflict';q['disposition']='OTHER_CP03_WAVE';p['rules'].append(q)
        with self.assertRaisesRegex(scope.ScopeError,'conflicting'):scope.compile_rows(r,s,i,p)

    def test_unconditional_rule_rejected(self):
        p=copy.deepcopy(self.policy);p['rules']=[{'id':'all','disposition':'W02_CORE','reason':'bad'}]
        with self.assertRaisesRegex(scope.ScopeError,'unconditional'):scope.validate_policy(p)

    def test_unknown_rule_field_rejected(self):
        p=copy.deepcopy(self.policy);p['rules'][0]['execute']='anything'
        with self.assertRaisesRegex(scope.ScopeError,'unknown rule'):scope.validate_policy(p)

    def test_self_approved_freeze_rejected(self):
        p=copy.deepcopy(self.policy);p['freeze_authorized']=True
        with self.assertRaisesRegex(scope.ScopeError,'authorize'):scope.validate_policy(p)

    def test_parity_promotion_rejected(self):
        p=copy.deepcopy(self.policy);p['parity_promotions']=32
        with self.assertRaisesRegex(scope.ScopeError,'authorize'):scope.validate_policy(p)

    def test_bool_schema_and_parity_rejected(self):
        for key in ('schema_version','parity_promotions'):
            p=copy.deepcopy(self.policy);p[key]=True if key=='schema_version' else False
            with self.subTest(key=key),self.assertRaises(scope.ScopeError):scope.validate_policy(p)

    def test_unknown_source_repository_rejected(self):
        r,s,i,p=self.data();r[0]['source_repo']='injected'
        with self.assertRaisesRegex(scope.ScopeError,'unknown source'):scope.compile_rows(r,s,i,p)

    def test_changed_denominator_rejected(self):
        p=copy.deepcopy(self.policy);p['expected_counts']['global']=646
        with self.assertRaisesRegex(scope.ScopeError,'denominator'):scope.validate_policy(p)

    def test_ledger_verified_mutation_rejected(self):
        r,s,i,p=self.data();r[0]['parity_status']='VERIFIED'
        with self.assertRaisesRegex(scope.ScopeError,'status drift'):scope.compile_rows(r,s,i,p)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(scope.ScopeError,'duplicate JSON'):scope.decode('{"x":1,"x":2}')

    def test_nan_infinity_rejected(self):
        for v in ('NaN','Infinity','-Infinity'):
            with self.subTest(v=v),self.assertRaises(scope.ScopeError):scope.decode('{"x":'+v+'}')

    def test_unsafe_relative_paths_rejected(self):
        for p in ('../escape','/tmp/path','a/../b','a\\b','a//b','a/./b','a\nb'):
            with self.subTest(path=p),self.assertRaises(scope.ScopeError):scope.safe_relative(p)

    def test_missing_or_incorrect_file_digest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'input').write_bytes(b'test')
            lock={'bytes':4,'git_blob_sha':scope.git_blob(b'test'),'sha256':'0'*64}
            with self.assertRaisesRegex(scope.ScopeError,'SHA256 drift'):scope.read_locked(root,'input',lock)

    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'real').write_bytes(b'a');(root/'link').symlink_to(root/'real')
            with self.assertRaisesRegex(scope.ScopeError,'symlink'):scope.local_path(root,'link')

    def test_required_freeze_is_nonzero_without_writing(self):
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/cp03/w02_scope.py'),'--root',str(ROOT),'--require-frozen'],capture_output=True,text=True,timeout=20)
        self.assertEqual(proc.returncode,2)
        self.assertFalse(json.loads(proc.stdout)['scope_frozen'])

    def test_generated_outputs_byte_check(self):
        for p,b in scope.products(self.reference).items():
            self.assertEqual((ROOT/p).read_bytes(),b)

    def test_input_files_not_mutated_by_compilation(self):
        before={p:scope.digest((ROOT/p).read_bytes()) for p in scope.INPUT_PATHS}
        scope.compile_root(ROOT)
        self.assertEqual(before,{p:scope.digest((ROOT/p).read_bytes()) for p in scope.INPUT_PATHS})


    def test_policy_cannot_repoint_input_snapshot(self):
        p=copy.deepcopy(self.policy);p['inputs'][scope.INPUT_PATHS[0]]['git_blob_sha']='0'*40
        with self.assertRaisesRegex(scope.ScopeError,'snapshot blob drift'):scope.validate_policy(p)

    def test_missing_surface_digest_rejected(self):
        r,s,i,p=self.data();s[0]['provenance'].pop('source_sha256')
        with self.assertRaisesRegex(scope.ScopeError,'source digest'):scope.compile_rows(r,s,i,p)

    def test_output_drift_is_rejected_by_cli(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for p in (*scope.INPUT_PATHS,scope.POLICY_PATH):
                target=root/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
            for p,b in scope.products(self.reference).items():
                target=root/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
            (root/'reports/cp03/w02_scope/SUMMARY.json').write_text('{}')
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/cp03/w02_scope.py'),'--root',str(root),'--check'],capture_output=True,text=True,timeout=20)
            self.assertEqual(proc.returncode,2)
            self.assertIn('output drift',json.loads(proc.stdout)['error'])

    def test_no_writes_when_freeze_gate_fails(self):
        hashes={p:scope.digest((ROOT/p).read_bytes()) for p in scope.products(self.reference)}
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/cp03/w02_scope.py'),'--root',str(ROOT),'--require-frozen','--write'],capture_output=True,text=True,timeout=20)
        self.assertEqual(proc.returncode,2)
        self.assertEqual(hashes,{p:scope.digest((ROOT/p).read_bytes()) for p in scope.products(self.reference)})


class EngineContractTests(unittest.TestCase):
    SOURCE = b"""raise RuntimeError('source must never execute')
class StreamChunk:
    content: str
    finish_reason: str
class ResponseFormat:
    type: str
    schema: dict
class InferenceEngine:
    @abstractmethod
    def generate(self, messages, *, model: str): pass
    @abstractmethod
    async def stream(self, messages, *, model: str): yield ''
    async def stream_full(self, messages, *, model: str):
        async for token in self.stream(messages, model=model):
            yield StreamChunk(content=token)
        yield StreamChunk(finish_reason='stop')
    @abstractmethod
    def list_models(self): pass
    @abstractmethod
    def health(self): pass
    def can_serve(self, model): return True
    def close(self): pass
    def prepare(self, model): pass
"""
    def audit(self, source=None):
        source = self.SOURCE if source is None else source
        return scope.audit_engine_contract(source,[],scope.git_blob(source))

    def test_ast_never_imports_or_executes_source(self):
        self.assertFalse(self.audit()['upstream_execution'])

    def test_all_eight_methods_extracted(self):
        self.assertEqual(len(self.audit()['methods']),8)

    def test_can_serve_default_is_not_model_availability(self):
        method=next(m for m in self.audit()['methods'] if m['name']=='can_serve')
        self.assertTrue(method['default_returns_true'])
        self.assertFalse(method['abstract'])

    def test_stream_full_wraps_stream_and_emits_synthetic_stop(self):
        method=next(m for m in self.audit()['methods'] if m['name']=='stream_full')
        self.assertEqual(method['delegates_to'],['stream'])
        self.assertEqual(method['emitted_finish_reasons'],['stop'])
        self.assertTrue(method['async'])

    def test_generate_abstractness_preserved(self):
        method=next(m for m in self.audit()['methods'] if m['name']=='generate')
        self.assertTrue(method['abstract'])
        self.assertIn('model: str',method['signature'])

    def test_prepare_close_noop_is_explicit(self):
        for method in self.audit()['methods']:
            if method['name'] in ('prepare','close'):self.assertTrue(method['default_noop'])

    def test_contract_fields_are_typed(self):
        self.assertEqual(self.audit()['fields']['ResponseFormat'],
                         [{'name':'type','annotation':'str'},{'name':'schema','annotation':'dict'}])

    def test_contract_cannot_promote_parity(self):
        self.assertEqual(self.audit()['parity_promotions'],0)

    def test_missing_methods_fail(self):
        changed=self.SOURCE.replace(b'def prepare(self, model): pass',b'def wrong(self, model): pass')
        with self.assertRaisesRegex(scope.ScopeError,'method-set drift'):self.audit(changed)

    def test_wrong_source_blob_fails_before_parsing(self):
        with self.assertRaisesRegex(scope.ScopeError,'blob drift'):
            scope.audit_engine_contract(self.SOURCE,[],'0'*40)

    def test_missing_class_fails(self):
        with self.assertRaisesRegex(scope.ScopeError,'missing contract class'):self.audit(b'class Wrong: pass')

    def test_contract_coverage_gaps_not_hidden(self):
        self.assertEqual(len(self.audit()['methods_absent_as_individual_cp01_surfaces']),8)


if __name__=='__main__':unittest.main(verbosity=2)
