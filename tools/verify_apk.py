import os
import subprocess
import sys
import zipfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APK = os.path.join(ROOT, "dist", "soul-knight-draw-v1.1.2.apk")
JDK = os.path.join(ROOT, "tools", "jdk", "jdk-17.0.20.1+1")
BT = os.path.join(ROOT, "tools", "build-tools", "android-14")
env = dict(os.environ)
env["JAVA_HOME"] = JDK
env["PATH"] = os.path.join(JDK, "bin") + os.pathsep + BT + os.pathsep + env["PATH"]

print("== apksigner verify ==")
print(subprocess.run(["cmd", "/c", os.path.join(BT, "apksigner.bat"), "verify", "--verbose", APK],
                     env=env, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip())

print("\n== assets/index.html 内容一致性 ==")
with open(os.path.join(ROOT, "web", "index.html"), "rb") as fh:
    local = fh.read()
with zipfile.ZipFile(APK) as z:
    packed = z.read("assets/index.html")
print("local bytes=%d crc=%08x | packed bytes=%d crc=%08x | identical=%s" % (
    len(local), zlib.crc32(local), len(packed), zlib.crc32(packed), local == packed))
names = set(z.namelist())
missing = [n for n in names if n.startswith("assets/assets/") and n not in names]
print("assets/assets/* 条目数:", sum(1 for n in names if n.startswith("assets/assets/")))
print("字体:", [n for n in names if n.endswith(".ttf")])

print("\n== dexdump classes.dex ==")
with zipfile.ZipFile(APK) as z:
    open(os.path.join(ROOT, "build", "classes.dex"), "wb").write(z.read("classes.dex"))
out = subprocess.run([os.path.join(BT, "dexdump.exe"), "-f", os.path.join(ROOT, "build", "classes.dex")],
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
for line in out.stdout.splitlines():
    if "Class descriptor" in line or "checksum" in line or "file_size" in line:
        print(line.strip())
