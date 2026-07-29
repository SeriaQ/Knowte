const form = document.querySelector("#search-form");
const input = form.querySelector("input[name='keywords']");
const searchSubmitBtn = document.querySelector("#search-submit");
const savePlanBtn = document.querySelector("#save-plan");
const searchModeButtons = document.querySelectorAll("[data-search-mode]");
const searchModeHint = document.querySelector("#search-mode-hint");
const intelligentProgressEl = document.querySelector("#intelligent-progress");
const academicStagesEl = document.querySelector("#academic-stages");
const webStagesEl = document.querySelector("#web-stages");
const intelligentBudgetEl = document.querySelector("#intelligent-budget");
const intelligentExpandedEl = document.querySelector("#intelligent-expanded");
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const emailInput = document.querySelector("#email");
const s2KeyInput = document.querySelector("#s2-key");
const s2KeyRemoveBtn = document.querySelector("#s2-key-remove");
const s2KeyRemoveNote = document.querySelector("#s2-key-remove-note");
const searxngInput = document.querySelector("#searxng-url");
const webIgnoreYearFilterInput = document.querySelector("#web-ignore-year-filter");
const saveConfigBtn = document.querySelector("#save-config");
const configStatusEl = document.querySelector("#config-status");
const searxngStatusEl = document.querySelector("#managed-searxng-status");
const searxngSetupBtn = document.querySelector("#searxng-setup");
const searxngStartBtn = document.querySelector("#searxng-start");
const searxngUpdateBtn = document.querySelector("#searxng-update");
const searxngLogsBtn = document.querySelector("#searxng-logs");
const searxngRemoveBtn = document.querySelector("#searxng-remove");
const searxngRemoveCacheInput = document.querySelector("#searxng-remove-cache");
const searxngRemoveCacheOption = document.querySelector("#searxng-remove-cache-option");
const searxngLogOutput = document.querySelector("#searxng-log-output");
const searxngLogNote = document.querySelector("#searxng-log-note");
const backendGrid = document.querySelector("#backend-grid");
const maxPapersInput = document.querySelector("#max-papers");
const intelligentMaxResultsInput = document.querySelector("#intelligent-max-results");
const aiBaseUrlInput = document.querySelector("#ai-base-url");
const aiApiKeyInput = document.querySelector("#ai-api-key");
const aiApiKeyRemoveBtn = document.querySelector("#ai-api-key-remove");
const aiApiKeyRemoveNote = document.querySelector("#ai-api-key-remove-note");
const aiChatModelInput = document.querySelector("#ai-chat-model");
const aiEnableThinkingInput = document.querySelector("#ai-enable-thinking");
const aiEmbeddingModelInput = document.querySelector("#ai-embedding-model");
const aiEmbeddingSeparateInput = document.querySelector("#ai-embedding-separate");
const aiEmbeddingBaseUrlInput = document.querySelector("#ai-embedding-base-url");
const aiEmbeddingApiKeyInput = document.querySelector("#ai-embedding-api-key");
const aiEmbeddingApiKeyRemoveBtn = document.querySelector("#ai-embedding-api-key-remove");
const aiEmbeddingApiKeyRemoveNote = document.querySelector("#ai-embedding-api-key-remove-note");
const aiVerifyBatchSizeInput = document.querySelector("#ai-verify-batch-size");
const aiVerifyConcurrencyInput = document.querySelector("#ai-verify-concurrency");
const aiTimeoutInput = document.querySelector("#ai-timeout");
const usage5MinEl = document.querySelector("#usage-5min");
const usageDayEl = document.querySelector("#usage-day");
const usage5MinWebEl = document.querySelector("#usage-5min-web");
const usageDayWebEl = document.querySelector("#usage-day-web");
const usageDayAiChatEl = document.querySelector("#usage-day-ai-chat");
const usageDayAiChatTokensEl = document.querySelector("#usage-day-ai-chat-tokens");
const usageDayAiEmbeddingEl = document.querySelector("#usage-day-ai-embedding");
const usageDayAiEmbeddingTokensEl = document.querySelector("#usage-day-ai-embedding-tokens");
const usageBar5 = document.querySelector("#usage-bar-5min");
const usageBarDay = document.querySelector("#usage-bar-day");
const usageBar5Web = document.querySelector("#usage-bar-5min-web");
const usageBarDayWeb = document.querySelector("#usage-bar-day-web");
const selectedAreasEl = document.querySelector("#selected-areas");
const areaPresetsEl = document.querySelector("#area-presets");
const filtersEl = document.querySelector("#search-filters");
const filtersToggleBtn = document.querySelector("#filters-toggle");
const yearFromInput = document.querySelector("#year-from");
const yearToInput = document.querySelector("#year-to");
const clearTimeBtn = document.querySelector("#time-clear");
const resultsToolbar = document.querySelector("#results-toolbar");
const findMoreBtn = document.querySelector("#find-more");
const abstractToggleBtn = document.querySelector("#abstract-toggle");
const stopBtn = document.querySelector("#stop-search");
const resultsPager = document.querySelector("#results-pager");
const pageSelectTop = document.querySelector("#page-select-top");
const pagePrevTop = document.querySelector("#page-prev-top");
const pageNextTop = document.querySelector("#page-next-top");
const scrollTopBtn = document.querySelector("#scroll-top");
const navLinks = document.querySelectorAll(".side-link");
const panels = document.querySelectorAll(".panel-view");
const themeToggleBtn = document.querySelector("#theme-toggle");
const configTab = document.querySelector('[data-target="config-panel"]');
const plansTab = document.querySelector('[data-target="plans-panel"]');
const plansListEl = document.querySelector("#plans-list");
const plansStatusEl = document.querySelector("#plans-status");
const goToSearchBtn = document.querySelector("#go-to-search");
let currentUsage = {
  last_5_min: 0,
  last_day: 0,
  last_5_min_web: 0,
  last_day_web: 0,
  last_day_ai_chat: 0,
  last_day_ai_chat_tokens: 0,
  last_day_ai_embedding: 0,
  last_day_ai_embedding_tokens: 0,
};
const activePresets = new Set();
const pageSize = 20;
let configuredMaxPapers = 100;
let configuredIntelligentMaxResults = 20;
let activeLimit = 100;
let activeWebPages = 1;
let lastSearchHasWeb = false;
let lastSearchHasAcademic = false;
let canFindMoreWeb = false;
let lastQuery = "";
let lastAreas = "";
let lastYearFrom = "";
let lastYearTo = "";
let fullResults = [];
let isSearching = false;
let canFindMore = false;
let abstractsHidden = false;
let searchController = null;
let semanticscholarKeyConfigured = false;
let aiApiKeyConfigured = false;
let aiEmbeddingApiKeyConfigured = false;
let semanticscholarKeyRemovalPending = false;
let aiApiKeyRemovalPending = false;
let aiEmbeddingApiKeyRemovalPending = false;
let savedProfileState = null;
let configStatusTimer = null;
let searchMode = "keyword";
let savedPlans = [];
let intelligentRunToken = 0;
let lastBackends = [];
let planSourceOverride = null;
let isIntelligentSearching = false;
const DEFAULT_SEARXNG_URL = "http://127.0.0.1:8888/search";

const serializeProfileState = (overrides = {}) => JSON.stringify({
  email: overrides.email ?? emailInput.value.trim(),
  searxng_url: overrides.searxng_url ?? (searxngInput?.value.trim() || ""),
  max_papers: overrides.max_papers ?? parseMaxPapers(maxPapersInput.value || "100"),
  intelligent_max_results: overrides.intelligent_max_results
    ?? Number(intelligentMaxResultsInput.value || 20),
  enabled_backends: overrides.enabled_backends ?? Array.from(
    backendGrid.querySelectorAll("input[type='checkbox']:checked"),
  ).map((box) => box.value).sort(),
  api_key_update: s2KeyInput.value.trim(),
  api_key_clear: semanticscholarKeyRemovalPending,
  web_ignore_year_filter: Boolean(webIgnoreYearFilterInput?.checked),
  ai_base_url: overrides.ai_base_url ?? aiBaseUrlInput.value.trim(),
  ai_chat_model: overrides.ai_chat_model ?? aiChatModelInput.value.trim(),
  ai_embedding_model: overrides.ai_embedding_model ?? aiEmbeddingModelInput.value.trim(),
  ai_embedding_separate_connection: overrides.ai_embedding_separate_connection
    ?? Boolean(aiEmbeddingSeparateInput.open),
  ai_enable_thinking: overrides.ai_enable_thinking
    ?? Boolean(aiEnableThinkingInput.checked),
  ai_embedding_base_url: overrides.ai_embedding_base_url
    ?? aiEmbeddingBaseUrlInput.value.trim(),
  ai_verify_batch_size: overrides.ai_verify_batch_size
    ?? Number(aiVerifyBatchSizeInput.value || 5),
  ai_verify_concurrency: overrides.ai_verify_concurrency
    ?? Number(aiVerifyConcurrencyInput.value || 1),
  ai_timeout_seconds: overrides.ai_timeout_seconds
    ?? Number(aiTimeoutInput.value || 45),
  ai_api_key_update: aiApiKeyInput.value.trim(),
  ai_api_key_clear: aiApiKeyRemovalPending,
  ai_embedding_api_key_update: aiEmbeddingApiKeyInput.value.trim(),
  ai_embedding_api_key_clear: aiEmbeddingApiKeyRemovalPending,
});

