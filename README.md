# 邮件发票识别系统

一个基于Python Flask的智能发票识别系统。既可以把发票文件直接拖进来识别，也可以自动从QQ邮箱读取发票邮件，最后导出为CSV报销表格。

## 功能特点

- **拖拽上传识别**：把发票文件拖进网页就能识别，不需要任何配置
- **电子发票免OCR**：PDF/OFD电子发票直接读取文字层（或内嵌XML），离线、免费、比OCR更准
- **OCR兜底**：只有图片和扫描件才需要百度OCR，可选配置
- 自动连接QQ邮箱，读取指定日期范围的邮件
- 智能识别发票邮件（PDF附件、OFD附件、图片附件、邮件正文、电子发票链接）
- 提取完整的报销信息：发票号码、抬头、金额、日期等
- 按发票号码自动去重
- 数据存储到SQLite数据库
- 导出CSV文件，方便财务报销

## 技术栈

- **后端**: Python 3.8+, Flask 3.0
- **数据库**: SQLite
- **邮件**: imaplib (QQ邮箱IMAP)
- **发票解析**: PyMuPDF（PDF文字层）+ 标准库zipfile/xml（OFD）
- **OCR（可选）**: 百度智能云OCR API，仅用于图片/扫描件
- **前端**: Bootstrap 5, jQuery, DataTables, SweetAlert2（全部本地化，断网也能正常显示）
- **桌面外壳**: pywebview（系统自带内核，macOS 用 WKWebView / Windows 用 WebView2）
- **安全**: cryptography (密码加密)

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/XiangZheng2002/invoice-ingestion-pipeline.git
cd invoice-ingestion-pipeline
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制`.env.example`为`.env`并填写配置：

```bash
cp .env.example .env
```

编辑`.env`文件：

```env
# Flask配置
SECRET_KEY=your-random-secret-key

# 加密密钥：留空即可。首次用到加密时会自动生成 data/encryption.key
# 只有需要沿用旧密钥时才填这里
ENCRYPTION_KEY=

# 百度OCR配置（可选，只有识别图片/扫描件才需要）
# 电子发票（PDF/OFD）不需要OCR。也可以在网页的"配置"页填写，无需改这个文件
BAIDU_APP_ID=
BAIDU_API_KEY=
BAIDU_SECRET_KEY=
```

### 5. 运行应用

```bash
python run.py
```

会自动弹出程序窗口。若想改用浏览器或只起服务：

```bash
BILL_BROWSER=1 python run.py      # 浏览器模式
BILL_NO_WINDOW=1 python run.py    # 只起服务，不开界面
```

端口默认自动挑选（5000 被占用会往后让），启动时会打印实际地址。

## 使用指南

### 最快上手：拖拽上传（无需任何配置）

