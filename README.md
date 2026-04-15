# Persona Evals

<p>
  <a href="https://github.com/Zhouzone/persona-evals/actions/workflows/pages.yml"><img alt="GitHub Pages" src="https://img.shields.io/badge/site-GitHub%20Pages-222222"></a>
  <a href="https://github.com/Zhouzone/persona-evals/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
  <img alt="Models: 39 selected, 23 scored" src="https://img.shields.io/badge/models-23%20scored%20/%2039%20selected-blue">
  <img alt="Pack: 95 items" src="https://img.shields.io/badge/test%20pack-95%20items-purple">
</p>

<p>
  <img src="web/assets/seevomap-hero.png" alt="Persona Evals research map texture" width="100%">
</p>

MBTI-style 和 SBTI-style 的 LLM / Agent 行为评测。

我们想回答一个简单但很适合传播的问题：

> 当大模型面对类似人格测试的选择题时，它们真的有不同的“人格”，还是都会收敛到同一种 assistant persona？

第一版先做一个可传播、可复现、可继续扩展的公开评测：用 95 道 MBTI-style / SBTI-style 强制选择题，批量测试多个模型家族。每道题的展示选项都会随机打乱，再在 trace 中映射回原始计分标签，避免结果只是固定 `A/B/C` 位置偏置。

网站：
`https://zhouzone.github.io/persona-evals/`

仓库：
`https://github.com/Zhouzone/persona-evals`

## 快速结论

| 指标 | 数值 |
| --- | ---: |
| 选中模型 | 39 |
| 完整计分模型 | 23 |
| API / parse error | 11 |
| 链路异常后移除 | 5 |
| 覆盖供应商 | 11 |
| 每个模型题量 | 95 |

### 1. 随机化选项后，MBTI-style 不再全塌成 ESTJ

早期固定标签版本明显过度产出 `ESTJ`。随机化展示选项后，完整批次变得更分散：

| MBTI-style label | Count |
| --- | ---: |
| ESTJ | 10 |
| ESFJ | 8 |
| ESFP | 3 |
| ESTP | 2 |

更保守的解释不是“所有 LLM 都是 ESTJ”，而是：

> 在 assistant 行为语境下，很多模型偏向外向、具体、组织化的选项，但不同模型家族仍然有差异。

### 2. SBTI-style 仍然高度集中到 BOSS

| SBTI-style label | Count |
| --- | ---: |
| BOSS | 22 |
| DIOR | 1 |

这是第一版最有传播点的信号：即使展示选项被随机打乱，绝大多数完成模型仍然选择了更稳定、自洽、边界清晰、执行导向的行为选项。

这说明 SBTI-style 的集中不只是 `A` 选项偏置，更可能来自 assistant 默认行为规范和题目语义本身。

### 3. 随机标签降低了位置偏置，但没有消掉语义偏置

| Choice space | A | B | C |
| --- | ---: | ---: | ---: |
| 模型看到的展示标签 | 1051 | 917 | 217 |
| remap 后的原始计分标签 | 1430 | 707 | 48 |

展示层面的 `A/B` 已经更接近，但回到原始计分标签后仍然明显倾斜。模型不是简单地“狂按 A”，而是在偏好某类被编码到题目里的行为。

## 完整结果

| Provider | Model | MBTI-style | SBTI-style |
| --- | --- | --- | --- |
| OpenAI | `gpt-5.4` | ESTJ | BOSS |
| OpenAI | `gpt-5.4-mini` | ESTJ | BOSS |
| OpenAI | `gpt-4o-mini` | ESFP | BOSS |
| Anthropic | `claude-opus-4-6` | ESTJ | BOSS |
| Anthropic | `claude-sonnet-4-6` | ESTJ | BOSS |
| Anthropic | `claude-haiku-4-5-20251001` | ESTJ | BOSS |
| Qwen | `qwen3.6-plus` | ESTJ | BOSS |
| Qwen | `qwen3-max` | ESTJ | BOSS |
| DeepSeek | `deepseek-v3.2` | ESTP | BOSS |
| DeepSeek | `deepseek-r1` | ESFP | BOSS |
| ByteDance | `doubao-seed-2-0-mini-260215` | ESFP | BOSS |
| Moonshot | `kimi-latest` | ESFJ | BOSS |
| xAI | `grok-4` | ESTJ | BOSS |
| xAI | `grok-4-fast-non-reasoning` | ESTJ | BOSS |
| xAI | `grok-4-fast-reasoning` | ESTJ | BOSS |
| Zhipu | `glm-5` | ESFJ | BOSS |
| Meta | `meta-llama/llama-4-maverick` | ESFJ | BOSS |
| Meta | `meta-llama/llama-4-scout` | ESTP | BOSS |
| Meta | `meta-llama/llama-3.3-70b-instruct` | ESFJ | BOSS |
| Mistral | `mistralai/mistral-large-2512` | ESFJ | BOSS |
| Mistral | `mistralai/mistral-medium-3.1` | ESFJ | BOSS |
| Mistral | `mistralai/mistral-small-3.1-24b-instruct` | ESFJ | BOSS |
| Other CN | `inclusionAI/Ling-flash-2.0` | ESFJ | DIOR |