const isConfigDirty = () => (
  savedProfileState !== null && serializeProfileState() !== savedProfileState
);

const updateProfileDirtyState = () => {
  if (savedProfileState === null || !configTab) return;
  const isDirty = isConfigDirty();
  configTab.classList.toggle("has-unsaved", isDirty);
  configTab.setAttribute("aria-label", isDirty ? "Config (unsaved changes)" : "Config");
  configTab.title = isDirty ? "Unsaved config changes" : "";
};

const setConfigStatus = (message, clearAfterMs = 0) => {
  if (configStatusTimer) window.clearTimeout(configStatusTimer);
  configStatusEl.textContent = message;
  if (clearAfterMs > 0) {
    configStatusTimer = window.setTimeout(() => {
      configStatusEl.textContent = "";
      configStatusTimer = null;
    }, clearAfterMs);
  }
};

const searxngActionButtons = [
  searxngSetupBtn,
  searxngStartBtn,
  searxngUpdateBtn,
  searxngLogsBtn,
  searxngRemoveBtn,
].filter(Boolean);

const renderSearxngStatus = (status) => {
  const state = status?.state || "error";
  const installed = Boolean(status?.installed);
  const running = Boolean(status?.running);
  searxngStatusEl.textContent = status?.message || "Could not inspect local Web Search.";
  searxngStatusEl.dataset.state = status?.healthy
    ? "running"
    : ["docker_not_installed", "docker_not_running", "container_name_conflict", "error"].includes(state)
      ? "error"
      : state;
  searxngSetupBtn.hidden = state !== "not_installed";
  searxngSetupBtn.disabled = state !== "not_installed";
  searxngStartBtn.hidden = !installed;
  searxngStartBtn.textContent = running ? "Stop" : "Start";
  searxngStartBtn.dataset.action = running ? "stop" : "start";
  searxngStartBtn.classList.toggle("managed-service-danger", running);
  searxngUpdateBtn.hidden = !installed;
  searxngLogsBtn.hidden = !installed;
  searxngRemoveBtn.hidden = !installed;
  if (searxngRemoveCacheOption) searxngRemoveCacheOption.hidden = !installed;
};

const fetchSearxngStatus = async () => {
  try {
    const response = await fetch("/api/searxng");
    const status = await response.json();
    renderSearxngStatus(status);
    return status;
  } catch (error) {
    const status = {
      state: "error",
      message: "Could not inspect local Web Search.",
    };
    renderSearxngStatus(status);
    return status;
  }
};

const searxngPhaseLabels = {
  queued: "Queued",
  checking: "Checking current state",
  pulling: "Downloading image",
  starting: "Starting container",
  health_check: "Checking service health",
  cleanup: "Cleaning up previous image",
  complete: "Complete",
  failed: "Failed",
};

const setSearxngLogVisible = (visible, note = "") => {
  searxngLogOutput.hidden = !visible;
  if (searxngLogNote) {
    searxngLogNote.textContent = note;
    searxngLogNote.hidden = !visible || !note;
  }
  if (searxngLogsBtn) {
    searxngLogsBtn.textContent = visible ? "Hide logs" : "View logs";
    searxngLogsBtn.setAttribute("aria-expanded", String(visible));
  }
};

const renderSearxngJob = (job) => {
  const phase = searxngPhaseLabels[job?.phase] || "Working";
  const elapsed = Number(job?.elapsed_seconds || 0).toFixed(1);
  searxngStatusEl.textContent = `${phase} · ${elapsed}s`;
  searxngStatusEl.dataset.state = job?.status === "failed" ? "error" : "";
  const lines = Array.isArray(job?.display_output)
    ? job.display_output
    : Array.isArray(job?.output) ? job.output : [];
  searxngLogOutput.textContent = [
    ...(job?.output_truncated ? ["[Earlier Docker output was truncated.]"] : []),
    ...lines,
  ].join("\n");
  setSearxngLogVisible(
    true,
    "Knowte stage messages are prefixed with [Knowte]. All other lines are Docker's unparsed output.",
  );
  searxngLogOutput.scrollTop = searxngLogOutput.scrollHeight;
};

const waitForSearxngJob = async (initialJob) => {
  let job = initialJob;
  while (job?.status === "running") {
    renderSearxngJob(job);
    await new Promise((resolve) => window.setTimeout(resolve, 500));
    const response = await fetch(`/api/searxng/job?id=${encodeURIComponent(job.job_id)}`);
    job = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(job.message || "Could not read the SearXNG task.");
    }
  }
  renderSearxngJob(job);
  if (job?.status === "failed") {
    throw new Error(job.message || "The SearXNG task failed.");
  }
  return job?.result || {};
};

const runSearxngAction = async (action, options = {}) => {
  const progressMessages = {
    setup: "Setting up local Web Search… The first image download may take a few minutes.",
    start: "Starting local Web Search…",
    update: "Checking for a newer SearXNG image…",
    stop: "Stopping local Web Search…",
    remove: "Removing the Knowte-managed service…",
    logs: "Loading SearXNG logs…",
  };
  searxngActionButtons.forEach((button) => {
    button.disabled = true;
  });
  searxngStatusEl.textContent = progressMessages[action] || "Working…";
  searxngStatusEl.dataset.state = "";
  try {
    const response = await fetch("/api/searxng", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...options }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.message || "Could not manage local Web Search.");
    }
    const finalResult = response.status === 202
      ? await waitForSearxngJob(result)
      : result;
    if (action === "logs") {
      searxngLogOutput.textContent = finalResult.logs || "No logs are available.";
      setSearxngLogVisible(
        true,
        finalResult.logs_note || `Showing the latest ${finalResult.logs_limit || 500} service log lines.`,
      );
    } else if (!["setup", "update"].includes(action)) {
      setSearxngLogVisible(false);
      if (action === "remove") {
        await fetchConfig();
      }
    }
    if (action === "setup") {
      await fetchConfig();
      if (finalResult.image_pull_status === "already_cached") {
        finalResult.message = "Local Web Search is running. Docker reused the image already stored on this machine.";
      } else if (finalResult.image_pull_status === "downloaded") {
        finalResult.message = "Local Web Search is running with the image Docker just downloaded.";
      }
    }
    if (action === "update") {
      if (finalResult.update_status === "up_to_date") {
        finalResult.message = "SearXNG is already current; the container was not recreated.";
      } else if (finalResult.update_status === "updated" && finalResult.old_image_removed) {
        finalResult.message = "SearXNG was updated and the previous image was removed.";
      } else if (finalResult.update_status === "updated") {
        finalResult.message = finalResult.old_image_retained_reason
          ? `SearXNG was updated. The previous image was retained: ${finalResult.old_image_retained_reason}`
          : "SearXNG was updated. No previous image needed removal.";
      }
    }
    if (action === "remove") {
      if (finalResult.image_cache_removed) {
        finalResult.message = "The managed service, configuration, and cached SearXNG image were removed.";
      } else if (finalResult.image_cache_requested) {
        finalResult.message = finalResult.image_cache_retained_reason
          ? `The managed service was removed, but Docker retained the image: ${finalResult.image_cache_retained_reason}`
          : "The managed service was removed. No cached image needed removal.";
      } else {
        finalResult.message = "The managed service was removed. Its image remains cached for faster setup.";
      }
      if (searxngRemoveCacheInput) searxngRemoveCacheInput.checked = false;
    }
    renderSearxngStatus(finalResult);
  } catch (error) {
    const currentStatus = await fetchSearxngStatus();
    const currentMessage = currentStatus?.message ? ` ${currentStatus.message}` : "";
    searxngStatusEl.textContent =
      (error.message || "Could not manage local Web Search.") + currentMessage;
    searxngStatusEl.dataset.state = "error";
  } finally {
    searxngActionButtons.forEach((button) => {
      button.disabled = false;
    });
  }
};

const parseMaxPapers = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 100;
  return Math.max(20, Math.min(1000, Math.floor(parsed)));
};

const normalizeYearInput = (value) => {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return "";
  const year = Math.floor(parsed);
  if (year < 1900 || year > 2100) return "";
  return String(year);
};


const updateResultTools = () => {
  const hasResults = fullResults.length > 0;
  const hasPages = fullResults.length > pageSize;
  if (resultsToolbar) resultsToolbar.hidden = !isSearching && !hasResults;
  if (findMoreBtn) {
    findMoreBtn.hidden = !hasResults;
    findMoreBtn.disabled = isSearching || !canFindMore;
  }
  if (abstractToggleBtn) abstractToggleBtn.hidden = !hasResults;
  if (stopBtn) {
    stopBtn.hidden = !isSearching;
    stopBtn.disabled = !isSearching;
  }
  if (resultsPager) resultsPager.hidden = !hasPages;
};

