#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引擎契约测试 — 契约、因子数值、多时刻采样、稳定性

⚠️ 2026-09-10 前名为 `test_engine_v58.py`：版本号写进文件名 → 引擎升到 v6.0 后即漂移。
现改名 `test_engine.py`（不带版本号），内容已对齐 v6.0。

引擎零第三方依赖，**测试也不应强制装 pytest**：
- 有 pytest：`python3 -m pytest scripts/test_engine.py -v`
- 没有 pytest：`python3 scripts/test_engine.py`（自带极简 runner，慢测默认跳过）
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

try:
    import pytest
except ImportError:                      # 无 pytest → 退化为直通装饰器
    pytest = None
    def mark_slow(fn):
        fn._slow = True
        return fn
else:
    def mark_slow(fn):
        fn._slow = True
        return pytest.mark.slow(fn)

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent  # scripts/ 的上一级 = skill 根
ENGINE = SKILL / "5minbtc-engine-v6.0.py"
MONITOR = HERE / "5minbtc-monitor.py"

spec = importlib.util.spec_from_file_location("eng", ENGINE)
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)


# ---------------- 契约 ----------------

def run_engine_subprocess(timeout=60):
    """真实跑一次引擎（不缓存）—— 稳定性测试用。"""
    out = subprocess.run(["python3", str(ENGINE)], capture_output=True,
                         text=True, timeout=timeout)
    assert out.returncode == 0, f"engine exit={out.returncode} stderr={out.stderr}"
    return json.loads(out.stdout)


_SNAPSHOT = {}


def engine_snapshot():
    """契约测试共用的引擎输出（缓存一次，避免每个测试都跑一遍 9 路 HTTP）。"""
    if "d" not in _SNAPSHOT:
        _SNAPSHOT["d"] = run_engine_subprocess()
    return _SNAPSHOT["d"]


def test_engine_version_is_600():
    assert eng.__file__ or True  # module loads
    d = engine_snapshot()
    assert d["version"] == "6.0.0"


def test_prediction_contract():
    d = engine_snapshot()
    pred = d["prediction"]
    for k in ("bias", "strength", "confidence", "score",
              "pred_close", "pred_high", "pred_low"):
        assert k in pred, f"prediction missing {k}"
    # v6.0: 方向二选一无中性 (neutral 分支不可达)
    assert pred["bias"] in ("bull", "bear"), f"bias 必须二选一, 实际 {pred['bias']}"
    assert pred["strength"] in ("weak", "medium", "moderate", "strong")
    assert 0 <= pred["confidence"] <= 100


def test_top_level_contract():
    d = engine_snapshot()
    for k in ("version", "candle", "price", "recent_candles", "indicators",
              "fng", "factors", "regime", "chainlink_offset", "atr_spike",
              "fng_black_swan", "news_risk", "prediction"):
        assert k in d, f"top-level missing {k}"
    p = d["price"]
    assert p["low"] <= p["current"] <= p["high"]


def test_ofi_block_contract():
    """v6.0 新增: 顶层 ofi 块是方向与概率的来源, 必须存在且 direction 与 bias 一致。"""
    d = engine_snapshot()
    assert "ofi" in d, "顶层缺 ofi 块"
    o = d["ofi"]
    for k in ("direction", "ofi_n"):
        assert k in o, f"ofi 块缺 {k}"
    assert o["direction"] in ("bull", "bear")
    assert d["prediction"]["bias"] == o["direction"], "bias 必须等于 ofi.direction"


def test_taker_buy_in_factors():
    d = engine_snapshot()
    assert "taker_buy" in d["factors"]
    assert -1.0 <= d["factors"]["taker_buy"] <= 1.0


def test_taker_buy_weight_is_zeroed():
    """v5.9 起 BASE_W['taker_buy'] 被**有意清零**（该因子从未被公平回测验证）。

    这里断言 == 0 是为了**防止它被误重新启用** —— 若要恢复，请先补公平回测，
    并同时改这条断言（别只把 0 改成非 0 就上）。
    """
    assert "taker_buy" in eng.BASE_W
    assert eng.BASE_W["taker_buy"] == 0.0, "taker_buy 权重应保持清零 (v5.9 决定)"
    for regime, adj in eng.REGIME_ADJ.items():
        assert "taker_buy" in adj, f"REGIME_ADJ[{regime}] missing taker_buy"


# ---------------- 因子数值 ----------------

def test_taker_buy_signal_math():
    # 全主动买: tb=v → ratio=1 → 2*(1-0.5)*3=3 → clamp 1.0
    candles = [{"o": 100, "h": 101, "l": 99, "c": 101, "v": 10, "tb": 10, "ct": 0}] * 6
    assert eng.taker_buy_signal(candles) == 1.0
    # 全主动卖: tb=0 → ratio=0 → 2*(0-0.5)*3=-3 → clamp -1.0 (v>0 有效)
    candles0 = [{"o": 100, "h": 101, "l": 99, "c": 99, "v": 10, "tb": 0, "ct": 0}] * 6
    assert eng.taker_buy_signal(candles0) == -1.0
    # 均衡 0.5 → 0
    candles_mid = [{"o": 100, "h": 101, "l": 99, "c": 100, "v": 10, "tb": 5, "ct": 0}] * 6
    assert eng.taker_buy_signal(candles_mid) == 0.0
    # 用已完成 K线 (排除当前未完成)
    done = [{"o": 100, "h": 101, "l": 99, "c": 100, "v": 10, "tb": 10, "ct": 0}] * 5
    cur = [{"o": 100, "h": 101, "l": 99, "c": 100, "v": 10, "tb": 0, "ct": 0}]
    assert eng.taker_buy_signal(done + cur) == 1.0  # 当前 tb=0 被排除
    # 数据容错: tb>v 时钳制到 v → ratio=1
    c_over = [{"o": 100, "h": 101, "l": 99, "c": 101, "v": 10, "tb": 99, "ct": 0}] * 6
    assert eng.taker_buy_signal(c_over) == 1.0


