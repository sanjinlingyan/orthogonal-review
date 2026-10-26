from pathlib import Path
from .engine import ROOT

def create(out):
    out=Path(out).resolve()
    if out.exists() or out.is_relative_to(ROOT) or ROOT.is_relative_to(out): raise ValueError('演示须放在仓库外的新目录')
    requests=[
        '虚构任务：汇总 stock.csv 的库存数量，输出可编辑 summary.csv（item,quantity 两列）以及 notes.txt 说明合计。保持商品顺序。',
        '在自己上一轮真实产物上，依据 changes.csv 调整数量；保留商品顺序。输出新的 summary.csv 和 notes.txt，写清新合计。',
        '沿用上一轮真实产物。根据 price.csv 新增 unit_price 和 total 列，输出 summary.csv 与 notes.txt。total=quantity*unit_price，notes 写数量合计与金额合计。']
    inputs=[('stock.csv','item,quantity\nWidget,3\nGadget,5\n'),('changes.csv','item,delta\nWidget,2\nGadget,-1\n'),('price.csv','item,unit_price\nWidget,4\nGadget,7\n')]
    for i,(request,(name,data)) in enumerate(zip(requests,inputs),1):
        p=out/f'R{i}'/'candidate'; p.mkdir(parents=True)
        (p/'request.md').write_text(request+'\n',encoding='utf-8'); (p/name).write_text(data,encoding='utf-8')
    return out
