"""
日志

打包成无控制台窗口的应用后，终端里的诊断信息就没人看得见了，
所以必须落到文件。这里做两件事：

  1. 把日志写到 logs/app.log（滚动，最多留 3 份）
  2. 处理 sys.stdout 为 None 的情况

第 2 点是 PyInstaller 的经典坑：Windows 上用 console=False 打包后，
进程根本没有标准输出，sys.stdout 和 sys.stderr 都是 None，
此时任何一句 print() 都会抛 AttributeError 直接把程序打崩。
本项目各处都在用 print() 输出处理进度，所以必须把它们接到日志上。
"""

import logging
import logging.handlers
import os
import sys

from app.paths import get_base_dir, get_log_dir

LOG_FILENAME = 'app.log'
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3

_configured = False


class _StreamToLogger:
    """把 print() 的输出转发到日志（无控制台时替代 sys.stdout/stderr）"""

    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self._buffer = ''

    def write(self, message):
        if not message:
            return
        self._buffer += message
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            if line.strip():
                self.logger.log(self.level, line.rstrip())

    def flush(self):
        if self._buffer.strip():
            self.logger.log(self.level, self._buffer.rstrip())
        self._buffer = ''

    def isatty(self):
        return False


def _force_utf8(stream):
    """
    把控制台流切到 UTF-8

    Windows 的标准输出默认跟随控制台代码页（英文环境是 cp1252），
    打印中文会直接抛 UnicodeEncodeError 把程序打断 ——
    本项目的日志和进度输出全是中文，所以必须显式切过来。
    errors='replace' 兜底，实在编码不了也只是显示成问号，不会崩。
    """
    if stream is None or not hasattr(stream, 'reconfigure'):
        return
    try:
        stream.reconfigure(encoding='utf-8', errors='replace')
    except (ValueError, OSError):
        pass    # 流已关闭或不支持，忽略


def get_log_path():
    """
    日志文件路径，可用 LOG_FILE 环境变量覆盖

    相对路径按 base_dir 解析，不能按当前工作目录：
    从 Finder / 资源管理器双击启动时 CWD 是不确定的（macOS 上是 /），
    按 CWD 解析会把日志写到莫名其妙的地方，甚至因无写权限而失败。
    """
    custom = os.getenv('LOG_FILE')
    if custom:
        path = custom if os.path.isabs(custom) else os.path.join(get_base_dir(), custom)
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path
    return os.path.join(get_log_dir(), LOG_FILENAME)


def setup_logging(level=None):
    """
    初始化日志，返回日志文件路径

    Args:
        level: 日志级别，默认读环境变量 LOG_LEVEL，再默认 INFO
    """
    global _configured
    log_path = get_log_path()

    if _configured:
        return log_path

    # 有控制台的话先把编码切到 UTF-8，否则 Windows 上第一句中文就崩
    _force_utf8(sys.stdout)
    _force_utf8(sys.stderr)

    level_name = (level or os.getenv('LOG_LEVEL') or 'INFO').upper()
    log_level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(file_handler)

    # 有控制台时同时输出一份，方便开发
    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        console.setLevel(log_level)
        root.addHandler(console)

    # 无控制台（Windows windowed 打包）时，接管 print 防止崩溃
    if sys.stdout is None:
        sys.stdout = _StreamToLogger(logging.getLogger('stdout'), logging.INFO)
    if sys.stderr is None:
        sys.stderr = _StreamToLogger(logging.getLogger('stderr'), logging.ERROR)

    # 未捕获异常也要留痕，否则窗口一闪而过什么都查不到
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger('unhandled').critical(
            '未捕获的异常', exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception

    _configured = True
    logging.getLogger(__name__).info('日志已初始化: %s', log_path)
    return log_path
