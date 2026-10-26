"""Optional local Docker runner; the host agent supplies specialist tools separately."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import time
from uuid import uuid4
from .engine import locate, verify, now
from .io import read, write, sha, inside, text

def execute(packet, plan_path):
    run, state, case, role, folder = locate(packet)
    if state['finalized'] or role['status'] != 'open': raise ValueError('角色已经冻结')
    plan = read(plan_path)
    text(plan.get('reason'), '命令与代码审阅说明')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', str(plan.get('image', ''))): raise ValueError('需要本地固定镜像完整 ID')
    argv = plan.get('argv')
    if not isinstance(argv, list) or not argv or any(not isinstance(s,str) or not s or '\x00' in s for s in argv):
        raise ValueError('argv 必须是非空字符串数组')
    timeout = plan.get('timeout_seconds', 180)
    if type(timeout) is not int or not 1 <= timeout <= 3600: raise ValueError('timeout_seconds 范围 1..3600')
    refs = plan.get('reviewed_files')
    if not isinstance(refs,list) or not refs: raise ValueError('须绑定实际审阅过的入口/代码文件')
    for ref in refs:
        p = inside(folder, ref.get('path',''))
        if not p.is_file() or sha(p) != ref.get('sha256'): raise ValueError('代码审阅指纹无效')
    cwd = plan.get('cwd', '.')
    if not inside(folder, cwd).is_dir(): raise ValueError('cwd 不存在')
    name = 'orthogonal-' + uuid4().hex
    log = folder/'logs'/name
    log.mkdir()
    write(log/'plan.json',plan)
    receipt = {'started_at': now(), 'status':'unavailable', 'argv':argv, 'image':plan['image'],
               'reason':'', 'plan_sha256':sha(log/'plan.json'), 'network':'none'}
    docker = shutil.which('docker')
    try:
        if not docker:
            receipt['reason']='Docker 不可用，未执行；可配置已有受控专业环境。'
        else:
            probe = subprocess.run([docker,'image','inspect',plan['image'],'--format','{{.Id}}'],capture_output=True,text=True,timeout=20)
            if probe.returncode or probe.stdout.strip()!=plan['image']:
                receipt['reason']='指定本地镜像不可用，未下载、未执行。'
            else:
                uid = os.getuid() if hasattr(os,'getuid') else 65534
                gid = os.getgid() if hasattr(os,'getgid') else 65534
                user = f'{uid}:{gid}' if uid else '65534:65534'
                command=[docker,'run','--name',name,'--pull','never','--network','none','--read-only',
                         '--cap-drop','ALL','--security-opt','no-new-privileges','--user',user,
                         '--memory','2g','--cpus','2','--pids-limit','128','--tmpfs','/tmp:rw,nosuid,nodev,size=256m',
                         '--env','PYTHONDONTWRITEBYTECODE=1','--mount',f'type=bind,source={folder},target=/work']
                for protected in ('input','parent','chain'):
                    if (folder/protected).is_dir(): command.extend(['--mount',f'type=bind,source={folder/protected},target=/work/{protected},readonly'])
                command.extend(['--workdir','/work/'+cwd.replace('\\','/'),'--entrypoint',argv[0],plan['image'],*argv[1:]])
                start=time.monotonic()
                with (log/'stdout.log').open('wb') as so, (log/'stderr.log').open('wb') as se:
                    try:
                        result=subprocess.run(command,stdout=so,stderr=se,timeout=timeout,check=False)
                        receipt.update(status='executed',exit_code=result.returncode,reason='退出码仅说明命令结果，产物另由独立审查判断。')
                    except subprocess.TimeoutExpired:
                        receipt.update(status='timeout',reason='超时，保留现场；不能据此判任务不可完成。')
                    finally:
                        subprocess.run([docker,'rm','--force',name],capture_output=True,timeout=20,check=False)
                receipt['elapsed_seconds']=round(time.monotonic()-start,3)
                receipt['stdout_sha256']=sha(log/'stdout.log'); receipt['stderr_sha256']=sha(log/'stderr.log')
    except (OSError,subprocess.TimeoutExpired) as exc:
        receipt.update(status='environment_error',reason=str(exc))
    receipt['finished_at']=now()
    write(log/'receipt.json',receipt)
    verify(run,state)
    return log/'receipt.json'
