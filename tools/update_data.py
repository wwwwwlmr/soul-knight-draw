#!/usr/bin/env python3
"""维护 web/index.html 里内嵌的 DATA（角色技能 + 皮肤），并做资源校验。

用法：
    python tools/update_data.py --extract data.json      # 导出当前数据
    python tools/update_data.py --data data.json         # 用新数据替换并校验
    python tools/update_data.py --check                  # 只校验（引用/未引用图片）
"""
import argparse
import json
import os
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "web", "index.html")
PREFIX = "const DATA = "


def read_page():
    with open(INDEX, "r", encoding="utf-8") as fh:
        return fh.read()


def load_data(text):
    for line in text.splitlines():
        if line.startswith(PREFIX):
            payload = line[len(PREFIX):].strip()
            if payload.endswith(";"):
                payload = payload[:-1]
            return json.loads(payload)
    raise SystemExit("index.html 里找不到 `const DATA = ...;` 这一行")


def replace_data(text, data):
    payload = PREFIX + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(PREFIX):
            lines[i] = payload
            break
    else:
        raise SystemExit("index.html 里找不到 `const DATA = ...;` 这一行")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def referenced_images(data):
    refs = set()
    for item in data.get("charSkill", []):
        for key in ("avatar", "skillImg"):
            if item.get(key):
                refs.add(item[key])
    for pool in data.get("skins", {}).values():
        for entry in pool:
            if len(entry) >= 2 and entry[1]:
                refs.add(entry[1])
    return refs


def check(data, verbose=True):
    refs = referenced_images(data)
    missing = sorted(r for r in refs if not os.path.exists(os.path.join(ROOT, "web", r)))
    on_disk = set()
    assets_dir = os.path.join(ROOT, "web", "assets")
    for name in os.listdir(assets_dir):
        on_disk.add("assets/" + name)
    unused = sorted(on_disk - refs)
    if verbose:
        combos = len(data.get("charSkill", []))
        chars = len(data.get("skins", {}))
        skins = sum(len(v) for v in data.get("skins", {}).values())
        print("角色技能组合 %d · 角色 %d 位 · 皮肤 %d 款 · 引用图片 %d 张" % (combos, chars, skins, len(refs)))
        if missing:
            print("\n[缺失] 数据引用了但文件不存在（%d）：" % len(missing))
            for m in missing:
                print("   -", m)
        else:
            print("图片引用全部存在 ✓")
        if unused:
            print("\n[未引用] assets/ 里没被 DATA 用到的图片 %d 张（可能属于新版本，或可以删除）" % len(unused))
            for u in unused[:20]:
                print("   -", u)
            if len(unused) > 20:
                print("   ... 其余 %d 张" % (len(unused) - 20))
    return missing, unused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", metavar="OUT")
    ap.add_argument("--data", metavar="JSON")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    text = read_page()
    data = load_data(text)

    if args.extract:
        with open(args.extract, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print("已导出 -> %s" % args.extract)
        check(data)
        return

    if args.data:
        with open(args.data, "r", encoding="utf-8") as fh:
            new_data = json.load(fh)
        for key in ("charSkill", "skins"):
            if key not in new_data:
                raise SystemExit("新数据缺少字段：%s" % key)
        missing, _ = check(new_data)
        if missing:
            print("\n有图片缺失，已中止写入。请先把图片补进 web/assets/。")
            sys.exit(1)
        with open(INDEX, "w", encoding="utf-8") as fh:
            fh.write(replace_data(text, new_data))
        print("\n已更新 web/index.html 内嵌数据 ✓  记得重新构建 APK。")
        return

    check(data)


if __name__ == "__main__":
    main()
