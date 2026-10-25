#!/usr/bin/env python3
"""元气骑士扭蛋机 · APK 构建脚本（不用 Gradle / Android Studio）

流程与 Gradle 做的事一致，只是显式调用 SDK 工具：
    aapt2 compile  ->  aapt2 link  ->  javac  ->  d8
    ->  classes.dex 并进 apk  ->  zipalign  ->  apksigner

依赖（放在 tools/ 下，用 tools/fetch_toolchain.py 下载）：
    tools/jdk/jdk-*/bin/java.exe             (Microsoft OpenJDK 17)
    tools/build-tools/android-*/             (Android build-tools 34.0.0)
    tools/platform/android-*/android.jar     (Android platform 35)

用法：
    python build.py            # 构建
    python build.py --clean    # 清空 build/ 后重建
"""
import glob
import os
import shutil
import subprocess
import sys
import time
import zipfile

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(ROOT, "tools")
ANDROID = os.path.join(ROOT, "android")
WEB = os.path.join(ROOT, "web")
BUILD = os.path.join(ROOT, "build")
DIST = os.path.join(ROOT, "dist")
KEYSTORE = os.path.join(ANDROID, "keystore", "yqqs-release.jks")
KS_PASS = "yqqs-draw-2024"
KS_ALIAS = "yqqs"

VERSION = "1.1.0"


def log(msg):
    print("\n==> " + msg, flush=True)


def fail(msg):
    print("\n!! " + msg, flush=True)
    sys.exit(1)


def find_one(pattern, what):
    hits = sorted(glob.glob(pattern))
    if not hits:
        fail("找不到%s：%s" % (what, pattern))
    return hits[-1]