const setSearching = (flag) => {
  isSearching = flag;
  updateResultTools();
};

const setFiltersCollapsed = (collapsed) => {
  if (!filtersEl || !filtersToggleBtn) return;
  const icon = filtersToggleBtn.querySelector(".filters-toggle-icon");
  filtersEl.classList.toggle("is-collapsed", collapsed);
  filtersToggleBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
  filtersToggleBtn.setAttribute("aria-label", collapsed ? "Expand filters" : "Collapse filters");
  filtersToggleBtn.title = collapsed ? "Expand filters" : "Collapse filters";
  if (icon) {
    icon.textContent = collapsed ? "+" : "-";
  }
};

const AREA_CATALOG = [
  { code: "ai.general", label: "AI-Generic", group: "AI", tags: ["artificial intelligence", "agents"] },
  { code: "ai.ml", label: "AI-ML", group: "AI", tags: ["ml", "deep learning", "stat.ml"] },
  { code: "ai.rl", label: "AI-RL", group: "AI", tags: ["rl", "policy gradient", "q-learning"] },
  { code: "ai.nlp", label: "AI-NLP", group: "AI", tags: ["language", "nlp", "llm"] },
  { code: "ai.cv", label: "AI-CV", group: "AI", tags: ["computer vision", "image"] },
  { code: "ai.robotics", label: "AI-Robotics", group: "AI", tags: ["robot", "control"] },
  { code: "ai.ir", label: "AI-IR", group: "AI", tags: ["retrieval", "search"] },
  { code: "ai.multi_agent", label: "AI-MultiAgent", group: "AI", tags: ["multi-agent", "coordination"] },
  { code: "ai.safety", label: "AI-Safety", group: "AI", tags: ["alignment", "safety", "robustness"] },
  { code: "ai.reasoning", label: "AI-Reasoning", group: "AI", tags: ["reasoning", "logic", "planning"] },
  { code: "cs.graphics", label: "CS-Graphics", group: "General", tags: ["computer graphics", "rendering", "3d"] },
  { code: "math.general", label: "Mathematics", group: "General", tags: ["algebra", "analysis"] },
  { code: "stat.general", label: "Statistics", group: "General", tags: ["probability", "inference"] },
  { code: "physics.general", label: "Physics", group: "General", tags: ["quantum", "astro"] },
  { code: "bio.general", label: "Biology", group: "General", tags: ["life science", "genomics"] },
  { code: "med.general", label: "Medicine", group: "General", tags: ["clinical", "healthcare"] },
  { code: "econ.general", label: "Economics", group: "General", tags: ["econometrics", "market"] },
  { code: "fin.general", label: "Finance", group: "General", tags: ["quant finance", "asset pricing", "risk"] },
];

const PRESETS = {
  "ai-generic": ["ai.general", "ai.ml", "ai.nlp", "ai.cv", "ai.robotics", "ai.ir", "ai.multi_agent", "ai.safety", "ai.reasoning"],
  "ai-rl": ["ai.rl", "ai.ml", "ai.general"],
  "ai-cv": ["ai.cv", "ai.ml", "ai.general"],
  "ai-nlp": ["ai.nlp", "ai.ml", "ai.general"],
  "ai-robo": ["ai.robotics", "ai.rl", "ai.general"],
  "math-stat": ["math.general", "stat.general"],
  physics: ["physics.general"],
  graphics: ["cs.graphics"],
  "econ-fin": ["econ.general", "fin.general"],
  "bio-med": ["bio.general", "med.general"],
};

