from __future__ import annotations
import hashlib
import json
import os
import shutil
from pathlib import Path

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def inside(root, value):
    root = Path(root).resolve()
    value = str(value)
    # Both separators are treated as paths, including on Unix.
    if not value or ":" in value or value.startswith(("/", "\\")):
        raise ValueError("需要根目录内的相对路径")
    p = root.joinpath(*value.replace("\\", "/").split("/"))
    for ancestor in [p, *p.parents]:
        if ancestor == root: break
        if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
            raise ValueError("拒绝链接和 junction")
    if not p.resolve().is_relative_to(root):
        raise ValueError("路径越界")
    return p

def files(root):
    root = Path(root)
    if root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
        raise ValueError("输入根目录不能是链接")
    if not root.is_dir(): raise ValueError(f"目录不存在：{root}")
    rows = {}
    for p in sorted(root.rglob("*")):
        inside(root, p.relative_to(root).as_posix())
        if p.is_file(): rows[p.relative_to(root).as_posix()] = sha(p)
    return rows

def fingerprint(root):
    return hashlib.sha256(json.dumps(files(root), sort_keys=True).encode()).hexdigest()

def copy(source, target):
    files(source)  # Reject links before copytree follows anything.
    shutil.copytree(source, target)

def text(value, label):
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"缺少 {label}")
    return value
