"""
路径解析

打包成可执行文件后，"程序在哪"和"数据在哪"是两个不同的位置：
  - 代码和模板被解压到临时目录 sys._MEIPASS，每次启动都会变
  - 数据必须放在可执行文件旁边，才能在下次启动时找回来

单独放一个模块是为了让 crypto、日志这些底层工具也能用，
而不必反向 import app/__init__.py 造成循环依赖。
"""

import os
import sys


def is_frozen():
    """是否运行在PyInstaller打包后的可执行文件里"""
    return getattr(sys, 'frozen', False)


def get_base_dir():
    """
    数据目录的基准路径

    打包后 = 可执行文件所在目录；开发时 = 项目根目录
    """
    if is_frozen():
        if sys.platform == 'darwin' and '.app/Contents/MacOS' in sys.executable:
            # macOS 的 .app 是个目录，数据写在 bundle 内部会被 Gatekeeper
            # 和"移动到废纸篓"连带清掉，所以放到 .app 同级目录
            app_bundle = sys.executable.split('.app/Contents/MacOS')[0] + '.app'
            return os.path.dirname(app_bundle)
        return os.path.dirname(sys.executable)

    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def get_resource_path(relative_path):
    """模板、静态文件等只读资源的路径"""
    if is_frozen():
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)


def get_data_dir():
    """数据目录，不存在则创建"""
    data_dir = os.path.join(get_base_dir(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_log_dir():
    """日志目录，不存在则创建"""
    log_dir = os.path.join(get_base_dir(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir
