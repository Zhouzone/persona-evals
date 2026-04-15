# AI Personality Eval

`ai-personality-v0.1` is a runnable MBTI-like and SBTI-style test for LLMs.

The priority of this package is the test itself, not the website. It produces
machine-readable traces and summary records that a later website can consume.

## What It Measures

The pack has 95 forced-choice items:

- 64 MBTI-like items for `E/I`, `S/N`, `T/F`, and `J/P`
- 31 SBTI-style items, matching the public SBTI-style shape of 15 dimensions:
  - `self_esteem`
  - `self_clarity`
  - `core_values`
  - `attachment_security`
  - `emotional_investment`
  - `boundary_dependence`
  - `worldview_orientation`
  - `rule_flexibility`
  - `life_meaning`
  - `motivation_orientation`
  - `decision_style`
  - `execution_mode`
  - `social_initiative`
  - `interpersonal_boundaries`
  - `expression_authenticity`

The output includes:

- `MBTI-like` type, such as `INTJ-like`
- `SBTI-style` type, selected from 27 type profiles such as `CTRL-like Controller`
- dimension scores
- a recommended prompt skill, such as `Evidence Before Victory`
- full per-item trace

This is inspired by 16-type and internet personality tests. It mirrors the
familiar test structure, but the items are rewritten for AI model and agent
behavior. It is not the official MBTI assessment and is not affiliated with
`sbti.one`.

## Run Locally

From this directory:

```bash
python -m ai_personality_eval.runner --list-pack
python -m ai_personality_eval.validate_pack
```

To run one model through an OpenAI-compatible gateway:

```bash
export OPENAI_BASE_URL="http://35.220.164.252:3888/v1/"
export OPENAI_API_KEY="replace_with_gateway_key"

python -m ai_personality_eval.runner \
  --model gpt-4o-mini \
  --output-dir runs/personality-eval
```

Or copy `.env.example` to `.env`, fill the gateway values, and run:

```bash
python -m ai_personality_eval.runner --env-file .env
```

To run the workspace Boyue gateway values without copying secrets into this
repo:

```bash
set -a
source /mnt/shared-storage-gpfs2/sciprismax2/zhouzhiwang/docs/platform/model-access/model-access.env.sh
set +a

export OPENAI_BASE_URL="$BOYUE_PRIMARY_BASE_URL"
export OPENAI_API_KEY="$BOYUE_API_KEY"

python -m ai_personality_eval.runner \
  --models "$BOYUE_MODEL_GPT_54,$BOYUE_MODEL_GPT_4O_MINI,$BOYUE_MODEL_CLAUDE_OPUS_46,$BOYUE_MODEL_QWEN35_PLUS,$BOYUE_MODEL_MINIMAX_M27,$BOYUE_MODEL_DEEPSEEK_V32,$BOYUE_MODEL_GROK4,$BOYUE_MODEL_KIMI25" \
  --output-dir runs/personality-eval
```

## Output

Each model run writes:

- one full trace JSON under `runs/personality-eval/`
- one line appended to `runs/personality-eval/summary.jsonl`

The trace shape is:

```json
{
  "run_id": "...",
  "created_at": "...",
  "provider": "openai-compatible",
  "model": "gpt-4o-mini",
  "pack_id": "ai-personality-v0.1",
  "settings": {},
  "responses": [],
  "results": {
    "mbti_like": {},
    "sbti_style": {},
    "recommended_skill": {}
  }
}
```

## Website Data

The static website reads one editable release file:

```text
web/data/results.json
```

That file should contain completed `status: "ok"` traces only. In-progress,
failed, and stopped jobs can remain under `runs/` and `logs/`, but they should
not be copied into the public website data.

## Scoring Notes

Direct items are rule-scored. The runner asks each model to return JSON:

```json
{"choice":"A","confidence":0.0,"brief_reason":"one sentence"}
```

Option order is randomized by default. After shuffling, displayed labels are
reassigned from `A/B/C`, then mapped back to the original scoring labels in the
trace. This keeps scoring deterministic while reducing fixed-label artifacts.

## Test

```bash
python -m unittest discover -s tests
```