const setSearchMode = (mode) => {
  searchMode = mode === "smart" ? "smart" : "keyword";
  searchModeButtons.forEach((button) => {
    const active = button.dataset.searchMode === searchMode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  if (searchMode === "smart") {
    input.placeholder = "Describe what you want to understand...";
    searchSubmitBtn.textContent = "Search";
    searchModeHint.textContent = "Discover and verify results against your full intent.";
  } else {
    input.placeholder = "Enter keywords, authors, or domains...";
    searchSubmitBtn.textContent = "Search";
    searchModeHint.textContent = "Search providers directly with your keywords.";
    intelligentProgressEl.hidden = true;
  }
};

const getEffectiveAreas = () => {
  const effective = new Set();
  activePresets.forEach((preset) => {
    (PRESETS[preset] || []).forEach((code) => effective.add(code));
  });
  return effective;
};

const renderSelectedAreas = () => {
  selectedAreasEl.innerHTML = "";
  const effective = getEffectiveAreas();
  if (!effective.size) {
    const hint = document.createElement("span");
    hint.className = "selected-empty";
    hint.textContent = "No area selected. Search all.";
    selectedAreasEl.appendChild(hint);
    return;
  }
  Array.from(effective).forEach((code) => {
    const area = AREA_CATALOG.find((item) => item.code === code);
    if (!area) return;
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "selected-chip";
    chip.dataset.code = code;
    chip.textContent = `${area.label} (${code})`;
    selectedAreasEl.appendChild(chip);
  });
};

const renderPresetState = () => {
  if (!areaPresetsEl) return;
  areaPresetsEl.querySelectorAll(".scope-chip").forEach((btn) => {
    const preset = btn.dataset.preset;
    btn.classList.toggle("is-active", !!preset && activePresets.has(preset));
  });
};

const togglePreset = (preset) => {
  if (preset === "clear") {
    activePresets.clear();
    renderPresetState();
    renderSelectedAreas();
    return;
  }
  if (activePresets.has(preset)) {
    activePresets.delete(preset);
  } else {
    activePresets.add(preset);
  }
  renderPresetState();
  renderSelectedAreas();
};

const renderPaginationControls = () => {
  const totalPages = Math.max(1, Math.ceil(fullResults.length / pageSize));
  const currentPage = Math.min(
    totalPages,
    Math.max(1, Number(pageSelectTop.value || "1")),
  );

  pageSelectTop.innerHTML = "";
  for (let page = 1; page <= totalPages; page += 1) {
    const option = document.createElement("option");
    option.value = String(page);
    option.textContent = `Page ${page} / ${totalPages}`;
    if (page === currentPage) option.selected = true;
    pageSelectTop.appendChild(option);
  }
  pagePrevTop.disabled = currentPage <= 1;
  pageNextTop.disabled = currentPage >= totalPages;
  scrollTopBtn.style.visibility = fullResults.length > pageSize ? "visible" : "hidden";
  updateResultTools();
};

const RESULT_ACTION_ICONS = {
  paper: [
    ["path", { d: "M6 2.75h7l5 5V21.25H6z" }],
    ["path", { d: "M13 2.75v5h5" }],
    ["path", { d: "M9 12h6M9 16h6" }],
  ],
  pdf: [
    ["path", { d: "M12 3v12" }],
    ["path", { d: "m7.5 10.5 4.5 4.5 4.5-4.5" }],
    ["path", { d: "M5 20h14" }],
  ],
  doi: [
    ["path", { d: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" }],
    ["path", { d: "M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" }],
  ],
  web: [
    ["circle", { cx: "12", cy: "12", r: "9" }],
    ["path", { d: "M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" }],
  ],
};

const createResultAction = (label, href, iconName) => {
  if (!href) return null;
  const link = document.createElement("a");
  link.className = "result-action";
  link.href = href;
  link.target = "_blank";
  link.rel = "noopener noreferrer";

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  for (const [tag, attributes] of RESULT_ACTION_ICONS[iconName] || []) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attributes).forEach(([name, value]) => {
      node.setAttribute(name, value);
    });
    svg.appendChild(node);
  }

  const text = document.createElement("span");
  text.textContent = label;
  link.append(svg, text);
  return link;
};

const renderResults = () => {
  resultsEl.innerHTML = "";
  const totalPages = Math.max(1, Math.ceil(fullResults.length / pageSize));
  const currentPage = Math.min(
    totalPages,
    Math.max(1, Number(pageSelectTop.value || "1")),
  );
  const start = (currentPage - 1) * pageSize;
  const visible = fullResults.slice(start, start + pageSize);

  if (!fullResults.length) {
    const empty = document.createElement("div");
    empty.className = "result-empty";
    empty.textContent = "No papers surfaced. Try widening the signal.";
    resultsEl.appendChild(empty);
    renderPaginationControls();
    return;
  }

  visible.forEach((paper) => {
    const card = document.createElement("article");
    card.className = "result-card";

    const title = document.createElement("h3");
    const primaryUrl = paper.paper_url || paper.url;
    if (primaryUrl) {
      const titleLink = document.createElement("a");
      titleLink.className = "result-title-link";
      titleLink.href = primaryUrl;
      titleLink.target = "_blank";
      titleLink.rel = "noopener noreferrer";
      titleLink.textContent = paper.title;
      title.appendChild(titleLink);
    } else {
      title.textContent = paper.title;
    }

    const meta = document.createElement("p");
    meta.className = "result-meta";
    const sourceLabel = paper.source ? ` · ${paper.source}` : "";
    meta.textContent = `${paper.authors} · ${paper.year}${sourceLabel}`;

    const abstract = document.createElement("p");
    abstract.className = "result-abstract";
    abstract.textContent = paper.abstract;

    const intelligence = document.createElement("div");
    intelligence.className = "result-intelligence";
    if (paper.discovery_path) {
      const path = document.createElement("span");
      path.className = "result-path";
      path.textContent = paper.discovery_path;
      intelligence.appendChild(path);
    }
    if (paper.match_reason) {
      const reason = document.createElement("p");
      reason.className = "result-reason";
      const fitScore = paper.verification_score ?? paper.semantic_score;
      const score = Number.isFinite(Number(fitScore))
        ? ` · ${Math.round(Number(fitScore) * 100)}% verified fit`
        : "";
      reason.textContent = `Why it matches${score}: ${paper.match_reason}`;
      intelligence.appendChild(reason);
    }

    const actions = document.createElement("div");
    actions.className = "result-actions";
    const isWebResult = paper.result_type === "web";
    const actionLinks = isWebResult
      ? [createResultAction("Web", primaryUrl, "web")]
      : [
          createResultAction("Paper", primaryUrl, "paper"),
          createResultAction("PDF", paper.pdf_url, "pdf"),
          createResultAction("DOI", paper.doi_url, "doi"),
        ];
    actionLinks.filter(Boolean).forEach((action) => actions.appendChild(action));

    card.append(title, meta, abstract);
    if (intelligence.childElementCount) card.appendChild(intelligence);
    if (actions.childElementCount) card.appendChild(actions);
    resultsEl.appendChild(card);
  });
  renderPaginationControls();
};

const updateUsage = (usage) => {
  if (!usage) {
    return;
  }
  currentUsage = {
    last_5_min: usage.last_5_min ?? 0,
    last_day: usage.last_day ?? 0,
    last_5_min_web: usage.last_5_min_web ?? 0,
    last_day_web: usage.last_day_web ?? 0,
    last_day_ai_chat: usage.last_day_ai_chat ?? 0,
    last_day_ai_chat_tokens: usage.last_day_ai_chat_tokens ?? 0,
    last_day_ai_embedding: usage.last_day_ai_embedding ?? 0,
    last_day_ai_embedding_tokens: usage.last_day_ai_embedding_tokens ?? 0,
  };
  usage5MinEl.textContent = currentUsage.last_5_min;
  usageDayEl.textContent = currentUsage.last_day;
  if (usage5MinWebEl) usage5MinWebEl.textContent = currentUsage.last_5_min_web;
  if (usageDayWebEl) usageDayWebEl.textContent = currentUsage.last_day_web;
  if (usageDayAiChatEl) usageDayAiChatEl.textContent = currentUsage.last_day_ai_chat;
  if (usageDayAiChatTokensEl) usageDayAiChatTokensEl.textContent = currentUsage.last_day_ai_chat_tokens.toLocaleString();
  if (usageDayAiEmbeddingEl) usageDayAiEmbeddingEl.textContent = currentUsage.last_day_ai_embedding;
  if (usageDayAiEmbeddingTokensEl) usageDayAiEmbeddingTokensEl.textContent = currentUsage.last_day_ai_embedding_tokens.toLocaleString();
  if (usageBar5) {
    const pct = Math.min(100, currentUsage.last_5_min);
    usageBar5.style.width = pct + "%";
  }
  if (usageBarDay) {
    const pct = Math.min(100, (currentUsage.last_day / 5000) * 100);
    usageBarDay.style.width = pct + "%";
  }
  if (usageBar5Web) {
    const pct = Math.min(100, (currentUsage.last_5_min_web / 10) * 100);
    usageBar5Web.style.width = pct + "%";
  }
  if (usageBarDayWeb) {
    const pct = Math.min(100, (currentUsage.last_day_web / 500) * 100);
    usageBarDayWeb.style.width = pct + "%";
  }
};

const renderSecretControl = (
  inputElement,
  removeButton,
  noteElement,
  configured,
  removalPending,
) => {
  removeButton.hidden = !configured;
  removeButton.textContent = removalPending ? "Undo" : "Remove";
  removeButton.classList.toggle("is-pending", removalPending);
  noteElement.hidden = !removalPending;
  inputElement.disabled = removalPending;
  if (removalPending) inputElement.value = "";
};

const renderSecretControls = () => {
  renderSecretControl(
    s2KeyInput,
    s2KeyRemoveBtn,
    s2KeyRemoveNote,
    semanticscholarKeyConfigured,
    semanticscholarKeyRemovalPending,
  );
  renderSecretControl(
    aiApiKeyInput,
    aiApiKeyRemoveBtn,
    aiApiKeyRemoveNote,
    aiApiKeyConfigured,
    aiApiKeyRemovalPending,
  );
  renderSecretControl(
    aiEmbeddingApiKeyInput,
    aiEmbeddingApiKeyRemoveBtn,
    aiEmbeddingApiKeyRemoveNote,
    aiEmbeddingApiKeyConfigured,
    aiEmbeddingApiKeyRemovalPending,
  );
};

const fetchConfig = async () => {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    emailInput.value = data.email || "";
    semanticscholarKeyConfigured = Boolean(data.semanticscholar_api_key_configured);
    s2KeyInput.value = "";
    s2KeyInput.placeholder = semanticscholarKeyConfigured
      ? "Configured; enter a new key to replace"
      : "Optional API key";
    aiBaseUrlInput.value = data.ai_base_url || "";
    aiApiKeyConfigured = Boolean(data.ai_api_key_configured);
    aiApiKeyInput.value = "";
    aiApiKeyInput.placeholder = aiApiKeyConfigured
      ? "Configured; enter a new key to replace"
      : "Optional for local services";
    aiChatModelInput.value = data.ai_chat_model || "";
    aiEmbeddingModelInput.value = data.ai_embedding_model || "";
    aiEmbeddingSeparateInput.open = Boolean(
      data.ai_embedding_separate_connection,
    );
    aiEnableThinkingInput.checked = Boolean(data.ai_enable_thinking);
    aiEmbeddingBaseUrlInput.value = data.ai_embedding_base_url || "";
    aiEmbeddingApiKeyConfigured = Boolean(
      data.ai_embedding_api_key_configured,
    );
    aiEmbeddingApiKeyInput.value = "";
    aiEmbeddingApiKeyInput.placeholder = aiEmbeddingApiKeyConfigured
      ? "Configured; enter a new key to replace"
      : "Optional for local services";
    aiVerifyBatchSizeInput.value = String(data.ai_verify_batch_size || 5);
    aiVerifyConcurrencyInput.value = String(data.ai_verify_concurrency || 1);
    aiTimeoutInput.value = String(data.ai_timeout_seconds || 45);
    semanticscholarKeyRemovalPending = false;
    aiApiKeyRemovalPending = false;
    aiEmbeddingApiKeyRemovalPending = false;
    renderSecretControls();
    s2KeyInput.disabled = false;
    if (searxngInput) {
      searxngInput.value = data.searxng_url || DEFAULT_SEARXNG_URL;
    }
    if (webIgnoreYearFilterInput) {
      webIgnoreYearFilterInput.checked = Boolean(data.web_ignore_year_filter);
    }
    configuredMaxPapers = parseMaxPapers(data.max_papers);
    configuredIntelligentMaxResults = Number(data.intelligent_max_results || 20);
    activeLimit = configuredMaxPapers;
    maxPapersInput.value = String(configuredMaxPapers);
    intelligentMaxResultsInput.value = String(configuredIntelligentMaxResults);
    const enabledBackends = new Set(data.enabled_backends || ["arxiv", "openalex", "semanticscholar"]);
    backendGrid.querySelectorAll("input[type='checkbox']").forEach((box) => {
      box.checked = enabledBackends.has(box.value);
    });
    savedProfileState = serializeProfileState();
    updateProfileDirtyState();
  } catch (error) {
    return;
  }
};

const fetchUsage = async () => {
  try {
    const response = await fetch("/api/usage");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    updateUsage(data);
  } catch (error) {
    return;
  }
};

const saveConfig = async () => {
  const email = emailInput.value.trim();
  const clear_semanticscholar_api_key = semanticscholarKeyRemovalPending;
  const semanticscholar_api_key = clear_semanticscholar_api_key
    ? ""
    : s2KeyInput.value.trim();
  const searxng_url = searxngInput?.value.trim() || "";
  const web_ignore_year_filter = Boolean(webIgnoreYearFilterInput?.checked);
  const enabled_backends = Array.from(
    backendGrid.querySelectorAll("input[type='checkbox']:checked"),
  ).map((box) => box.value);
  const max_papers = parseMaxPapers(maxPapersInput.value || "100");
  const intelligent_max_results = Math.max(
    1,
    Math.min(Number(intelligentMaxResultsInput.value || 20), 100),
  );
  const clear_ai_api_key = aiApiKeyRemovalPending;
  const ai_api_key = clear_ai_api_key ? "" : aiApiKeyInput.value.trim();
  const clear_ai_embedding_api_key = aiEmbeddingApiKeyRemovalPending;
  const ai_embedding_api_key = clear_ai_embedding_api_key
    ? ""
    : aiEmbeddingApiKeyInput.value.trim();
  if (!enabled_backends.length) {
    setConfigStatus("Select at least one search backend.");
    return false;
  }
  let saved = false;
  saveConfigBtn.disabled = true;
  saveConfigBtn.textContent = "Saving…";
  setConfigStatus("Saving config…");
  try {
    const response = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        ...(semanticscholar_api_key || clear_semanticscholar_api_key
          ? { semanticscholar_api_key }
          : {}),
        searxng_url,
        web_ignore_year_filter,
        enabled_backends,
        max_papers,
        intelligent_max_results,
        ai_base_url: aiBaseUrlInput.value.trim(),
        ...(ai_api_key || clear_ai_api_key ? { ai_api_key } : {}),
        ai_chat_model: aiChatModelInput.value.trim(),
        ai_embedding_model: aiEmbeddingModelInput.value.trim(),
        ai_embedding_separate_connection: Boolean(
          aiEmbeddingSeparateInput.open,
        ),
        ai_enable_thinking: Boolean(aiEnableThinkingInput.checked),
        ai_embedding_base_url: aiEmbeddingBaseUrlInput.value.trim(),
        ...(ai_embedding_api_key || clear_ai_embedding_api_key
          ? { ai_embedding_api_key }
          : {}),
        ai_verify_batch_size: Number(aiVerifyBatchSizeInput.value || 5),
        ai_verify_concurrency: Number(aiVerifyConcurrencyInput.value || 1),
        ai_timeout_seconds: Number(aiTimeoutInput.value || 45),
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      if (error.error === "no_search_backends") {
        throw new Error("no_search_backends");
      }
      throw new Error("save_failed");
    }
    const data = await response.json();
    setConfigStatus("Config saved.", 1000);
    if (data.email) {
      emailInput.value = data.email;
    }
    semanticscholarKeyConfigured = Boolean(data.semanticscholar_api_key_configured);
    s2KeyInput.value = "";
    s2KeyInput.placeholder = semanticscholarKeyConfigured
      ? "Configured; enter a new key to replace"
      : "Optional API key";
    semanticscholarKeyRemovalPending = false;
    aiBaseUrlInput.value = data.ai_base_url || "";
    aiApiKeyConfigured = Boolean(data.ai_api_key_configured);
    aiApiKeyInput.value = "";
    aiApiKeyInput.placeholder = aiApiKeyConfigured
      ? "Configured; enter a new key to replace"
      : "Optional for local services";
    aiApiKeyRemovalPending = false;
    aiChatModelInput.value = data.ai_chat_model || "";
    aiEmbeddingModelInput.value = data.ai_embedding_model || "";
    aiEmbeddingSeparateInput.open = Boolean(
      data.ai_embedding_separate_connection,
    );
    aiEnableThinkingInput.checked = Boolean(data.ai_enable_thinking);
    aiEmbeddingBaseUrlInput.value = data.ai_embedding_base_url || "";
    aiEmbeddingApiKeyConfigured = Boolean(
      data.ai_embedding_api_key_configured,
    );
    aiEmbeddingApiKeyInput.value = "";
    aiEmbeddingApiKeyInput.placeholder = aiEmbeddingApiKeyConfigured
      ? "Configured; enter a new key to replace"
      : "Optional for local services";
    aiEmbeddingApiKeyRemovalPending = false;
    aiVerifyBatchSizeInput.value = String(data.ai_verify_batch_size || 5);
    aiVerifyConcurrencyInput.value = String(data.ai_verify_concurrency || 1);
    aiTimeoutInput.value = String(data.ai_timeout_seconds || 45);
    renderSecretControls();
    if (searxngInput) {
      searxngInput.value = data.searxng_url || DEFAULT_SEARXNG_URL;
    }
    if (webIgnoreYearFilterInput) {
      webIgnoreYearFilterInput.checked = Boolean(data.web_ignore_year_filter);
    }
    configuredMaxPapers = parseMaxPapers(data.max_papers);
    configuredIntelligentMaxResults = Number(data.intelligent_max_results || 20);
    maxPapersInput.value = String(configuredMaxPapers);
    intelligentMaxResultsInput.value = String(configuredIntelligentMaxResults);
    activeLimit = configuredMaxPapers;
    const enabledBackends = new Set(data.enabled_backends || ["arxiv", "openalex", "semanticscholar", "websearch"]);
    backendGrid.querySelectorAll("input[type='checkbox']").forEach((box) => {
      box.checked = enabledBackends.has(box.value);
    });
    savedProfileState = serializeProfileState();
    updateProfileDirtyState();
    saved = true;
  } catch (error) {
    setConfigStatus(error.message === "no_search_backends"
      ? "Select at least one search backend."
      : "Could not save config.");
  } finally {
    saveConfigBtn.disabled = false;
    saveConfigBtn.textContent = "Save";
  }
  return saved;
};

