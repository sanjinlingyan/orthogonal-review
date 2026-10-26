"""Fictional fixtures and simulated sessions test protocol, not model independence."""
import tempfile
import sys
from orthogonal_review.environment import declare, attempt
import unittest
from pathlib import Path
from unittest.mock import patch
from orthogonal_review.demo import create
from orthogonal_review.engine import prepare, handoff, submit, finalize, load, limitation
from orthogonal_review.io import write, read, sha, inside
from orthogonal_review.execute import execute

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=create(self.root/'fictional-task')
        self.run=prepare([self.source],self.root/'run')
        self.actor=self.make_actor('fictional-executor')
        self.ready(self.run)

    def make_actor(self,name):
        proof=self.root/(name+'.txt'); proof.write_text('SIMULATED PLATFORM RECEIPT — UNIT TEST ONLY',encoding='utf-8')
        actor=self.root/(name+'.json')
        write(actor,dict(session_id=name,platform='unit-test-simulation',fresh_context=True,isolation='simulated protocol; no actual agent',launch_evidence=str(proof)))
        return actor

    def packet(self,role='executor',actor=None):
        return handoff(self.run,'case-0001',role,actor or self.actor)

    def ref(self,p,relative):
        return dict(path=relative,sha256=sha(p/relative),locator='fictional fixture line 1')

    def finish(self,p,status='completed'):
        (p/'output'/'artifact.txt').write_text('fictional output',encoding='utf-8')
        result=dict(session_id='fictional-executor',status=status,summary='simulated execution',questions=[],assumptions=[],environment='unit-test-only',steps=['simulated step'],evidence=[self.ref(p,'output/artifact.txt')])
        write(p/'result.json',result); return submit(p,p/'result.json')

    def chain(self):
        packets=[]
        for _ in range(3):
            p=self.packet(); self.finish(p); packets.append(p)
        return packets

    def ready(self,run):
        req=self.root/'requirements.json'
        write(req,[dict(id='fictional-tool',title='SIMULATED fixture capability',rounds=['R1','R2','R3'])])
        declare(run,'case-0001',req)
        script=self.root/'fictional-probe.py'
        script.write_text('import json;print(json.dumps(dict(capability_verified=True,operation="FICTIONAL TEST ONLY",measurements=dict(fixture=True))))')
        plan=self.root/'environment-plan.json'
        write(plan,dict(requirement_id='fictional-tool',phase='probe',reason='FICTIONAL UNIT TEST',source='local fictional fixture',version='1',argv=[sys.executable,str(script)],reviewed_files=[dict(path=str(script),sha256=sha(script))]))
        attempt(run,'case-0001',plan,allow_host=True)

    def review(self,p,usability='usable',findings=None):
        status='pass' if usability=='usable' else 'fail'
        result=dict(session_id=read(p/'packet.json')['session_id'],summary='simulated independent check',rounds=[],findings=findings or [],evidence=[self.ref(p,'chain/R1/output/artifact.txt')],limitations=[])
        for r in ('R1','R2','R3'):
            exists=(p/f'chain/{r}/output/artifact.txt').exists()
            evidence=[self.ref(p,f'chain/{r}/output/artifact.txt')] if exists else [self.ref(p,'chain/R1/output/artifact.txt')]
            check=dict(id='fixture-check',title='FICTIONAL CHECK',status=status,reason='fixture result',evidence=evidence)
            if status=='fail':check.update(cause='execution',owner='executor',action='correct fictional output',done_when='fictional check passes')
            result['rounds'].append(dict(round=r,status=status,reason='fixture check',evidence=evidence,checks=[check]))
        write(p/'result.json',result); submit(p,p/'result.json')

    def test_success_and_two_reports(self):
        self.chain(); p=self.packet('reviewer',self.make_actor('fictional-reviewer')); self.review(p)
        self.assertEqual(finalize(self.run)['verdict'],'pass')
        self.assertEqual({p.name for p in self.run.iterdir() if p.is_file()},{'review.html','repair.md'})
        self.assertIn('chain/R1/output/artifact.txt',(self.run/'review.html').read_text(encoding='utf-8'))

    def test_no_execution_cannot_finalize(self):
        limitation(self.run,'case-0001','No specialist environment')
        with self.assertRaises(ValueError): finalize(self.run)

    def test_failed_agent_is_not_task_defect(self):
        p=self.packet(); self.finish(p,'failed')
        p=self.packet('reviewer',self.make_actor('fictional-reviewer')); self.review(p,'unusable')
        self.assertEqual(finalize(self.run)['verdict'],'fail')

    def test_confirmed_task_defect(self):
        self.finish(self.packet(),'blocked'); p=self.packet('reviewer',self.make_actor('fictional-reviewer'))
        f=dict(id='OBS-1',problem='fictional inconsistent units',location='request.md',cause='task_material',confidence='confirmed',action='clarify units',done_when='units consistent',evidence=[self.ref(p,'chain/R1/input/request.md')])
        self.review(p,'unusable',[f]); self.assertEqual(finalize(self.run)['verdict'],'fail')

    def test_identity_separation(self):
        self.chain()
        with self.assertRaises(ValueError): self.packet('reviewer',self.actor)

    def test_real_parent_and_no_future_round(self):
        p=self.packet(); self.assertFalse((p/'parent').exists()); self.assertFalse((p/'input'/'changes.csv').exists())
        self.finish(p); next_p=self.packet()
        self.assertEqual((next_p/'parent'/'artifact.txt').read_bytes(),(p/'output'/'artifact.txt').read_bytes())
        self.assertFalse((next_p/'input'/'price.csv').exists())
        self.assertNotIn(str(self.source), (next_p/'packet.json').read_text(encoding='utf-8'))

    def test_cannot_continue_after_failure(self):
        self.finish(self.packet(),'blocked')
        with self.assertRaises(ValueError): self.packet()

    def test_no_overwrite_result(self):
        p=self.packet(); self.finish(p)
        with self.assertRaises(ValueError): submit(p,p/'result.json')

    def test_source_mutation(self):
        (self.source/'R1/candidate/request.md').write_text('changed',encoding='utf-8')
        with self.assertRaises(ValueError): finalize(self.run)

    def test_frozen_parent_mutation(self):
        p=self.packet(); self.finish(p); (p/'output/artifact.txt').write_text('tampered',encoding='utf-8')
        with self.assertRaises(ValueError): self.packet()

    def test_result_state_mutation(self):
        p=self.packet(); self.finish(p); state=load(self.run)
        state['cases'][0]['packets'][0]['result']['summary']='tampered'
        write(self.run/'_internal/state.json',state)
        with self.assertRaises(ValueError): finalize(self.run)

    def test_cannot_use_wrong_evidence_hash(self):
        p=self.packet(); (p/'output/artifact.txt').write_text('a')
        result=dict(session_id='fictional-executor',status='completed',summary='test',environment='test',steps=['test'],questions=[],assumptions=[],evidence=[dict(path='output/artifact.txt',sha256='0'*64,locator='line 1')])
        write(p/'result.json',result)
        with self.assertRaises(ValueError): submit(p,p/'result.json')

    def test_cannot_claim_complete_without_artifacts(self):
        p=self.packet(); result=read(p/'packet.json')['result_template']
        result.update(session_id='fictional-executor',status='completed',summary='test',environment='test',steps=['test'])
        write(p/'result.json',result)
        with self.assertRaises(ValueError): submit(p,p/'result.json')

    def test_windows_evidence_and_escape(self):
        p=self.packet()
        self.assertEqual(inside(p,'input\\request.md'),p/'input/request.md')
        for value in ('../state.json','..\\state.json','C:\\secret.txt','/etc/passwd'):
            with self.assertRaises(ValueError): inside(p,value)

    def test_missing_round(self):
        other=self.root/'partial'; (other/'R1/candidate').mkdir(parents=True)
        (other/'R1/candidate/request.md').write_text('fictional')
        run=prepare([other],self.root/'partial-run')
        self.assertEqual(load(run)['cases'][0]['missing_rounds'],['R2','R3'])
        with self.assertRaises(ValueError): finalize(run)

    def test_review_cannot_skip_rounds(self):
        self.chain(); p=self.packet('reviewer',self.make_actor('fictional-reviewer'))
        result=read(p/'packet.json')['result_template']; result.update(session_id='fictional-reviewer',summary='test',usability='usable')
        write(p/'result.json',result)
        with self.assertRaises(ValueError): submit(p,p/'result.json')

    def test_docker_unavailable_never_runs_host(self):
        p=self.packet(); (p/'checks/probe.py').write_text('print(1)')
        plan=dict(image='sha256:'+'a'*64,argv=['python','checks/probe.py'],reason='fictional test',reviewed_files=[dict(path='checks/probe.py',sha256=sha(p/'checks/probe.py'))])
        write(p/'plan.json',plan)
        with patch('orthogonal_review.execute.shutil.which',return_value=None), patch('orthogonal_review.execute.subprocess.run') as proc:
            receipt=read(execute(p,p/'plan.json')); proc.assert_not_called()
        self.assertEqual(receipt['status'],'unavailable')

    def test_batch_without_review_cannot_finalize(self):
        second=create(self.root/'second-fictional'); run=prepare([self.source,second],self.root/'batch-run')
        self.assertEqual(len(load(run)['cases']),2)
        with self.assertRaises(ValueError): finalize(run)

    def test_render_escapes_untrusted_html(self):
        limitation(self.run,'case-0001','<script>alert(1)</script>')
        self.chain(); p=self.packet('reviewer',self.make_actor('fictional-reviewer')); self.review(p)
        finalize(self.run)
        self.assertNotIn('<script>',(self.run/'review.html').read_text(encoding='utf-8'))

    def test_one_diagnostic_and_no_replacement(self):
        self.chain()
        reviewer=self.packet('reviewer',self.make_actor('fictional-reviewer')); self.review(reviewer,'unusable')
        diagnostic=self.packet('diagnostician',self.make_actor('fictional-diagnostic'))
        result=read(reviewer/'sealed-result.json')
        result.update(session_id='fictional-diagnostic',attempt_status='completed',findings=[])
        for rr in result['rounds']:
            rr['status']='pass'
            for check in rr['checks']:check['status']='pass'
        write(diagnostic/'result.json',result); submit(diagnostic,diagnostic/'result.json')
        with self.assertRaises(ValueError): self.packet('diagnostician',self.make_actor('fictional-extra'))
        self.assertEqual(finalize(self.run)['verdict'],'fail')
        self.assertEqual(read(reviewer/'sealed-result.json')['rounds'][0]['status'],'fail')

    def test_formal_partial_does_not_hide_behind_workcopy(self):
        source=create(self.root/'dual-layout')
        from shutil import copytree
        copytree(source, self.root/'stored-copy')
        copytree(self.root/'stored-copy', source/'task')
        # Rename, not delete, the formal R3 input: the formal layout remains authoritative.
        (source/'R3').rename(source/'unused-R3')
        run=prepare([source],self.root/'dual-run')
        self.assertEqual(load(run)['cases'][0]['missing_rounds'],['R3'])

    def test_reject_output_inside_repository(self):
        from orthogonal_review.engine import ROOT
        with self.assertRaises(ValueError): prepare([self.source],ROOT/'forbidden-output')

    def test_reject_unfrozen_actor(self):
        actor=read(self.actor); actor['fresh_context']=False; write(self.actor,actor)
        with self.assertRaises(ValueError): self.packet()

    def test_reject_cross_case_actor_reuse(self):
        source=create(self.root/'another-task')
        run=prepare([self.source,source],self.root/'independent-batch')
        self.ready(run)
        handoff(run,'case-0001','executor',self.actor)
        with self.assertRaises(ValueError): handoff(run,'case-0002','executor',self.actor)

    def block_environment(self):
        script=self.root/'broken-tool.py'
        script.write_text('import sys;print("SIMULATED dependency failure");sys.exit(7)')
        plan=self.root/'broken-plan.json'
        for phase in ('configure','repair','probe'):
            write(plan,dict(requirement_id='fictional-tool',phase=phase,reason='FICTIONAL failure fixture',source='local fixture',version='1',argv=[sys.executable,str(script)],reviewed_files=[dict(path=str(script),sha256=sha(script))],blocker='dependency_unavailable'))
            attempt(self.run,'case-0001',plan,allow_host=True)

    def test_environment_required_before_execution(self):
        run=prepare([self.source],self.root/'unprepared')
        with self.assertRaises(ValueError): handoff(run,'case-0001','executor',self.actor)

    def test_environment_cannot_finalize_without_real_attempts(self):
        limitation(self.run,'case-0001','No tools; handwritten claim')
        with self.assertRaises(ValueError): finalize(self.run)

    def test_real_failed_setup_and_repair_allow_incomplete(self):
        self.block_environment()
        result=finalize(self.run)
        self.assertIsNone(result['verdict']); self.assertEqual(result['review_status'],'incomplete')
        report=(self.run/'review.html').read_text(encoding='utf-8')
        self.assertIn('<h1>未完成审查</h1>',report)
        self.assertNotIn('尚无法确定',report)
        self.assertIn('责任方：review',(self.run/'repair.md').read_text(encoding='utf-8'))

    def test_installed_but_no_operational_probe_is_not_ready(self):
        plan=self.root/'install-only.json'
        write(plan,dict(requirement_id='fictional-tool',phase='configure',reason='fixture installation only',source='local fixture',version='1',argv=[sys.executable,'-c','print("installed")']))
        attempt(self.run,'case-0001',plan,allow_host=True)
        with self.assertRaises(ValueError): self.packet()
        with self.assertRaises(ValueError): finalize(self.run)

    def test_failed_operation_after_successful_install_is_not_ready(self):
        self.block_environment()
        with self.assertRaises(ValueError): self.packet()

    def test_frozen_environment_event_and_metadata(self):
        state=load(self.run);state['cases'][0]['environment_events'][0]['capability_verified']=False
        write(self.run/'_internal/state.json',state)
        with self.assertRaises(ValueError): self.packet()

    def test_frozen_environment_log(self):
        event=load(self.run)['cases'][0]['environment_events'][0]
        (self.run/event['folder']/'stdout.log').write_text('tampered')
        with self.assertRaises(ValueError): self.packet()

    def test_no_implicit_host_execution(self):
        with self.assertRaises(ValueError): attempt(self.run,'case-0001',self.root/'missing-plan.json')

    def test_old_run_not_rewritten(self):
        state=load(self.run);state['schema']='orthogonal-review.run.v1'
        write(self.run/'_internal/state.json',state)
        with self.assertRaises(ValueError): finalize(self.run)
        self.assertFalse((self.run/'review.html').exists())

    def test_cannot_finalize_twice(self):
        self.chain();p=self.packet('reviewer',self.make_actor('fictional-reviewer'));self.review(p)
        finalize(self.run)
        before=(self.run/'review.html').read_bytes()
        with self.assertRaises(ValueError):finalize(self.run)
        self.assertEqual(before,(self.run/'review.html').read_bytes())

    def partial_result(self, fail=False):
        self.chain();self.block_environment()
        p=self.packet('reviewer',self.make_actor('fictional-reviewer'))
        ev=[self.ref(p,'chain/R1/output/artifact.txt')]
        rounds=[]
        for r in ('R1','R2','R3'):
            status='not_reviewed' if r=='R3' else 'fail' if fail and r=='R1' else 'pass'
            check=dict(id=r+'-check',title='FICTIONAL check',status=status,reason='fixture',evidence=ev)
            if status!='pass':check.update(cause='environment' if r=='R3' else 'execution',owner='review' if r=='R3' else 'executor',action='fixture action',done_when='fixture verified')
            if status=='not_reviewed':check['requirement_id']='fictional-tool'
            rounds.append(dict(round=r,status=status,reason='fixture result',evidence=ev,checks=[check]))
        result=dict(session_id='fictional-reviewer',summary='fixture mixed result',rounds=rounds,findings=[],evidence=ev,limitations=[])
        write(p/'result.json',result);submit(p,p/'result.json')
        return finalize(self.run)

    def test_partial_pass_has_no_quality_verdict(self):
        result=self.partial_result()
        self.assertIsNone(result['verdict']);self.assertEqual(result['review_status'],'incomplete')

    def test_failure_with_unreviewed_is_fail_and_incomplete(self):
        result=self.partial_result(True)
        self.assertEqual(result['verdict'],'fail');self.assertEqual(result['review_status'],'incomplete')
        text=(self.run/'review.html').read_text(encoding='utf-8')
        self.assertIn('<h1>不通过</h1>',text);self.assertIn('未审查 <b>1</b>',text)

    def test_all_fail_is_completed_with_specific_attribution(self):
        self.chain();p=self.packet('reviewer',self.make_actor('fictional-reviewer'));self.review(p,'unusable')
        result=finalize(self.run)
        self.assertEqual(result['verdict'],'fail');self.assertEqual(result['review_status'],'completed')
        repair=(self.run/'repair.md').read_text(encoding='utf-8')
        self.assertIn('执行结果',repair);self.assertNotIn('归因：任务材料/交付',repair)

    def test_batch_pass_and_blocked_remains_incomplete(self):
        self.chain();p=self.packet('reviewer',self.make_actor('fictional-reviewer'));self.review(p)
        state=load(self.run)
        import copy
        self.block_environment()
        after=load(self.run)
        extra=copy.deepcopy(after['cases'][0]);extra.update(key='case-0002',label='fictional-blocked',packets=[])
        state['cases'].append(extra)
        write(self.run/'_internal/state.json',state)
        result=finalize(self.run)
        self.assertIsNone(result['verdict']);self.assertEqual(result['review_status'],'incomplete')
        self.assertEqual(load(self.run)['cases'][0]['verdict'],'pass')

    def test_declare_accepts_cli_relative_run(self):
        import os
        run=prepare([self.source],self.root/'relative-run')
        req=self.root/'relative-requirements.json'
        write(req,[dict(id='tool',title='fixture',rounds=['R1','R2','R3'])])
        declare(os.path.relpath(run,Path.cwd()),'case-0001',req)
        self.assertTrue(load(run)['cases'][0]['requirements_receipt'])

if __name__=='__main__': unittest.main()