def test_taker_buy_signal_edges():
    # 空列表
    assert eng.taker_buy_signal([]) == 0.0
    # v=0 全跳过
    c = [{"o": 100, "h": 101, "l": 99, "c": 100, "v": 0, "tb": 0, "ct": 0}] * 6
    assert eng.taker_buy_signal(c) == 0.0
    # 无 tb 字段向后兼容 (fetch_klines 守卫不足时)
    c2 = [{"o": 100, "h": 101, "l": 99, "c": 100, "v": 10}] * 6
    assert eng.taker_buy_signal(c2) == 0.0


# ---------------- 订单簿多时刻采样 ----------------

def test_fetch_depth_avg_merges_and_truncates(monkeypatch):
    calls = {"n": 0}
    snaps = [
        {"bids": [(100.0, 1.0), (99.5, 2.0)], "asks": [(100.5, 3.0)]},
        {"bids": [(100.0, 3.0), (99.5, 1.0)], "asks": [(100.5, 1.0)]},
        None,  # 失败采样应被跳过
    ]
    def fake_depth(*a, **k):
        s = snaps[calls["n"] % len(snaps)]
        calls["n"] += 1
        return s
    monkeypatch.setattr(eng, "fetch_depth", fake_depth)
    monkeypatch.setattr(eng, "time", _FakeTime())
    res = eng.fetch_depth_avg(limit=20, samples=3, interval_s=0.0)
    assert res is not None
    # 同价位取平均: (1+3)/2=2 (第3次None被跳过 → got=2)
    assert res["bids"][0] == (100.0, 2.0)
    assert res["bids"][1] == (99.5, 1.5)
    assert res["asks"][0] == (100.5, 2.0)


def test_fetch_depth_avg_all_fail(monkeypatch):
    monkeypatch.setattr(eng, "fetch_depth", lambda *a, **k: None)
    monkeypatch.setattr(eng, "time", _FakeTime())
    assert eng.fetch_depth_avg(samples=3, interval_s=0.0) is None


def test_fetch_depth_avg_limit_truncation(monkeypatch):
    # 3 次采样价位漂移 → 合并后层数 > limit, 必须截断到 limit
    def fake_depth(*a, **k):
        return {"bids": [(float(i), 1.0) for i in range(100, 0, -1)],
                "asks": [(float(i), 1.0) for i in range(101, 201)]}
    monkeypatch.setattr(eng, "fetch_depth", fake_depth)
    monkeypatch.setattr(eng, "time", _FakeTime())
    res = eng.fetch_depth_avg(limit=20, samples=3, interval_s=0.0)
    assert len(res["bids"]) == 20
    assert len(res["asks"]) == 20


class _FakeTime:
    def sleep(self, *_a, **_k):
        return None


# ---------------- 稳定性 (可跳过) ----------------

@mark_slow
def test_multiple_runs_stable():
    biases = []
    for _ in range(3):
        d = run_engine_subprocess()
        biases.append(d["prediction"]["bias"])
        assert "taker_buy" in d["factors"]
    # 只断言不崩, 不做 bias 一致性断言 (market 实时变化)


def test_monitor_dry_run_compatible():
    out = subprocess.run(["python3", str(MONITOR), "--dry-run"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, f"monitor dry-run failed: {out.stderr}"
    assert "DRY" in out.stdout
    assert "[20" in out.stdout or "progress" in out.stdout or "conf=" in out.stdout


def _run_without_pytest(argv):
    """极简 runner —— 引擎零依赖, 不该为了跑测试强装 pytest。

    提供 monkeypatch 的最小替身（只实现 setattr/undo），慢测默认跳过（加 --slow 才跑）。
    """
    class _MonkeyPatch:
        def __init__(self):
            self._undo = []

        def setattr(self, obj, name, value):
            self._undo.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

        def undo(self):
            for obj, name, old in reversed(self._undo):
                setattr(obj, name, old)
            self._undo.clear()

    want_slow = "--slow" in argv
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed, failed, skipped = [], [], []

    for fn in fns:
        if getattr(fn, "_slow", False) and not want_slow:
            skipped.append(fn.__name__)
            continue
        mp = _MonkeyPatch()
        try:
            if "monkeypatch" in fn.__code__.co_varnames[:fn.__code__.co_argcount]:
                fn(mp)
            else:
                fn()
            passed.append(fn.__name__)
            print(f"  ✅ {fn.__name__}")
        except Exception as e:
            failed.append((fn.__name__, e))
            print(f"  ❌ {fn.__name__}: {type(e).__name__}: {e}")
        finally:
            mp.undo()

    print(f"\n通过 {len(passed)} | 失败 {len(failed)} | 跳过 {len(skipped)}"
          + (f"（慢测: {' '.join(skipped)}，加 --slow 可跑）" if skipped else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    if pytest is not None:
        sys.exit(pytest.main([__file__, "-v"]))
    print("未装 pytest → 使用内置 runner\n")
    sys.exit(_run_without_pytest(sys.argv[1:]))