saveConfigBtn.addEventListener("click", saveConfig);

searxngSetupBtn.addEventListener("click", async () => {
  const willSaveConfig = isConfigDirty();
  const confirmed = window.confirm(
    "Knowte will download the official SearXNG image and create a private local container bound to an available localhost port."
      + (willSaveConfig ? " Your unsaved Config changes will be saved first." : "")
      + " Continue?",
  );
  if (!confirmed) return;
  if (willSaveConfig && !(await saveConfig())) return;
  await runSearxngAction("setup");
});

searxngStartBtn.addEventListener("click", async () => {
  await runSearxngAction(searxngStartBtn.dataset.action || "start");
});

searxngUpdateBtn.addEventListener("click", async () => {
  const confirmed = window.confirm(
    "Check the official SearXNG image for updates? If it is already current, Knowte will not restart the container. If a newer image is available, the service will restart briefly and the previous image will be removed only when Docker confirms it is unused.",
  );
  if (confirmed) await runSearxngAction("update");
});

searxngLogsBtn.addEventListener("click", async () => {
  if (!searxngLogOutput.hidden) {
    setSearxngLogVisible(false);
    return;
  }
  await runSearxngAction("logs");
});

searxngRemoveBtn.addEventListener("click", async () => {
  const removeImage = Boolean(searxngRemoveCacheInput?.checked);
  const confirmed = window.confirm(
    "Remove the Knowte-managed SearXNG container and its generated configuration?"
      + (removeImage
        ? " The exact cached image will also be removed if Docker confirms that no other container uses it."
        : " The image will remain cached for faster setup."),
  );
  if (confirmed) await runSearxngAction("remove", { remove_image: removeImage });
});

