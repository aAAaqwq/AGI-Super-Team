"""prelaunch_scan.py 冒烟测试：纯函数 + 凭证卫生（不联网）。"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "prelaunch_scan.py")


def _load():
    spec = importlib.util.spec_from_file_location("prelaunch_scan", SRC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["prelaunch_scan"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_tc_normalizes_market_prefix():
    mod = _load()
    assert mod.tc("600000") == "sh600000", "6 开头应补 sh"
    assert mod.tc("000001") == "sz000001", "0 开头应补 sz"
    assert mod.tc("300750") == "sz300750", "创业板应补 sz"
    assert mod.tc("sh600000") == "sh600000", "已带前缀不应重复补"


def test_bjnow_is_tz_aware():
    mod = _load()
    assert mod.bjnow().tzinfo is not None, "北京时间应带时区"


def test_no_hardcoded_credential():
    src = open(SRC, encoding="utf-8").read()
    assert "longqin@666" not in src, "硬编码密码必须移除"
    assert "LONGQIN_PASSWORD" in src, "密码应改为环境变量读取"
    assert "LONGQIN_USERNAME" in src, "用户名也应从环境变量读取"


if __name__ == "__main__":
    test_tc_normalizes_market_prefix()
    test_bjnow_is_tz_aware()
    test_no_hardcoded_credential()
    print("PASS: prelaunch_scan.py 冒烟测试通过")
