#!/usr/bin/env python3
"""Daniel 写作语言检查器的最小回归测试。"""

import importlib.util
import unittest
from pathlib import Path


脚本路径 = Path(__file__).with_name("style_lint.py")
模块规格 = importlib.util.spec_from_file_location("daniel_style_lint", 脚本路径)
检查器 = importlib.util.module_from_spec(模块规格)
模块规格.loader.exec_module(检查器)


class 语言检查测试(unittest.TestCase):
    def test_检出_agent_越权(self):
        self.assertIn("Agent越权", 检查器.lint("Agent 自动完成整个剪辑流程。"))

    def test_无关否定不能掩盖_agent_越权(self):
        文本 = "它并不神奇，但 Agent 自动完成整个剪辑流程。"
        self.assertIn("Agent越权", 检查器.lint(文本))

    def test_直接否定可以忽略能力短语(self):
        self.assertNotIn("Agent越权", 检查器.lint("Agent 不能自动完成整个剪辑流程。"))

    def test_检出抽检扩大为问题消失(self):
        self.assertIn("绝对归因", 检查器.lint("调整以后，问题才消失。"))

    def test_检出未经测量的最费时间(self):
        self.assertIn("未经测量的收益", 检查器.lint("最费时间的不是画面。"))


if __name__ == "__main__":
    unittest.main()