const runSearch = async () => {
  if (!lastQuery) return;
  if (searchController) {
    searchController.abort();
  }
  const controller = new AbortController();
  searchController = controller;
  statusEl.textContent = `Scanning for "${lastQuery}"...`;
  resultsEl.innerHTML = "";
  setSearching(true);

  try {
    const params = new URLSearchParams({
      q: lastQuery,
      areas: lastAreas,
      limit: String(activeLimit),
      web_pages: String(activeWebPages),
      backends: lastBackends.join(","),
    });
    if (lastYearFrom) params.set("year_from", lastYearFrom);
    if (lastYearTo) params.set("year_to", lastYearTo);
    const queryString = params.toString();
    const response = await fetch(`/api/search?${queryString}`, { signal: controller.signal });
    if (searchController !== controller) return;
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null);
      if ((response.status === 429 || response.status === 400) && errorPayload?.usage) {
        updateUsage(errorPayload.usage);
        if (errorPayload?.error === "web_rate_limited") {
          statusEl.textContent = "Web search rate limit reached. Disable Web Search or wait before retrying.";
          return;
        }
        if (errorPayload?.error === "no_search_backends") {
          statusEl.textContent = "No searchable backend is available. Configure at least one paper source or set a SearXNG URL.";
          return;
        }
        statusEl.textContent = "Paper rate limit reached. Wait before sending more queries.";
        return;
      }
      throw new Error("Search failed");
    }
    const data = await response.json();
    fullResults = data.results || [];
    canFindMore = Boolean(data.can_find_more);
    canFindMoreWeb = Boolean(data.search_diagnostics?.websearch?.has_more);
    let timeHint = "";
    if (data.year_from && data.year_to) {
      timeHint = ` in ${data.year_from}-${data.year_to}`;
    } else if (data.year_from) {
      timeHint = ` since ${data.year_from}`;
    } else if (data.year_to) {
      timeHint = ` before ${data.year_to}`;
    }
    const warnings = data.warnings || [];
    const warningMessages = [];
    if (warnings.includes("paper_rate_limited")) {
      warningMessages.push("Academic sources are temporarily disabled by rate limit; cached candidates may still be shown.");
    }
    if (warnings.includes("websearch_rate_limited")) {
      warningMessages.push("New Web Search pages are temporarily disabled by rate limit; cached pages may still be shown.");
    }
    if (warnings.includes("websearch_unconfigured")) {
      warningMessages.push("Web Search is enabled in Config but the SearXNG URL is empty.");
    }
    if (warnings.includes("websearch_unavailable")) {
      warningMessages.push("SearXNG could not be reached. Start it or update its URL in Config.");
    }
    if (warnings.includes("websearch_invalid_response")) {
      warningMessages.push("SearXNG did not return valid JSON. Check its JSON format setting in Config.");
    }
    if (warnings.includes("websearch_empty_response")) {
      warningMessages.push("SearXNG returned an empty page, possibly because its engines were temporarily unavailable. The empty response was not cached; try Search again.");
    }
    if (warnings.includes("websearch_no_matching_results")) {
      warningMessages.push("Web Search returned results, but none matched the active query and filters.");
    }
    if (warnings.includes("websearch_strict_year_filter")) {
      warningMessages.push("Undated web results are excluded by the year filter. Enable ‘Ignore year filter for Web Search’ in Config if needed.");
    }
    const sourceSummary = Object.entries(data.source_counts || {})
      .map(([source, count]) => `${source}: ${count}`)
      .join(", ");
    const sourceHint = sourceSummary ? ` Sources: ${sourceSummary}.` : "";
    const webDiagnostics = data.search_diagnostics?.websearch;
    const cacheHint = webDiagnostics?.cache_hits > 0
      && webDiagnostics?.external_requests === 0
      ? " Reused cached Web results."
      : "";
    const warningHint = warningMessages.length ? ` ${warningMessages.join(" ")}` : "";
    statusEl.textContent = `Found ${data.count} paper(s) for "${data.query}"${timeHint}.` + sourceHint + cacheHint + warningHint;
    updateUsage(data.usage);
    renderResults();
    if (data.count > 0) {
      setFiltersCollapsed(true);
    }
  } catch (error) {
    if (searchController !== controller) return;
    canFindMore = false;
    if (error.name === "AbortError") {
      statusEl.textContent = "Search stopped.";
    } else {
      statusEl.textContent = "Search channel offline. Try again soon.";
    }
  } finally {
    if (searchController === controller) {
      searchController = null;
      setSearching(false);
    }
  }
};

const normalizeSearchYears = () => {
  let yearFrom = normalizeYearInput(yearFromInput?.value || "");
  let yearTo = normalizeYearInput(yearToInput?.value || "");
  if (yearFrom && yearTo && Number(yearFrom) > Number(yearTo)) {
    [yearFrom, yearTo] = [yearTo, yearFrom];
    if (yearFromInput) yearFromInput.value = yearFrom;
    if (yearToInput) yearToInput.value = yearTo;
  }
  return { yearFrom, yearTo };
};

const configuredBackends = () => Array.from(
  backendGrid.querySelectorAll("input[type='checkbox']:checked"),
).map((box) => box.value);

const activeBackends = () => {
  const available = new Set(["arxiv", "openalex", "semanticscholar", "websearch"]);
  const selected = (planSourceOverride || configuredBackends()).filter((source) => available.has(source));
  return selected.length ? selected : configuredBackends();
};

const beginSearch = async (query, areas, yearFrom, yearTo, backends = activeBackends()) => {
  if (!query) {
    statusEl.textContent = "Enter a signal to wake the archive.";
    return;
  }

  const wantsWeb = backends.includes("websearch");
  const academicBackends = new Set(["arxiv", "openalex", "semanticscholar"]);
  lastQuery = query;
  lastAreas = areas;
  lastYearFrom = yearFrom;
  lastYearTo = yearTo;
  lastBackends = [...backends];
  activeLimit = configuredMaxPapers;
  activeWebPages = 1;
  lastSearchHasWeb = wantsWeb;
  lastSearchHasAcademic = backends.some((backend) => academicBackends.has(backend));
  canFindMoreWeb = false;
  fullResults = [];
  canFindMore = false;
  pageSelectTop.value = "1";
  await runSearch();
};

const resetStageGroup = (group, enabled) => {
  group.querySelectorAll("[data-stage]").forEach((stage) => {
    stage.classList.remove("is-active", "is-complete", "is-degraded");
    stage.classList.toggle("is-skipped", !enabled);
  });
};

const markStage = (group, stageName, state) => {
  const stage = group.querySelector(`[data-stage="${stageName}"]`);
  if (!stage) return;
  stage.classList.remove(
    "is-active",
    "is-complete",
    "is-degraded",
    "is-skipped",
  );
  if (state === "skipped") {
    stage.classList.add("is-skipped");
  } else if (state === "degraded") {
    stage.classList.add("is-degraded");
  } else {
    stage.classList.add(state === "complete" ? "is-complete" : "is-active");
  }
};

const finishActiveStages = (group) => {
  group.querySelectorAll(".is-active").forEach((stage) => {
    stage.classList.remove("is-active");
    stage.classList.add("is-complete");
  });
};

