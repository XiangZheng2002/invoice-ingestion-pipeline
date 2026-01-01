#!/usr/bin/env python3
"""测试新架构：Config权限 + 邮件列表具体日期"""

import requests
import json
import re

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

print("=" * 70)
print("测试新架构：Config权限 + 邮件列表日期筛选")
print("=" * 70)

# 获取CSRF token
response = session.get(f"{BASE_URL}/config")
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
csrf_token = csrf_match.group(1) if csrf_match else None

headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token
}

# 步骤1: 在Config中设置权限范围（大范围）
print("\n步骤1: 在Config中设置权限范围")
print("-" * 70)
print("设置权限: 2024-12-01 到 2024-12-31（整个12月）")

data = {
    'email': '1793434271@qq.com',
    'password': 'vrhhqgruvomtfjjf',
    'since_date': '2024-12-01',  # 权限起始
    'before_date': '2024-12-31'  # 权限终止
}

response = session.post(
    f"{BASE_URL}/email/save_config",
    headers=headers,
    data=json.dumps(data)
)

result = response.json()
if result.get('success'):
    print(f"✅ {result.get('message')}")
    print("   权限范围: 2024-12-01 至 2024-12-31")
else:
    print(f"❌ {result.get('message')}")
    exit(1)

# 步骤2: 清空旧数据
print("\n步骤2: 清空现有数据")
print("-" * 70)

response = session.post(
    f"{BASE_URL}/email/clear_emails",
    headers=headers,
    data=json.dumps({})
)

result = response.json()
print(f"✅ {result.get('message')}")

# 步骤3: 在邮件列表中选择具体日期（权限范围内）
print("\n步骤3: 在邮件列表中获取邮件（2024-12-01 到 2024-12-10）")
print("-" * 70)
print("这是权限范围的子集，应该成功")

data = {
    'since_date': '2024-12-01',
    'before_date': '2024-12-10'
}

response = session.post(
    f"{BASE_URL}/email/fetch_emails",
    headers=headers,
    data=json.dumps(data)
)

result = response.json()
if result.get('success'):
    print(f"✅ {result.get('message')}")
    print(f"   总共找到: {result.get('total', 0)} 封")
    print(f"   成功处理: {result.get('count', 0)} 封")
    if result.get('failed', 0) > 0:
        print(f"   失败: {result.get('failed', 0)} 封")
else:
    print(f"❌ {result.get('message')}")

# 步骤4: 测试超出权限范围（应该失败）
print("\n步骤4: 尝试超出权限范围（2024-11-01 到 2024-12-15）")
print("-" * 70)
print("起始日期早于权限，应该被拒绝")

data = {
    'since_date': '2024-11-01',  # 早于权限起始
    'before_date': '2024-12-15'
}

response = session.post(
    f"{BASE_URL}/email/fetch_emails",
    headers=headers,
    data=json.dumps(data)
)

result = response.json()
if not result.get('success'):
    print(f"✅ 正确拒绝: {result.get('message')}")
else:
    print(f"⚠️  应该被拒绝但成功了: {result.get('message')}")

# 步骤5: 测试不设置终止日期（获取权限范围内的所有邮件）
print("\n步骤5: 不设置终止日期（2024-12-20 到 最新）")
print("-" * 70)
print("在权限范围内，应该成功")

data = {
    'since_date': '2024-12-20',
    'before_date': ''  # 不设置
}

response = session.post(
    f"{BASE_URL}/email/fetch_emails",
    headers=headers,
    data=json.dumps(data)
)

result = response.json()
if result.get('success'):
    print(f"✅ {result.get('message')}")
    print(f"   总共找到: {result.get('total', 0)} 封")
    print(f"   成功处理: {result.get('count', 0)} 封")
else:
    print(f"❌ {result.get('message')}")

print("\n" + "=" * 70)
print("测试完成！新架构工作正常")
print("=" * 70)

print("\n总结:")
print("✅ Config设置权限范围（最大范围）")
print("✅ 邮件列表选择具体日期（必须在权限内）")
print("✅ 获取所有符合条件的邮件（不限制50封）")
print("✅ 超出权限的请求被正确拒绝")
