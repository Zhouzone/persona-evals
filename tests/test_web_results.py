import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WebResultsDataTests(unittest.TestCase):
    def test_site_loads_results_from_editable_json_file(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        results_path = ROOT / "web" / "data" / "results.json"

        self.assertNotIn("./data.js", html)
        self.assertIn("./app.js", html)
        self.assertIn("./data/results.json", app)
        self.assertNotIn("rerun needed", app)
        self.assertIn("no complete trace", app)
        self.assertIn('id="provider-coverage"', html)
        self.assertIn('id="provider-grid"', html)
        self.assertIn('id="conclusions"', html)
        self.assertIn("renderConclusions", app)
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


if __name__ == "__main__":
    unittest.main()
