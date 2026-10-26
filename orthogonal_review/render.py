"""Compact client report; operational details stay in the private run record."""
from html import escape
from urllib.parse import quote

WORDS={'pass':'通过','fail':'不通过','not_reviewed':'未审查',None:'未完成审查',
       'completed':'已完成审查','incomplete':'未完成审查','task_material':'任务材料/交付',
       'environment':'审查环境','execution':'执行结果','agent_capability':'Agent 能力','unresolved':'原因未明'}

def h(x): return escape(str(x),quote=True)
def md(x): return str(x).replace('<','&lt;').replace('>','&gt;').replace('\r','').replace('\n',' ')
def ev_text(e): return f"{e['path']} — {e['locator']} · SHA256 {e['sha256']}"


def render(state):
    rows=[]; items=[]; detail=[]; counts={k:0 for k in ('pass','fail','not_reviewed')}
    repair=['# 正交审查修复单','',f"**结论：{WORDS[state['verdict']]}；{WORDS[state['review_status']]}**",'',
            '甲方审查：任务缺陷、实作错误与审查环境责任分别处理。不能把未审查写成乙方缺陷。保留首次现场，修订交付或更换执行条件后新建运行。','']
    for case in state['cases']:
        packet=next((p for p in case['packets'] if p['role']=='reviewer' and p['status']=='submitted'),None)
        rounds=packet['result']['rounds'] if packet else case['unreviewed_rounds']
        root=packet['folder'] if packet else '_internal/environment'
        for rr in rounds:
            checks=rr['checks']
            for ch in checks: counts[ch['status']]+=1
            round_refs=''.join(f"<li><a href='{quote(root+'/'+e['path'],safe='/')}'>{h(e['locator'])}</a></li>" for e in rr.get('evidence',[]))
            evidence_detail=f'<details><summary>依据</summary><ul>{round_refs}</ul></details>' if round_refs else ''
            rows.append(f"<tr><td>{h(case['label'])}</td><td>{h(rr['round'])}</td><td class='{h(rr['status'])}'>{WORDS[rr['status']]}</td><td>{h(rr['reason'])}{evidence_detail}</td></tr>")
            for ch in checks:
                if ch['status']=='pass': continue
                title=f"{rr['round']} · {ch['title']}"
                evidence=ch.get('evidence',[])
                short='；'.join(e['locator'] for e in evidence[:2]) or '环境配置与排障回执'
                refs=''.join(f"<li><a href='{quote(root+'/'+e['path'],safe='/')}'>{h(e['locator'])}</a></li>" for e in evidence)
                items.append(f"<article><h3>{h(title)} · {WORDS[ch['status']]}</h3><p>{h(ch['reason'])}</p><p>影响与下一步：{h(ch['action'])}</p><p class='muted'>依据：{h(short)}</p><details><summary>查看证据</summary><ul>{refs}</ul></details></article>")
                repair.extend([f"## {md(case['label'])} / {md(title)}",'',f"状态：{WORDS[ch['status']]}；归因：{WORDS[ch['cause']]}；责任方：{md(ch['owner'])}",'',
                    f"问题及影响：{md(ch['reason'])}",'',f"位置：{rr['round']} / {md(ch['id'])}",'',f"行动：{md(ch['action'])}",'',f"复验条件：{md(ch['done_when'])}",'',f"证据根目录：{root}",'',*['- '+md(ev_text(e)) for e in evidence],''])
                if ch.get('requirement_id'):
                    for event in case['environment_events']:
                        if event['requirement_id']==ch['requirement_id']:
                            repair.append(f"- 环境回执：{event['folder']}/receipt.json；阶段 {event['phase']}；退出码 {event['exit_code']}；目录 SHA256 {event['sha256']}")
        if packet:
            for f in packet['result']['findings']:
                repair.extend([f"### 发现 {md(f['id'])}",'',f"{md(f['problem'])}；位置：{md(f['location'])}",'',f"归因：{WORDS[f['cause']]} / {md(f['confidence'])}",'',f"行动：{md(f['action'])}",'',f"完成条件：{md(f['done_when'])}",'',*['- '+md(ev_text(e)) for e in f['evidence']],''])
        for limit in state['limitations']:
            if limit['case_key']==case['key']: detail.append(h(limit['reason']))
    headline=WORDS[state['verdict']]
    reason=(f"{counts['fail']} 项不通过，需要处理后复验。" if counts['fail'] else
            '所有必要项目均已完成实作及独立验证。' if state['verdict']=='pass' else
            '真实配置和排障后仍有必要项目未审查，当前不作质量判定。')
    if not items:
        items=['<p>本轮未发现需修复问题。</p>']
        repair.extend(['无需修复事项；结论仅覆盖本次版本、实际任务与验证范围。',''])
    repair.extend(['## 私有追溯记录','',f"运行编号：{state['run_id']}",'','完整平台回执、环境配置、角色结果及证据均在 `_internal/`。不要改写旧记录。',''])
    html=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>正交审查 · {headline}</title><style>
body{{font:16px/1.65 system-ui,'Microsoft YaHei',sans-serif;max-width:1040px;margin:32px auto;padding:0 20px;background:#f5f7f9;color:#18313b}}header,section{{background:white;padding:24px;border:1px solid #dfe6eb;border-radius:12px;margin:16px 0}}h1{{font-size:36px;margin:8px 0}}h2{{font-size:21px}}h3{{font-size:17px}}.muted{{color:#607482;font-size:13px}}.pass{{color:#136648}}.fail{{color:#b52d35}}.not_reviewed{{color:#89600b}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #e3e9ec;vertical-align:top}}td:last-child{{width:58%}}article{{border-top:1px solid #e3e9ec;padding:12px 0}}a{{color:#076879}}p,td{{overflow-wrap:anywhere}}@media(max-width:650px){{body{{padding:0 8px}}header,section{{padding:16px}}td,th{{padding:6px}}}}
</style></head><body><header><p class="muted">ORTHOGONAL REVIEW · 甲方独立实作审查</p><h1>{headline}</h1><p>{h(reason)}</p><p>通过 <b>{counts['pass']}</b> · 不通过 <b>{counts['fail']}</b> · 未审查 <b>{counts['not_reviewed']}</b> ｜ {WORDS[state['review_status']]}</p><a href="repair.md">Agent 修复单</a></header>
<section><h2>审查结果</h2><table><thead><tr><th>提交</th><th>轮次</th><th>结论</th><th>说明</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
<section><h2>需要处理的事项</h2>{''.join(items)}</section><section><details><summary>审查范围与追溯</summary><p>独立冷启动实作与产物复核，不代替合同逐项验收。</p>{''.join('<p>'+x+'</p>' for x in detail)}<p class="muted">{h(state['run_id'])} · {h(state['finalized_at'])} · 内部记录：_internal/state.json</p></details></section></body></html>'''
    return html,'\n'.join(repair)
