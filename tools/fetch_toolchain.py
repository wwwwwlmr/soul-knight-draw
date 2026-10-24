"""Download + unpack the Windows toolchain needed to build the yqqs-draw APK
without Android Studio / Gradle: Microsoft OpenJDK 17, Android build-tools 34,
Android platform (android-35) jar.
"""
import os
import sys
import time
import zipfile
import threading
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(ROOT, 'downloads')
os.makedirs(DL, exist_ok=True)

JOBS = [
    # name, url, zip name, unpack dir
    ('jdk17', 'https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip',
     'jdk-17-windows-x64.zip', 'jdk'),
    ('build-tools', 'https://dl.google.com/android/repository/build-tools_r34-windows.zip',
     'build-tools_r34-windows.zip', 'build-tools'),
    ('platform', 'https://dl.google.com/android/repository/platform-35_r02.zip',
     'platform-35_r02.zip', 'platform'),
]

lock = threading.Lock()
status = {}


def human(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return '%.1f%s' % (n, unit)
        n /= 1024.0
    return '%.1fTB' % n


def fetch(name, url, zipname, unpack):
    dest = os.path.join(DL, zipname)
    outdir = os.path.join(ROOT, unpack)
    if os.path.isdir(outdir) and os.listdir(outdir):
        with lock:
            status[name] = 'already unpacked'
        print('[%s] already unpacked -> %s' % (name, outdir), flush=True)
        return
    if not (os.path.exists(dest) and os.path.getsize(dest) > 1000):
        tmp = dest + '.part'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            total = int(r.headers.get('Content-Length') or 0)
            got = 0
            t0 = time.time()
            with open(tmp, 'wb') as f:
                while True:
                    chunk = r.read(262144)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if total and got % (8 * 262144) < 262144:
                        el = max(time.time() - t0, 0.01)
                        print('[%s] %s/%s  %.2f MB/s' % (
                            name, human(got), human(total), got / el / 1048576), flush=True)
        os.replace(tmp, dest)
    print('[%s] downloading done, size=%s' % (name, human(os.path.getsize(dest))), flush=True)
    t0 = time.time()
    with zipfile.ZipFile(dest) as z:
        z.extractall(outdir)
    print('[%s] unpacked in %.1fs -> %s' % (name, time.time() - t0, outdir), flush=True)
    with lock:
        status[name] = 'ok'


threads = []
for job in JOBS:
    t = threading.Thread(target=fetch, args=job, daemon=True)
    t.start()
    threads.append(t)
for t in threads:
    t.join()
print('ALL DONE %r' % (status,), flush=True)