## 这是什么

Persona Evals 是一个开源评测 harness，目前包含：

- 95 道强制选择题
- 64 道 MBTI-style 题，`E/I`、`S/N`、`T/F`、`J/P` 各 16 道
- 31 道 SBTI-style 题，覆盖 15 个行为维度
- 每题要求模型返回 JSON
- 每个模型一份完整 trace
- 每个模型一份 scored summary

题目不是直接问“你是什么人格”，而是改写成 AI assistant / agent 在压力、模糊、失败、证据不足、边界冲突等场景下的行为选择。模型在答题时不会看到 MBTI 或 SBTI 标签。

示例输出格式：

```json
{"choice":"A","confidence":0.0,"brief_reason":"one sentence"}
```

## 这不是什么

这不是官方 MBTI 测试，也不隶属于 The Myers Briggs Company、MBTI 商标权利方或 `sbti.one`。

这里的 MBTI-style / SBTI-style 标签只用于描述模型行为倾向，不是临床、心理学或官方人格测评。

## 如何复现

验证题库：

```bash
python -m ai_personality_eval.runner --list-pack
python -m ai_personality_eval.validate_pack
```

运行一个 OpenAI-compatible 模型：

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-gateway/v1"
export OPENAI_API_KEY="replace_with_your_key"

python -m ai_personality_eval.runner \
  --model gpt-4o-mini \
  --output-dir runs/personality-eval
```

批量运行：

```bash
python -m ai_personality_eval.runner \
  --models "gpt-5.4,gpt-4o-mini,claude-sonnet-4-6" \
  --output-dir runs/personality-eval \
  --continue-on-error
```

输出文件：

```text
runs/personality-eval/<run-stamp>/<model>-<run-id>.json
runs/personality-eval/<run-stamp>/summary.jsonl
```

## 静态网站

网站是纯静态文件：

```text
web/
  index.html
  app.js
  styles.css
  data/results.json
```

本地预览：

```bash
python -m http.server 5176 --directory web
```

打开：

```text
http://127.0.0.1:5176/
```

GitHub Pages 手动设置：

```text
Settings -> Pages -> Build and deployment -> Source -> GitHub Actions
```

设置后 push 到 `main` 会触发 `.github/workflows/pages.yml`，并把 `web/` 目录部署出去。

公开结果只读取：

```text
web/data/results.json
```

更新结果时，只把 `status: "ok"` 的完整 trace 放进 `runs`。失败、停止、链路异常的模型应该留在 `diagnostics.errors` 或 `diagnostics.dropped`，不要混进公开 leaderboard。

## 仓库结构

```text
ai_personality_eval/        runner, scoring, validation, and test pack loader
ai_personality_eval/data/   95-item v0.1 pack
configs/                   selected Boyue model lists and rjob manifests
jobs/                      PJLab rjob scripts
tests/                     unit tests for pack shape, scoring, runner, web data
web/                       static launch site
```

## 测试

```bash
python -m unittest discover -s tests
node --check web/app.js
python -m ai_personality_eval.validate_pack
bash -n jobs/run_boyue_personality_eval.sh
python -m json.tool web/data/results.json
```

## 小红书一句话

> 我们随机化了选项标签来降低 A/B/C 偏置。结果 MBTI 不再全是 ESTJ，但 SBTI 仍然 22/23 个完成模型都是 BOSS。这说明问题不只是选项位置偏置，而是 LLM 默认 assistant persona 本身就偏稳定、边界、执行和自洽。

## English Summary

Persona Evals is an open-source MBTI-style and SBTI-style probe suite for LLM and agent behavior. The launch batch evaluates 39 selected model routes, publishes 23 complete scored traces, and randomizes displayed option labels before remapping them back to scoring labels. MBTI-style results diversify after randomization, while SBTI-style results still collapse strongly into BOSS behavior.

## License

MIT
