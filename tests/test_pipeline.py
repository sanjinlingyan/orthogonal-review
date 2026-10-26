"""Fictional fixtures and simulated sessions test protocol, not model independence."""
import tempfile
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

    def review(self,p,usability='usable',findings=None):
        result=dict(session_id=read(p/'packet.json')['session_id'],usability=usability,summary='simulated independent check',rounds=[],findings=findings or [],evidence=[self.ref(p,'chain/R1/output/artifact.txt')],limitations=[])
        for r in ('R1','R2','R3'):
            exists=(p/f'chain/{r}/output/artifact.txt').exists()
            result['rounds'].append(dict(round=r,status=usability if exists else 'unknown',reason='fixture check' if exists else 'not executed',evidence=[self.ref(p,f'chain/{r}/output/artifact.txt')] if exists else []))
        write(p/'result.json',result); submit(p,p/'result.json')

    def test_success_and_two_reports(self):
        self.chain(); p=self.packet('reviewer',self.make_actor('fictional-reviewer')); self.review(p)
        self.assertEqual(finalize(self.run)['verdict'],'verified')
        self.assertEqual({p.name for p in self.run.iterdir() if p.is_file()},{'review.html','repair.md'})
        self.assertIn('chain/R1/output/artifact.txt',(self.run/'review.html').read_text(encoding='utf-8'))

    def test_no_execution_is_unknown(self):
        limitation(self.run,'case-0001','No specialist environment')
        self.assertEqual(finalize(self.run)['verdict'],'unknown')

    def test_failed_agent_is_not_task_defect(self):
        p=self.packet(); self.finish(p,'failed')
        p=self.packet('reviewer',self.make_actor('fictional-reviewer')); self.review(p,'unusable')
        self.assertEqual(finalize(self.run)['verdict'],'unknown')

    def test_confirmed_task_defect(self):
        self.finish(self.packet(),'blocked'); p=self.packet('reviewer',self.make_actor('fictional-reviewer'))
        f=dict(id='OBS-1',problem='fictional inconsistent units',location='request.md',cause='task_material',confidence='confirmed',action='clarify units',done_when='units consistent',evidence=[self.ref(p,'chain/R1/input/request.md')])
        self.review(p,'unusable',[f]); self.assertEqual(finalize(self.run)['verdict'],'defect')

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
        self.assertEqual(finalize(run)['verdict'],'unknown')

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

    def test_batch_does_not_hide_unknown(self):
        second=create(self.root/'second-fictional'); run=prepare([self.source,second],self.root/'batch-run')
        self.assertEqual(len(load(run)['cases']),2)
        self.assertEqual(finalize(run)['verdict'],'unknown')

    def test_render_escapes_untrusted_html(self):
        limitation(self.run,'case-0001','<script>alert(1)</script>')
        finalize(self.run)
        self.assertNotIn('<script>',(self.run/'review.html').read_text(encoding='utf-8'))

    def test_one_diagnostic_and_no_replacement(self):
        self.chain()
        reviewer=self.packet('reviewer',self.make_actor('fictional-reviewer')); self.review(reviewer,'unusable')
        diagnostic=self.packet('diagnostician',self.make_actor('fictional-diagnostic'))
        result=dict(session_id='fictional-diagnostic',usability='usable',summary='separate diagnostic',attempt_status='completed',rounds=[],findings=[],evidence=[self.ref(diagnostic,'chain/R1/output/artifact.txt')],limitations=[])
        for r in ('R1','R2','R3'):
            result['rounds'].append(dict(round=r,status='usable',reason='diagnostic fixture',evidence=[self.ref(diagnostic,f'chain/{r}/output/artifact.txt')]))
        write(diagnostic/'result.json',result); submit(diagnostic,diagnostic/'result.json')
        with self.assertRaises(ValueError): self.packet('diagnostician',self.make_actor('fictional-extra'))
        self.assertEqual(finalize(self.run)['verdict'],'unknown')
        self.assertEqual(read(reviewer/'sealed-result.json')['usability'],'unusable')

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
        handoff(run,'case-0001','executor',self.actor)
        with self.assertRaises(ValueError): handoff(run,'case-0002','executor',self.actor)

if __name__=='__main__': unittest.main()
