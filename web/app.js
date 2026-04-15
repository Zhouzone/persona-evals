const axisOrder = ["E_I", "S_N", "T_F", "J_P"];

const nodes = {
  themeToggle: document.querySelector("#theme-toggle"),
  themeLabel: document.querySelector("#theme-label"),
  themeIcon: document.querySelector(".theme-icon"),
  scanSummary: document.querySelector("#scan-summary"),
  personaMap: document.querySelector("#persona-map"),
  providerGrid: document.querySelector("#provider-grid"),
  findingSnapshot: document.querySelector("#finding-snapshot"),
  resultCount: document.querySelector("#result-count"),
  resultSearch: document.querySelector("#result-search"),
  searchHints: document.querySelector("#search-hints"),
  filterBar: document.querySelector("#filter-bar"),
  leaderboardBody: document.querySelector("#leaderboard-body"),
  modelCards: document.querySelector("#model-cards"),
  conclusionList: document.querySelector("#conclusion-list"),
};

const state = {
  data: null,
  filter: "all",
  query: "",
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
  if (nodes.themeIcon) nodes.themeIcon.textContent = theme === "dark" ? "亮" : "夜";
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

function initSearch() {
  nodes.resultSearch?.addEventListener("input", (event) => {
    state.query = event.target.value;
    updateResultViews();
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

function publishedRuns(data) {
  return (data.runs || []).filter((run) => run.status === "ok");
}

function sortedRuns(data) {
  return publishedRuns(data).sort((a, b) => {
    const byProvider = text(a.providerGroup).localeCompare(text(b.providerGroup));
    return byProvider || text(a.displayName).localeCompare(text(b.displayName));
  });
}

function axisSignature(run) {
  if (!run.axes) return "暂无可复核记录";
  return axisOrder.map((key) => run.axes[key]?.chosen || "?").join("");
}

function profileLabel(run, key) {
  if (run.status !== "ok") return "暂无可复核记录";
  return text(run[key], "暂无可复核记录");
}

function renderScanSummary(data) {
  const runs = publishedRuns(data);
  const providers = new Set(runs.map((run) => run.providerGroup).filter(Boolean)).size;
  const dominantMbti = countValues(runs, "mbtiType")[0]?.[0] || "待定";
  const dominantSbti = countValues(runs, "sbtiType")[0]?.[0] || "待定";
  const metrics = [
    ["模型数", runs.length],
    ["来源数", providers],
    ["题库规模", data.pack.totalItems],
    ["MBTI 主峰", dominantMbti],
    ["SBTI 主峰", dominantSbti],
    ["选项顺序", "已打乱"],
  ];

  nodes.scanSummary.replaceChildren(
    ...metrics.map(([label, value]) => {
      const item = document.createElement("div");
      const labelNode = document.createElement("span");
      const valueNode = document.createElement("strong");
      item.className = "scan-tile";
      labelNode.textContent = label;
      valueNode.textContent = value;
      item.replaceChildren(labelNode, valueNode);
      return item;
    }),
  );
}

function typeShare(runs, key, value) {
  if (!runs.length) return 0;
  return runs.filter((run) => run[key] === value).length / runs.length;
}

function typeShareLabel(runs, key, value) {
  if (!value || !runs.length) return "0%";
  return pct(typeShare(runs, key, value));
}

function renderPersonaMap(data) {
  const runs = publishedRuns(data);
  const mbtiCounts = countValues(runs, "mbtiType");
  const sbtiCounts = countValues(runs, "sbtiType");
  const maxMbti = Math.max(...mbtiCounts.map(([, count]) => count), 1);
  const dominantMbti = mbtiCounts[0]?.[0] || "待定";
  const dominantSbti = sbtiCounts[0]?.[0] || "待定";

  nodes.personaMap.innerHTML = `
    <div class="map-topline">
      <span>人格图谱</span>
      <strong>${escapeHtml(dominantMbti)} / ${escapeHtml(dominantSbti)}</strong>
    </div>
    <div class="map-focus">
      <div>
        <span>MBTI 主峰</span>
        <strong>${escapeHtml(dominantMbti)}</strong>
        <p>${Math.round(typeShare(runs, "mbtiType", dominantMbti) * 100)}% 模型落在这里</p>
      </div>
      <div>
        <span>SBTI 主峰</span>
        <strong>${escapeHtml(dominantSbti)}</strong>
        <p>${Math.round(typeShare(runs, "sbtiType", dominantSbti) * 100)}% 模型落在这里</p>
      </div>
    </div>
    <div class="map-bars">
      ${mbtiCounts
        .map(
          ([label, count]) => `
            <div class="map-bar">
              <div class="map-bar-label"><span>${escapeHtml(label)}</span><strong>${count}</strong></div>
              <i style="width: ${pct(count / maxMbti)}"></i>
            </div>
          `,
        )
        .join("")}
    </div>
    <div class="map-footnote">选项已随机化，标签由同一套映射规则得到。</div>
  `;
}

function providerStats(runs) {
  const groups = new Map();
  runs.forEach((run) => {
    const key = text(run.providerGroup, "unknown");
    if (!groups.has(key)) {
      groups.set(key, { providerGroup: key, total: 0 });
    }
    groups.get(key).total += 1;
  });
  return [...groups.values()].sort((a, b) => b.total - a.total || providerLabel(a.providerGroup).localeCompare(providerLabel(b.providerGroup)));
}

function renderProviderCoverage(data) {
  const groups = providerStats(publishedRuns(data));
  const maxCount = Math.max(...groups.map((group) => group.total), 1);
  nodes.providerGrid.replaceChildren(
    ...groups.map((group) => {
      const item = document.createElement("article");
      item.className = "provider-card";
      item.innerHTML = `
        <div class="provider-topline">
          <span>${escapeHtml(providerLabel(group.providerGroup))}</span>
          <strong>${group.total}</strong>
        </div>
        <div class="provider-track" aria-label="${escapeHtml(providerLabel(group.providerGroup))} ${group.total} 个模型">
          <i style="width: ${pct(group.total / maxCount)}"></i>
        </div>
        <p>${group.total} 个模型样本</p>
      `;
      return item;
    }),
  );
}

function renderAxisBars(run) {
  if (!run.axes) {
    return `<span class="axis-empty">${escapeHtml("暂无可复核记录")}</span>`;
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
          <em class="axis-percent">${width}</em>
        </div>
      `;
    })
    .join("");
}

function countValues(runs, key) {
  const counts = new Map();
  runs.forEach((run) => {
    const value = run[key];
    if (value) counts.set(value, (counts.get(value) || 0) + 1);
  });
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

function renderFilters(data) {
  const runs = publishedRuns(data);
  const providerPriority = ["openai", "anthropic", "qwen", "deepseek", "xai", "meta", "mistral"];
  const availableProviders = new Set(runs.map((run) => run.providerGroup));
  const filters = [
    { label: "全部", value: "all", count: runs.length },
    ...providerPriority
      .filter((provider) => availableProviders.has(provider))
      .map((provider) => ({
        label: providerLabel(provider),
        value: `provider:${provider}`,
        count: runs.filter((run) => run.providerGroup === provider).length,
      })),
    ...countValues(runs, "mbtiType")
      .slice(0, 4)
      .map(([label, count]) => ({ label, value: `mbti:${label}`, count })),
    ...countValues(runs, "sbtiType")
      .slice(0, 3)
      .map(([label, count]) => ({ label, value: `sbti:${label}`, count })),
  ];

  nodes.filterBar.replaceChildren(
    ...filters.map((filter) => {
      const button = document.createElement("button");
      button.className = filter.value === state.filter ? "filter-chip active" : "filter-chip";
      button.type = "button";
      button.dataset.filter = filter.value;
      button.textContent = `${filter.label} ${filter.count}`;
      button.addEventListener("click", () => {
        state.filter = filter.value;
        renderFilters(data);
        updateResultViews();
      });
      return button;
    }),
  );
}

function renderSearchHints(data) {
  const runs = publishedRuns(data);
  const providerHints = ["OpenAI", "Anthropic", "Qwen", "DeepSeek"].filter((label) =>
    runs.some((run) => providerLabel(run.providerGroup) === label),
  );
  const typeHints = [
    ...countValues(runs, "mbtiType").slice(0, 3).map(([label]) => label),
    ...countValues(runs, "sbtiType").slice(0, 2).map(([label]) => label),
  ];
  const modelHints = runs
    .filter((run) => ["gpt-5.4", "claude-sonnet-4-6", "deepseek-v3.2"].includes(run.model))
    .map((run) => text(run.displayName, run.model));
  const hints = [...providerHints, ...typeHints, ...modelHints].slice(0, 10);

  nodes.searchHints.replaceChildren(
    ...hints.map((hint) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hint-chip";
      button.textContent = hint;
      button.addEventListener("click", () => {
        state.query = hint;
        if (nodes.resultSearch) nodes.resultSearch.value = hint;
        updateResultViews();
      });
      return button;
    }),
  );
}

function filterMatches(run) {
  if (state.filter === "all") return true;
  const [kind, value] = state.filter.split(":");
  if (kind === "provider") return run.providerGroup === value;
  if (kind === "mbti") return run.mbtiType === value;
  if (kind === "sbti") return run.sbtiType === value;
  return true;
}

function searchMatches(run) {
  const query = state.query.trim().toLowerCase();
  if (!query) return true;
  const searchable = [
    run.displayName,
    run.model,
    providerLabel(run.providerGroup),
    run.mbtiType,
    run.sbtiType,
    axisSignature(run),
  ]
    .map((value) => text(value, "").toLowerCase())
    .join(" ");
  return searchable.includes(query);
}

function visibleRuns() {
  return sortedRuns(state.data).filter((run) => filterMatches(run) && searchMatches(run));
}

function renderLeaderboardRows(rows, total) {
  nodes.resultCount.textContent = `显示 ${rows.length} / ${total} 个模型`;
  if (!rows.length) {
    nodes.leaderboardBody.innerHTML = `
      <tr>
        <td class="result-empty" colspan="5">没有匹配的模型，换一个关键词或筛选标签试试。</td>
      </tr>
    `;
    return;
  }

  nodes.leaderboardBody.replaceChildren(
    ...rows.map((run) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><strong>${escapeHtml(text(run.displayName, run.model))}</strong><span>${escapeHtml(run.model)}</span></td>
        <td>${escapeHtml(providerLabel(run.providerGroup))}</td>
        <td><mark class="type-pill">${escapeHtml(profileLabel(run, "mbtiType"))}</mark></td>
        <td><mark class="type-pill muted">${escapeHtml(profileLabel(run, "sbtiType"))}</mark></td>
        <td><code>${escapeHtml(axisSignature(run))}</code></td>
      `;
      return row;
    }),
  );
}

function renderCardsRows(rows, allRows) {
  if (!rows.length) {
    nodes.modelCards.innerHTML = `<div class="result-empty card-empty">没有匹配的模型。</div>`;
    return;
  }

  nodes.modelCards.replaceChildren(
    ...rows.map((run) => {
      const card = document.createElement("article");
      card.className = "model-card";
      card.innerHTML = `
        <div class="card-topline">
          <span>${escapeHtml(providerLabel(run.providerGroup))}</span>
          <code>${escapeHtml(axisSignature(run))}</code>
        </div>
        <p class="model-name">${escapeHtml(text(run.displayName, run.model))}</p>
        <div class="profile-badges">
          <mark class="type-pill">
            ${escapeHtml(profileLabel(run, "mbtiType"))}
            <span class="type-share">${escapeHtml(typeShareLabel(allRows, "mbtiType", run.mbtiType))}</span>
          </mark>
          <mark class="type-pill muted">
            ${escapeHtml(profileLabel(run, "sbtiType"))}
            <span class="type-share">${escapeHtml(typeShareLabel(allRows, "sbtiType", run.sbtiType))}</span>
          </mark>
        </div>
        <div class="axis-stack">${renderAxisBars(run)}</div>
      `;
      return card;
    }),
  );
}

function updateResultViews() {
  if (!state.data) return;
  const allRows = publishedRuns(state.data);
  const total = allRows.length;
  const rows = visibleRuns();
  renderLeaderboardRows(rows, total);
  renderCardsRows(rows, allRows);
}

function findingStats(data) {
  const runs = publishedRuns(data);
  const mbtiCounts = countValues(runs, "mbtiType");
  const sbtiCounts = countValues(runs, "sbtiType");
  const dominantMbti = mbtiCounts[0] || ["待定", 0];
  const dominantSbti = sbtiCounts[0] || ["待定", 0];
  const providers = new Set(runs.map((run) => run.providerGroup).filter(Boolean)).size;
  return { runs, mbtiCounts, sbtiCounts, dominantMbti, dominantSbti, providers };
}

function renderFindingSnapshot(data) {
  const { runs, dominantMbti, dominantSbti, providers } = findingStats(data);
  const nonDominantMbtiShare = 1 - typeShare(runs, "mbtiType", dominantMbti[0]);
  nodes.findingSnapshot.innerHTML = `
    <div class="snapshot-main">
      <span>SBTI 主峰</span>
      <strong>${escapeHtml(dominantSbti[0])}</strong>
      <em>${escapeHtml(typeShareLabel(runs, "sbtiType", dominantSbti[0]))} 模型落在这里</em>
    </div>
    <div class="snapshot-mini">
      <span>MBTI 主峰</span>
      <strong>${escapeHtml(dominantMbti[0])}</strong>
      <em>${escapeHtml(typeShareLabel(runs, "mbtiType", dominantMbti[0]))} 模型落在这里</em>
    </div>
    <div class="snapshot-mini">
      <span>非 ${escapeHtml(dominantMbti[0])}</span>
      <strong>${escapeHtml(pct(nonDominantMbtiShare))}</strong>
      <em>${providers} 类来源共同构成样本</em>
    </div>
  `;
}

function buildFindingItems(data) {
  const { runs, mbtiCounts, dominantMbti, dominantSbti, providers } = findingStats(data);
  const secondaryMbti = mbtiCounts
    .slice(1)
    .map(([label]) => label)
    .join("、");

  return [
    {
      value: `${mbtiCounts.length} 种`,
      title: "MBTI-style 不是一刀切",
      body: `选项随机化后，${dominantMbti[0]} 仍是当前主峰，占 ${pct(dominantMbti[1] / Math.max(runs.length, 1))}；${secondaryMbti ? `同时还能看到 ${secondaryMbti}` : "但仍有其它低频标签"}。`,
    },
    {
      value: pct(dominantSbti[1] / Math.max(runs.length, 1)),
      title: "SBTI-style 几乎同频",
      body: `${dominantSbti[0]} 占比最高，说明很多模型默认会选择更稳定、负责、边界清晰的回答方式。`,
    },
    {
      value: pct(1 - dominantMbti[1] / Math.max(runs.length, 1)),
      title: `非 ${dominantMbti[0]} 模型并不少`,
      body: `ESFJ、ESFP、ESTP 这类结果稳定出现，说明模型默认行为不是简单复制同一种助手模板。`,
    },
    {
      value: `${providers} 类`,
      title: "来源覆盖支撑横向比较",
      body: `${runs.length} 个可计分模型覆盖 ${providers} 类来源，这个分布不是单一厂商或单一路线的结果。`,
    },
  ];
}

function renderFindingItems(data) {
  const conclusions = buildFindingItems(data);
  nodes.conclusionList.replaceChildren(
    ...conclusions.map((item, index) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="finding-index">${String(index + 1).padStart(2, "0")}</span>
        <div class="finding-copy">
          <em class="finding-value">${escapeHtml(item.value)}</em>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.body)}</p>
        </div>
      `;
      return li;
    }),
  );
}

function renderError(error) {
  nodes.scanSummary.innerHTML = `
    <div class="scan-tile error-card">
      <span>数据加载失败</span>
      <strong>${escapeHtml(error.message)}</strong>
    </div>
  `;
  nodes.resultCount.textContent = "数据暂时没有加载出来。";
}

initTheme();
initSearch();

loadResults()
  .then((data) => {
    state.data = data;
    renderScanSummary(data);
    renderPersonaMap(data);
    renderProviderCoverage(data);
    renderFindingSnapshot(data);
    renderFindingItems(data);
    renderSearchHints(data);
    renderFilters(data);
    updateResultViews();
  })
  .catch(renderError);
