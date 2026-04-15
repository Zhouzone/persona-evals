import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai_personality_eval import runner
from ai_personality_eval.runner import build_item_messages, parse_model_choice


class RunnerTests(unittest.TestCase):
    def test_build_item_messages_asks_for_json_choice_only(self):
        item = {
            "id": "x",
            "prompt": "Choose a path.",
            "options": [
                {"id": "A", "text": "Path A", "scores": {"E": 1}},
                {"id": "B", "text": "Path B", "scores": {"I": 1}},
                {"id": "C", "text": "Path C", "scores": {"I": 0}},
            ],
        }

        messages = build_item_messages(item)

        self.assertEqual("system", messages[0]["role"])
        self.assertEqual("user", messages[1]["role"])
        self.assertIn('"choice"', messages[1]["content"])
        self.assertIn("Path A", messages[1]["content"])
        self.assertIn("A, B, or C", messages[1]["content"])

    def test_parse_model_choice_accepts_json_object(self):
        content = json.dumps(
            {"choice": "b", "confidence": 0.6, "brief_reason": "short"}
        )

        parsed = parse_model_choice(content)

        self.assertEqual("B", parsed["choice"])
        self.assertEqual(0.6, parsed["confidence"])

    def test_parse_model_choice_recovers_from_text_with_json_block(self):
        content = 'Here is my answer:\n{"choice": "A", "confidence": 0.8}'

        parsed = parse_model_choice(content)

        self.assertEqual("A", parsed["choice"])
        self.assertEqual(0.8, parsed["confidence"])

    def test_parse_model_choice_accepts_three_way_items(self):
        parsed = parse_model_choice('{"choice": "C", "confidence": 0.4}')

        self.assertEqual("C", parsed["choice"])

    def test_main_continue_on_error_records_failure_and_runs_next_model(self):
        def fake_run_model(**kwargs):
            model = kwargs["model"]
            if model == "bad-model":
                raise RuntimeError("gateway rejected model")
            return {
                "run_id": "run-good",
                "model": model,
                "results": {
                    "mbti_like": {"type": "INTJ-like"},
                    "sbti_style": {"type": "BOSS-like"},
                    "recommended_skill": {"id": "evidence_before_victory"},
                },
            }

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(runner, "run_model", side_effect=fake_run_model):
                exit_code = runner.main(
                    [
                        "--models",
                        "bad-model,good-model",
                        "--base-url",
                        "http://example.test/v1",
                        "--api-key",
                        "test-key",
                        "--output-dir",
                        tmp,
                        "--continue-on-error",
                    ]
                )

            self.assertEqual(0, exit_code)
            summary_path = Path(tmp) / "summary.jsonl"
            summaries = [
                json.loads(line)
                for line in summary_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(["error", "ok"], [row["status"] for row in summaries])
            self.assertEqual("bad-model", summaries[0]["model"])
            self.assertIn("gateway rejected model", summaries[0]["error"])
            self.assertEqual("good-model", summaries[1]["model"])

    def test_chat_completion_retries_malformed_gateway_json(self):
        malformed = json.JSONDecodeError("bad json", "{", 1)
        good_response = {"choices": [{"message": {"content": "{}"}}]}

        with mock.patch.object(
            runner,
            "_chat_completion",
            side_effect=[malformed, good_response],
        ):
            response = runner._chat_completion_with_retry(
                base_url="http://example.test/v1",
                api_key="test-key",
                model="test-model",
                messages=[],
                temperature=0.2,
                max_tokens=128,
                timeout_seconds=10,
                max_retries=2,
                retry_backoff_seconds=0,
            )

        self.assertEqual(good_response, response)

    def test_run_model_retries_item_when_model_output_is_not_json(self):
        pack = {
            "items": [
                {
                    "id": "item-1",
                    "prompt": "Pick a route.",
                    "options": [
                        {"id": "A", "text": "Route A"},
                        {"id": "B", "text": "Route B"},
                    ],
                }
            ]
        }
        malformed_response = {"choices": [{"message": {"content": "I would choose A."}}]}
        valid_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"choice":"B","confidence":0.7,"brief_reason":"clear"}'
                    }
                }
            ]
        }

        with (
            mock.patch.object(runner, "load_pack", return_value=pack),
            mock.patch.object(runner, "score_run", return_value={"ok": True}),
            mock.patch.object(
                runner,
                "_chat_completion_with_retry",
                side_effect=[malformed_response, valid_response],
            ) as chat,
        ):
            trace = runner.run_model(
                model="repair-model",
                base_url="http://example.test/v1",
                api_key="test-key",
                item_parse_retries=1,
                retry_backoff_seconds=0,
                randomize_options=False,
            )

        self.assertEqual(2, chat.call_count)
        self.assertEqual("B", trace["responses"][0]["choice"])
        self.assertEqual(2, trace["responses"][0]["parse_attempts"])

    def test_run_model_reports_item_progress(self):
        pack = {
            "items": [
                {
                    "id": "item-1",
                    "prompt": "Pick one.",
                    "options": [
                        {"id": "A", "text": "A"},
                        {"id": "B", "text": "B"},
                    ],
                },
                {
                    "id": "item-2",
                    "prompt": "Pick another.",
                    "options": [
                        {"id": "A", "text": "A"},
                        {"id": "B", "text": "B"},
                    ],
                },
            ]
        }
        response = {
            "choices": [
                {
                    "message": {
                        "content": '{"choice":"A","confidence":0.5,"brief_reason":"ok"}'
                    }
                }
            ]
        }
        progress_events = []

        with (
            mock.patch.object(runner, "load_pack", return_value=pack),
            mock.patch.object(runner, "score_run", return_value={"ok": True}),
            mock.patch.object(
                runner,
                "_chat_completion_with_retry",
                side_effect=[response, response],
            ),
        ):
            runner.run_model(
                model="progress-model",
                base_url="http://example.test/v1",
                api_key="test-key",
                retry_backoff_seconds=0,
                randomize_options=False,
                progress_callback=progress_events.append,
            )

        self.assertEqual(
            [
                {
                    "status": "item_complete",
                    "model": "progress-model",
                    "item_id": "item-1",
                    "item_index": 1,
                    "total_items": 2,
                    "parse_attempts": 1,
                },
                {
                    "status": "item_complete",
                    "model": "progress-model",
                    "item_id": "item-2",
                    "item_index": 2,
                    "total_items": 2,
                    "parse_attempts": 1,
                },
            ],
            progress_events,
        )

    def test_randomized_options_reassign_display_labels_before_prompting(self):
        item = {
            "id": "item-1",
            "prompt": "Pick one.",
            "options": [
                {"id": "A", "text": "Original A", "scores": {"E": 1}},
                {"id": "B", "text": "Original B", "scores": {"I": 1}},
            ],
        }
        pack = {"items": [item]}
        response = {
            "choices": [
                {
                    "message": {
                        "content": '{"choice":"A","confidence":0.5,"brief_reason":"first displayed"}'
                    }
                }
            ]
        }

        with (
            mock.patch.object(runner, "load_pack", return_value=pack),
            mock.patch.object(runner, "score_run", return_value={"ok": True}),
            mock.patch.object(
                runner,
                "_chat_completion_with_retry",
                return_value=response,
            ) as chat,
        ):
            trace = runner.run_model(
                model="label-test",
                base_url="http://example.test/v1",
                api_key="test-key",
                retry_backoff_seconds=0,
                randomize_options=True,
                seed=1,
            )

        prompt = chat.call_args.kwargs["messages"][1]["content"]
        self.assertIn("A. Original B", prompt)
        self.assertIn("B. Original A", prompt)
        self.assertEqual("B", trace["responses"][0]["choice"])
        self.assertEqual("A", trace["responses"][0]["display_choice"])


if __name__ == "__main__":
    unittest.main()