const runIntelligentSearch = async (query, areas, yearFrom, yearTo, backends) => {
  const token = ++intelligentRunToken;
  const startedAt = performance.now();
  let elapsedTimer = null;
  let progressTimer = null;
  const academicEnabled = backends.some((source) => ["arxiv", "openalex", "semanticscholar"].includes(source));
  const webEnabled = backends.includes("websearch");
  if (!academicEnabled && !webEnabled) {
    statusEl.textContent = "Select at least one source in Config.";
    return;
  }

  lastQuery = query;
  lastAreas = areas;
  lastYearFrom = yearFrom;
  lastYearTo = yearTo;
  lastBackends = [...backends];
  lastSearchHasAcademic = academicEnabled;
  lastSearchHasWeb = webEnabled;
  fullResults = [];
  canFindMore = false;
  canFindMoreWeb = false;
  pageSelectTop.value = "1";
  resultsEl.innerHTML = "";
  intelligentProgressEl.hidden = false;
  resetStageGroup(academicStagesEl, academicEnabled);
  resetStageGroup(webStagesEl, webEnabled);
  intelligentBudgetEl.textContent = "Request counts will appear when the pipeline completes.";
  intelligentExpandedEl.hidden = true;
  intelligentExpandedEl.replaceChildren();
  isIntelligentSearching = true;
  setSearching(true);
  const renderElapsed = () => {
    if (token !== intelligentRunToken) return;
    const elapsedSeconds = Math.floor((performance.now() - startedAt) / 1000);
    statusEl.textContent = `Running Intelligent discovery for “${query}”…\n${elapsedSeconds}s elapsed.`;
  };
  renderElapsed();
  elapsedTimer = window.setInterval(renderElapsed, 1000);
  const controller = new AbortController();
  searchController = controller;
  const runId = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  let lastProgressStage = "";
  const renderExpandedQueries = (queries, expansionStatus = "complete") => {
    intelligentExpandedEl.replaceChildren();
    const label = document.createElement("strong");
    label.textContent = "Expanded queries";
    intelligentExpandedEl.appendChild(label);
    if (queries.length) {
      queries.forEach((expandedQuery) => {
        const chip = document.createElement("span");
        chip.textContent = expandedQuery;
        intelligentExpandedEl.appendChild(chip);
      });
    } else {
      const empty = document.createElement("span");
      empty.textContent = expansionStatus === "degraded"
        ? "Unavailable; continuing with the original query"
        : "None generated; using the original query";
      intelligentExpandedEl.appendChild(empty);
    }
    intelligentExpandedEl.hidden = false;
  };
  const renderProgressStage = (stage) => {
    if (!stage || stage === lastProgressStage) return;
    lastProgressStage = stage;
    const academicOrder = ["expand", "recall", "embed", "verify"];
    const academicIndex = academicOrder.indexOf(stage);
    if (academicEnabled && academicIndex >= 0) {
      academicOrder.forEach((name, index) => {
        if (index <= academicIndex) {
          markStage(
            academicStagesEl,
            name,
            index < academicIndex ? "complete" : "active",
          );
        }
      });
    }
    if (webEnabled) {
      if (stage === "recall") {
        markStage(webStagesEl, "recall", "active");
      } else if (stage === "embed") {
        markStage(webStagesEl, "recall", "complete");
      } else if (stage === "verify") {
        markStage(webStagesEl, "recall", "complete");
        markStage(webStagesEl, "verify", "active");
      }
    }
  };
  const pollProgress = async () => {
    try {
      const response = await fetch(`/api/intelligent-progress?run_id=${encodeURIComponent(runId)}`);
      if (!response.ok || token !== intelligentRunToken) return;
      const progress = await response.json();
      renderProgressStage(progress.stage);
      if (
        academicEnabled
        && Object.hasOwn(progress, "expanded_queries")
      ) {
        renderExpandedQueries(
          progress.expanded_queries || [],
          progress.expansion_status || "complete",
        );
      }
    } catch (_error) {
      // The main request remains authoritative if a progress poll is missed.
    }
  };
  progressTimer = window.setInterval(pollProgress, 500);

  try {
    const params = new URLSearchParams({
      q: query,
      areas,
      limit: String(configuredIntelligentMaxResults),
      web_pages: "1",
      backends: backends.join(","),
      run_id: runId,
    });
    if (yearFrom) params.set("year_from", yearFrom);
    if (yearTo) params.set("year_to", yearTo);
    const response = await fetch(`/api/intelligent-search?${params}`, {
      signal: controller.signal,
    });
    const data = await response.json().catch(() => ({}));
    if (token !== intelligentRunToken) return;
    if (!response.ok) {
      if (data.error === "ai_unconfigured") {
        throw new Error(data.message || "Add an AI Base URL and Language Model in Config, save, then try again.");
      }
      if (data.error === "intelligent_rate_limited") {
        throw new Error("A search channel is rate limited. Wait before retrying.");
      }
      throw new Error(data.message || "Intelligent Search could not complete.");
    }
    const stages = data.stages || {};
    if (academicEnabled) {
      ["recall", "expand", "embed", "verify"].forEach((stageName) => {
        markStage(
          academicStagesEl,
          stageName,
          stages[stageName]?.status || "skipped",
        );
      });
    }
    if (webEnabled) {
      markStage(webStagesEl, "recall", stages.recall?.status || "complete");
      markStage(webStagesEl, "verify", stages.verify?.status || "skipped");
    }
    const budget = data.request_budget || {};
    intelligentBudgetEl.textContent = `Actual pipeline work: ${budget.retrieval || 0} retrieval round(s) · ${budget.embedding || 0} embedding batch(es) · ${budget.chat || 0} LLM request(s)`;
    const expandedQueries = data.expanded_queries || [];
    if (academicEnabled) {
      renderExpandedQueries(
        expandedQueries,
        stages.expand?.status || "complete",
      );
    }
    fullResults = data.results || [];
    updateUsage(data.usage);
    renderResults();
    if (fullResults.length) setFiltersCollapsed(true);
    const counts = data.candidate_counts || {};
    const degraded = (data.warnings || []).length
      ? (
          stages.verify?.message
            ? ` LLM verification failed: ${stages.verify.message} Fallback results may be included.`
            : " Some AI stages degraded; fallback results may be included."
        )
      : "";
    statusEl.textContent = `Found ${fullResults.length} verified result(s) from ${counts.academic || 0} academic and ${counts.web || 0} Web candidate(s).${degraded}`;
  } catch (error) {
    if (token !== intelligentRunToken) return;
    if (error.name === "AbortError") {
      statusEl.textContent = "Intelligent Search stopped.";
    } else {
      statusEl.textContent = error.message;
    }
    resetStageGroup(academicStagesEl, academicEnabled);
    resetStageGroup(webStagesEl, webEnabled);
  } finally {
    if (elapsedTimer !== null) {
      window.clearInterval(elapsedTimer);
    }
    if (progressTimer !== null) {
      window.clearInterval(progressTimer);
    }
    if (token === intelligentRunToken) {
      isIntelligentSearching = false;
      if (searchController === controller) searchController = null;
      setSearching(false);
    }
  }
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = input.value.trim();

  if (!query) {
    statusEl.textContent = "Enter a signal to wake the archive.";
    return;
  }

  const areas = Array.from(getEffectiveAreas()).join(",");
  const { yearFrom, yearTo } = normalizeSearchYears();
  const backends = activeBackends();
  if (searchMode === "smart") {
    await runIntelligentSearch(query, areas, yearFrom, yearTo, backends);
  } else {
    intelligentProgressEl.hidden = true;
    await beginSearch(query, areas, yearFrom, yearTo, backends);
  }
});

searchModeButtons.forEach((button) => {
  button.addEventListener("click", () => setSearchMode(button.dataset.searchMode));
});

selectedAreasEl.addEventListener("click", (event) => {
  const target = event.target.closest(".selected-chip");
  if (!target) return;
  const code = target.dataset.code;
  if (!code) return;
  Array.from(activePresets).forEach((preset) => {
    if ((PRESETS[preset] || []).includes(code)) {
      activePresets.delete(preset);
    }
  });
  renderPresetState();
  renderSelectedAreas();
});

if (areaPresetsEl) {
  areaPresetsEl.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    const btn = event.target.closest(".scope-chip");
    if (!btn) return;
    const preset = btn.dataset.preset;
    if (!preset) return;
    togglePreset(preset);
  });
}

if (clearTimeBtn) {
  clearTimeBtn.addEventListener("click", () => {
    if (yearFromInput) yearFromInput.value = "";
    if (yearToInput) yearToInput.value = "";
  });
}

if (filtersToggleBtn) {
  filtersToggleBtn.addEventListener("click", () => {
    const collapsed = !filtersEl?.classList.contains("is-collapsed");
    setFiltersCollapsed(collapsed);
  });
}

const syncPage = (pageNumber) => {
  pageSelectTop.value = String(pageNumber);
  renderResults();
};

pageSelectTop.addEventListener("change", () => {
  syncPage(Number(pageSelectTop.value || "1"));
});
pagePrevTop.addEventListener("click", () => {
  syncPage(Math.max(1, Number(pageSelectTop.value || "1") - 1));
});
pageNextTop.addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(fullResults.length / pageSize));
  syncPage(Math.min(totalPages, Number(pageSelectTop.value || "1") + 1));
});
findMoreBtn.addEventListener("click", async () => {
  if (!lastQuery) {
    statusEl.textContent = "Run an initial search first.";
    return;
  }
  if (lastSearchHasAcademic) {
    activeLimit = Math.min(1000, activeLimit + configuredMaxPapers);
  }
  if (lastSearchHasWeb && canFindMoreWeb) {
    activeWebPages = Math.min(10, activeWebPages + 1);
  }
  await runSearch();
});
abstractToggleBtn.addEventListener("click", () => {
  abstractsHidden = !abstractsHidden;
  resultsEl.classList.toggle("is-abstract-hidden", abstractsHidden);
  abstractToggleBtn.setAttribute("aria-pressed", String(abstractsHidden));
  abstractToggleBtn.textContent = abstractsHidden ? "Show abstracts" : "Hide abstracts";
});
stopBtn.addEventListener("click", () => {
  if (isIntelligentSearching) {
    intelligentRunToken += 1;
    if (searchController) {
      searchController.abort();
      searchController = null;
    }
    isIntelligentSearching = false;
    statusEl.textContent = "Intelligent Search stopped.";
    setSearching(false);
  } else if (isSearching && searchController) {
    searchController.abort();
  }
});
scrollTopBtn.addEventListener("click", () => {
  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
});

const showPanel = (target) => {
  navLinks.forEach((link) => {
    link.classList.toggle("is-active", link.dataset.target === target);
  });
  panels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === target);
  });
};

const currentPlanPayload = () => {
  const query = input.value.trim();
  if (!query) throw new Error("Enter a query before saving a plan.");
  const { yearFrom, yearTo } = normalizeSearchYears();
  return {
    query,
    mode: searchMode === "smart" ? "intelligent" : "keyword",
    areas: Array.from(getEffectiveAreas()),
    year_from: yearFrom || null,
    year_to: yearTo || null,
    sources: activeBackends(),
  };
};

const sourceDisplayName = (source) => ({
  arxiv: "arXiv",
  openalex: "OpenAlex",
  semanticscholar: "Semantic Scholar",
  websearch: "Web",
}[source] || source);

const planSummary = (plan) => {
  const year = plan.year_from && plan.year_to
    ? `${plan.year_from}–${plan.year_to}`
    : plan.year_from
      ? `Since ${plan.year_from}`
      : plan.year_to
        ? `Through ${plan.year_to}`
        : "Any year";
  const areas = plan.areas?.length ? `${plan.areas.length} area codes` : "All areas";
  const sources = (plan.sources || []).map(sourceDisplayName).join(" · ");
  return `${year} · ${areas} · ${sources || "Default academic sources"}`;
};

