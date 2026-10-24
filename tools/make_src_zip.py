"""把项目源码（不含工具链/构建产物）打成一个 zip，方便备份或拷到别的机器。"""
import os
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dist", "yqqs-draw-src.zip")
EXCLUDE_DIRS = {"tools/downloads", "tools/jdk", "tools/build-tools", "tools/platform",
                "build", "dist", "__pycache__", ".git/objects"}  # .git 只保留可读部分


def skip(rel):
    for ex in ("tools/downloads", "tools/jdk", "tools/build-tools", "tools/platform", "build", "dist"):
        if rel == ex or rel.startswith(ex + "/"):
            return True
    return "__pycache__" in rel


count = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not skip(os.path.relpath(os.path.join(dirpath, d), ROOT).replace("\\", "/"))]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            if skip(rel) or name == "yqqs-draw-src.zip":
                continue
            z.write(full, "yqqs-draw/" + rel)
            count += 1

print("打包 %d 个文件 -> %s (%.1f MB)" % (count, OUT, os.path.getsize(OUT) / 1048576.0))
