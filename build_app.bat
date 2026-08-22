@echo off
REM 邮件发票识别系统 - Windows自动打包脚本
REM 用于将应用打包成可执行文件

echo =========================================
echo 邮件发票识别系统 - 自动打包工具
echo =========================================
echo.

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo 错误: 找不到虚拟环境目录 venv
    echo 请先运行: python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat

REM 检查PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 正在安装PyInstaller...
    pip install pyinstaller
)

REM 清理旧文件
echo 清理旧的打包文件...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM 打包应用
echo.
echo 开始打包应用...
pyinstaller bill_app.spec

REM 检查是否成功
if %errorlevel% equ 0 (
    echo.
    echo =========================================
    echo 打包成功！
    echo =========================================
    echo.
    echo 产物: dist\邮件发票识别系统.exe
    echo.
    echo 使用方法：双击 exe，会直接弹出程序窗口（不再需要打开浏览器）
    echo.
    echo 首次运行如果被 SmartScreen 拦截（未做代码签名）：
    echo   点"更多信息" -^> "仍要运行"
    echo.
    echo 数据与日志（都在 exe 同级目录，首次运行自动创建）：
    echo   data\invoices.db      发票数据库
    echo   data\encryption.key   加密密钥，丢失后已存的邮箱授权码无法解密
    echo   data\attachments\     邮件附件与上传的发票原件
    echo   logs\app.log          运行日志，出问题先看这里
    echo.
    echo 迁移到别的电脑：连同 data\ 目录一起复制
    echo.
) else (
    echo.
    echo =========================================
    echo 打包失败！请检查错误信息
    echo =========================================
    pause
    exit /b 1
)

pause
