#!/bin/bash
# 邮件发票识别系统 - 自动打包脚本
# 用于将应用打包成可执行文件

echo "========================================="
echo "邮件发票识别系统 - 自动打包工具"
echo "========================================="
echo ""

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "检测到未激活虚拟环境，正在激活..."
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "错误: 找不到虚拟环境目录 venv"
        echo "请先运行: python3 -m venv venv"
        exit 1
    fi
fi

# 检查PyInstaller是否已安装
if ! pip show pyinstaller > /dev/null 2>&1; then
    echo "正在安装PyInstaller..."
    pip install pyinstaller
fi

# 清理之前的打包文件
echo "清理旧的打包文件..."
rm -rf build dist

# 使用PyInstaller打包
echo ""
echo "开始打包应用..."
pyinstaller bill_app.spec

# 检查打包是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "打包成功！"
    echo "========================================="
    echo ""

    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "产物: dist/邮件发票识别系统.app"
        echo ""
        echo "使用方法：双击应用图标，会直接弹出程序窗口（不再需要打开浏览器）"
        echo ""
        echo "首次打开如果提示\"无法验证开发者\"（未做代码签名）："
        echo "  右键点图标 -> 打开 -> 再点\"打开\""
        echo "  或执行: xattr -cr dist/邮件发票识别系统.app"
    else
        echo "产物: dist/邮件发票识别系统"
        echo ""
        echo "使用方法：chmod +x 后双击或命令行运行，会弹出程序窗口"
    fi

    echo ""
    echo "数据与日志（都在可执行文件同级目录，首次运行自动创建）："
    echo "  data/invoices.db      发票数据库"
    echo "  data/encryption.key   加密密钥，丢失后已存的邮箱授权码无法解密"
    echo "  data/attachments/     邮件附件与上传的发票原件"
    echo "  logs/app.log          运行日志，出问题先看这里"
    echo ""
    echo "迁移到别的电脑：连同 data/ 目录一起复制"
    echo ""
else
    echo ""
    echo "========================================="
    echo "打包失败！请检查错误信息"
    echo "========================================="
    exit 1
fi
