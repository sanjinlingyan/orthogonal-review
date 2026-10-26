"""Export a new presentation without changing an archived audit or its verdict."""
import copy
import os
from pathlib import Path
from .io import sha, write
from .engine import ROOT, load, verify, conclude
from .render import render


def export(run, out):
    run=Path(run).resolve();out=Path(out).resolve()
    state=load(run)
    # Historical code is recorded by its implementation fingerprint. Rendering
    # never executes it or changes it; all source and sealed evidence is checked.
    verify(run,state,check_implementation=False)
    if not state['finalized']: raise ValueError('仅可导出已完成收口的 v2 报告')
    for case in state['cases']:
        if any(p['status']=='open' for p in case['packets']): raise ValueError('存在未冻结角色')
        if (case['verdict'],case['review_status'])!=conclude(case): raise ValueError('冻结结论与原始角色结果不一致')
    verdict='fail' if any(c['verdict']=='fail' for c in state['cases']) else 'pass' if all(c['verdict']=='pass' for c in state['cases']) else None
    status='completed' if all(c['review_status']=='completed' for c in state['cases']) else 'incomplete'
    if (state['verdict'],state['review_status'])!=(verdict,status): raise ValueError('批次冻结结论不一致')
    if out.exists(): raise ValueError('报告导出目录必须是新目录')
    for protected in [ROOT,run,*[Path(c['submission']) for c in state['cases']]]:
        if out.is_relative_to(protected) or protected.is_relative_to(out): raise ValueError('导出目录不能覆盖仓库、输入或原运行')
    try: prefix=Path(os.path.relpath(run,out)).as_posix()
    except ValueError: raise ValueError('导出目录须与原运行在同一盘符，以保留相对证据链接')
    display=copy.deepcopy(state)
    display['record_path']=prefix+'/_internal/state.json'
    for case in display['cases']:
        for packet in case['packets']:packet['folder']=prefix+'/'+packet['folder']
        for event in case['environment_events']:event['folder']=prefix+'/'+event['folder']
    human,repair=render(display)
    out.mkdir(parents=True)
    (out/'review.html').write_text(human,encoding='utf-8')
    (out/'repair.md').write_text(repair,encoding='utf-8')
    write(out/'_internal/provenance.json',{'audit_run':str(run),'audit_state_sha256':sha(run/'_internal/state.json'),
          'audit_implementation':state['implementation'],'renderer_sha256':sha(Path(__file__).with_name('render.py')),
          'verdict':verdict,'review_status':status,'operation':'presentation export; no new execution or changed judgement'})
    return {'human_report':str(out/'review.html'),'agent_report':str(out/'repair.md'),'verdict':verdict,'review_status':status}
