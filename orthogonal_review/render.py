from html import escape

WORDS={'verified':'已验证可完成且可用','defect':'已确认存在任务或交付缺陷','unknown':'尚无法确定',
       'completed':'完成','failed':'执行失败','blocked':'阻塞','usable':'可用','unusable':'不可用','open':'未提交',
       'task_material':'任务材料/交付缺陷','environment':'环境问题','execution':'执行问题','agent_capability':'Agent 能力限制','unresolved':'原因未明',
       'executor':'冷启动实作','reviewer':'独立产物审查','diagnostician':'独立诊断'}
def h(value): return escape(str(value),quote=True)
def md(value): return str(value).replace('<','&lt;').replace('>','&gt;').replace('\r','').replace('\n',' ')
def ev_text(e): return f"{e['path']} — {e['locator']} · SHA256 {e['sha256']}"

def render(state):
    summary=[]; details=[]; findings=[]
    repair=['# 正交审查修复单','',f"**结论：{WORDS[state['verdict']]}**",'',
            '你是乙方修复 Agent。按下面的现场证据修复交付；不要修改甲方原始材料、审查记录或用参考答案替换实作。修复后提交新版本并新建冷启动运行。',
            '', '任务缺陷、执行错误、环境问题和原因未明分别处理；Agent 失败不自动证明任务有缺陷。','']
    for c in state['cases']:
        summary.append(f"<tr><td>{h(c['label'])}</td><td>{h(WORDS[c['verdict']])}</td></tr>")
        body=[]
        for p in c['packets']:
            r=p.get('result',{})
            verdict=r.get('status',r.get('usability','open'))
            body.append(f"<h3>{h(WORDS[p['role']])} {h(p['round'] or '')} · {h(WORDS.get(verdict,verdict))}</h3><p>{h(r.get('summary','本角色尚未提交结果'))}</p>")
            body.append(f"<p class='muted'>会话：{h(p['actor']['session_id'])}；隔离方式：{h(p['actor']['isolation'])}。会话身份来自平台回执和调度记录，文件指纹不证明模型记忆隔离。</p>")
            for key in ('questions','assumptions','steps','limitations'):
                if r.get(key): body.append(f"<details><summary>{h({'questions':'澄清问题','assumptions':'采用的假设','steps':'实际步骤','limitations':'判断限制'}[key])}</summary><ul>"+''.join(f'<li>{h(x)}</li>' for x in r[key])+'</ul></details>')
            if r.get('evidence'):
                body.append(f"<details><summary>本角色判断的直接证据</summary><p class='muted'>相对根目录：{h(p['folder'])}</p><ul>"+''.join(f'<li>{h(ev_text(e))}</li>' for e in r['evidence'])+'</ul></details>')
            for rr in r.get('rounds',[]):
                body.append(f"<details><summary>{h(rr['round'])}：{h(WORDS[rr['status']])}</summary><p>{h(rr['reason'])}</p><ul>"+''.join(f'<li>{h(ev_text(e))}</li>' for e in rr['evidence'])+'</ul></details>')
            for f in r.get('findings',[]):
                title=f"{c['label']} · {f['id']} · {WORDS[f['cause']]}"
                findings.append((f['confidence']=='confirmed' and f['cause']=='task_material',title,f['problem']))
                body.append(f"<details><summary>{h(title)} · {h(f['confidence'])}</summary><p>{h(f['problem'])}</p><p>位置：{h(f['location'])}</p><p>行动：{h(f['action'])}</p><p>验证条件：{h(f['done_when'])}</p><ul>"+''.join(f'<li>{h(ev_text(e))}</li>' for e in f['evidence'])+'</ul></details>')
                repair.extend([f'## {md(title)}','',f"归因状态：{md(f['confidence'])}",'',f"问题：{md(f['problem'])}",'',f"位置：{md(f['location'])}",'',f"行动：{md(f['action'])}",'',f"完成条件：{md(f['done_when'])}",'',f"证据根目录：{p['folder']}",'',*['- '+md(ev_text(e)) for e in f['evidence']],''])
        if c['missing_rounds']: body.append(f"<p>未提供轮次材料：{h(', '.join(c['missing_rounds']))}</p>")
        limitations=[x['reason'] for x in state['limitations'] if x['case_key']==c['key']]
        if c['verdict']=='unknown' and not limitations: limitations=['现有实作和独立检查尚不足以确认三轮可完成且可用；详见角色状态及证据。']
        for reason in limitations:
            body.append(f'<p class="unknown">限制：{h(reason)}</p>')
            repair.extend([f"## {md(c['label'])} · 待补证或环境条件",'',md(reason),'','行动：核实缺失条件并提交实际证据；环境问题由环境负责人处理，原因未明保留待定。',''])
        details.append(f"<section><h2>{h(c['label'])} · {h(WORDS[c['verdict']])}</h2>{''.join(body)}</section>")
    major=''.join(f'<li><strong>{h(title)}</strong><p>{h(problem)}</p></li>' for _,title,problem in sorted(findings,key=lambda x:not x[0])[:5])
    if not major: major='<li>没有已记录的具体缺陷；是否已验证可用请看总体结论与各题执行范围。</li>'
    if not findings and state['verdict']=='verified': repair.extend(['没有需修复事项。本结论仅覆盖本次任务、版本、环境和实际执行范围。',''])
    repair.extend(['## 重审','', '保留本次输入、失败现场及所有尝试。修订交付、补充说明或更换执行条件后，建立新的运行；不挑选最好一次覆盖原结果。',''])
    html=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Orthogonal Review · {h(WORDS[state['verdict']])}</title><style>
body{{font-family:system-ui,'Microsoft YaHei',sans-serif;max-width:1080px;margin:32px auto;padding:0 22px;background:#f1f5f7;color:#172f3b;line-height:1.7}}header,section{{background:white;border:1px solid #dce4e8;border-radius:14px;padding:26px;margin:18px 0}}h1{{font-size:32px}}h2{{font-size:22px}}h3{{font-size:17px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #ddd}}table{{width:100%}}.muted{{color:#607681;font-size:13px}}.unknown{{color:#946000}}details{{padding:12px 0;border-bottom:1px solid #e8edf0}}p,li,td{{overflow-wrap:anywhere}}a{{color:#126b76}}@media(max-width:650px){{body{{padding:0 10px}}header,section{{padding:18px}}h1{{font-size:26px}}}}</style></head><body>
<header><p class="muted">ORTHOGONAL REVIEW / 甲方独立实作审查</p><h1>{h(WORDS[state['verdict']])}</h1><p>判断实际接手、完成和使用情况。执行者的失败与任务缺陷分别归因，无法证实的事项保留未确定。</p><p><a href="repair.md">给乙方 Agent 的修复单</a></p><p class="muted">{h(state['run_id'])} · {h(state['finalized_at'])}</p></header>
<section><h2>最需要关注的发现</h2><ol>{major}</ol></section><section><h2>逐题结论</h2><table><thead><tr><th>提交</th><th>结论</th></tr></thead><tbody>{''.join(summary)}</tbody></table></section>
{''.join(details)}<section><h2>证据与范围</h2><p>详细机器记录、平台回执索引、角色输入和冻结产物保存在本运行的 _internal 目录。没有独立执行与产物证据时，报告不能确认可完成且可用。</p><p class="muted">实现指纹：{h(state['implementation'])}</p></section></body></html>'''
    return html,'\n'.join(repair)
