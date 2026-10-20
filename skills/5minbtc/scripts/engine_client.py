#!/usr/bin/env python3
"""引擎调用客户端 — 优先走常驻服务, 失败自动回退到子进程。

为什么: 引擎单次约 10–12s, 绝大部分是 TLS 握手。常驻服务复用连接后约 3.7s
(实测 10 次中位: 服务 3.7s vs 子进程 9.2s)。但服务只是优化, 不是依赖 ——
服务没起/挂了/超时, 必须静默回退到原来的子进程路径, 交易不能因此停摆。
"""
import json
import os
import subprocess
import urllib.request

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(SKILL, "5minbtc-engine-v6.0.py")
PY = "/usr/bin/python3"
SERVER_URL = os.environ.get("ENGINE_SERVER_URL", "http://127.0.0.1:8791/predict")

_last_path = {"value": None}  # 诊断用: "server" / "subprocess"


def last_path():
    return _last_path["value"]


def run_engine(server_timeout=12, subprocess_timeout=45):
    """返回引擎结果 dict; 两条路都不通则返回 None (调用方自行决定重试)。"""
    try:
        with urllib.request.urlopen(SERVER_URL, timeout=server_timeout) as r:
            data = json.loads(r.read())
        if isinstance(data, dict) and "prediction" in data:
            _last_path["value"] = "server"
            return data
    except Exception:
        pass

    try:
        out = subprocess.run([PY, ENGINE], capture_output=True, text=True,
                             timeout=subprocess_timeout)
        data = json.loads(out.stdout)
        _last_path["value"] = "subprocess"
        return data
    except Exception:
        return None
