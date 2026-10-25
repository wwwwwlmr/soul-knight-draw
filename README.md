# 元气骑士扭蛋机（yqqs-draw）

一个纯静态的「双重抽卡」小网页：抽角色 + 技能，再抽该角色的专属皮肤。
数据与图片来自**元气骑士中文维基**，仅供娱乐。

现在这个仓库同时是**网页源**和 **Android APK 的构建工程**，不需要 Android Studio、不需要 Gradle，一条命令出包。

## 下载安装

- **APK 下载**：<https://github.com/wwwwwlmr/yqqs-draw/releases/latest>
- 仓库地址：<https://github.com/wwwwwlmr/yqqs-draw>
- 网页版：直接打开 `web/index.html` 即可（无需服务器）

---

## 目录结构

```
yqqs-draw/
├── web/                        # 网页本体（唯一需要维护的内容）
│   ├── index.html              # 单文件页面：样式 + 逻辑 + 内嵌 DATA 数据
│   ├── assets/                 # 角色/技能/皮肤图片（798 gif + 146 png）
│   └── _shared/fonts/          # 页面用的两款字体
├── android/                    # Android 容器工程（只是壳）
│   ├── AndroidManifest.xml
│   ├── src/com/yqqs/gacha/MainActivity.java
│   ├── res/                    # 图标、主题、字符串
│   └── keystore/               # 签名密钥（首次构建自动生成）
├── build.py                    # 构建脚本：aapt2 → javac → d8 → zipalign → apksigner
├── tools/
│   ├── fetch_toolchain.py      # 一次性下载 JDK / build-tools / android.jar
│   ├── make_icons.py           # 生成启动图标（需要 Pillow）
│   └── update_data.py          # 更新内嵌数据并把资源缺失/多余找出来
└── dist/                       # 构建产物 APK
```

`web/` 原样整包进 APK 的 `assets/`，所以 **网页改完重新构建即可生效**，Android 侧一般不用动。

## 构建 APK

```bash
# 第一次：下载工具链（约 300 MB，仅一次）
python tools/fetch_toolchain.py

# 之后每次：
python build.py            # 产物在 dist/yqqs-draw-v1.1.1.apk
python build.py --clean    # 干净重建
```

要求：Python 3.8+（本机 `C:\Python314\python.exe` 即可），Windows。
工具链落在 `tools/`：

| 组件 | 版本 | 用途 |
| --- | --- | --- |
| Microsoft OpenJDK | 17 | javac / jar / keytool |
| Android build-tools | 34.0.0 | aapt2 / d8 / zipalign / apksigner |
| Android platform | 35 (`android.jar`) | 编译期类库与资源表 |

构建流程和 Gradle 内部一致：`aapt2 compile` → `aapt2 link`（把 `web/` 当 assets 塞进去）→ `javac` → `d8` → dex 追加进 apk → `zipalign` → `apksigner`。脚本最后会跑 `apksigner verify` 和 `aapt2 dump badging` 自检。

## 安装

把 `dist/yqqs-draw-v1.1.1.apk` 传到手机点开安装（需要允许「安装未知来源应用」）。
应用完全离线：**没有申请 INTERNET 权限**，页面、图片、字体都在安装包里。

## 签名密钥

`android/keystore/yqqs-release.jks`（口令见 `build.py` 顶部常量）。
**请备份这个文件**：Android 只允许用同一把签名钥匙覆盖安装升级，丢了就只能卸载重装。

## 更新数据（角色 / 技能 / 皮肤）

数据在 `web/index.html` 里是一行 `const DATA = {...};`：

```js
DATA.charSkill = [{ char, skill, avatar, skillImg }, ...]   // 角色 + 技能
DATA.skins     = { "角色名": [ ["皮肤名", "assets/xxx.gif"], ... ] }
```

维护流程：

1. 从维基抓新的角色/技能/皮肤和图片，图片放进 `web/assets/`。
2. 用 `python tools/update_data.py --data 新数据.json` 替换内嵌数据（会校验每个引用到的图片是否存在、并列出没被引用的图片）。
3. `python build.py` 重新出包，改 `build.py` / `AndroidManifest.xml` 里的版本号即可。

## 卡池模式（v1.1.0 新增）

默认是「全收集」卡池，但大多数玩家并不是全角色全皮肤，所以可以自己圈定卡池。点右下角 **⚙ 卡池** 打开设置：

- **精准模式**：先勾选角色，再按角色勾选技能和皮肤，作为自己的基础卡池。
- **自定义模式**：在精准卡池的基础上做减法——可以把整个角色移出，也可以逐条删掉某个技能/皮肤。
- 主界面标题下有「精准模式 / 自定义模式」切换，**抽卡按当前模式的卡池来出**；侧边栏的 tab 和主界面的开关是同一个状态。
- 设置存在浏览器 `localStorage`（APK 的 WebView 里同样有效），关掉重开还在；「恢复全收集」一键回到默认。
- 以后数据更新新增的角色/技能/皮肤会自动并入卡池，不会因为旧存档漏掉新内容。

## 已知情况

- `screenOrientation="portrait"`：竖屏使用，旋转不重载页面。
- 页面 ≤600px 宽有专门的手机端布局（会改成上下排列）。
- 卡池设置会持久化到 `localStorage`；「抽卡记录」目前不持久化，关掉应用后清空。
