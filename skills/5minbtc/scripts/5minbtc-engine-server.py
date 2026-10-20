#!/usr/bin/env python3
"""5minbtc 引擎常驻服务 — 连接复用 + 60s TTL 缓存。

为什么存在: 引擎单次运行约 10–12s, 其中 ~100% 是在等网络 (profiler 实测
15.94/15.97s 在 thread lock)。而同一请求在已建立的连接上只要 0.7–1.0s。
引擎原本每次都以短命子进程运行, 进程一退连接就死, 所以永远重付 TLS 握手。
把它常驻起来后, 线程内连接池可跨轮复用, 实测 9.3s → 3.7s。

接口 (仅本机):
  GET /health   → {"ok": true}
  GET /predict  → 与 `python3 5minbtc-engine-v6.0.py` 完全相同的 JSON

调用方必须保留"服务不可用则回退到子进程"的路径 —— 本服务是优化, 不是依赖。
"""
import importlib.util
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 本文件在 scripts/ 下
ENGINE = os.path.join(SKILL, "5minbtc-engine-v6.0.py")
PORT = int(os.environ.get("ENGINE_SERVER_PORT", "8791"))

# 引擎模块含模块级状态 (线程池/连接池/缓存), 必须单实例。
spec = importlib.util.spec_from_file_location("engine", ENGINE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

# 引擎内部已用 9 路并行; 串行化整个 run() 避免并发请求争抢连接池。
_run_lock = threading.Lock()
_served = {"count": 0, "last_ts": None}  # 供 /health 观测


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            self._send(200, {"ok": True, "served": _served["count"],
                             "last_ts": _served["last_ts"]})
            return
        if path != "/predict":
            self._send(404, {"error": "not found"})
            return
        try:
            with _run_lock:
                result = engine.run()
            _served["count"] += 1
            _served["last_ts"] = time.strftime("%H:%M:%S")
            self._send(200, result)
        except Exception as e:  # 网络等异常 → 调用方据此回退
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *args):
        pass  # 不写访问日志, 避免刷屏


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[engine-server] listening on 127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()
