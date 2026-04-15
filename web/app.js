const axisOrder = ["E_I", "S_N", "T_F", "J_P"];
const statusRank = { ok: 0, error: 1, skipped: 2 };

const nodes = {
  batchLabel: document.querySelector("#batch-label"),
  packVersion: document.querySelector("#pack-version"),
  themeToggle: document.querySelector("#theme-toggle"),
  themeLabel: document.querySelector("#theme-label"),
  themeIcon: document.querySelector(".theme-icon"),
  metricGrid: document.querySelector("#metric-grid"),
  providerGrid: document.querySelector("#provider-grid"),
  resultCount: document.querySelector("#result-count"),
  leaderboardBody: document.querySelector("#leaderboard-body"),
  modelCards: document.querySelector("#model-cards"),
  conclusionList: document.querySelector("#conclusion-list"),
  refinementList: document.querySelector("#refinement-list"),
  systemPrompt: document.querySelector("#system-prompt"),
  userPrompt: document.querySelector("#user-prompt"),
};

const THEME_STORAGE_KEY = "persona-evals-theme";

function getInitialTheme() {
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  if (nodes.themeLabel) nodes.themeLabel.textContent = theme === "dark" ? "日间" : "夜间";
  if (nodes.themeIcon) nodes.themeIcon.textContent = theme === "dark" ? "☼" : "☾";
  if (nodes.themeToggle) {
    nodes.themeToggle.setAttribute("aria-label", theme === "dark" ? "切换到日间主题" : "切换到夜间主题");
  }
}

function initTheme() {
  setTheme(document.documentElement.dataset.theme || getInitialTheme());
  nodes.themeToggle?.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(next);
  });
}

async function loadResults() {
  const response = await fetch("./data/results.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`data/results.json returned ${response.status}`);
  }
  return response.json();
}

function text(value, fallback = "待定") {
  return value === undefined || value === null || value === "" ? fallback : String(value);
}

