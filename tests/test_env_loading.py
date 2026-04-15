import os
import tempfile
import unittest
from pathlib import Path

from ai_personality_eval.runner import load_env_file


class EnvLoadingTests(unittest.TestCase):
    def test_load_env_file_sets_missing_values_without_overriding_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "OPENAI_BASE_URL=http://example.test/v1/",
                        "OPENAI_API_KEY=file-key",
                        "QUOTED_VALUE=\"hello world\"",
                    ]
                ),
                encoding="utf-8",
            )

            old_key = os.environ.get("OPENAI_API_KEY")
            old_base_url = os.environ.get("OPENAI_BASE_URL")
            old_quoted = os.environ.get("QUOTED_VALUE")
            os.environ.pop("OPENAI_BASE_URL", None)
            os.environ.pop("QUOTED_VALUE", None)
            os.environ["OPENAI_API_KEY"] = "existing-key"
            try:
                load_env_file(env_path)
                self.assertEqual("http://example.test/v1/", os.environ["OPENAI_BASE_URL"])
                self.assertEqual("existing-key", os.environ["OPENAI_API_KEY"])
                self.assertEqual("hello world", os.environ["QUOTED_VALUE"])
            finally:
                if old_key is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = old_key
                if old_base_url is None:
                    os.environ.pop("OPENAI_BASE_URL", None)
                else:
                    os.environ["OPENAI_BASE_URL"] = old_base_url
                if old_quoted is None:
                    os.environ.pop("QUOTED_VALUE", None)
                else:
                    os.environ["QUOTED_VALUE"] = old_quoted


if __name__ == "__main__":
    unittest.main()