def rmtree_soft(path):
    """删除目录；被 JVM 占用或受限的子目录忽略掉，不阻塞构建。"""
    if not os.path.isdir(path):
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(root, name))
            except OSError:
                pass
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def run(argv, cwd=None, env=None, allow_fail=False):
    """执行外部命令；输出先落盘再读，避开受限沙箱里的管道问题。"""
    logfile = os.path.join(BUILD, "cmd.log")
    os.makedirs(BUILD, exist_ok=True)
    # .bat / .cmd 必须经 cmd.exe 执行
    if argv[0].lower().endswith((".bat", ".cmd")):
        argv = ["cmd", "/c"] + argv
    with open(logfile, "w", encoding="utf-8", errors="replace") as fh:
        fh.write("$ " + " ".join(argv) + "\n")
        fh.flush()
        proc = subprocess.run(
            argv,
            cwd=cwd or ROOT,
            env=env,
            stdout=fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
    with open(logfile, "r", encoding="utf-8", errors="replace") as fh:
        output = fh.read()
    print(output.strip()[-4000:], flush=True)
    if proc.returncode != 0 and not allow_fail:
        fail("命令失败(%d)：%s" % (proc.returncode, " ".join(argv)))
    return proc.returncode, output


def detect_toolchain():
    jdk_home = os.path.dirname(
        os.path.dirname(find_one(os.path.join(TOOLS, "jdk", "jdk-*", "bin", "java.exe"), "JDK"))
    )
    build_tools = find_one(os.path.join(TOOLS, "build-tools", "android-*"), "build-tools")
    android_jar = find_one(os.path.join(TOOLS, "platform", "android-*", "android.jar"), "android.jar")
    env = dict(os.environ)
    env["JAVA_HOME"] = jdk_home
    # JDK 工具会往系统临时目录写文件，沙箱下可能被拒；统一改到 build/tmp
    tmp_dir = os.path.join(BUILD, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    env["TEMP"] = env["TMP"] = tmp_dir
    env["PATH"] = os.pathsep.join([
        os.path.join(jdk_home, "bin"),
        build_tools,
        env.get("PATH", ""),
    ])
    return {
        "java_home": jdk_home,
        "javac": os.path.join(jdk_home, "bin", "javac.exe"),
        "keytool": os.path.join(jdk_home, "bin", "keytool.exe"),
        "aapt2": os.path.join(build_tools, "aapt2.exe"),
        "d8": os.path.join(build_tools, "d8.bat"),
        "zipalign": os.path.join(build_tools, "zipalign.exe"),
        "apksigner": os.path.join(build_tools, "apksigner.bat"),
        "android_jar": android_jar,
        "env": env,
    }


def main():
    t0 = time.time()
    if "--clean" in sys.argv:
        rmtree_soft(BUILD)
    for d in (BUILD, DIST):
        os.makedirs(d, exist_ok=True)

    tc = detect_toolchain()
    log("工具链就绪：JDK=%s" % tc["java_home"])
    log("android.jar=%s" % tc["android_jar"])

    # 1. 编译资源
    log("aapt2 compile 资源")
    res_compiled = os.path.join(BUILD, "res-compiled")
    rmtree_soft(res_compiled)
    os.makedirs(res_compiled)
    run([tc["aapt2"], "compile", "--dir", os.path.join(ANDROID, "res"), "-o", res_compiled], env=tc["env"])
    flats = glob.glob(os.path.join(res_compiled, "**", "*.flat"), recursive=True)
    if not flats:
        fail("资源编译结果为空")
    print("   %d 个 .flat 资源" % len(flats))

    # 2. 链接资源和 assets（web/ 整个目录原样进 assets/）
    log("aapt2 link（打包资源 + assets）")
    gen_dir = os.path.join(BUILD, "gen")
    os.makedirs(gen_dir, exist_ok=True)
    unsigned = os.path.join(BUILD, "unsigned.apk")
    if os.path.exists(unsigned):
        os.remove(unsigned)
    run([
        tc["aapt2"], "link",
        "-o", unsigned,
        "-I", tc["android_jar"],
        "--manifest", os.path.join(ANDROID, "AndroidManifest.xml"),
        "-A", WEB,
        "--java", gen_dir,
        "--auto-add-overlay",
    ] + flats, env=tc["env"])

    # 3. 编译 Java
    log("javac 编译 MainActivity")
    classes = os.path.join(BUILD, "classes")
    rmtree_soft(classes)
    os.makedirs(classes)
    sources = glob.glob(os.path.join(ANDROID, "src", "**", "*.java"), recursive=True)
    sources += glob.glob(os.path.join(gen_dir, "**", "*.java"), recursive=True)
    run([
        tc["javac"], "-encoding", "UTF-8", "-source", "8", "-target", "8",
        "-bootclasspath", tc["android_jar"], "-classpath", tc["android_jar"],
        "-d", classes,
    ] + sources, env=tc["env"])

    # 4. d8 生成 dex（直接喂 .class，避免 jar 工具往系统临时目录写文件）
    log("d8 生成 classes.dex")
    class_files = glob.glob(os.path.join(classes, "**", "*.class"), recursive=True)
    if not class_files:
        fail("没有编译出 .class")
    dex_dir = os.path.join(BUILD, "dex")
    rmtree_soft(dex_dir)
    os.makedirs(dex_dir)
    run([tc["d8"], "--release", "--min-api", "21", "--lib", tc["android_jar"],
         "--output", dex_dir] + class_files, env=tc["env"])
    dex = os.path.join(dex_dir, "classes.dex")
    if not os.path.exists(dex):
        fail("没生成 classes.dex")

    # 5. dex 并进 apk（重写 zip，保持条目顺序与存储方式，避免残留两份中央目录）
    log("classes.dex 写入 APK")
    repacked = os.path.join(BUILD, "repacked.apk")
    if os.path.exists(repacked):
        os.remove(repacked)
    with zipfile.ZipFile(unsigned) as src, zipfile.ZipFile(repacked, "w") as dst:
        for info in src.infolist():
            entry = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            entry.compress_type = info.compress_type
            entry.external_attr = info.external_attr
            entry.create_system = info.create_system
            dst.writestr(entry, src.read(info.filename))
        dex_entry = zipfile.ZipInfo("classes.dex", date_time=time.localtime()[:6])
        dex_entry.compress_type = zipfile.ZIP_DEFLATED
        with open(dex, "rb") as fh:
            dst.writestr(dex_entry, fh.read())

    # 6. 对齐
    log("zipalign 4 字节对齐")
    aligned = os.path.join(BUILD, "aligned.apk")
    if os.path.exists(aligned):
        os.remove(aligned)
    run([tc["zipalign"], "-f", "-p", "4", repacked, aligned], env=tc["env"])

    # 7. 签名（首次构建自动生成密钥，务必保留：覆盖安装要用同一把钥匙）
    log("apksigner 签名")
    os.makedirs(os.path.dirname(KEYSTORE), exist_ok=True)
    if not os.path.exists(KEYSTORE):
        print("   首次构建，生成签名密钥 -> " + KEYSTORE)
        run([
            tc["keytool"], "-genkeypair", "-noprompt",
            "-keystore", KEYSTORE,
            "-storepass", KS_PASS, "-keypass", KS_PASS,
            "-alias", KS_ALIAS, "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "36500",
            "-dname", "CN=yqqs-draw, OU=Personal, O=yqqs-draw, L=Shanghai, C=CN",
        ], env=tc["env"])

    out_apk = os.path.join(DIST, "yqqs-draw-v%s.apk" % VERSION)
    if os.path.exists(out_apk):
        os.remove(out_apk)
    run([
        tc["apksigner"], "sign",
        "--ks", KEYSTORE, "--ks-key-alias", KS_ALIAS,
        "--ks-pass", "pass:" + KS_PASS, "--key-pass", "pass:" + KS_PASS,
        "--v1-signing-enabled", "true", "--v2-signing-enabled", "true",
        "--v4-signing-enabled", "false",
        "--out", out_apk, aligned,
    ], env=tc["env"])

    # 8. 校验
    log("校验 APK")
    rc, _ = run([tc["apksigner"], "verify", "--print-certs", out_apk], env=tc["env"], allow_fail=True)
    if rc != 0:
        fail("签名校验失败")
    rc, badging = run([tc["aapt2"], "dump", "badging", out_apk], env=tc["env"], allow_fail=True)
    pkg = [ln for ln in badging.splitlines() if ln.startswith("package:")]

    size_mb = os.path.getsize(out_apk) / 1048576.0
    log("构建完成：%s (%.1f MB, 用时 %.1fs)" % (out_apk, size_mb, time.time() - t0))
    if pkg:
        print("   " + pkg[0])


if __name__ == "__main__":
    main()
