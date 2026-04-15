"""OpenAI-compatible runner for the AI personality test."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ai_personality_eval.packs import load_pack
from ai_personality_eval.scoring import score_run


SYSTEM_PROMPT = (
    "You are completing an AI assistant behavior questionnaire. "
    "Answer according to how you would operate as an AI assistant in the "
    "situation. Do not role-play a human life, do not mention personality "
    "tests, and do not explain outside the requested JSON."
)

DISPLAY_OPTION_IDS = ("A", "B", "C", "D", "E")


def build_item_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build a single-item chat prompt."""
    options = "\n".join(
        f"{_display_option_id(option)}. {option['text']}" for option in item["options"]
    )
    valid_choices = _format_choice_list(
        [_display_option_id(option) for option in item["options"]]
    )
    content = (
        f"Item ID: {item['id']}\n\n"
        f"Situation:\n{item['prompt']}\n\n"
        f"Options:\n{options}\n\n"
        "Return only valid JSON with this shape:\n"
        '{"choice":"A","confidence":0.0,"brief_reason":"one sentence"}\n'
        f"The choice must be exactly one of: {valid_choices}."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def build_item_repair_messages(
    item: dict[str, Any], previous_content: str, error: Exception
) -> list[dict[str, str]]:
    """Build a stricter retry prompt after an invalid item response."""
    messages = build_item_messages(item)
    valid_choices = _format_choice_list(
        [_display_option_id(option) for option in item["options"]]
    )
    messages.extend(
        [
            {
                "role": "assistant",
                "content": previous_content[:1000],
            },
            {
                "role": "user",
                "content": (
                    "The previous answer could not be parsed as the required JSON "
                    f"because: {type(error).__name__}: {error}. "
                    "Return exactly one JSON object and no surrounding text. "
                    f'The choice must be exactly one of: {valid_choices}. '
                    'Example: {"choice":"A","confidence":0.5,"brief_reason":"short"}'
                ),
            },
        ]
    )
    return messages


def parse_model_choice(content: str) -> dict[str, Any]:
    """Parse model output into a normalized choice response."""
    parsed = _load_json_object(content)
    choice = str(parsed.get("choice", "")).strip().upper()
    if choice not in {"A", "B", "C", "D", "E"}:
        raise ValueError(f"model returned invalid choice: {choice!r}")
    confidence = parsed.get("confidence", None)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = None
    if confidence is not None:
        confidence = max(0.0, min(1.0, confidence))
    return {
        "choice": choice,
        "confidence": confidence,
        "brief_reason": str(parsed.get("brief_reason", "")).strip(),
    }


def run_model(
    *,
    model: str,
    base_url: str,
    api_key: str,
    pack_id: str = "ai-personality-v0.1",
    temperature: float = 0.2,
    max_tokens: int = 512,
    timeout_seconds: int = 120,
    max_retries: int = 3,
    retry_backoff_seconds: float = 2,
    item_parse_retries: int = 1,
    randomize_options: bool = True,
    seed: int = 7,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run one model through the test pack and return a scored trace."""
    pack = load_pack(pack_id)
    rng = random.Random(seed)
    responses = []

    total_items = len(pack["items"])
    for item_index, item in enumerate(pack["items"], start=1):
        runtime_item = _maybe_shuffle_options(item, rng, randomize_options)
        parsed, content, parse_attempts = _answer_item_with_retry(
            base_url=base_url,
            api_key=api_key,
            model=model,
            item=runtime_item,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            item_parse_retries=item_parse_retries,
        )
        responses.append(
            {
                "item_id": item["id"],
                "choice": parsed["choice"],
                "display_choice": parsed["display_choice"],
                "confidence": parsed["confidence"],
                "brief_reason": parsed["brief_reason"],
                "raw_content": content,
                "parse_attempts": parse_attempts,
            }
        )
        if progress_callback is not None:
            progress_callback(
                {
                    "status": "item_complete",
                    "model": model,
                    "item_id": item["id"],
                    "item_index": item_index,
                    "total_items": total_items,
                    "parse_attempts": parse_attempts,
                }
            )

    result = score_run(pack, responses)
    return {
        "run_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": "openai-compatible",
        "base_url": _redact_base_url(base_url),
        "model": model,
        "pack_id": pack_id,
        "settings": {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "randomize_options": randomize_options,
            "seed": seed,
            "item_parse_retries": item_parse_retries,
        },
        "responses": responses,
        "results": result,
    }


def main(argv: list[str] | None = None) -> int:
    env_file = _preload_env(argv)
    parser = argparse.ArgumentParser(
        description="Run MBTI-style and SBTI-style AI personality tests."
    )
    parser.add_argument(
        "--env-file",
        default=str(env_file) if env_file else None,
        help="Optional dotenv-style file. Defaults to .env when it exists.",
    )
    parser.add_argument("--model", default=os.getenv("MODEL_ACCESS_DEFAULT_MODEL"))
    parser.add_argument("--models", default=os.getenv("EVAL_MODELS"))
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL"))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--pack", default=os.getenv("EVAL_TEST_PACK", "ai-personality-v0.1"))
    parser.add_argument("--temperature", type=float, default=float(os.getenv("EVAL_TEMPERATURE", "0.2")))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("EVAL_MAX_TOKENS", "512")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("MODEL_ACCESS_TIMEOUT_SECONDS", "120")))
    parser.add_argument("--max-retries", type=int, default=int(os.getenv("MODEL_ACCESS_MAX_RETRIES", "3")))
    parser.add_argument("--retry-backoff", type=float, default=float(os.getenv("MODEL_ACCESS_RETRY_BACKOFF_SECONDS", "2")))
    parser.add_argument("--item-parse-retries", type=int, default=int(os.getenv("EVAL_ITEM_PARSE_RETRIES", "1")))
    parser.add_argument("--progress-every", type=int, default=int(os.getenv("EVAL_PROGRESS_EVERY", "10")))
    parser.add_argument("--output-dir", default=os.getenv("EVAL_OUTPUT_DIR", "runs/personality-eval"))
    parser.add_argument("--no-randomize-options", action="store_true")
    parser.add_argument("--seed", type=int, default=int(os.getenv("EVAL_SEED", "7")))
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Record failed models in summary.jsonl and continue the batch.",
    )
    parser.add_argument("--list-pack", action="store_true")
    args = parser.parse_args(argv)

    if args.list_pack:
        pack = load_pack(args.pack)
        print(json.dumps(_pack_summary(pack), ensure_ascii=False, indent=2))
        return 0

    if not args.base_url or not args.api_key:
        raise SystemExit("OPENAI_BASE_URL and OPENAI_API_KEY are required")

    models = _resolve_models(args.model, args.models)
    if not models:
        raise SystemExit("provide --model, --models, MODEL_ACCESS_DEFAULT_MODEL, or EVAL_MODELS")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.jsonl"

    for model in models:
        print(json.dumps({"status": "starting", "model": model}, ensure_ascii=False), flush=True)
        progress_callback = _build_progress_printer(args.progress_every)
        try:
            trace = run_model(
                model=model,
                base_url=args.base_url,
                api_key=args.api_key,
                pack_id=args.pack,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                timeout_seconds=args.timeout,
                max_retries=args.max_retries,
                retry_backoff_seconds=args.retry_backoff,
                item_parse_retries=args.item_parse_retries,
                randomize_options=not args.no_randomize_options,
                seed=args.seed,
                progress_callback=progress_callback,
            )
        except Exception as exc:
            if not args.continue_on_error:
                raise
            summary = {
                "status": "error",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            with summary_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
            print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
            continue

        trace_path = out_dir / f"{_safe_filename(model)}-{trace['run_id']}.json"
        trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {
            "status": "ok",
            "run_id": trace["run_id"],
            "model": model,
            "mbti_like": trace["results"]["mbti_like"],
            "sbti_style": trace["results"]["sbti_style"],
            "recommended_skill": trace["results"]["recommended_skill"],
            "trace_path": str(trace_path),
        }
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    return 0


def _answer_item_with_retry(
    *,
    base_url: str,
    api_key: str,
    model: str,
    item: dict[str, Any],
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
    max_retries: int,
    retry_backoff_seconds: float,
    item_parse_retries: int,
) -> tuple[dict[str, Any], str, int]:
    messages = build_item_messages(item)
    total_parse_attempts = max(0, item_parse_retries) + 1
    for attempt in range(total_parse_attempts):
        raw = _chat_completion_with_retry(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )
        content = raw["choices"][0]["message"]["content"]
        try:
            parsed = parse_model_choice(content)
            parsed["display_choice"] = parsed["choice"]
            parsed["choice"] = _original_choice_for_display_choice(
                item, parsed["display_choice"]
            )
            return parsed, content, attempt + 1
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            if attempt == total_parse_attempts - 1:
                raise
            messages = build_item_repair_messages(item, content, exc)
            if retry_backoff_seconds > 0:
                time.sleep(retry_backoff_seconds * (attempt + 1))

    raise RuntimeError("unreachable item retry state")


def _build_progress_printer(progress_every: int) -> Callable[[dict[str, Any]], None] | None:
    if progress_every <= 0:
        return None

    def progress_callback(event: dict[str, Any]) -> None:
        item_index = int(event.get("item_index", 0))
        total_items = int(event.get("total_items", 0))
        if item_index % progress_every == 0 or item_index == total_items:
            print(json.dumps(event, ensure_ascii=False), flush=True)

    return progress_callback


def load_env_file(path: str | Path) -> None:
    """Load simple KEY=VALUE lines into the process environment.

    Existing environment variables win. This keeps shell-exported secrets from
    being accidentally replaced by a file.
    """
    env_path = Path(path)
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _preload_env(argv: list[str] | None) -> Path | None:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--env-file")
    known, _ = pre_parser.parse_known_args(argv)

    if known.env_file:
        env_file = Path(known.env_file)
    else:
        env_file = Path(".env")

    if env_file.exists():
        load_env_file(env_file)
        return env_file
    return None


def _load_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _format_choice_list(choices: list[str]) -> str:
    if len(choices) <= 2:
        return " or ".join(choices)
    return ", ".join(choices[:-1]) + ", or " + choices[-1]


def _display_option_id(option: dict[str, Any]) -> str:
    return str(option.get("display_id", option["id"]))


def _original_choice_for_display_choice(item: dict[str, Any], display_choice: str) -> str:
    for option in item["options"]:
        if _display_option_id(option) == display_choice:
            return str(option.get("original_id", option["id"]))
    raise ValueError(f"model returned invalid displayed choice: {display_choice!r}")


def _maybe_shuffle_options(
    item: dict[str, Any], rng: random.Random, enabled: bool
) -> dict[str, Any]:
    if not enabled:
        return item
    shuffled = dict(item)
    options = [dict(option) for option in item["options"]]
    rng.shuffle(options)
    for display_id, option in zip(DISPLAY_OPTION_IDS, options):
        option["original_id"] = option["id"]
        option["display_id"] = display_id
    shuffled["options"] = options
    return shuffled


def _chat_completion_with_retry(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
    max_retries: int,
    retry_backoff_seconds: float,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return _chat_completion(
                base_url=base_url,
                api_key=api_key,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            )
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            last_error = exc
            if attempt == max_retries - 1:
                break
            time.sleep(retry_backoff_seconds * (attempt + 1))
    raise RuntimeError(f"chat completion failed after {max_retries} attempts") from last_error


def _chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _resolve_models(model: str | None, models: str | None) -> list[str]:
    if models:
        return [part.strip() for part in models.split(",") if part.strip()]
    if model:
        return [model]
    return []


def _pack_summary(pack: dict[str, Any]) -> dict[str, Any]:
    sections: dict[str, int] = {}
    dimensions: dict[str, int] = {}
    for item in pack["items"]:
        sections[item["section"]] = sections.get(item["section"], 0) + 1
        dimensions[item["dimension"]] = dimensions.get(item["dimension"], 0) + 1
    return {
        "id": pack["id"],
        "name": pack["name"],
        "version": pack["version"],
        "items": len(pack["items"]),
        "sections": sections,
        "dimensions": dimensions,
        "disclaimer": pack["disclaimer"],
    }


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in value)


def _redact_base_url(base_url: str) -> str:
    return base_url.split("?")[0]


if __name__ == "__main__":
    raise SystemExit(main())
