import unittest

from ai_personality_eval.packs import load_pack
from ai_personality_eval.scoring import SBTI_TYPE_PROFILES
from ai_personality_eval.validation import validate_pack_for_release


class PackShapeTests(unittest.TestCase):
    def test_v01_pack_matches_public_viral_shape(self):
        pack = load_pack("ai-personality-v0.1")
        mbti_items = [item for item in pack["items"] if item["section"] == "mbti_like"]
        sbti_items = [item for item in pack["items"] if item["section"] == "sbti_style"]

        self.assertEqual(64, len(mbti_items))
        self.assertEqual(31, len(sbti_items))
        self.assertEqual(64, pack["shape"]["mbti_like_items"])
        self.assertEqual(31, pack["shape"]["sbti_style_items"])
        self.assertEqual(15, pack["shape"]["sbti_style_dimensions"])
        self.assertEqual(27, pack["shape"]["sbti_style_type_profiles"])
        self.assertEqual(
            {"E_I", "S_N", "T_F", "J_P"},
            {item["dimension"] for item in mbti_items},
        )
        self.assertEqual(
            {
                "self_esteem",
                "self_clarity",
                "core_values",
                "attachment_security",
                "emotional_investment",
                "boundary_dependence",
                "worldview_orientation",
                "rule_flexibility",
                "life_meaning",
                "motivation_orientation",
                "decision_style",
                "execution_mode",
                "social_initiative",
                "interpersonal_boundaries",
                "expression_authenticity",
            },
            {item["dimension"] for item in sbti_items},
        )
        self.assertTrue(all(len(item["options"]) == 3 for item in sbti_items))
        self.assertEqual(27, len(SBTI_TYPE_PROFILES))

    def test_v01_pack_passes_release_validator(self):
        pack = load_pack("ai-personality-v0.1")

        report = validate_pack_for_release(pack)

        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(95, report["total_items"])
        self.assertEqual(
            {
                "E_I": 16,
                "S_N": 16,
                "T_F": 16,
                "J_P": 16,
            },
            report["mbti_axis_counts"],
        )


if __name__ == "__main__":
    unittest.main()
