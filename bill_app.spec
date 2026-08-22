# -*- mode: python ; coding: utf-8 -*-
"""
邮件发票识别系统 - PyInstaller配置

打包成桌面应用：无控制台窗口，双击启动后弹出原生窗口。
"""

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
is_windows = sys.platform == 'win32'
is_macos = sys.platform == 'darwin'

# ---------- 数据文件 ----------
datas = [
    ('app/templates', 'app/templates'),   # Jinja模板
    ('app/static', 'app/static'),         # 前端资源（含本地化的 vendor/ 目录）
]

# .env 默认【不】打包。它装着 SECRET_KEY 和 ENCRYPTION_KEY，
# 打进去等于把自己的密钥随应用发给每一个人，而且所有人共用一把钥匙 ——
# 与"每台机器首次运行自动生成 data/encryption.key"的设计正好相反。
# 确实需要内置配置时，设 BILL_BUNDLE_ENV=1 显式开启。
if os.environ.get('BILL_BUNDLE_ENV') == '1' and os.path.exists('.env'):
    print('警告: 正在把 .env 打包进应用，其中的密钥会随应用分发出去。')
    datas.append(('.env', '.'))
else:
    print('提示: 未打包 .env，应用首次运行会自行生成 data/encryption.key。')

# ---------- 隐式导入 ----------
hiddenimports = [
    'flask',
    'flask_wtf',
    'flask_wtf.csrf',
    'werkzeug',
    'jinja2',
    'email',
    'imaplib',
    'sqlite3',
    'cryptography',
    'cryptography.fernet',
    'aip',
    'PIL',
    'pymupdf',
    'fitz',
    'requests',
    'dateutil',
    'chardet',
    'webview',
]

# pywebview 的后端按平台分：macOS 走 Cocoa/WebKit，Windows 走 EdgeChromium
hiddenimports += collect_submodules('webview')
if is_macos:
    hiddenimports += ['objc', 'Foundation', 'AppKit', 'WebKit', 'Quartz']
if is_windows:
    hiddenimports += ['clr', 'webview.platforms.edgechromium', 'webview.platforms.winforms']

for package in ['aip', 'webview']:
    try:
        datas += collect_data_files(package)
    except Exception as e:
        print(f'警告: 收集 {package} 的数据文件失败: {e}')

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='邮件发票识别系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX 压缩是 Windows Defender 误报的主要来源之一
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # 桌面应用，不要黑窗口；诊断信息见 logs/app.log
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# macOS: 打成 .app bundle
if is_macos:
    app = BUNDLE(
        exe,
        name='邮件发票识别系统.app',
        icon=None,
        bundle_identifier='com.bill.invoice',
        info_plist={
            'NSHighResolutionCapable': True,
            'LSBackgroundOnly': False,
            'CFBundleDisplayName': '邮件发票识别系统',
            'CFBundleShortVersionString': '1.0.0',
            # 只连本机的 Flask，不需要放开任意 HTTP
            'NSAppTransportSecurity': {
                'NSAllowsLocalNetworking': True,
            },
        },
    )