1. 访问[上传识别](http://127.0.0.1:5000/upload/)
2. 把发票文件拖进虚线框，或点击选择（支持一次多个）
3. 电子发票（PDF/OFD）会直接读取文字层，秒出结果；图片/扫描件需要先配好百度OCR
4. 识别结果自动入库，去[发票列表](http://127.0.0.1:5000/invoice/list)查看或直接导出CSV

支持格式：PDF、OFD、JPG、PNG、BMP、WEBP、TIFF（单个文件最大50MB）。
同一张发票重复上传会自动跳过，不会产生重复记录。

### 从邮箱批量获取

#### 第一步：配置QQ邮箱

1. 访问[配置页面](http://127.0.0.1:5000/config)
2. 输入QQ邮箱地址
3. 输入授权码（**不是QQ密码！**）
   - 登录QQ邮箱
   - 设置 → 账户 → POP3/IMAP/SMTP服务
   - 开启IMAP服务
   - 生成授权码
4. 选择起始日期（从哪天开始获取邮件）
5. 测试连接
6. 保存配置

#### 第二步：获取邮件

1. 访问[邮件列表](http://127.0.0.1:5000/email/list)
2. 点击"获取新邮件"按钮
3. 系统会从QQ邮箱读取邮件并保存到数据库

#### 第三步：识别发票

点击"识别发票"，系统会自动挑出发票邮件、下载附件并提取信息：
PDF/OFD附件直接解析文字层，图片附件走百度OCR（需已配置）。

#### 第四步：导出CSV

1. 访问[发票列表](http://127.0.0.1:5000/invoice/list)
2. 查看已识别的发票
3. 点击"导出CSV"下载报销表格

## 项目结构

```
bill/
├── app/
│   ├── __init__.py           # Flask应用初始化
│   ├── paths.py              # 路径解析（兼容PyInstaller打包）
│   ├── logging_setup.py      # 日志 + 无控制台环境兜底
│   ├── config.py             # 配置
│   ├── models.py             # 数据模型
│   ├── routes/               # 路由（含 upload.py 拖拽上传）
│   ├── services/
│   │   ├── pdf_parser.py     # PDF/OFD 直接解析（免OCR的核心）
│   │   ├── invoice_extractor.py  # 识别调度：直接解析优先，OCR兜底
│   │   ├── ocr_service.py    # 百度OCR（仅图片/扫描件）
│   │   └── ...
│   ├── utils/                # 加密、校验
│   ├── static/
│   │   ├── css/main.css      # 主题样式
│   │   └── vendor/           # 本地化的前端库，不依赖CDN
│   └── templates/
├── data/                     # 运行时自动创建
│   ├── invoices.db           # SQLite数据库
│   ├── encryption.key        # 加密密钥（首次用到加密时生成）
│   ├── attachments/          # 附件与上传的发票原件
│   └── exports/              # CSV导出
├── logs/app.log              # 运行日志
├── bill_app.spec             # PyInstaller配置
├── build_app.sh / .bat       # 一键打包
├── test_pdf_parser.py        # 解析回归测试
├── run.py                    # 启动入口
├── PACKAGING.md              # 打包与分发说明
└── README.md
```

## 打包成桌面应用

```bash
./build_app.sh      # macOS / Linux
build_app.bat       # Windows
```

打包后是一个双击即用的桌面程序，对方不需要装 Python、不需要联网、电子发票也不需要注册百度账号。
详见 [PACKAGING.md](PACKAGING.md)。

注意 PyInstaller 不能交叉编译，两个系统要各打一次；仓库里配好了 GitHub Actions
（`.github/workflows/build.yml`）可以一次出两个平台的包。

## 开发进度

- [x] Phase 1: 基础框架搭建
- [x] Phase 2: 邮件连接功能
- [x] Phase 3: 发票识别（PDF/OFD 直接解析 + OCR 兜底）
- [x] Phase 4: 数据管理和CSV导出
- [x] Phase 5: 界面优化
- [x] Phase 6: 拖拽/文件夹上传、打包分发

## 注意事项

### 安全性

- 邮箱授权码和OCR密钥使用Fernet加密存储
- 加密密钥存放在 `data/encryption.key`（权限600），首次用到加密时自动生成
- **丢失该文件会导致已保存的授权码无法解密**，换电脑时请连同 `data/` 一起复制
- `.env` 包含敏感信息，已加入 `.gitignore`，打包时默认也不会打进分发包
- 所有数据都在本机，不上传到任何服务器

### QQ邮箱授权码

- 授权码不是QQ密码
- 需要在QQ邮箱设置中单独生成
- 一个授权码只能用于一个应用

### 百度OCR额度

- 免费版每天500次调用
- 超出额度需要付费
- 建议监控使用量

## 常见问题

### 1. 连接QQ邮箱失败

- 检查邮箱地址是否正确
- 确认使用的是授权码而非QQ密码
- 确认已在QQ邮箱中开启IMAP服务

### 2. OCR识别不准确

- 确保发票图片清晰
- 支持的发票类型：增值税专用发票、普通发票
- 可以手动编辑识别结果

### 3. 虚拟环境问题

```bash
# 重新创建虚拟环境
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 后续计划

- [ ] 支持更多邮箱类型（Gmail、163等）
- [ ] 批量处理和后台任务
- [ ] 发票真伪验证
- [ ] Excel导出格式
- [ ] 移动端适配
- [ ] 发票去重检测

## 许可证

MIT License

## 作者

Li Zheng and Xiang Zheng

## 更新日志

### v0.1.0 (Phase 1)
- 初始项目框架
- 基础Web界面
- 数据库设计

---

如有问题，请提交Issue或联系作者。
