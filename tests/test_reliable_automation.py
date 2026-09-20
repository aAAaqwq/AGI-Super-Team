"""镜像 skill 内的 reliable-automation 测试，使 `unittest discover` 与 CI 能收集到。

skill 自己的测试住在 `skills/reliable-automation/scripts/test_*.py`（与实现同目录，
便于单独运行）；本文件只做加载与再导出，不复制用例。三个测试模块共 15 个测试类。
"""

import importlib.util
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "skills/reliable-automation/scripts"


def _load(module_name, filename):
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


_MODULES = (
    _load("reliable_automation_watchdog_tests", "test_watchdog.py"),
    _load("reliable_automation_heartbeat_tests", "test_heartbeat.py"),
    _load("reliable_automation_idempotency_tests", "test_idempotency.py"),
)

# discover 只收集本模块命名空间里的测试类；上面加载的模块不在 sys.modules 里，
# 所以要把测试类显式抬上来。按 "Tests" 结尾筛选即可排除各模块的 TestCase 基类。
for _module in _MODULES:
    for _name, _value in vars(_module).items():
        if isinstance(_value, type) and _name.endswith("Tests"):
            globals()[_name] = _value

del _module, _name, _value
