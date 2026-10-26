"""Coordinator-owned environment preparation and immutable command receipts.

Commands are reviewed by the host agent, never sourced from task instructions.
This is an explicitly authorized host runner, not a security sandbox.
"""
from pathlib import Path
from uuid import uuid4
import json
import subprocess
import time
from .io import read, write, sha, fingerprint, text


def verify_environment(run, state):
    for case in state['cases']:
        if case.get('requirements_receipt'):
            req=Path(run)/case['requirements_receipt']['path']
            if sha(req)!=case['requirements_receipt']['sha256'] or read(req)!=case['requirements']:
                raise ValueError('冻结环境需求被修改')
        for event in case['environment_events']:
            folder = Path(run)/event['folder']
            if fingerprint(folder) != event['sha256']:
                raise ValueError('环境配置/能力回执被修改')
            if read(folder/'receipt.json') != {k:v for k,v in event.items() if k not in {'folder','sha256'}}:
                raise ValueError('环境事件与实际回执不一致')


def declare(run, case_key, requirements_path):
    from .engine import load, verify, save, ROUNDS
    run=Path(run).resolve()
    state = load(run); verify(run,state)
    if state['finalized']: raise ValueError('运行已冻结')
    case = next(c for c in state['cases'] if c['key']==case_key)
    if case['requirements'] or case['packets']: raise ValueError('环境需求须在实作前一次声明')
    requirements = read(requirements_path)
    if not isinstance(requirements,list) or not requirements: raise ValueError('须声明专业能力需求')
    ids = set(); covered = set()
    for req in requirements:
        text(req.get('id'),'requirement id'); text(req.get('title'),'能力需求')
        if req['id'] in ids: raise ValueError('重复环境需求')
        ids.add(req['id'])
        if not isinstance(req.get('rounds'),list) or not req['rounds'] or not set(req['rounds'])<=set(ROUNDS): raise ValueError('需求须对应实际轮次')
        covered.update(req['rounds'])
    if covered != set(ROUNDS): raise ValueError('须覆盖三轮环境需求')
    receipt=Path(run)/'_internal/environment'/case_key/'requirements.json'
    write(receipt,requirements)
    case['requirements']=requirements
    case['requirements_receipt']={'path':receipt.relative_to(Path(run).resolve()).as_posix(),'sha256':sha(receipt)}
    save(run,state)


def readiness(case, requirement_id):
    events=[e for e in case['environment_events'] if e['requirement_id']==requirement_id]
    if not events: return 'unprepared'
    return 'ready' if events[-1]['phase']=='probe' and events[-1]['capability_verified'] else 'blocked'


def blocked_with_attempts(case, requirement_id):
    if not any(r['id']==requirement_id for r in case['requirements']): return False
    events=[e for e in case['environment_events'] if e['requirement_id']==requirement_id]
    # A failed operational probe after a real install AND a repair/alternative.
    phases=[e['phase'] for e in events]
    return (len(events)>=3 and 'configure' in phases and 'repair' in phases
            and phases.index('configure')<len(events)-1 and phases.index('repair')<len(events)-1
            and events[-1]['phase']=='probe' and not events[-1]['capability_verified']
            and events[-1].get('blocker') in {'license','permission','dependency_unavailable'})


def attempt(run, case_key, plan_path, allow_host=False):
    from .engine import load, verify, save, now
    run=Path(run).resolve();state=load(run);verify(run,state)
    if state['finalized']: raise ValueError('运行已冻结')
    if not allow_host: raise ValueError('宿主执行须由获授权调度者明确传入 --allow-host')
    case=next(c for c in state['cases'] if c['key']==case_key)
    plan=read(plan_path)
    if plan.get('requirement_id') not in {r['id'] for r in case['requirements']}: raise ValueError('先声明环境需求')
    if plan.get('phase') not in {'configure','repair','probe'}: raise ValueError('环境阶段无效')
    for key in ('reason','source','version'): text(plan.get(key),key)
    argv=plan.get('argv')
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x or '\x00' in x for x in argv): raise ValueError('argv 必须是参数数组')
    timeout=plan.get('timeout_seconds',600)
    if type(timeout)!=int or not 1<=timeout<=3600: raise ValueError('timeout 范围 1..3600')
    refs=plan.get('reviewed_files',[])
    if plan['phase']=='probe' and not refs: raise ValueError('能力 probe 须绑定已审阅的实际操作代码')
    for ref in refs:
        if sha(ref['path'])!=ref.get('sha256'): raise ValueError('环境操作代码指纹不符')
    folder=run/'_internal/environment'/uuid4().hex
    folder.mkdir(parents=True)
    write(folder/'plan.json',plan)
    for i,ref in enumerate(refs): (folder/f'reviewed-{i}.txt').write_bytes(Path(ref['path']).read_bytes())
    receipt={'phase':plan['phase'],'requirement_id':plan['requirement_id'],'argv':argv,'started_at':now(),
             'source':plan['source'],'version':plan['version'],'capability_verified':False,'blocker':plan.get('blocker'),
             'execution':'authorized host; not OS-isolated','exit_code':None}
    start=time.monotonic()
    with (folder/'stdout.log').open('wb') as so,(folder/'stderr.log').open('wb') as se:
        try:
            result=subprocess.run(argv,cwd=run,stdout=so,stderr=se,timeout=timeout,check=False)
            receipt['exit_code']=result.returncode
        except (OSError,subprocess.TimeoutExpired) as exc:
            receipt['error']=str(exc)
    receipt.update(finished_at=now(),elapsed_seconds=round(time.monotonic()-start,3))
    if plan['phase']=='probe' and receipt['exit_code']==0:
        try:
            data=json.loads((folder/'stdout.log').read_text(encoding='utf-8').strip().splitlines()[-1])
            if data.get('capability_verified') is True and text(data.get('operation'),'实际操作') and data.get('measurements'):
                receipt['capability_verified']=True;receipt['measurements']=data
        except (ValueError,IndexError,AttributeError): pass
    receipt['stdout_sha256']=sha(folder/'stdout.log');receipt['stderr_sha256']=sha(folder/'stderr.log')
    write(folder/'receipt.json',receipt)
    verify(run,state)
    case['environment_events'].append({**receipt,'folder':folder.relative_to(run).as_posix(),'sha256':fingerprint(folder)})
    save(run,state)
    return folder/'receipt.json'


def unreviewed_rounds(case):
    from .engine import ROUNDS
    blocked=[r for r in case['requirements'] if blocked_with_attempts(case,r['id'])]
    if not blocked: raise ValueError('不能以未开始审查收尾；须实作/复核，或留下真实配置和排障阻断证据')
    if set().union(*(set(r['rounds']) for r in blocked)) != set(ROUNDS):
        raise ValueError('部分环境可用：须先完成可执行轮次的实作和独立复核')
    reason='；'.join(r['title'] for r in blocked)
    return [{'round':r,'status':'not_reviewed','reason':'环境配置及排障后仍被阻断：'+reason,'checks':[
        {'id':r+'-unreviewed','title':'独立实作与产物核验','status':'not_reviewed','reason':reason,
         'cause':'environment','owner':'review','action':'解决记录中的客观环境阻断后新建运行',
         'done_when':'独立实作及必要产物验证均完成','requirement_id':blocked[0]['id'],'evidence':[]}
    ],'evidence':[]} for r in ROUNDS]
