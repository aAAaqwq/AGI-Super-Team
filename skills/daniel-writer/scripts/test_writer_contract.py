from pathlib import Path
import re
import unittest


WRITER = Path(__file__).resolve().parents[1]


class WriterContractTests(unittest.TestCase):
    def test_formal_draft_route_has_fixed_minimum_set(self):
        skill = (WRITER / "SKILL.md").read_text(encoding="utf-8")
        for name in (
            "brand-and-taste.md",
            "voice-and-style.md",
            "human-agent-collaboration.md",
            "quality-gates.md",
            "draft-evidence-ledger.md",
            "platform-adapters.md",
        ):
            self.assertIn(name, skill)
        self.assertIn("下表是在固定最小集之上累积加载", skill)
        self.assertIn("起草和适配必须读取目标平台模板", skill)
        self.assertIn("第一人称稿件还必须读取", skill)

    def test_daniel_decision_gate_blocks_first_person_draft(self):
        skill = (WRITER / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Daniel 判断门", skill)
        self.assertIn("不得进入 Daniel 第一人称正式草稿", skill)

    def test_evidence_gap_returns_non_publishable_skeleton(self):
        skill = (WRITER / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("阻断说明＋不可发布骨架", skill)
        self.assertNotIn("边界明确的最佳草稿", skill)

    def test_all_platform_templates_exist(self):
        for platform in ("wechat", "x", "xiaohongshu", "bilibili", "zhihu", "douyin"):
            self.assertTrue((WRITER / "references" / f"templates-{platform}.md").is_file())

    def test_video_templates_have_all_tracks(self):
        for platform in ("bilibili", "douyin"):
            text = (WRITER / "references" / f"templates-{platform}.md").read_text(encoding="utf-8")
            for field in ("时间码", "口播", "证据 ID", "屏幕字幕", "素材权利", "未验证项"):
                self.assertIn(field, text)

    def test_xiaohongshu_template_has_emoji_and_hashtag_contracts(self):
        template = (WRITER / "references" / "templates-xiaohongshu.md").read_text(encoding="utf-8")
        contract = (WRITER / "references" / "xhs-card-contract.md").read_text(encoding="utf-8")
        for phrase in ("Emoji 使用合同", "4–6", "彼此不同", "每个 emoji 只出现 `1` 次", "按内容原型选择 Emoji", "三种模板的 Emoji 落点", "标签合同", "4–8", "任务/人群"):
            self.assertIn(phrase, template)
        for archetype in ("干货合集 / 保姆级攻略", "踩雷避坑 / 真实测评", "真实故事 / 复盘", "工具教程 / 工作流", "工具避坑 / 实测纠偏"):
            self.assertIn(archetype, template)
        for emoji in ("✨", "📌", "❌", "⭕", "🎬", "🌱", "✂️", "🔍"):
            self.assertIn(emoji, template)
        for field in ("emoji_plan", "hashtags"):
            self.assertIn(field, contract)
        self.assertIn("不得在同一篇笔记或同一卡组内重复 emoji", contract)
        for forbidden in ("#必火", "#热门", "#流量密码"):
            self.assertIn(forbidden, template)
            self.assertIn(forbidden, contract)

    def test_xiaohongshu_emoji_research_keeps_causality_boundary(self):
        ledger = (WRITER / "references" / "source-ledger.md").read_text(encoding="utf-8")
        self.assertIn("小红书 Emoji 与标签补充", ledger)
        self.assertIn("不作为“使用某个 emoji 会导致爆火”的因果证据", ledger)
        self.assertIn("样本量小、互动数据不完整", ledger)

    def test_zhihu_templates_cover_story_and_knowledge_without_fabrication(self):
        template = (WRITER / "references" / "templates-zhihu.md").read_text(encoding="utf-8")
        for phrase in (
            "故事 / 盐选叙事轨",
            "干货 / 观点回答轨",
            "强钩子 → 冲突或问题升级 → 反转或认知修正 → 共鸣或可执行结论",
            "模板四：故事 / 盐选式叙事",
            "模板五：干货 / 观点回答",
            "标题公式",
            "获授权改编 / 匿名化",
            "明确虚构",
            "不得凭空追加隐藏身份、阴谋、财富或巧合",
            "有逐字记录时才使用引号还原对话",
            "失效条件",
        ):
            self.assertIn(phrase, template)
        self.assertIn("不保证“爆火”", template)
        self.assertIn("第一人称标题只用于有证据的本人经历", template)

    def test_default_entry_enforces_decision_and_evidence_gates(self):
        entry = (WRITER / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("Daniel 判断门", entry)
        self.assertIn("逐稿证据台账", entry)
        self.assertIn("只返回候选角度", entry)

    def test_quality_gate_cannot_pass_with_blockers(self):
        gate = (WRITER / "references" / "quality-gates.md").read_text(encoding="utf-8")
        self.assertIn("总结果不得为“通过”", gate)
        self.assertIn("阻断条目数", gate)

    def test_all_creation_capabilities_are_integrated(self):
        skill = (WRITER / "SKILL.md").read_text(encoding="utf-8")
        references = (
            "x-editorial-contract.md",
            "wechat-editorial-contract.md",
            "xhs-card-contract.md",
            "douyin-script-contract.md",
            "short-video-production-contract.md",
            "work-package-schema.md",
        )
        for name in references:
            self.assertTrue((WRITER / "references" / name).is_file())
            self.assertIn(name, skill)
        for name in (
            "check_x_length.py",
            "init_content_package.py",
            "validate_content_package.py",
        ):
            self.assertTrue((WRITER / "scripts" / name).is_file())
            self.assertIn(name, skill)

    def test_skill_markdown_relative_links_resolve(self):
        skill = (WRITER / "SKILL.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", skill)
        for link in links:
            if "://" not in link and not link.startswith("#"):
                self.assertTrue((WRITER / link).exists(), link)


if __name__ == "__main__":
    unittest.main()
