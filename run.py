#!/usr/bin/env python3
"""
邮件发票识别系统 · 启动入口

三种运行形态，自动选择：
  1. 桌面窗口（默认）—— 有 pywebview 时，弹一个原生窗口，关窗即退出
  2. 浏览器       —— 没有 pywebview 时，起服务并自动打开浏览器
  3. 纯服务       —— BILL_NO_WINDOW=1，只起服务不开界面（调试用）

环境变量：
  BILL_NO_WINDOW=1   不开窗口也不开浏览器
  BILL_BROWSER=1     强制用浏览器而不是桌面窗口
  BILL_PORT=5001     指定端口（默认自动挑一个可用的）
  BILL_DEBUG=1       开发时强制开启 debug（打包后无效）
"""

import logging
import os
import socket
import sys
import threading
import time

from app import create_app
from app.paths import is_frozen

HOST = '127.0.0.1'
PREFERRED_PORT = 5000
WINDOW_TITLE = '邮件发票识别系统'
IDLE_EXIT_MINUTES = 30


def find_free_port(preferred=PREFERRED_PORT):
    """
    挑一个可用端口

    5000 在 macOS 上常年被"隔空播放接收器"(AirPlay Receiver) 占用，
    写死端口会让程序在一部分 Mac 上直接起不来，所以先试首选再退让。
    """
    for port in [preferred, preferred + 1, preferred + 2, 8000, 8080]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((HOST, port))
                return port
            except OSError:
                continue

    # 都被占了，让系统随便给一个
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def wait_until_ready(url, timeout=20.0):
    """等 Flask 起来，避免窗口打开时还是空白页"""
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except urllib.error.HTTPError:
            return True          # 有响应就算起来了，哪怕是 4xx
        except Exception:
            time.sleep(0.15)
    return False


def run_server(app, port, debug):
    app.run(host=HOST, port=port, debug=debug, threaded=True, use_reloader=False)


def start_desktop_window(url):
    """用 pywebview 开一个原生窗口，返回是否成功"""
    try:
        import webview
    except ImportError:
        return False

    try:
        webview.create_window(WINDOW_TITLE, url, width=1280, height=860,
                              min_size=(960, 640))
        webview.start()          # 阻塞，直到用户关掉窗口
        return True
    except Exception as e:
        logging.getLogger(__name__).warning('桌面窗口启动失败，改用浏览器: %s', e)
        return False


def track_activity(app):
    """
    记录最后一次请求时间

    必须在服务启动前调用：Flask 2.2 起，应用开始处理请求之后
    再注册 before_request 会直接抛 AssertionError。
    """
    state = {'last': time.time()}

    @app.before_request
    def _touch():
        state['last'] = time.time()

    return state


def watch_idle_and_exit(state, minutes=IDLE_EXIT_MINUTES):
    """浏览器模式下，长时间没有请求就自动退出，避免留下僵尸进程"""
    log = logging.getLogger(__name__)
    limit = minutes * 60
    interval = max(1.0, min(20.0, limit / 4))   # 轮询间隔跟着阈值走，别比阈值还粗
    while True:
        time.sleep(interval)
        if time.time() - state['last'] > limit:
            log.info('闲置超过 %s 分钟，自动退出', minutes)
            os._exit(0)


def main():
    app = create_app()
    log = logging.getLogger(__name__)
    activity = track_activity(app)      # 必须在起服务之前挂上

    port = int(os.getenv('BILL_PORT') or find_free_port())
    url = f'http://{HOST}:{port}'

    # 打包后绝不能开 debug —— Werkzeug 的调试器等于在本机开了个可执行任意代码的入口
    debug = False if is_frozen() else os.getenv('BILL_DEBUG') == '1'

    banner = [
        '=' * 60,
        f'{WINDOW_TITLE}启动中...',
        f'访问地址: {url}',
        f'数据目录: {os.path.dirname(app.config["DATABASE_PATH"])}',
        f'日志文件: {app.config.get("LOG_PATH", "-")}',
        '=' * 60,
    ]
    for line in banner:
        log.info(line)
        print(line)

    no_window = os.getenv('BILL_NO_WINDOW') == '1'
    force_browser = os.getenv('BILL_BROWSER') == '1'

    # 只起服务：留在前台，方便开发和排查
    if no_window:
        run_server(app, port, debug)
        return

    server = threading.Thread(target=run_server, args=(app, port, debug), daemon=True)
    server.start()

    if not wait_until_ready(url):
        log.error('服务启动超时，请查看日志')
        print('服务启动超时，请查看日志文件')
        return

    if not force_browser and start_desktop_window(url):
        log.info('窗口已关闭，程序退出')
        # Flask 在守护线程里，直接退出进程即可
        os._exit(0)

    # 没有 pywebview 或窗口起不来：退回浏览器模式
    import webbrowser
    webbrowser.open(url)
    log.info('已退回浏览器模式')

    if is_frozen():
        # 打包版没有控制台窗口，用户没法 Ctrl+C。
        # 如果不加这个看门狗，窗口起不来时就会留下一个看不见也关不掉的后台进程，
        # 只能去任务管理器杀 —— 对非技术用户等于死锁。
        print(f'已在浏览器中打开 {url}')
        print(f'闲置 {IDLE_EXIT_MINUTES} 分钟后程序会自动退出。')
        watch_idle_and_exit(activity)
    else:
        print('已在浏览器中打开。按 Ctrl+C 退出。')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print('\n已退出')


if __name__ == '__main__':
    main()
