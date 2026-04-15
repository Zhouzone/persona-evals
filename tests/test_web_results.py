import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WebResultsDataTests(unittest.TestCase):
    def test_public_results_do_not_use_legacy_suffix_on_persona_labels(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        data = json.loads((ROOT / "web" / "data" / "results.json").read_text(encoding="utf-8"))
        legacy_suffix = "-li" + "ke"

        public_text = "\n".join(
            [
                readme,
                html,
                json.dumps(data["summary"], ensure_ascii=False),
                json.dumps(data["conclusions"], ensure_ascii=False),
                json.dumps(data["runs"], ensure_ascii=False),
            ]
        )

        self.assertIsNone(
            re.search(rf"\b(?:[EINSPTFJ]{{4}}|BOSS|DIOR){legacy_suffix}\b", public_text)
        )

    def test_site_loads_results_from_editable_json_file(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        results_path = ROOT / "web" / "data" / "results.json"

        self.assertNotIn("./data.js", html)
        self.assertIn("./app.js", html)
        self.assertIn("./data/results.json", app)
        self.assertIn("https://github.com/Zhouzone/persona-evals", html)
        self.assertIn("Persona Evals", html)
        self.assertIn('lang="zh-CN"', html)
        self.assertIn("模型人格评测", html)
        self.assertIn("切换主题", html)
        self.assertNotIn("A first pass", html)
        styles = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('[data-theme="light"]', styles)
        self.assertIn('[data-theme="dark"]', styles)
        self.assertIn(".theme-toggle", styles)
        self.assertIn("persona-evals-theme", app)
        self.assertNotIn("rerun needed", app)
        self.assertIn("暂无可复核记录", app)
        self.assertIn('id="provider-coverage"', html)
        self.assertIn('id="provider-grid"', html)
        self.assertIn('id="conclusions"', html)
        self.assertIn("renderFindingItems", app)
        self.assertIn("renderProviderCoverage", app)
        self.assertIn("providerGroup", app)
        self.assertTrue(results_path.exists(), "web/data/results.json should be the editable data source")

        data = json.loads(results_path.read_text(encoding="utf-8"))

        self.assertEqual("ai-personality-v0.1", data["pack"]["id"])
        self.assertEqual(95, data["pack"]["totalItems"])
        self.assertEqual(64, data["pack"]["mbtiItems"])
        self.assertEqual(31, data["pack"]["sbtiItems"])
        self.assertIn("prompt", data["pack"])
        self.assertIn("refinement", data["pack"])
        self.assertIn("conclusions", data)
        self.assertGreaterEqual(len(data["conclusions"]), 3)
        self.assertIn("diagnostics", data)
        self.assertIn("errors", data["diagnostics"])
        self.assertIn("dropped", data["diagnostics"])

        statuses = {run["model"]: run["status"] for run in data["runs"]}
        self.assertEqual("ok", statuses["gpt-5.4"])
        self.assertEqual("ok", statuses["claude-sonnet-4-6"])
        self.assertEqual("ok", statuses["deepseek-v3.2"])
        self.assertEqual("ok", statuses["qwen3-max"])
        self.assertEqual("ok", statuses["mistralai/mistral-large-2512"])

        ok_runs = [run for run in data["runs"] if run["status"] == "ok"]
        error_runs = [run for run in data["runs"] if run["status"] == "error"]
        skipped_runs = [run for run in data["runs"] if run["status"] == "skipped"]
        provider_groups = {run["providerGroup"] for run in data["runs"]}
        self.assertEqual(len(data["runs"]), len(ok_runs))
        self.assertGreaterEqual(len(ok_runs), 5)
        self.assertEqual(0, len(error_runs))
        self.assertEqual(0, len(skipped_runs))
        self.assertGreaterEqual(len(provider_groups), 5)
        self.assertEqual(len(ok_runs), data["summary"]["scoredModels"])
        self.assertEqual(
            data["summary"]["selectedModels"],
            data["summary"]["scoredModels"]
            + data["summary"]["errorModels"]
            + data["summary"]["droppedModels"],
        )
        for run in ok_runs:
            self.assertIn("mbtiType", run)
            self.assertIn("sbtiType", run)
            self.assertIn("recommendedSkill", run)
            self.assertEqual({"E_I", "S_N", "T_F", "J_P"}, set(run["axes"]))

    def test_public_site_uses_audience_facing_copy(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        data = json.loads((ROOT / "web" / "data" / "results.json").read_text(encoding="utf-8"))

        public_source = "\n".join([html, app, json.dumps(data["conclusions"], ensure_ascii=False)])
        hidden_copy = [
            "随机选项完整批次",
            "ai-personality-v0.1",
            "只展示完整跑完且可计分的模型结果",
            "随机化选项后，故事变得更清楚",
            "按厂商统计的公开结果",
            "runs/personality-eval",
            "sourceSummary",
            "source-path",
            "建议技能",
            "干预提示词",
            "网关",
            "题库如何改写",
            "每道题使用的 Prompt",
            "User template",
            "operator-run",
            "下一步",
            "标签数量",
        ]
        for phrase in hidden_copy:
            self.assertNotIn(phrase, public_source)

        self.assertIn("评测流程", html)
        self.assertIn("题库参考大众熟悉的 MBTI/SBTI 问题形式", html)
        self.assertIn("随机化选项", html)
        self.assertIn("逐题记录", html)
        self.assertIn("映射计分", html)
        self.assertIn("搜索模型、厂商或人格标签", html)
        self.assertIn('id="result-search"', html)
        self.assertIn('id="filter-bar"', html)
        self.assertIn("renderFilters", app)

    def test_public_site_uses_uipro_readable_console_layout(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")

        required_html = [
            'class="uipro-shell"',
            'class="release-strip"',
            'data-rollback="0be6b32"',
            "测试版",
            "回退版本 0be6b32",
            'class="uipro-hero"',
            'id="scan-summary"',
            'class="method-timeline"',
            'id="persona-map"',
            'class="readability-rail"',
            'class="finding-board"',
            'id="finding-snapshot"',
            "一个反直觉结果",
            "MBTI 分叉，SBTI 收敛",
            'class="result-console"',
            'id="search-hints"',
            'class="card-grid detail-card-grid"',
            'class="section-label"',
        ]
        for marker in required_html:
            self.assertIn(marker, html)

        required_app = [
            "renderScanSummary",
            "renderPersonaMap",
            "renderFindingSnapshot",
            "renderFindingItems",
            "renderSearchHints",
            "非 ${dominantMbti[0]}",
            "来源覆盖",
            "选项随机化后",
            "typeShareLabel",
            "typeShare",
            "axis-percent",
            "type-share",
            "search-hints",
        ]
        for marker in required_app:
            self.assertIn(marker, app)

        required_styles = [
            ".uipro-shell",
            ".release-strip",
            ".uipro-hero",
            ".scan-summary",
            ".persona-map",
            ".method-timeline",
            ".readability-rail",
            ".finding-board",
            ".finding-snapshot",
            ".snapshot-main",
            ".finding-list",
            ".result-console",
            ".search-hints",
            ".detail-card-grid",
            ".axis-percent",
            ".type-share",
        ]
        for marker in required_styles:
            self.assertIn(marker, styles)

        legacy_layout = [
            "适合传播的模型卡片",
            "spotlight-grid",
            "spotlight-card",
            "renderSpotlightCards",
            "下一步",
            "标签数量",
            "poster-hero",
            "poster-stat",
            "section-kicker",
            "flow-grid",
            "flow-step",
            "metric-card",
            "visual-strip",
        ]
        for marker in legacy_layout:
            self.assertNotIn(marker, html)


if __name__ == "__main__":
    unittest.main()
