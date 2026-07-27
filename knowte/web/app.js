const form = document.querySelector("#search-form");
const input = form.querySelector("input[name='keywords']");
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const emailInput = document.querySelector("#email");
const s2KeyInput = document.querySelector("#s2-key");
const s2KeyClearInput = document.querySelector("#s2-key-clear");
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
const usage5MinEl = document.querySelector("#usage-5min");
const usageDayEl = document.querySelector("#usage-day");
const usage5MinWebEl = document.querySelector("#usage-5min-web");
const usageDayWebEl = document.querySelector("#usage-day-web");
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
let currentUsage = { last_5_min: 0, last_day: 0, last_5_min_web: 0, last_day_web: 0 };
const activePresets = new Set();
const pageSize = 20;
let configuredMaxPapers = 100;
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
let savedProfileState = null;
let configStatusTimer = null;
const DEFAULT_SEARXNG_URL = "http://127.0.0.1:8888/search";

const serializeProfileState = (overrides = {}) => JSON.stringify({
  email: overrides.email ?? emailInput.value.trim(),
  searxng_url: overrides.searxng_url ?? (searxngInput?.value.trim() || ""),
  max_papers: overrides.max_papers ?? parseMaxPapers(maxPapersInput.value || "100"),
  enabled_backends: overrides.enabled_backends ?? Array.from(
    backendGrid.querySelectorAll("input[type='checkbox']:checked"),
  ).map((box) => box.value).sort(),
  api_key_update: s2KeyInput.value.trim(),
  api_key_clear: Boolean(s2KeyClearInput?.checked),
  web_ignore_year_filter: Boolean(webIgnoreYearFilterInput?.checked),
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
  };
  usage5MinEl.textContent = currentUsage.last_5_min;
  usageDayEl.textContent = currentUsage.last_day;
  if (usage5MinWebEl) usage5MinWebEl.textContent = currentUsage.last_5_min_web;
  if (usageDayWebEl) usageDayWebEl.textContent = currentUsage.last_day_web;
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
    if (searxngInput) {
      searxngInput.value = data.searxng_url || DEFAULT_SEARXNG_URL;
    }
    if (webIgnoreYearFilterInput) {
      webIgnoreYearFilterInput.checked = Boolean(data.web_ignore_year_filter);
    }
    configuredMaxPapers = parseMaxPapers(data.max_papers);
    activeLimit = configuredMaxPapers;
    maxPapersInput.value = String(configuredMaxPapers);
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
  const semanticscholar_api_key = s2KeyInput.value.trim();
  const clear_semanticscholar_api_key = Boolean(s2KeyClearInput?.checked);
  const searxng_url = searxngInput?.value.trim() || "";
  const web_ignore_year_filter = Boolean(webIgnoreYearFilterInput?.checked);
  const enabled_backends = Array.from(
    backendGrid.querySelectorAll("input[type='checkbox']:checked"),
  ).map((box) => box.value);
  const max_papers = parseMaxPapers(maxPapersInput.value || "100");
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
    if (s2KeyClearInput) s2KeyClearInput.checked = false;
    if (searxngInput) {
      searxngInput.value = data.searxng_url || DEFAULT_SEARXNG_URL;
    }
    if (webIgnoreYearFilterInput) {
      webIgnoreYearFilterInput.checked = Boolean(data.web_ignore_year_filter);
    }
    configuredMaxPapers = parseMaxPapers(data.max_papers);
    maxPapersInput.value = String(configuredMaxPapers);
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = input.value.trim();
  const areas = Array.from(getEffectiveAreas()).join(",");
  let yearFrom = normalizeYearInput(yearFromInput?.value || "");
  let yearTo = normalizeYearInput(yearToInput?.value || "");
  if (yearFrom && yearTo && Number(yearFrom) > Number(yearTo)) {
    [yearFrom, yearTo] = [yearTo, yearFrom];
    if (yearFromInput) yearFromInput.value = yearFrom;
    if (yearToInput) yearToInput.value = yearTo;
  }

  if (!query) {
    statusEl.textContent = "Enter a signal to wake the archive.";
    return;
  }

  const enabledBackends = Array.from(
    backendGrid.querySelectorAll("input[type='checkbox']:checked"),
  ).map((box) => box.value);
  const wantsWeb = enabledBackends.includes("websearch");
  const academicBackends = new Set(["arxiv", "openalex", "semanticscholar"]);
  lastQuery = query;
  lastAreas = areas;
  lastYearFrom = yearFrom;
  lastYearTo = yearTo;
  activeLimit = configuredMaxPapers;
  activeWebPages = 1;
  lastSearchHasWeb = wantsWeb;
  lastSearchHasAcademic = enabledBackends.some((backend) => academicBackends.has(backend));
  canFindMoreWeb = false;
  fullResults = [];
  canFindMore = false;
  pageSelectTop.value = "1";
  await runSearch();
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
  if (isSearching && searchController) {
    searchController.abort();
  }
});
scrollTopBtn.addEventListener("click", () => {
  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
});

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    const target = link.dataset.target;
    if (!target) return;
    navLinks.forEach((l) => l.classList.toggle("is-active", l === link));
    panels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.id === target);
    });
  });
});

[emailInput, s2KeyInput, s2KeyClearInput, searxngInput, webIgnoreYearFilterInput, maxPapersInput, backendGrid]
  .filter(Boolean)
  .forEach((control) => {
    control.addEventListener("input", updateProfileDirtyState);
    control.addEventListener("change", updateProfileDirtyState);
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
