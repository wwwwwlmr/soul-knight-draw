"""下载 GitHub CLI（gh.exe）到 tools/gh/，用于登录并创建仓库。"""
import json
import os
import re
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
DEST = os.path.join(TOOLS, "gh")


def http(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout)


def find_asset():
    try:
        data = json.load(http("https://api.github.com/repos/cli/cli/releases/latest"))
        for asset in data["assets"]:
            if asset["name"].endswith("windows_amd64.zip"):
                return asset["name"], asset["browser_download_url"]
    except Exception as exc:
        print("api.github.com 不可用（%s），改用页面解析" % exc)
    html = http("https://github.com/cli/cli/releases/latest").read().decode("utf-8", "replace")
    m = re.search(r"/cli/cli/releases/tag/(v[\d.]+)", html)
    if not m:
        raise SystemExit("找不到最新版本号")
    version = m.group(1)
    name = "gh_%s_windows_amd64.zip" % version[1:]
    return name, "https://github.com/cli/cli/releases/download/%s/%s" % (version, name)


def main():
    name, url = find_asset()
    print("asset:", name)
    os.makedirs(TOOLS, exist_ok=True)
    zpath = os.path.join(TOOLS, name)
    with http(url, timeout=300) as r, open(zpath, "wb") as fh:
        total = 0
        while True:
            chunk = r.read(262144)
            if not chunk:
                break
            fh.write(chunk)
            total += len(chunk)
    print("downloaded %.1f MB" % (total / 1048576.0))
    os.makedirs(DEST, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(DEST)
    os.remove(zpath)
    for base, _, files in os.walk(DEST):
        if "gh.exe" in files:
            print("gh:", os.path.join(base, "gh.exe"))
            break


if __name__ == "__main__":
    main()
