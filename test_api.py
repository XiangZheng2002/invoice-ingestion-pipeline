#!/usr/bin/env python3
"""测试API端点"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

# 测试数据
email = "1793434271@qq.com"
password = "vrhhqgruvomtfjjf"

print("=" * 60)
print("测试邮箱配置API")
print("=" * 60)

# 1. 首先访问配置页面获取CSRF token
session = requests.Session()
response = session.get(f"{BASE_URL}/config")
print(f"访问配置页面: {response.status_code}")

# 从HTML中提取CSRF token
import re
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
if csrf_match:
    csrf_token = csrf_match.group(1)
    print(f"CSRF Token: {csrf_token[:20]}...")
else:
    print("未找到CSRF Token")
    csrf_token = None

print("\n" + "=" * 60)
print("测试连接API")
print("=" * 60)

# 2. 测试连接
headers = {
    'Content-Type': 'application/json',
}
if csrf_token:
    headers['X-CSRFToken'] = csrf_token

data = {
    'email': email,
    'password': password
}

response = session.post(
    f"{BASE_URL}/email/test_connection",
    headers=headers,
    data=json.dumps(data)
)

print(f"状态码: {response.status_code}")
print(f"响应: {response.text}")

if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        print("\n✅ 测试连接成功！")
    else:
        print(f"\n❌ 连接失败: {result.get('message')}")
else:
    print(f"\n❌ API请求失败: {response.status_code}")

print("\n" + "=" * 60)
print("测试保存配置API")
print("=" * 60)

data['since_date'] = '2024-12-01'

response = session.post(
    f"{BASE_URL}/email/save_config",
    headers=headers,
    data=json.dumps(data)
)

print(f"状态码: {response.status_code}")
print(f"响应: {response.text}")

if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        print("\n✅ 保存配置成功！")
    else:
        print(f"\n❌ 保存失败: {result.get('message')}")
else:
    print(f"\n❌ API请求失败: {response.status_code}")
