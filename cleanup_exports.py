"""
清理旧的导出文件
定期运行此脚本可以清理超过N天的CSV导出文件
"""

import os
import time
from datetime import datetime, timedelta

def cleanup_old_exports(exports_dir='data/exports', days=7):
    """
    清理超过指定天数的导出文件

    Args:
        exports_dir: 导出文件目录
        days: 保留天数，默认7天
    """
    if not os.path.exists(exports_dir):
        print(f"目录不存在: {exports_dir}")
        return

    cutoff_time = time.time() - (days * 24 * 60 * 60)
    deleted_count = 0
    kept_count = 0

    print(f"清理 {exports_dir} 中超过 {days} 天的文件...")
    print(f"截止时间: {datetime.fromtimestamp(cutoff_time)}")
    print("-" * 60)

    for filename in os.listdir(exports_dir):
        if not filename.endswith('.csv'):
            continue

        filepath = os.path.join(exports_dir, filename)

        # 检查文件修改时间
        file_mtime = os.path.getmtime(filepath)
        file_date = datetime.fromtimestamp(file_mtime)

        if file_mtime < cutoff_time:
            try:
                os.remove(filepath)
                deleted_count += 1
                print(f"✓ 删除: {filename} (日期: {file_date.strftime('%Y-%m-%d %H:%M')})")
            except Exception as e:
                print(f"✗ 删除失败: {filename} - {e}")
        else:
            kept_count += 1
            print(f"  保留: {filename} (日期: {file_date.strftime('%Y-%m-%d %H:%M')})")

    print("-" * 60)
    print(f"清理完成: 删除 {deleted_count} 个文件, 保留 {kept_count} 个文件")

if __name__ == '__main__':
    # 清理超过7天的文件
    cleanup_old_exports(days=7)
