"""Standard-library CLI. A coding agent orchestrates independent sessions."""
import argparse
import json
import sys
from pathlib import Path
from orthogonal_review.engine import prepare, handoff, submit, limitation, finalize
from orthogonal_review.io import read

def main(argv=None):
    parser=argparse.ArgumentParser(description='Orthogonal Review — 甲方独立实作审查')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run'); group=run.add_mutually_exclusive_group(required=True)
    group.add_argument('--submission',type=Path); group.add_argument('--batch',type=Path)
    run.add_argument('--out',type=Path)
    run.add_argument('--previous-run',type=Path)
    env=sub.add_parser('environment'); env.add_argument('--run',type=Path,required=True); env.add_argument('--case',required=True)
    eg=env.add_mutually_exclusive_group(required=True); eg.add_argument('--requirements',type=Path); eg.add_argument('--plan',type=Path)
    env.add_argument('--allow-host',action='store_true')
    h=sub.add_parser('handoff'); h.add_argument('--run',type=Path,required=True); h.add_argument('--case',required=True)
    h.add_argument('--role',choices=['executor','reviewer','diagnostician'],required=True); h.add_argument('--actor',type=Path,required=True)
    s=sub.add_parser('submit'); s.add_argument('--packet',type=Path,required=True); s.add_argument('--result',type=Path,required=True)
    e=sub.add_parser('execute'); e.add_argument('--packet',type=Path,required=True); e.add_argument('--plan',type=Path,required=True)
    l=sub.add_parser('limit'); l.add_argument('--run',type=Path,required=True); l.add_argument('--case',required=True); l.add_argument('--reason',required=True)
    f=sub.add_parser('finalize'); f.add_argument('--run',type=Path,required=True)
    report=sub.add_parser('report');report.add_argument('--run',type=Path,required=True);report.add_argument('--out',type=Path,required=True)
    d=sub.add_parser('demo'); d.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='run':
            if args.batch:
                batch=read(args.batch)
                if batch.get('schema')!='orthogonal-review.batch.v1' or not isinstance(batch.get('submissions'),list): raise ValueError('批次格式无效')
                submissions=[(args.batch.resolve().parent/Path(p)).resolve() for p in batch['submissions']]
            else: submissions=[args.submission]
            result={'run':str(prepare(submissions,args.out,args.previous_run)),'next':'先声明环境需求并完成真实能力 probe，再创建全新执行会话。'}
        elif args.command=='environment':
            from orthogonal_review.environment import declare, attempt
            if args.requirements:
                declare(args.run,args.case,args.requirements); result={'declared':True}
            else: result={'receipt':str(attempt(args.run,args.case,args.plan,args.allow_host))}
        elif args.command=='handoff': result={'packet':str(handoff(args.run,args.case,args.role,args.actor))}
        elif args.command=='submit': result=submit(args.packet,args.result)
        elif args.command=='execute':
            from orthogonal_review.execute import execute
            result={'receipt':str(execute(args.packet,args.plan))}
        elif args.command=='limit': limitation(args.run,args.case,args.reason); result={'recorded':True}
        elif args.command=='finalize': result=finalize(args.run)
        elif args.command=='report':
            from orthogonal_review.reporting import export
            result=export(args.run,args.out)
        else:
            from orthogonal_review.demo import create
            result={'submission':str(create(args.out))}
        print(json.dumps(result,ensure_ascii=False)); return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(f'Orthogonal Review: {exc}',file=sys.stderr); return 2

if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'): stream.reconfigure(encoding='utf-8')
    sys.exit(main())
