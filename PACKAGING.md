# 打包与分发

把应用打包成独立可执行文件，对方**不需要装 Python、不需要联网、不需要注册任何账号**就能用。

打包后是一个桌面应用：双击弹出程序窗口，关窗即退出。没有黑窗口，也不用手动打开浏览器。

---

## 快速开始

```bash
# macOS / Linux
./build_app.sh

# Windows
build_app.bat
```

产物：

| 系统 | 位置 |
|---|---|
| macOS | `dist/邮件发票识别系统.app` |
| Windows | `dist\邮件发票识别系统.exe` |
| Linux | `dist/邮件发票识别系统` |

体积约 45MB，其中大头是 PyMuPDF 的渲染引擎。

---

## 两个系统要各打一次

**PyInstaller 不能交叉编译。** Mac 上打出来的包在 Windows 上跑不了，反之亦然。三个办法：

1. **借一台对应系统的机器**，跑一次对应的构建脚本
2. **用 GitHub Actions**（推荐）——仓库里已经配好 `.github/workflows/build.yml`：
   - 在 Actions 页面手动触发，或推一个 `v*` 开头的 tag
   - 会在 macOS 和 Windows 上各构建一次，产物可直接下载
   - 打 tag 时还会自动创建 Release
3. Windows 虚拟机

---

## 分发给别人

打包好的可执行文件直接发过去就行，不需要附带任何其他文件。

### 对方首次打开会被系统拦截

因为**没有做代码签名**（Apple 开发者证书每年 99 美元，Windows 代码签名证书每年也要几百块）。这不是程序有问题，但要提前跟对方说清楚，否则很多人到这一步就放弃了。

**macOS**
```
右键点应用图标 → 打开 → 在弹窗里再点一次"打开"
```
之后就不会再提示了。或者在终端执行：
```bash
xattr -cr /path/to/邮件发票识别系统.app
```

**Windows**
```
SmartScreen 弹窗 → 点"更多信息" → "仍要运行"
```

如果被杀毒软件误报，把程序加进白名单。PyInstaller 打包的程序被误报是常见现象，spec 里已经关掉了 UPX 压缩（那是误报的主要来源之一）。

---

## 数据存在哪

程序会在**可执行文件所在目录**创建这些文件夹（macOS 上是 `.app` 的同级目录）：

```
邮件发票识别系统.app        ← 程序本体
data/
  ├── invoices.db          ← 发票和邮件数据
  ├── encryption.key       ← 加密密钥，权限 600
  ├── attachments/         ← 邮件附件和上传的发票原件
  └── exports/             ← 导出的 CSV
logs/
  └── app.log              ← 运行日志，出问题先看这里
```

**换电脑或升级版本时，把 `data/` 目录一起复制过去。**

`data/encryption.key` 是首次用到加密功能（保存邮箱授权码或 OCR 密钥）时自动生成的，每台机器一把、互不相同。**丢了这个文件，已保存的邮箱授权码和 OCR 密钥就再也解不开了**，需要重新填写（发票数据本身没加密，不受影响）。

---

## `.env` 默认不打包

`.env` 里装着 `SECRET_KEY` 和 `ENCRYPTION_KEY`。打进分发包意味着：

- 你自己的密钥跟着应用发给了每一个人
- 所有人共用同一把加密钥匙

所以默认**不打包**，应用在每台机器上自行生成密钥。

确实需要内置配置时（比如公司内部统一分发），显式开启：

```bash
BILL_BUNDLE_ENV=1 ./build_app.sh
```

---

## 环境变量

开发和排查问题时有用，普通使用者不需要关心：

| 变量 | 作用 |
|---|---|
| `BILL_NO_WINDOW=1` | 只起服务，不开窗口也不开浏览器 |
| `BILL_BROWSER=1` | 强制用浏览器而不是桌面窗口 |
| `BILL_PORT=5001` | 指定端口（默认自动挑一个可用的） |
| `BILL_DEBUG=1` | 开发时开启 debug（打包后强制无效） |
| `BILL_BUNDLE_ENV=1` | 打包时包含 `.env` |

**关于端口**：默认优先用 5000，被占用会自动往后让（5001、5002、8000、8080，再不行让系统随便给一个）。macOS 的"隔空播放接收器"常年占着 5000，写死端口会让程序在一部分 Mac 上直接起不来。

**关于 debug**：打包后 debug 会被强制关闭，与环境变量无关。Werkzeug 的调试器等于开放了一个可执行任意代码的入口，绝不能出现在分发出去的程序里。

---

## 常见问题

### 双击没反应 / 窗口一闪而过

看 `logs/app.log`。打包后没有控制台窗口，所有诊断信息（包括未捕获的异常和完整堆栈）都在这个文件里。

### 窗口起不来，变成了浏览器打开

说明 pywebview 的系统组件不可用，常见于较老的 Windows 10 缺少 WebView2 运行时。程序会自动退回浏览器模式，功能不受影响。装上 [WebView2 运行时](https://developer.microsoft.com/microsoft-edge/webview2/)就能恢复窗口模式。

浏览器模式下，程序闲置 30 分钟会自动退出，不会在后台一直挂着。

### 界面没有样式，全是白底黑字

正常情况不会出现——所有前端资源（Bootstrap、jQuery、DataTables、SweetAlert2、图标字体）都已经本地化到 `app/static/vendor/`，不依赖任何 CDN。如果真遇到，检查 `logs/app.log` 里有没有静态文件 404。

### 打包后体积 45MB，能不能更小

大头是 PyMuPDF 的 PDF 渲染引擎，去不掉——它正是"电子发票不用 OCR"的基础。spec 里已经排除了 tkinter、numpy、pandas 等用不到的库。

---

## 技术细节

### 路径处理

`app/paths.py` 统一处理打包前后的路径差异：

- **只读资源**（模板、静态文件）→ `sys._MEIPASS`，PyInstaller 每次启动解压的临时目录
- **数据文件**（数据库、密钥、附件、日志）→ 可执行文件所在目录，这样重启后才找得回来
- macOS 的 `.app` 是个目录，数据写在 bundle 内部会被 Gatekeeper 和"移到废纸篓"连带清掉，所以放到 `.app` 的同级目录

配置里的相对路径（如 `LOG_FILE=logs/app.log`）一律按这个基准目录解析，**不能按当前工作目录**——从 Finder 双击启动时 CWD 是 `/`。

### 无控制台时的输出

Windows 上 `console=False` 打包后，进程根本没有标准输出，`sys.stdout` 和 `sys.stderr` 都是 `None`，此时任何一句 `print()` 都会抛 `AttributeError` 把程序打崩。

`app/logging_setup.py` 会检测这种情况并把 `sys.stdout` / `sys.stderr` 接到日志上，同时接管 `sys.excepthook`，保证未捕获异常也能留下完整堆栈。

### 相关文件

| 文件 | 作用 |
|---|---|
| `bill_app.spec` | PyInstaller 配置 |
| `build_app.sh` / `build_app.bat` | 一键打包脚本 |
| `.github/workflows/build.yml` | 双平台 CI 构建 |
| `app/paths.py` | 路径解析 |
| `app/logging_setup.py` | 日志与无控制台兜底 |
| `run.py` | 启动入口，窗口/浏览器/纯服务三种形态 |
