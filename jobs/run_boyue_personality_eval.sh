#!/bin/bash
# Submit this script with rjob on a CPU networked node.
# It validates the test pack before spending paid gateway calls.

set -eo pipefail

CONDA_BASE="/mnt/shared-storage-user/sciprismax/zhouzhiwang/conda/miniconda3"
export PATH="${CONDA_BASE}/bin:/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/usr/local/nvidia/lib64:/usr/local/nvidia/lib:${LD_LIBRARY_PATH:-}"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY 2>/dev/null || true

# Conda activate scripts in this image reference optional variables such as
# ADDR2LINE, so nounset must stay disabled until activation is complete.
set +u
eval "$("${CONDA_BASE}/bin/conda" shell.bash hook)"
conda activate nanobot
set -u

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY 2>/dev/null || true

PROJECT_DIR="/mnt/shared-storage-gpfs2/sciprismax2/zzw/project/ai-personality-eval"
cd "$PROJECT_DIR"

RUN_LABEL="${EVAL_RUN_LABEL:-job${RANDOM}}"
RUN_LABEL="${RUN_LABEL//[^A-Za-z0-9_.-]/-}"
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_${RUN_LABEL}"
LOG_DIR="$PROJECT_DIR/logs"
OUT_DIR="$PROJECT_DIR/runs/personality-eval/$RUN_STAMP"
mkdir -p "$LOG_DIR" "$OUT_DIR"
LOG_FILE="$LOG_DIR/rjob_boyue_personality_eval_${RUN_STAMP}.log"
exec > >(tee "$LOG_FILE") 2>&1

echo "started_at=$(date -Is)"
echo "host=$(hostname)"
echo "project_dir=$PROJECT_DIR"
echo "output_dir=$OUT_DIR"

python -m ai_personality_eval.validate_pack

unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy 2>/dev/null || true
source <(curl -sSL http://deploy.i.h.pjlab.org.cn/infra/scripts/setup_proxy.sh)

set -a
source /mnt/shared-storage-gpfs2/sciprismax2/zhouzhiwang/docs/platform/model-access/model-access.env.sh
set +a

export OPENAI_BASE_URL="$BOYUE_PRIMARY_BASE_URL"
export OPENAI_API_KEY="$BOYUE_API_KEY"
export MODEL_ACCESS_MAX_RETRIES="${MODEL_ACCESS_MAX_RETRIES:-3}"
export MODEL_ACCESS_RETRY_BACKOFF_SECONDS="${MODEL_ACCESS_RETRY_BACKOFF_SECONDS:-2}"
export MODEL_ACCESS_TIMEOUT_SECONDS="${MODEL_ACCESS_TIMEOUT_SECONDS:-120}"
export EVAL_ITEM_PARSE_RETRIES="${EVAL_ITEM_PARSE_RETRIES:-2}"
export EVAL_PROGRESS_EVERY="${EVAL_PROGRESS_EVERY:-10}"

MODELS="${EVAL_MODELS:-$BOYUE_MODEL_GPT_54,$BOYUE_MODEL_GPT_4O_MINI,$BOYUE_MODEL_CLAUDE_OPUS_46,$BOYUE_MODEL_QWEN35_PLUS,$BOYUE_MODEL_MINIMAX_M27,$BOYUE_MODEL_DEEPSEEK_V32,$BOYUE_MODEL_GROK4,$BOYUE_MODEL_KIMI25}"

echo "base_url=$OPENAI_BASE_URL"
echo "models=$MODELS"

python -m ai_personality_eval.runner \
  --models "$MODELS" \
  --output-dir "$OUT_DIR" \
  --temperature "${EVAL_TEMPERATURE:-0.2}" \
  --max-tokens "${EVAL_MAX_TOKENS:-512}" \
  --timeout "$MODEL_ACCESS_TIMEOUT_SECONDS" \
  --max-retries "$MODEL_ACCESS_MAX_RETRIES" \
  --retry-backoff "$MODEL_ACCESS_RETRY_BACKOFF_SECONDS" \
  --item-parse-retries "$EVAL_ITEM_PARSE_RETRIES" \
  --progress-every "$EVAL_PROGRESS_EVERY" \
  --continue-on-error

echo "finished_at=$(date -Is)"
echo "summary=$OUT_DIR/summary.jsonl"
