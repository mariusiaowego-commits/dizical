"""dizical kid 启动命令 — 启动儿童版 Web 服务器"""

import os
import sys
import socket
import time
import webbrowser
import threading
from pathlib import Path

import typer
import uvicorn

# 添加项目路径
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

kid_app = typer.Typer(help="\U0001F3B5 竹笛练习助手（儿童版）")

def get_local_ip() -> str:
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@kid_app.command()
def start(
    port: int = typer.Option(8765, "--port", "-p", help="服务端口"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="监听地址"),
    open_browser: bool = typer.Option(True, "--no-open", help="启动后不打开浏览器"),
):
    """
    启动竹笛练习助手（儿童版 Web 界面）。

    启动后在 iPad Safari 访问：
      http://<本机IP>:8765

    例如： http://192.168.1.100:8765
    """
    local_ip = get_local_ip()

    print()
    print("\U0001F3B5 竹笛练习助手（儿童版）")
    print("=" * 40)
    print(f"\n本地访问:  http://localhost:{port}")
    print(f"iPad 访问:  http://{local_ip}:{port}")
    print()
    print("按 Ctrl+C 停止服务")
    print()

    if open_browser:
        def open_browser_delayed():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=open_browser_delayed, daemon=True).start()

    # 导入并运行 FastAPI app
    from src.kid_app.app import app as fastapi_app

    uvicorn.run(
        fastapi_app,
        host=host,
        port=port,
        log_level="warning",
    )

@kid_app.command()
def status():
    """检查服务是否在运行"""
    import urllib.request
    port = 8765
    try:
        urllib.request.urlopen(f"http://localhost:{port}/", timeout=2)
        print(f"\u2705 服务正在运行: http://localhost:{port}")
    except Exception:
        print(f"\u274C 服务未运行，请先执行: dizical-kid start")

if __name__ == "__main__":
    kid_app()
