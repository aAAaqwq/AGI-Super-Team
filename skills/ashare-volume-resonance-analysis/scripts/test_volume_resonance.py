"""volume_resonance.py 冒烟测试：纯函数（不联网）。"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "volume_resonance.py")


def _load():
    spec = importlib.util.spec_from_file_location("volume_resonance", SRC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["volume_resonance"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_prefix_and_secid():
    mod = _load()
    assert mod.prefix("600838") == "sh600838", "6 开头补 sh"
    assert mod.prefix("300750") == "sz300750", "3 开头补 sz"
    assert mod.prefix("430047") == "bj430047", "4 开头补 bj"
    assert mod.code6("sh600838") == "600838", "code6 取后 6 位"
    assert mod.secid("600838") == "1.600838", "沪市 secid 前缀 1."
    assert mod.secid("300750") == "0.300750", "深市 secid 前缀 0."


def test_bj_now_tz_aware():
    mod = _load()
    assert mod.bj_now().tzinfo is not None, "北京时间应带时区"


def test_resonance_scores_and_labels():
    mod = _load()
    res = {"time": {"score": 2}, "structure": {"score": 3},
           "rhythm": {"score": 1}, "pv": {"score": 2}}
    r = mod.resonance(res)
    assert r["total"] == 8, "四维加总应为 8"
    assert r["pos"] == 4 and r["neg"] == 0, "全正应为 4 正 0 负"
    assert r["label"] == "共振", "全正应标共振"


if __name__ == "__main__":
    test_prefix_and_secid()
    test_bj_now_tz_aware()
    test_resonance_scores_and_labels()
    print("PASS: volume_resonance.py 冒烟测试通过")
