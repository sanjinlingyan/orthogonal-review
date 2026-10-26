"""Scan the exact Git index or tracked files before publishing; no secret values printed."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOP={'README.md','AGENTS.md','LICENSE','.gitignore','.gitattributes','run.py'}
DIRS={'orthogonal_review','docs','tests','tools','.github'}
PATTERNS={
    'credential':re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{25,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)'),
    'personal_path':re.compile(r'(?:[A-Za-z]:[\\/]+Users[\\/]+[^\s/\\]+|/(?:Users|home)/[A-Za-z0-9_.-]+/)'),
    'private_link':re.compile(r'https?://(?:[^/]+\.)?(?:dingtalk\.com|feishu\.cn|larksuite\.com)/'),
    'real_task_id':re.compile(r'\b[A-Z]{3}-\d{2}\b'),
}

def scan(staged):
    command=['git','diff','--cached','--name-only','--diff-filter=ACMR','-z'] if staged else ['git','ls-files','-z']
    names=subprocess.check_output(command,cwd=ROOT).decode().split('\0')
    errors=[]
    for name in filter(None,names):
        p=Path(name)
        if name not in TOP and (p.parts[0] not in DIRS or p.suffix not in {'.py','.md','.yml','.yaml'}):
            errors.append(f'{name}: 不在公开文件允许清单'); continue
        data=subprocess.check_output(['git','show',':'+name],cwd=ROOT).decode('utf-8') if staged else (ROOT/p).read_text(encoding='utf-8')
        for n,line in enumerate(data.splitlines(),1):
            for label,pattern in PATTERNS.items():
                if pattern.search(line): errors.append(f'{name}:{n}: {label}')
    return errors

if __name__=='__main__':
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'): stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--staged',action='store_true'); g.add_argument('--tracked',action='store_true'); args=p.parse_args()
    errors=scan(args.staged); print('\n'.join(errors) if errors else '公开检查通过；仍需人工核对完整 diff。'); raise SystemExit(bool(errors))