function escapeHtml(value) {
  return text(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function pct(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function providerLabel(providerGroup) {
  const labels = {
    openai: "OpenAI",
    anthropic: "Anthropic",
    google: "Google",
    qwen: "Qwen",
    deepseek: "DeepSeek",
    bytedance: "ByteDance",
    minimax: "MiniMax",
    moonshot: "Moonshot",
    xai: "xAI",
    zhipu: "Zhipu",
    meta: "Meta",
    mistral: "Mistral",
    other_cn: "Other CN",
  };
  return labels[providerGroup] || text(providerGroup, "unknown");
}

function labelModeText(value) {
  if (value === "randomized") return "随机选项";
  return text(value);
}

function statusLabel(run) {
  if (run.status === "ok") return "已计分";
  if (run.status === "error") return "运行失败";
  return "已停止";
}

function publishedRuns(data) {
  return (data.runs || []).filter((run) => run.status === "ok");
}

function axisSignature(run) {
  if (!run.axes) return "无完整 trace";
  return axisOrder.map((key) => run.axes[key]?.chosen || "?").join("");
}

function profileLabel(run, key) {
  if (run.status !== "ok") return "无完整 trace";
  return text(run[key], "无完整 trace");
}

function runNote(run) {
  if (run.status === "ok") return skillNameText(run.recommendedSkill);
  if (run.errorType) return `${run.errorType}: ${text(run.error, "无完整 trace")}`;
  return text(run.error, "无完整 trace");
}

function skillNameText(skill) {
  const labels = {
    evidence_before_victory: "先证据后胜利",
    boundary_first: "边界优先",
    calm_failure: "稳定处理失败",
    stop_loss_replan: "止损并重规划",
  };
  return labels[skill?.id] || text(skill?.name);
}

function skillPromptText(run) {
  const prompts = {
    evidence_before_victory: "在宣称成功前，先引用具体证据：测试结果、日志、可复现输出或已检查约束。证据不足时，明确不确定性并给出下一步最稳妥动作。",
    boundary_first: "当用户压力、任务目标或成功指标与系统规则或证据冲突时，先保住边界，再说明合规且安全的替代路径。",
    calm_failure: "遇到失败、低分或反复报错时，先稳定状态、复述已知事实，再缩小问题范围，避免为了挽回局面而过度迎合。",
    stop_loss_replan: "当当前路线证据不足或成本继续上升时，及时止损，说明放弃原因，并给出新的最小可验证计划。",
  };
  return prompts[run.recommendedSkill?.id] || run.recommendedSkill?.prompt;
}

function renderMetrics(data) {
  const runs = publishedRuns(data);
  const providers = new Set(runs.map((run) => run.providerGroup).filter(Boolean)).size;
  const mbtiTypes = new Set(runs.map((run) => run.mbtiType).filter(Boolean)).size;
  const sbtiTypes = new Set(runs.map((run) => run.sbtiType).filter(Boolean)).size;
  const metrics = [
    ["完成模型", runs.length],
    ["覆盖厂商", providers],
    ["题目数量", data.pack.totalItems],
    ["MBTI 类型", mbtiTypes],
    ["SBTI 类型", sbtiTypes],
    ["选项模式", labelModeText(data.optionLabelMode || "randomized")],
  ];

  nodes.metricGrid.replaceChildren(
    ...metrics.map(([label, value]) => {
      const item = document.createElement("div");
      const labelNode = document.createElement("span");
      const valueNode = document.createElement("strong");
      item.className = "metric-card";
      labelNode.textContent = label;
      valueNode.textContent = value;
      item.replaceChildren(labelNode, valueNode);
      return item;
    }),
  );
}

function providerStats(runs) {
  const groups = new Map();
  runs.forEach((run) => {
    const key = text(run.providerGroup, "unknown");
    if (!groups.has(key)) {
      groups.set(key, { providerGroup: key, total: 0, scored: 0, failed: 0, stopped: 0 });
    }
    const group = groups.get(key);
    group.total += 1;
    if (run.status === "ok") group.scored += 1;
    if (run.status === "error") group.failed += 1;
    if (run.status === "skipped") group.stopped += 1;
  });
  return [...groups.values()];
}

function renderProviderCoverage(data) {
  const groups = providerStats(publishedRuns(data));
  nodes.providerGrid.replaceChildren(
    ...groups.map((group) => {
      const rate = group.scored / Math.max(group.total, 1);
      const item = document.createElement("article");
      item.className = group.failed || group.stopped ? "provider-card has-failures" : "provider-card";
      item.innerHTML = `
        <div class="provider-topline">
          <span>${escapeHtml(providerLabel(group.providerGroup))}</span>
          <strong>${group.scored}/${group.total}</strong>
        </div>
        <div class="provider-track" aria-label="${escapeHtml(providerLabel(group.providerGroup))} ${group.scored} 条公开 trace，共 ${group.total} 条">
          <i style="width: ${pct(rate)}"></i>
        </div>
        <p>${group.scored} 条公开 trace</p>
      `;
      return item;
    }),
  );
}

function renderAxisBars(run) {
  if (!run.axes) {
    return `<span class="axis-empty">${escapeHtml(text(run.error, "无完整 trace"))}</span>`;
  }

  return axisOrder
    .map((key) => {
      const axis = run.axes[key];
      const width = pct(axis.score);
      const sideClass = axis.chosen === axis.right ? "right-win" : "left-win";
      return `
        <div class="axis-row ${sideClass}">
          <span>${escapeHtml(axis.left)}</span>
          <div class="axis-track" aria-label="${escapeHtml(axis.label)} ${escapeHtml(axis.chosen)} ${width}">
            <i style="width: ${width}"></i>
          </div>
          <span>${escapeHtml(axis.right)}</span>
          <strong>${escapeHtml(axis.chosen)}</strong>
        </div>
      `;
    })
    .join("");
}

function renderLeaderboard(data) {
  const rows = publishedRuns(data).sort((a, b) => {
    const byStatus = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
    const byProvider = text(a.providerGroup).localeCompare(text(b.providerGroup));
    return byStatus || byProvider || text(a.displayName).localeCompare(text(b.displayName));
  });

  nodes.resultCount.textContent = `${rows.length} 条已计分 trace`;
  nodes.leaderboardBody.replaceChildren(
    ...rows.map((run) => {
      const row = document.createElement("tr");
      row.className = `run-${run.status}`;
      row.innerHTML = `
        <td><strong>${escapeHtml(text(run.displayName, run.model))}</strong><span>${escapeHtml(run.model)}</span></td>
        <td>${escapeHtml(providerLabel(run.providerGroup))}</td>
        <td><mark class="status-pill ${escapeHtml(run.status)}">${escapeHtml(statusLabel(run))}</mark></td>
        <td>${escapeHtml(profileLabel(run, "mbtiType"))}</td>
        <td>${escapeHtml(profileLabel(run, "sbtiType"))}</td>
        <td><code>${escapeHtml(axisSignature(run))}</code></td>
        <td>${escapeHtml(runNote(run))}</td>
      `;
      return row;
    }),
  );
}

function renderCards(data) {
  const rows = publishedRuns(data).sort((a, b) => {
    const byStatus = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
    const byProvider = text(a.providerGroup).localeCompare(text(b.providerGroup));
    return byStatus || byProvider || text(a.displayName).localeCompare(text(b.displayName));
  });
  nodes.modelCards.replaceChildren(
    ...rows.map((run) => {
      const card = document.createElement("article");
      card.className = `model-card run-${run.status}`;
      card.innerHTML = `
        <div class="card-topline">
          <span>${escapeHtml(providerLabel(run.providerGroup))}</span>
          <mark class="status-pill ${escapeHtml(run.status)}">${escapeHtml(statusLabel(run))}</mark>
        </div>
        <p class="model-name">${escapeHtml(text(run.displayName, run.model))}</p>
        <h3>${escapeHtml(profileLabel(run, "mbtiType"))} / ${escapeHtml(profileLabel(run, "sbtiType"))}</h3>
        <div class="axis-stack">${renderAxisBars(run)}</div>
        <div class="skill-box">
          <span>${run.status === "ok" ? "干预提示词" : "运行备注"}</span>
          <p>${escapeHtml(text(skillPromptText(run), text(run.error, "暂无输出。")))}</p>
        </div>
        <p class="source-path">${escapeHtml(text(run.sourceSummary))}</p>
      `;
      return card;
    }),
  );
}

function renderConclusions(data) {
  const conclusions = data.conclusions || [];
  nodes.conclusionList.replaceChildren(
    ...conclusions.map((item) => {
      const li = document.createElement("li");
      const title = document.createElement("strong");
      const body = document.createElement("span");
      title.textContent = text(item.title);
      body.textContent = text(item.body);
      li.replaceChildren(title, body);
      return li;
    }),
  );
}

function renderMethod(data) {
  nodes.batchLabel.textContent = text(data.batchLabel, "批量评测");
  nodes.packVersion.textContent = `${data.pack.id} ${data.pack.version}`;
  nodes.refinementList.replaceChildren(
    ...data.pack.refinement.map((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      return li;
    }),
  );
  nodes.systemPrompt.textContent = data.pack.prompt.system;
  nodes.userPrompt.textContent = data.pack.prompt.userTemplate;
}

function renderError(error) {
  nodes.metricGrid.innerHTML = `
    <div class="metric-card error-card">
      <span>数据加载失败</span>
      <strong>${escapeHtml(error.message)}</strong>
    </div>
  `;
  nodes.resultCount.textContent = "请检查 web/data/results.json 后刷新。";
}

initTheme();

loadResults()
  .then((data) => {
    renderMetrics(data);
    renderProviderCoverage(data);
    renderLeaderboard(data);
    renderCards(data);
    renderConclusions(data);
    renderMethod(data);
  })
  .catch(renderError);
