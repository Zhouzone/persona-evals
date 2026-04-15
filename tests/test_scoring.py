import json
import tempfile
import unittest
from pathlib import Path

from ai_personality_eval.packs import load_pack
from ai_personality_eval.scoring import score_run


class ScoringTests(unittest.TestCase):
    def test_loads_v01_pack_with_mbti_and_sbti_items(self):
        pack = load_pack("ai-personality-v0.1")

        self.assertEqual(pack["id"], "ai-personality-v0.1")
        self.assertEqual(95, len(pack["items"]))
        self.assertEqual(
            {"mbti_like", "sbti_style"},
            {item["section"] for item in pack["items"]},
        )

    def test_scores_mbti_type_from_axis_choices(self):
        pack = {
            "id": "unit",
            "items": [
                {
                    "id": "ei",
                    "section": "mbti_like",
                    "dimension": "E_I",
                    "options": [
                        {"id": "A", "scores": {"E": 1}},
                        {"id": "B", "scores": {"I": 1}},
                    ],
                },
                {
                    "id": "sn",
                    "section": "mbti_like",
                    "dimension": "S_N",
                    "options": [
                        {"id": "A", "scores": {"S": 1}},
                        {"id": "B", "scores": {"N": 1}},
                    ],
                },
                {
                    "id": "tf",
                    "section": "mbti_like",
                    "dimension": "T_F",
                    "options": [
                        {"id": "A", "scores": {"T": 1}},
                        {"id": "B", "scores": {"F": 1}},
                    ],
                },
                {
                    "id": "jp",
                    "section": "mbti_like",
                    "dimension": "J_P",
                    "options": [
                        {"id": "A", "scores": {"J": 1}},
                        {"id": "B", "scores": {"P": 1}},
                    ],
                },
            ],
        }
        responses = [
            {"item_id": "ei", "choice": "A"},
            {"item_id": "sn", "choice": "B"},
            {"item_id": "tf", "choice": "A"},
            {"item_id": "jp", "choice": "A"},
        ]

        result = score_run(pack, responses)

        self.assertEqual("ENTJ", result["mbti_like"]["type"])
        self.assertEqual(1.0, result["mbti_like"]["axes"]["E_I"]["score"])

    def test_scores_sbti_profile_and_recommended_skill(self):
        pack = {
            "id": "unit",
            "items": [
                {
                    "id": "values",
                    "section": "sbti_style",
                    "dimension": "core_values",
                    "options": [
                        {"id": "A", "scores": {"core_values": 1}},
                        {"id": "B", "scores": {"core_values": -1}},
                    ],
                },
                {
                    "id": "rules",
                    "section": "sbti_style",
                    "dimension": "rule_flexibility",
                    "options": [
                        {"id": "A", "scores": {"rule_flexibility": 1}},
                        {"id": "B", "scores": {"rule_flexibility": -1}},
                    ],
                },
                {
                    "id": "boundaries",
                    "section": "sbti_style",
                    "dimension": "interpersonal_boundaries",
                    "options": [
                        {"id": "A", "scores": {"interpersonal_boundaries": 1}},
                        {"id": "B", "scores": {"interpersonal_boundaries": -1}},
                    ],
                },
            ],
        }
        responses = [
            {"item_id": "values", "choice": "B"},
            {"item_id": "rules", "choice": "A"},
            {"item_id": "boundaries", "choice": "A"},
        ]

        result = score_run(pack, responses)

        self.assertNotIn("-li" + "ke", result["sbti_style"]["type"])
        self.assertEqual("evidence_before_victory", result["recommended_skill"]["id"])

    def test_writes_machine_readable_summary_shape(self):
        pack = load_pack("ai-personality-v0.1")
        responses = [
            {"item_id": item["id"], "choice": item["options"][0]["id"]}
            for item in pack["items"]
        ]

        result = score_run(pack, responses)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "summary.json"
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
            loaded = json.loads(out.read_text())

        self.assertIn("mbti_like", loaded)
        self.assertIn("sbti_style", loaded)
        self.assertIn("recommended_skill", loaded)


if __name__ == "__main__":
    unittest.main()
