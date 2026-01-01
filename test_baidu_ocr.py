#!/usr/bin/env python3
"""
独立测试脚本 - 测试百度OCR配置是否正确
Independent test script to verify Baidu OCR configuration
"""

import os
from dotenv import load_dotenv
from aip import AipOcr

# 加载环境变量
load_dotenv()

print("=" * 70)
print("百度OCR配置测试 / Baidu OCR Configuration Test")
print("=" * 70)

# 读取配置
APP_ID = os.getenv('BAIDU_APP_ID')
API_KEY = os.getenv('BAIDU_API_KEY')
SECRET_KEY = os.getenv('BAIDU_SECRET_KEY')

print("\n1. 检查环境变量 / Checking environment variables:")
print("-" * 70)
print(f"BAIDU_APP_ID:     {APP_ID}")
print(f"BAIDU_API_KEY:    {API_KEY[:30]}..." if API_KEY and len(API_KEY) > 30 else f"BAIDU_API_KEY:    {API_KEY}")
print(f"BAIDU_SECRET_KEY: {SECRET_KEY}")

# 检查是否为占位符
if not APP_ID or not API_KEY or not SECRET_KEY:
    print("\n❌ 错误: 环境变量未配置")
    print("请检查 .env 文件是否包含 BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY")
    exit(1)

if SECRET_KEY == 'your-baidu-secret-key' or SECRET_KEY.startswith('your-'):
    print("\n❌ 错误: BAIDU_SECRET_KEY 仍然是占位符")
    print("请将 .env 文件中的 BAIDU_SECRET_KEY 替换为真实的密钥")
    exit(1)

print("\n✓ 环境变量已配置")

# 初始化OCR客户端
print("\n2. 初始化百度OCR客户端 / Initializing Baidu OCR client:")
print("-" * 70)
try:
    client = AipOcr(APP_ID, API_KEY, SECRET_KEY)
    print("✓ OCR客户端初始化成功")
except Exception as e:
    print(f"❌ 客户端初始化失败: {e}")
    exit(1)

# 查找测试图片
print("\n3. 查找测试图片 / Looking for test image:")
print("-" * 70)

test_image_paths = [
    'data/attachments/Weixin Image_20251228174616_577_78.jpg',
    'data/attachments/*.jpg',
    'data/attachments/*.png',
]

test_image = None
for pattern in test_image_paths:
    if '*' in pattern:
        import glob
        files = glob.glob(pattern)
        if files:
            test_image = files[0]
            break
    else:
        if os.path.exists(pattern):
            test_image = pattern
            break

if not test_image:
    print("⚠ 警告: 未找到测试图片")
    print("请确保 data/attachments/ 目录中有图片文件")
    print("\n但我们可以继续测试API连接...")
    test_image = None
else:
    print(f"✓ 找到测试图片: {test_image}")
    print(f"  文件大小: {os.path.getsize(test_image) / 1024:.2f} KB")

# 测试API连接
print("\n4. 测试API连接 / Testing API connection:")
print("-" * 70)

if test_image:
    try:
        # 读取图片
        with open(test_image, 'rb') as f:
            image = f.read()

        print("开始调用百度OCR API...")
        print("(这可能需要几秒钟...)")

        # 调用增值税发票识别
        result = client.vatInvoice(image)

        print("\nAPI响应:")
        print("-" * 70)

        # 检查是否有错误
        if 'error_code' in result:
            print(f"❌ OCR识别失败")
            print(f"错误代码: {result.get('error_code')}")
            print(f"错误信息: {result.get('error_msg')}")
            print("\n常见错误:")
            print("  - 'Invalid parameter' / 'IAM Certification failed': 密钥错误")
            print("  - 'Open api daily request limit reached': 超过每日免费额度")
            print("  - 'Image format error': 图片格式不支持")

            if 'IAM Certification failed' in result.get('error_msg', ''):
                print("\n⚠️  您的密钥配置不正确！")
                print("请检查:")
                print("  1. APP_ID 是否正确")
                print("  2. API_KEY 是否正确")
                print("  3. SECRET_KEY 是否正确（不是 'your-baidu-secret-key'）")
                print("\n请访问: https://console.bce.baidu.com/ai/#/ai/ocr/app/list")
                print("检查您的应用凭证")

        elif 'words_result' in result:
            print("✅ OCR识别成功!")
            print("\n识别结果:")
            words_result = result['words_result']

            # 显示关键字段
            key_fields = [
                ('InvoiceNum', '发票号码'),
                ('InvoiceCode', '发票代码'),
                ('InvoiceDate', '开票日期'),
                ('PurchaserName', '购买方名称'),
                ('SellerName', '销售方名称'),
                ('TotalAmount', '价税合计'),
                ('AmountInFiguress', '金额合计'),
                ('TotalTax', '税额')
            ]

            print("-" * 70)
            for field, label in key_fields:
                if field in words_result:
                    # Handle both dict and string formats
                    value = words_result[field]
                    if isinstance(value, dict):
                        value = value.get('words', '')
                    if value:
                        print(f"{label:12s}: {value}")

            print("\n✅ 您的百度OCR配置正确，可以正常使用！")

        else:
            print("⚠️  收到意外的响应格式:")
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except FileNotFoundError:
        print(f"❌ 测试图片未找到: {test_image}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

else:
    # 没有测试图片，尝试简单的API调用
    print("⚠️  没有测试图片，无法完整测试OCR功能")
    print("但配置看起来是正确的")

print("\n" + "=" * 70)
print("测试完成 / Test completed")
print("=" * 70)
