# CSV导出说明

## 新的导出逻辑（节省服务器空间）

### 工作原理

1. **识别发票时**：只识别并保存到数据库，**不自动生成CSV**
2. **点击"导出CSV"时**：
   - 临时生成带时间戳的CSV文件
   - 立即发送给用户下载
   - **下载完成后自动删除临时文件**

### 优点

✅ **节省服务器磁盘空间**：不会堆积大量CSV文件
✅ **按需生成**：用户需要时才生成
✅ **最新数据**：每次导出都是数据库中的最新数据
✅ **不会爆盘**：即使长期运行也不会占用过多空间

### 使用流程

1. 配置系统（QQ邮箱 + 百度OCR）
2. 获取邮件
3. 识别发票 → 数据保存到数据库
4. 查看发票列表
5. **随时点击"导出CSV"下载** → 临时生成 → 下载 → 自动删除

### 定期清理（可选）

如果有遗留文件，可以运行清理脚本：

```bash
# 清理超过7天的CSV文件
python3 cleanup_exports.py

# 自定义保留天数
python3 -c "from cleanup_exports import cleanup_old_exports; cleanup_old_exports(days=3)"
```

### 服务器部署建议

在生产环境（如Zeabur），建议：
1. 使用临时目录存储CSV（如 `/tmp/exports`）
2. 设置定时任务（cron）每天清理
3. 或者完全不保存到磁盘，直接在内存中生成CSV

### 内存优化版（可选）

如果你想完全避免写文件到磁盘，可以改为在内存中生成CSV：

```python
# 在 invoice.py 中修改
from io import StringIO, BytesIO

@bp.route('/export')
def export_csv():
    # 在内存中生成CSV
    output = StringIO()
    writer = csv.writer(output)
    # ... 写入数据 ...

    # 转为bytes
    csv_bytes = BytesIO()
    csv_bytes.write(output.getvalue().encode('utf-8-sig'))
    csv_bytes.seek(0)

    # 直接返回，不保存到磁盘
    return send_file(csv_bytes, ...)
```

这样**完全不占用磁盘空间**！
