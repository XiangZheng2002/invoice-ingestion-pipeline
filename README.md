# 邮件发票识别系统

一个基于Python Flask的智能发票识别系统，能够自动从QQ邮箱中读取邮件，识别发票内容，并使用百度OCR提取发票信息，最后导出为CSV格式。

## 功能特点

- 自动连接QQ邮箱，读取指定日期后的邮件
- 智能识别发票邮件（支持PDF附件、图片附件、邮件正文、电子发票链接）
- 使用百度OCR AI技术自动提取发票信息
- 提取完整的报销信息：发票号码、抬头、金额、日期等
- 数据存储到SQLite数据库
- 导出CSV文件，方便财务报销
- 美观的Web界面，操作简单直观

## 技术栈

- **后端**: Python 3.8+, Flask 3.0
- **数据库**: SQLite
- **邮件**: imaplib (QQ邮箱IMAP)
- **OCR**: 百度智能云OCR API
- **前端**: Bootstrap 5, jQuery, DataTables, SweetAlert2
- **安全**: cryptography (密码加密)

## 安装步骤

### 1. 克隆项目

```bash
cd /Users/zhengxiang/Documents/ZLiang/bill
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

# 首次运行会自动生成加密密钥，请保存到这里
ENCRYPTION_KEY=

# 百度OCR配置（访问 https://cloud.baidu.com/product/ocr 注册）
BAIDU_APP_ID=your-app-id
BAIDU_API_KEY=your-api-key
BAIDU_SECRET_KEY=your-secret-key
```

### 5. 运行应用

```bash
python run.py
```

访问: http://127.0.0.1:5000

## 使用指南

### 第一步：配置QQ邮箱

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

### 第二步：获取邮件

1. 访问[邮件列表](http://127.0.0.1:5000/email/list)
2. 点击"获取新邮件"按钮
3. 系统会从QQ邮箱读取邮件并保存到数据库

### 第三步：识别发票（Phase 3实现）

系统会自动识别包含发票的邮件，并使用OCR提取信息

### 第四步：导出CSV

1. 访问[发票列表](http://127.0.0.1:5000/invoice/list)
2. 查看已识别的发票
3. 点击"导出CSV"下载报销表格

## 项目结构

```
bill/
├── app/                    # 应用主目录
│   ├── __init__.py        # Flask应用初始化
│   ├── config.py          # 配置文件
│   ├── models.py          # 数据模型
│   ├── routes/            # 路由
│   ├── services/          # 业务逻辑
│   ├── utils/             # 工具类
│   ├── static/            # 静态文件
│   └── templates/         # HTML模板
├── data/                  # 数据目录
│   ├── attachments/       # 邮件附件
│   ├── exports/           # CSV导出文件
│   └── invoices.db        # SQLite数据库
├── logs/                  # 日志
├── .env                   # 环境变量（不提交到git）
├── .env.example           # 环境变量示例
├── requirements.txt       # Python依赖
├── run.py                 # 启动文件
└── README.md             # 项目说明
```

## 开发进度

- [x] Phase 1: 基础框架搭建
- [ ] Phase 2: 邮件连接功能
- [ ] Phase 3: 发票识别和OCR
- [ ] Phase 4: 数据管理和CSV导出
- [ ] Phase 5: 界面优化
- [ ] Phase 6: 测试和完善

## 注意事项

### 安全性

- 邮箱密码使用Fernet加密存储
- `.env`文件包含敏感信息，已加入`.gitignore`
- 不要将`.env`文件提交到版本控制系统

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

Created with Claude Code

## 更新日志

### v0.1.0 (Phase 1)
- 初始项目框架
- 基础Web界面
- 数据库设计

---

如有问题，请提交Issue或联系作者。
