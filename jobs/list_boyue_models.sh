#!/bin/bash
# Query the Boyue OpenAI-compatible /models endpoint without printing secrets.

set -eo pipefail

CONDA_BASE="/mnt/shared-storage-user/sciprismax/zhouzhiwang/conda/miniconda3"
export PATH="${CONDA_BASE}/bin:/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export LD_LIBRARY_PATH="/usr/local/nvidia/lib64:/usr/local/nvidia/lib:${LD_LIBRARY_PATH:-}"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY 2>/dev/null || true

set +u
eval "$("${CONDA_BASE}/bin/conda" shell.bash hook)"
conda activate nanobot
set -u

PROJECT_DIR="/mnt/shared-storage-gpfs2/sciprismax2/zzw/project/ai-personality-eval"
cd "$PROJECT_DIR"

RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/rjob_boyue_model_list_${RUN_STAMP}.log"
JSON_FILE="$LOG_DIR/boyue_models_${RUN_STAMP}.json"
TXT_FILE="$LOG_DIR/boyue_models_${RUN_STAMP}.txt"
exec > >(tee "$LOG_FILE") 2>&1

echo "started_at=$(date -Is)"
echo "host=$(hostname)"
echo "project_dir=$PROJECT_DIR"

unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy 2>/dev/null || true
source <(curl -sSL http://deploy.i.h.pjlab.org.cn/infra/scripts/setup_proxy.sh)

set -a
source /mnt/shared-storage-gpfs2/sciprismax2/zhouzhiwang/docs/platform/model-access/model-access.env.sh
set +a

export OPENAI_BASE_URL="${BOYUE_PRIMARY_BASE_URL}"
export OPENAI_API_KEY="${BOYUE_API_KEY}"

python - "$JSON_FILE" "$TXT_FILE" <<'PY'
import json
import os
import sys
import urllib.request

json_file, txt_file = sys.argv[1:3]
base_url = os.environ["OPENAI_BASE_URL"].rstrip("/")
api_key = os.environ["OPENAI_API_KEY"]
request = urllib.request.Request(
    f"{base_url}/models",
    method="GET",
    headers={"Authorization": f"Bearer {api_key}"},
)

with urllib.request.urlopen(request, timeout=120) as response:
    payload = json.loads(response.read().decode("utf-8"))

models = payload.get("data", payload if isinstance(payload, list) else [])
ids = []
for item in models:
    if isinstance(item, dict) and item.get("id"):
        ids.append(str(item["id"]))
    elif isinstance(item, str):
        ids.append(item)

ids = sorted(set(ids), key=str.lower)
with open(json_file, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
with open(txt_file, "w", encoding="utf-8") as handle:
    for model_id in ids:
        handle.write(model_id + "\n")

print(f"model_count={len(ids)}")
print(f"json_file={json_file}")
print(f"txt_file={txt_file}")
for model_id in ids[:300]:
    print(model_id)
if len(ids) > 300:
    print(f"... truncated {len(ids) - 300} more model ids")
PY

echo "finished_at=$(date -Is)"
