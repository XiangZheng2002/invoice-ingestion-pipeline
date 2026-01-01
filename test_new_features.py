#!/usr/bin/env python3
"""测试新功能"""

import requests
import json
import re

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

print("=" * 70)
print("测试新功能")
print("=" * 70)

# 1. 获取CSRF token
response = session.get(f"{BASE_URL}/config")
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
csrf_token = csrf_match.group(1) if csrf_match else None

headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token
}

# 2. 保存配置（包含起始日期）
print("\n1. 测试保存配置（带起始日期）")
print("-" * 70)

data = {
    'email': '1793434271@qq.com',
    'password': 'vrhhqgruvomtfjjf',
    'since_date': '2024-12-01'
}

response = session.post(
    f"{BASE_URL}/email/save_config",
    headers=headers,
    data=json.dumps(data)
)

result = response.json()
if result.get('success'):
    print(f"✅ 配置保存成功: {result.get('message')}")
    print(f"   起始日期: 2024-12-01")
else:
    print(f"❌ 保存失败: {result.get('message')}")

# 3. 测试获取邮件（应该使用配置的日期）
print("\n2. 测试获取邮件（使用配置的起始日期）")
print("-" * 70)

response = session.post(
    f"{BASE_URL}/email/fetch_emails",
    headers=headers,
    data=json.dumps({})  # 不传递日期，应该使用配置的日期
)

result = response.json()
if result.get('success'):
    print(f"✅ 获取邮件成功: {result.get('message')}")
    print(f"   获取数量: {result.get('count')} 封")
else:
    print(f"❌ 获取失败: {result.get('message')}")

# 4. 测试清空邮件列表
print("\n3. 测试清空邮件列表")
print("-" * 70)

response = session.post(
    f"{BASE_URL}/email/clear_emails",
    headers=headers,
    data=json.dumps({})
)

result = response.json()
if result.get('success'):
    print(f"✅ 清空成功: {result.get('message')}")
else:
    print(f"❌ 清空失败: {result.get('message')}")

# 5. 重新获取邮件确认清空成功
print("\n4. 验证清空后重新获取")
print("-" * 70)

response = session.post(
    f"{BASE_URL}/email/fetch_emails",
    headers=headers,
    data=json.dumps({})
)

result = response.json()
if result.get('success'):
    print(f"✅ 重新获取成功: {result.get('message')}")
    print(f"   获取数量: {result.get('count')} 封")
else:
    print(f"❌ 获取失败: {result.get('message')}")

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