const renderPlans = () => {
  plansListEl.innerHTML = "";
  if (!savedPlans.length) {
    const empty = document.createElement("div");
    empty.className = "plans-empty";
    empty.textContent = "No saved plans yet. Save the current search to reuse its intent, filters, mode, and sources.";
    plansListEl.appendChild(empty);
    return;
  }
  savedPlans.forEach((plan) => {
    const card = document.createElement("article");
    card.className = "plan-card";
    card.dataset.planId = plan.id;

    const heading = document.createElement("div");
    heading.className = "plan-card-head";
    const name = document.createElement("strong");
    name.textContent = plan.name;
    const mode = document.createElement("span");
    mode.className = `plan-mode ${plan.mode === "intelligent" ? "is-intelligent" : ""}`;
    mode.textContent = plan.mode === "intelligent" ? "Intelligent" : "Keyword";
    heading.append(name, mode);

    const query = document.createElement("p");
    query.className = "plan-query";
    query.textContent = plan.query;
    const summary = document.createElement("small");
    summary.className = "plan-summary";
    summary.textContent = planSummary(plan);

    const actions = document.createElement("div");
    actions.className = "plan-actions";
    [
      ["run", "Run"],
      ["load", "Load"],
      ["edit", "Edit"],
      ["delete", "Delete"],
    ].forEach(([action, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.planAction = action;
      button.textContent = label;
      if (action === "delete") button.classList.add("plan-delete");
      actions.appendChild(button);
    });
    card.append(heading, query, summary, actions);
    plansListEl.appendChild(card);
  });
};

const fetchPlans = async () => {
  plansStatusEl.textContent = "Loading plans…";
  try {
    const response = await fetch("/api/plans");
    if (!response.ok) throw new Error("Could not load plans.");
    const data = await response.json();
    savedPlans = data.plans || [];
    renderPlans();
    plansStatusEl.textContent = "";
  } catch (error) {
    plansStatusEl.textContent = error.message;
  }
};

const saveCurrentPlan = async () => {
  let payload;
  try {
    payload = currentPlanPayload();
  } catch (error) {
    statusEl.textContent = error.message;
    plansStatusEl.textContent = error.message;
    input.focus();
    return;
  }
  savePlanBtn.disabled = true;
  try {
    const response = await fetch("/api/plans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Could not save this plan.");
    const plan = await response.json();
    statusEl.textContent = `Plan saved: ${plan.name}`;
    await fetchPlans();
    plansStatusEl.textContent = `Plan saved: ${plan.name}`;
  } catch (error) {
    statusEl.textContent = error.message;
    plansStatusEl.textContent = error.message;
  } finally {
    savePlanBtn.disabled = false;
  }
};

const restorePlanAreas = (areas) => {
  const target = new Set(areas || []);
  activePresets.clear();
  const entries = Object.entries(PRESETS);
  for (let mask = 0; mask < 2 ** entries.length; mask += 1) {
    const combined = new Set();
    const chosen = [];
    entries.forEach(([name, codes], index) => {
      if (!(mask & (1 << index))) return;
      chosen.push(name);
      codes.forEach((code) => combined.add(code));
    });
    if (combined.size === target.size && [...combined].every((code) => target.has(code))) {
      chosen.forEach((name) => activePresets.add(name));
      break;
    }
  }
  renderPresetState();
  renderSelectedAreas();
};

const loadPlanIntoSearch = (plan) => {
  input.value = plan.query || "";
  setSearchMode(plan.mode === "intelligent" ? "smart" : "keyword");
  yearFromInput.value = plan.year_from || "";
  yearToInput.value = plan.year_to || "";
  restorePlanAreas(plan.areas);
  planSourceOverride = [...(plan.sources || [])];
  const sourceNames = planSourceOverride.map(sourceDisplayName).join(", ");
  searchModeHint.textContent += sourceNames ? ` Plan sources: ${sourceNames}.` : "";
  showPanel("search-panel");
  statusEl.textContent = `Loaded plan “${plan.name}”. It will use current Config credentials and endpoints.`;
};

savePlanBtn.addEventListener("click", saveCurrentPlan);
goToSearchBtn.addEventListener("click", () => {
  showPanel("search-panel");
  input.focus();
});

plansListEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-plan-action]");
  const card = event.target.closest("[data-plan-id]");
  if (!button || !card) return;
  const plan = savedPlans.find((item) => item.id === card.dataset.planId);
  if (!plan) return;
  const action = button.dataset.planAction;
  if (action === "load") {
    loadPlanIntoSearch(plan);
    return;
  }
  if (action === "run") {
    loadPlanIntoSearch(plan);
    await fetch(`/api/plans/${encodeURIComponent(plan.id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ last_run_at: new Date().toISOString() }),
    });
    form.requestSubmit();
    return;
  }
  if (action === "edit") {
    const name = window.prompt("Plan name", plan.name);
    if (name === null) return;
    const query = window.prompt("Search intent or keywords", plan.query);
    if (query === null) return;
    const response = await fetch(`/api/plans/${encodeURIComponent(plan.id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, query }),
    });
    const message = response.ok ? "Plan updated." : "Could not update the plan.";
    await fetchPlans();
    plansStatusEl.textContent = message;
    return;
  }
  if (action === "delete" && window.confirm(`Delete “${plan.name}”?`)) {
    const response = await fetch(`/api/plans/${encodeURIComponent(plan.id)}`, { method: "DELETE" });
    const message = response.ok ? "Plan deleted." : "Could not delete the plan.";
    await fetchPlans();
    plansStatusEl.textContent = message;
  }
});

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    const target = link.dataset.target;
    if (!target) return;
    showPanel(target);
    if (target === "plans-panel") fetchPlans();
  });
});

[
  emailInput,
  s2KeyInput,
  searxngInput,
  webIgnoreYearFilterInput,
  maxPapersInput,
  intelligentMaxResultsInput,
  backendGrid,
  aiBaseUrlInput,
  aiApiKeyInput,
  aiChatModelInput,
  aiEnableThinkingInput,
  aiEmbeddingModelInput,
  aiEmbeddingSeparateInput,
  aiEmbeddingBaseUrlInput,
  aiEmbeddingApiKeyInput,
  aiVerifyBatchSizeInput,
  aiVerifyConcurrencyInput,
  aiTimeoutInput,
]
  .filter(Boolean)
  .forEach((control) => {
    control.addEventListener("input", updateProfileDirtyState);
    control.addEventListener("change", updateProfileDirtyState);
  });

backendGrid.addEventListener("change", () => {
  planSourceOverride = null;
  setSearchMode(searchMode);
});

aiEmbeddingSeparateInput.addEventListener("toggle", () => {
  updateProfileDirtyState();
});

[
  {
    button: s2KeyRemoveBtn,
    toggle: () => {
      semanticscholarKeyRemovalPending = !semanticscholarKeyRemovalPending;
    },
  },
  {
    button: aiApiKeyRemoveBtn,
    toggle: () => {
      aiApiKeyRemovalPending = !aiApiKeyRemovalPending;
    },
  },
  {
    button: aiEmbeddingApiKeyRemoveBtn,
    toggle: () => {
      aiEmbeddingApiKeyRemovalPending = !aiEmbeddingApiKeyRemovalPending;
    },
  },
].forEach(({ button, toggle }) => {
  button.addEventListener("click", () => {
    toggle();
    renderSecretControls();
    updateProfileDirtyState();
  });
});


const initTheme = () => {
  if (!themeToggleBtn) return;
  const storageKey = "knowte-theme";
  const themeIcon = themeToggleBtn.querySelector(".theme-icon");
  const systemTheme = window.matchMedia?.("(prefers-color-scheme: dark)");
  let selectedMode = localStorage.getItem(storageKey);
  if (!["auto", "light", "dark"].includes(selectedMode)) {
    selectedMode = "auto";
  }

  const automaticTheme = () => {
    if (systemTheme) {
      return systemTheme.matches ? "dark" : "light";
    }
    const hour = new Date().getHours();
    return hour >= 7 && hour < 19 ? "light" : "dark";
  };

  const apply = (mode) => {
    const theme = mode === "auto" ? automaticTheme() : mode;
    const isLight = theme === "light";
    if (isLight) {
      document.body.setAttribute("data-theme", "light");
    } else {
      document.body.removeAttribute("data-theme");
    }
    if (themeIcon) {
      themeIcon.textContent = mode === "auto" ? "◐" : isLight ? "☀" : "☾";
    }
    const nextMode = mode === "auto" ? "light" : mode === "light" ? "dark" : "auto";
    const modeLabel = mode === "auto" ? "Auto" : isLight ? "Light" : "Dark";
    const nextLabel = nextMode === "auto" ? "auto" : nextMode;
    themeToggleBtn.dataset.mode = mode;
    themeToggleBtn.setAttribute("aria-label", `Theme: ${modeLabel}. Switch to ${nextLabel} mode`);
    themeToggleBtn.title = `${modeLabel} mode`;
  };

  apply(selectedMode);

  const syncAutomaticTheme = () => {
    if (selectedMode === "auto") {
      apply("auto");
    }
  };
  if (systemTheme?.addEventListener) {
    systemTheme.addEventListener("change", syncAutomaticTheme);
  } else if (systemTheme?.addListener) {
    systemTheme.addListener(syncAutomaticTheme);
  }

  themeToggleBtn.addEventListener("click", () => {
    selectedMode = selectedMode === "auto" ? "light" : selectedMode === "light" ? "dark" : "auto";
    apply(selectedMode);
    localStorage.setItem(storageKey, selectedMode);
  });
};

fetchConfig();
fetchUsage();
fetchSearxngStatus();
renderSelectedAreas();
renderPresetState();
initTheme();
setFiltersCollapsed(false);
renderPaginationControls();
