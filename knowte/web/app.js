const form = document.querySelector("#search-form");
const input = form.querySelector("input[name='keywords']");
const searchSubmitBtn = document.querySelector("#search-submit");
const savePlanBtn = document.querySelector("#save-plan");
const searchModeButtons = document.querySelectorAll("[data-search-mode]");
const defaultSearchModeButtons = document.querySelectorAll(
  "[data-default-search-mode]",
);
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
const aiCopilotInstructionsInput = document.querySelector("#ai-copilot-instructions");
const aiCopilotTemperatureInput = document.querySelector("#ai-copilot-temperature");
const aiCopilotMaxTokensInput = document.querySelector("#ai-copilot-max-tokens");
const aiCopilotParameterList = document.querySelector("#ai-copilot-parameter-list");
const aiCopilotAddParameterBtn = document.querySelector("#ai-copilot-add-parameter");
const aiCopilotPromptPreviewEl = document.querySelector("#ai-copilot-prompt-preview");
const companionPairingKeyInput = document.querySelector("#companion-pairing-key");
const companionPairingGenerateBtn = document.querySelector("#companion-pairing-generate");
const companionPathCopyBtn = document.querySelector("#companion-path-copy");
const companionPathStatusEl = document.querySelector("#companion-path-status");
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
const collectArtifactSelect = document.querySelector("#collect-artifact");
const libraryListEl = document.querySelector("#library-list");
const libraryStatusEl = document.querySelector("#library-status");
const libraryAbstractToggleBtn = document.querySelector("#library-abstract-toggle");
const evidenceLibraryListEl = document.querySelector("#evidence-library-list");
const libraryProposeClaimsBtn = document.querySelector("#library-propose-claims");
const evidenceCreateClaimBtn = document.querySelector("#evidence-create-claim");
const evidenceStatusEl = document.querySelector("#evidence-status");
const resultsSelectAllInput = document.querySelector("#results-select-all");
const librarySelectAllInput = document.querySelector("#library-select-all");
const evidenceLibrarySelectAllInput = document.querySelector("#evidence-library-select-all");
const evidenceTagFilterInput = document.querySelector("#evidence-tag-filter");
const claimsSelectAllInput = document.querySelector("#claims-select-all");
const claimsTagFilterInput = document.querySelector("#claims-tag-filter");
const claimsReviewFilterInput = document.querySelector("#claims-review-filter");
const evidenceSelectAllInput = document.querySelector("#evidence-select-all");
const sourceReaderEl = document.querySelector("#source-reader");
const libraryPanelInnerEl = sourceReaderEl.closest(".panel");
const sourceReaderBackBtn = document.querySelector("#source-reader-back");
const sourceDetailsToggleBtn = document.querySelector("#source-details-toggle");
const sourceReaderTitleEl = document.querySelector("#source-reader-title");
const sourceReaderMetaEl = document.querySelector("#source-reader-meta");
const sourceReaderStatusEl = document.querySelector("#source-reader-status");
const sourceReaderSegmentsEl = document.querySelector("#source-reader-segments");
const sourceCaptureBtn = document.querySelector("#source-capture");
const sourceViewerToolbarEl = document.querySelector("#source-viewer-toolbar");
const sourceViewerPdfControlsEl = document.querySelector("#source-viewer-pdf-controls");
const evidenceTextToolBtn = document.querySelector("#evidence-text-tool");
const evidenceSnapshotToolBtn = document.querySelector("#evidence-snapshot-tool");
const pdfZoomOutBtn = document.querySelector("#pdf-zoom-out");
const pdfZoomInBtn = document.querySelector("#pdf-zoom-in");
const pdfZoomLabelEl = document.querySelector("#pdf-zoom-label");
const sourceOpenOriginalEl = document.querySelector("#source-open-original");
const contextPanel = document.querySelector("#context-panel");
const contextPanelBody = document.querySelector(".context-panel-body");
const contextPanelToggleBtn = document.querySelector("#context-panel-toggle");
const contextPanelCloseBtn = document.querySelector("#context-panel-close");
const contextToggleCountEl = document.querySelector("#context-toggle-count");
const contextModeLabelEl = document.querySelector("#context-mode-label");
const contextSelectionLabelEl = document.querySelector("#context-selection-label");
const contextSelectedCountEl = document.querySelector("#context-selected-count");
const contextSelectionListEl = document.querySelector("#context-selection-list");
const reviewActionsSection = document.querySelector("#review-actions-section");
const evidenceSelectionOverviewEl = document.querySelector("#evidence-selection-overview");
const evidenceProfileSummaryEl = document.querySelector("#evidence-profile-summary");
const evidenceProfileSourcesEl = document.querySelector("#evidence-profile-sources");
const evidenceProfileTextEl = document.querySelector("#evidence-profile-text");
const evidenceProfileSnapshotsEl = document.querySelector("#evidence-profile-snapshots");
const evidenceProfileLinkedEl = document.querySelector("#evidence-profile-linked");
const reviewStageActionsSection = document.querySelector("#review-stage-actions");
const reviewStageAdvanceBtn = document.querySelector("#review-stage-advance");
const reviewStageStatusEl = document.querySelector("#review-stage-status");
const reviewCopilotSection = document.querySelector("#review-copilot-section");
const reviewKnowledgeSection = document.querySelector("#review-knowledge-section");
const evidenceSelectionLocationEl = document.querySelector("#evidence-selection-location");
const evidenceSelectionQuoteEl = document.querySelector("#evidence-selection-quote");
const evidenceSnapshotPreviewEl = document.querySelector("#evidence-snapshot-preview");
const evidenceArtifactSelect = document.querySelector("#evidence-artifact");
const createEvidenceBtn = document.querySelector("#create-evidence");
const reviewEvidenceListEl = document.querySelector("#review-evidence-list");
const annotationTargetLabelEl = document.querySelector("#annotation-target-label");
const annotationBodyEl = document.querySelector("#annotation-body");
const createAnnotationBtn = document.querySelector("#create-annotation");
const reviewAnnotationListEl = document.querySelector("#review-annotation-list");
const reviewKnowledgeStatusEl = document.querySelector("#review-knowledge-status");
const companionInboxEl = document.querySelector("#companion-inbox");
const companionInboxCountEl = document.querySelector("#companion-inbox-count");
const companionInboxListEl = document.querySelector("#companion-inbox-list");
const companionInboxStatusEl = document.querySelector("#companion-inbox-status");
const evidenceDetailDialog = document.querySelector("#evidence-detail-dialog");
const evidenceDetailMetaEl = document.querySelector("#evidence-detail-meta");
const evidenceDetailContentEl = document.querySelector("#evidence-detail-content");
const evidenceDetailAnnotationCountEl = document.querySelector("#evidence-detail-annotation-count");
const evidenceDetailAnnotationListEl = document.querySelector("#evidence-detail-annotation-list");
const evidenceDetailTagsEl = document.querySelector("#evidence-detail-tags");
const evidenceDetailCloseBtn = document.querySelector("#evidence-detail-close");
const evidenceDetailEditTagsBtn = document.querySelector("#evidence-detail-edit-tags");
const evidenceDetailDeleteBtn = document.querySelector("#evidence-detail-delete");
const evidenceQuickEditor = document.querySelector("#evidence-quick-editor");
const evidenceQuickTitleEl = document.querySelector("#evidence-quick-title");
const evidenceQuickKindEl = document.querySelector("#evidence-quick-kind");
const evidenceQuickPreviewEl = document.querySelector("#evidence-quick-preview");
const evidenceQuickArtifactSelect = document.querySelector("#evidence-quick-artifact");
const evidenceQuickTagsInput = document.querySelector("#evidence-quick-tags");
const evidenceQuickAnnotationInput = document.querySelector("#evidence-quick-annotation");
const evidenceQuickDiscardBtn = document.querySelector("#evidence-quick-discard");
const evidenceQuickSaveBtn = document.querySelector("#evidence-quick-save");
const evidenceQuickStatusEl = document.querySelector("#evidence-quick-status");
const tagEditorDialog = document.querySelector("#tag-editor-dialog");
const tagEditorTypeEl = document.querySelector("#tag-editor-type");
const tagEditorSelectedEl = document.querySelector("#tag-editor-selected");
const tagEditorForm = document.querySelector("#tag-editor-form");
const tagEditorInput = document.querySelector("#tag-editor-input");
const tagEditorSuggestions = document.querySelector("#tag-suggestions");
const tagEditorCloseBtn = document.querySelector("#tag-editor-close");
const tagEditorSaveBtn = document.querySelector("#tag-editor-save");
const contextCollectSelectedBtn = document.querySelector("#context-collect-selected");
const contextActionStatusEl = document.querySelector("#context-action-status");
const contextChatEl = document.querySelector("#context-chat");
const contextChatForm = document.querySelector("#context-chat-form");
const contextChatInput = document.querySelector("#context-chat-input");
const contextChatSendBtn = document.querySelector("#context-chat-send");
const chatExpandBtn = document.querySelector("#chat-expand");
const chatWorkspace = document.querySelector("#chat-workspace");
const chatWorkspaceBody = document.querySelector("#chat-workspace-body");
const chatWorkspaceContextEl = document.querySelector("#chat-workspace-context");
const chatCollapseBtn = document.querySelector("#chat-collapse");
const chatContextSummaryEl = document.querySelector("#chat-context-summary");
const chatContextAddBtn = document.querySelector("#chat-context-add");
const chatContextClearBtn = document.querySelector("#chat-context-clear");
const chatContextStatusEl = document.querySelector("#chat-context-status");
const chatContextTrayEl = document.querySelector("#chat-context-tray");
const artifactForm = document.querySelector("#artifact-form");
const artifactTitleInput = document.querySelector("#artifact-title");
const artifactPurposeInput = document.querySelector("#artifact-purpose");
const artifactCreateBtn = document.querySelector("#artifact-create");
const artifactListEl = document.querySelector("#artifact-list");
const artifactStatusEl = document.querySelector("#artifact-status");
const claimsListEl = document.querySelector("#claims-list");
const claimsStatusEl = document.querySelector("#claims-status");
const claimStatementInput = document.querySelector("#claim-statement");
const claimBasisInput = document.querySelector("#claim-basis");
const claimArtifactInput = document.querySelector("#claim-artifact");
const claimCreateBtn = document.querySelector("#claim-create");
const claimCreateStatusEl = document.querySelector("#claim-create-status");
const claimsProposalsToggleBtn = document.querySelector("#claims-proposals-toggle");
const claimsRelateBtn = document.querySelector("#claims-relate");
const claimsBuildViewBtn = document.querySelector("#claims-build-view");
const claimsSelectedCountEl = document.querySelector("#claims-selected-count");
const claimsRelationTypeInput = document.querySelector("#claims-relation-type");
const claimProposalBoardEl = document.querySelector("#claim-proposal-board");
const claimProposalListEl = document.querySelector("#claim-proposal-list");
const claimIncomingTrayEl = document.querySelector("#claim-incoming-tray");
const claimIncomingTitleEl = document.querySelector("#claim-incoming-title");
const claimIncomingItemsEl = document.querySelector("#claim-incoming-items");
const claimAddEvidenceBtn = document.querySelector("#claim-add-evidence");
const evidenceHandoffReturnEl = document.querySelector("#evidence-handoff-return");
const evidenceHandoffCancelBtn = document.querySelector("#evidence-handoff-cancel");
const evidenceHandoffApplyBtn = document.querySelector("#evidence-handoff-apply");
const claimsHandoffReturnEl = document.querySelector("#claims-handoff-return");
const claimsHandoffCancelBtn = document.querySelector("#claims-handoff-cancel");
const claimsHandoffApplyBtn = document.querySelector("#claims-handoff-apply");
const viewIncomingTrayEl = document.querySelector("#view-incoming-tray");
const viewIncomingTitleEl = document.querySelector("#view-incoming-title");
const viewIncomingItemsEl = document.querySelector("#view-incoming-items");
const viewAddClaimsBtn = document.querySelector("#view-add-claims");
const viewForm = document.querySelector("#view-form");
const viewTitleInput = document.querySelector("#view-title");
const viewTypeInput = document.querySelector("#view-type");
const viewProjectInput = document.querySelector("#view-project");
const viewPurposeInput = document.querySelector("#view-purpose");
const viewCreateBtn = document.querySelector("#view-create");
const viewsStatusEl = document.querySelector("#views-status");
const viewsListEl = document.querySelector("#views-list");
const viewIndexWorkspaceEl = document.querySelector("#view-index-workspace");
const viewDetailEl = document.querySelector("#view-detail");
const viewDetailBackBtn = document.querySelector("#view-detail-back");
const viewDetailAddClaimsBtn = document.querySelector("#view-detail-add-claims");
const viewDetailEditBtn = document.querySelector("#view-detail-edit");
const viewDetailDeleteBtn = document.querySelector("#view-detail-delete");
const viewDetailTypeEl = document.querySelector("#view-detail-type");
const viewDetailProjectEl = document.querySelector("#view-detail-project");
const viewDetailTitleEl = document.querySelector("#view-detail-title");
const viewDetailPurposeEl = document.querySelector("#view-detail-purpose");
const viewDetailEditor = document.querySelector("#view-detail-editor");
const viewEditTitleInput = document.querySelector("#view-edit-title");
const viewEditProjectInput = document.querySelector("#view-edit-project");
const viewEditPurposeInput = document.querySelector("#view-edit-purpose");
const viewEditTypeInput = document.querySelector("#view-edit-type");
const viewBlockEditorShell = document.querySelector("#view-block-editor-shell");
const viewBlockEditorEl = document.querySelector("#view-block-editor");
const viewAddHeadingBtn = document.querySelector("#view-add-heading");
const viewAddParagraphBtn = document.querySelector("#view-add-paragraph");
const viewEditCancelBtn = document.querySelector("#view-edit-cancel");
const viewDetailClaimsEl = document.querySelector("#view-detail-claims");
const viewDetailStatusEl = document.querySelector("#view-detail-status");
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
let defaultSearchMode = "keyword";
let savedPlans = [];
let intelligentRunToken = 0;
let lastBackends = [];
let planSourceOverride = null;
let isIntelligentSearching = false;
let artifacts = [];
let librarySources = [];
let libraryEvidence = [];
let claims = [];
let claimProposals = [];
let views = [];
let activeViewId = "";
let viewDraftClaimIds = [];
let viewDraftBlocks = [];
let viewAddingClaims = false;
let activeGraphClaimId = "";
const selectedResultKeys = new Set();
const selectedLibrarySourceKeys = new Set();
const selectedEvidenceIds = new Set();
const selectedClaimIds = new Set();
const incomingClaimEvidenceIds = new Set();
const incomingClaimEvidenceStances = new Map();
const incomingViewClaimIds = new Set();
let evidenceReturnToClaim = false;
let claimsReturnToView = false;
const chatContextSources = new Map();
const chatContextEvidence = new Map();
const CHAT_CONTEXT_LIMIT = 12;
const CHAT_SNAPSHOT_LIMIT = 4;
let libraryAbstractsHidden = false;
let activeSourceWorkspace = null;
let pendingEvidenceSelection = null;
let annotationTarget = null;
let pdfjsLib = null;
let activePdfDocument = null;
let pdfRenderToken = 0;
let pdfZoom = 1;
let evidenceTool = "text";
let activeEvidenceDetailId = null;
let pendingPdfScrollAnchor = null;
let activeTagEditor = null;
let readerDetailsExpanded = false;
let companionInboxItems = [];
let activeReviewContextKey = "search";
let chatExpanded = false;
const reviewConversations = {
  search: [],
  library: [],
  evidence: [],
  claims: [],
  views: [],
  artifact: [],
};
const expandedArtifactIds = new Set();
const DEFAULT_SEARXNG_URL = "http://127.0.0.1:8888/search";

const closeEvidenceQuickEditor = ({ discard = false } = {}) => {
  evidenceQuickEditor.hidden = true;
  evidenceQuickStatusEl.textContent = "";
  if (discard) {
    pendingEvidenceSelection = null;
    renderReviewWorkspace();
  }
};

const openEvidenceQuickEditor = (rect = null) => {
  if (!pendingEvidenceSelection || !activeSourceWorkspace) return;
  evidenceQuickTitleEl.textContent = activeSourceWorkspace.source.title;
  evidenceQuickKindEl.textContent = pendingEvidenceSelection.evidence_type === "snapshot"
    ? "Snapshot Evidence" : "Text Evidence";
  evidenceQuickPreviewEl.textContent = pendingEvidenceSelection.quote || "Selected region";
  evidenceQuickArtifactSelect.replaceChildren(new Option("Evidence only", ""));
  artifacts.forEach((artifact) => evidenceQuickArtifactSelect.appendChild(
    new Option(`Evidence + ${artifact.title}`, artifact.id),
  ));
  evidenceQuickTagsInput.value = "";
  evidenceQuickAnnotationInput.value = "";
  evidenceQuickStatusEl.textContent = "";
  evidenceQuickEditor.hidden = false;
  const anchor = rect || { left: innerWidth / 2 - 172, bottom: innerHeight / 2 - 120 };
  const left = Math.max(12, Math.min(innerWidth - 356, anchor.left));
  const top = Math.max(12, Math.min(innerHeight - 390, anchor.bottom + 8));
  evidenceQuickEditor.style.left = `${left}px`;
  evidenceQuickEditor.style.top = `${top}px`;
};

const fetchCompanionInbox = async () => {
  try {
    const response = await fetch("/api/companion/inbox");
    if (!response.ok) return;
    companionInboxItems = (await response.json()).items || [];
    renderCompanionInbox();
  } catch (_) {
    // Knowte can continue normally when the optional companion is unavailable.
  }
};

const renderCompanionInbox = () => {
  companionInboxEl.hidden = companionInboxItems.length === 0;
  companionInboxCountEl.textContent = `${companionInboxItems.length} pending`;
  if (companionInboxItems.length) {
    contextPanelToggleBtn.classList.add("has-selection");
    if (!Number(contextToggleCountEl.textContent || 0)) {
      contextToggleCountEl.textContent = String(companionInboxItems.length);
    }
  }
  companionInboxListEl.replaceChildren();
  companionInboxItems.forEach((item) => {
    const card = document.createElement("article");
    card.className = "companion-inbox-item";
    const title = document.createElement("strong");
    title.textContent = item.source?.title || item.source?.url || "Web Source";
    const meta = document.createElement("small");
    meta.textContent = `${item.kind === "text" ? "Text Evidence" : item.kind === "snapshot" ? "Snapshot Evidence" : "Source"} · Original web`;
    const quote = document.createElement("p");
    quote.textContent = item.quote || "Save this page to Sources.";
    const target = document.createElement("select");
    target.appendChild(new Option("Sources only", ""));
    artifacts.forEach((artifact) => target.appendChild(
      new Option(`Sources + ${artifact.title}`, artifact.id),
    ));
    const confirm = document.createElement("button");
    confirm.type = "button";
    confirm.className = "context-primary-action";
    confirm.textContent = "Confirm";
    confirm.addEventListener("click", async () => {
      confirm.disabled = true;
      companionInboxStatusEl.textContent = "Saving Companion capture…";
      try {
        const response = await fetch(`/api/companion/inbox/${item.id}/confirm`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ artifact_id: target.value }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "Could not confirm capture.");
        companionInboxStatusEl.textContent = "Saved to Sources.";
        await Promise.all([fetchCompanionInbox(), fetchLibrary(), fetchArtifacts()]);
      } catch (error) {
        companionInboxStatusEl.textContent = error.message;
        confirm.disabled = false;
      }
    });
    const discard = document.createElement("button");
    discard.type = "button";
    discard.className = "danger-action";
    discard.textContent = "Discard";
    discard.addEventListener("click", async () => {
      await fetch(`/api/companion/inbox/${item.id}`, { method: "DELETE" });
      await fetchCompanionInbox();
    });
    const actions = document.createElement("div");
    actions.className = "companion-inbox-actions";
    actions.append(confirm, discard);
    card.append(title, meta, quote, target, actions);
    companionInboxListEl.appendChild(card);
  });
};

companionPairingGenerateBtn.addEventListener("click", async () => {
  companionPairingGenerateBtn.disabled = true;
  try {
    const response = await fetch("/api/companion/pairing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        theme: document.body.dataset.theme === "light" ? "light" : "dark",
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Could not generate key.");
    companionPairingKeyInput.value = `${data.code}.${data.nonce}`;
    companionPairingKeyInput.select();
  } finally {
    companionPairingGenerateBtn.disabled = false;
  }
});

companionPathCopyBtn.addEventListener("click", async () => {
  companionPathCopyBtn.disabled = true;
  try {
    const response = await fetch("/api/companion/info");
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Could not locate the extension.");
    try {
      await navigator.clipboard.writeText(data.path);
    } catch (_) {
      const temporary = document.createElement("textarea");
      temporary.value = data.path;
      temporary.style.position = "fixed";
      temporary.style.opacity = "0";
      document.body.appendChild(temporary);
      temporary.select();
      document.execCommand("copy");
      temporary.remove();
    }
    const platform = navigator.userAgentData?.platform || navigator.platform || "";
    const pickerSteps = /mac/i.test(platform)
      ? "In the folder picker: ⌘⇧G → ⌘V → Enter → Select."
      : /win/i.test(platform)
        ? "In the folder picker: Ctrl+L → Ctrl+V → Enter → Select Folder."
        : "In the folder picker: Ctrl+L → Ctrl+V → Enter → Select.";
    companionPathStatusEl.textContent = `Path copied. ${pickerSteps}`;
  } catch (error) {
    companionPathStatusEl.textContent = error.message;
  } finally {
    companionPathCopyBtn.disabled = false;
  }
});

const parseCopilotParameterValue = (value) => {
  try {
    return JSON.parse(value);
  } catch (_) {
    throw new Error("Advanced parameter values must use valid JSON syntax.");
  }
};

const copilotAdvancedParameters = () => {
  const parameters = Object.create(null);
  aiCopilotParameterList.querySelectorAll(".copilot-parameter-row").forEach((row) => {
    const key = row.querySelector(".copilot-parameter-key").value.trim();
    const rawValue = row.querySelector(".copilot-parameter-value").value.trim();
    if (!key && !rawValue) return;
    if (!key) throw new Error("Each Advanced parameter needs a key.");
    if (!/^[A-Za-z][A-Za-z0-9_.-]{0,63}$/.test(key)) {
      throw new Error(`Invalid Advanced parameter key: ${key}.`);
    }
    if (["model", "messages", "temperature", "max_tokens", "stream", "chat_template_kwargs"].includes(key)) {
      throw new Error(`${key} is managed by Knowte and cannot be overridden.`);
    }
    if (Object.hasOwn(parameters, key)) throw new Error(`Duplicate Advanced parameter: ${key}.`);
    parameters[key] = parseCopilotParameterValue(rawValue);
  });
  return parameters;
};

const addCopilotParameterRow = (key = "", value = "") => {
  const row = document.createElement("div");
  row.className = "copilot-parameter-row";
  row.innerHTML = `
    <input class="copilot-parameter-key" type="text" aria-label="Parameter key" placeholder="parameter" />
    <input class="copilot-parameter-value" type="text" aria-label="Parameter JSON value" placeholder="JSON value" />
    <button type="button" class="copilot-parameter-remove" aria-label="Remove parameter">×</button>
  `;
  row.querySelector(".copilot-parameter-key").value = key;
  row.querySelector(".copilot-parameter-value").value = value;
  row.querySelector(".copilot-parameter-remove").addEventListener("click", () => {
    row.remove();
    updateProfileDirtyState();
  });
  row.querySelectorAll("input").forEach((field) => field.addEventListener("input", updateProfileDirtyState));
  aiCopilotParameterList.appendChild(row);
};

const renderCopilotAdvancedParameters = (parameters = { top_p: 0.9 }) => {
  aiCopilotParameterList.replaceChildren();
  Object.entries(parameters).forEach(([key, value]) => {
    addCopilotParameterRow(key, JSON.stringify(value));
  });
};

aiCopilotAddParameterBtn.addEventListener("click", () => {
  addCopilotParameterRow();
  aiCopilotParameterList.lastElementChild?.querySelector("input")?.focus();
  updateProfileDirtyState();
});

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
  ai_copilot_instructions: overrides.ai_copilot_instructions
    ?? aiCopilotInstructionsInput.value.trim(),
  ai_copilot_temperature: overrides.ai_copilot_temperature
    ?? Number(aiCopilotTemperatureInput.value || 0),
  ai_copilot_max_tokens: overrides.ai_copilot_max_tokens
    ?? Number(aiCopilotMaxTokensInput.value || 1200),
  ai_copilot_advanced_parameters: overrides.ai_copilot_advanced_parameters
    ?? copilotAdvancedParameters(),
  ai_api_key_update: aiApiKeyInput.value.trim(),
  ai_api_key_clear: aiApiKeyRemovalPending,
  ai_embedding_api_key_update: aiEmbeddingApiKeyInput.value.trim(),
  ai_embedding_api_key_clear: aiEmbeddingApiKeyRemovalPending,
});

const isConfigDirty = () => {
  if (savedProfileState === null) return false;
  try {
    return serializeProfileState() !== savedProfileState;
  } catch (_) {
    return true;
  }
};

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

const clearDisplayedSearchResults = () => {
  if (searchController) {
    searchController.abort();
    searchController = null;
  }
  intelligentRunToken += 1;
  isSearching = false;
  isIntelligentSearching = false;
  fullResults = [];
  selectedResultKeys.clear();
  lastQuery = "";
  lastAreas = "";
  lastYearFrom = "";
  lastYearTo = "";
  lastBackends = [];
  canFindMore = false;
  canFindMoreWeb = false;
  lastSearchHasWeb = false;
  lastSearchHasAcademic = false;
  pageSelectTop.value = "1";
  resultsEl.replaceChildren();
  intelligentProgressEl.hidden = true;
  setSearching(false);
  renderPaginationControls();
};

const setSearchMode = (mode) => {
  const nextMode = mode === "smart" ? "smart" : "keyword";
  const modeChanged = nextMode !== searchMode;
  searchMode = nextMode;
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
  if (modeChanged) {
    clearDisplayedSearchResults();
    statusEl.textContent = searchMode === "smart"
      ? "Intelligent mode ready. Describe what you want to understand."
      : "Keyword mode ready. Enter a query to search providers directly.";
  }
};

const renderDefaultSearchMode = () => {
  defaultSearchModeButtons.forEach((button) => {
    const isDefault = button.dataset.defaultSearchMode === defaultSearchMode;
    const label = isDefault ? "Default search mode" : "Set as default";
    const modeName = button.dataset.defaultSearchMode === "intelligent"
      ? "Intelligent"
      : "Keyword";
    button.classList.toggle("is-default", isDefault);
    button.textContent = isDefault ? "★" : "☆";
    button.setAttribute("aria-pressed", String(isDefault));
    button.setAttribute(
      "aria-label",
      isDefault
        ? `${modeName} is the default search mode`
        : `Set ${modeName} as the default search mode`,
    );
    button.title = label;
  });
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
  scrollTopBtn.style.visibility = fullResults.length ? "visible" : "hidden";
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

const CONTROL_ICONS = {
  inspect: [
    ["circle", { cx: "11", cy: "11", r: "6.5" }],
    ["path", { d: "m16 16 4.25 4.25" }],
  ],
  delete: [
    ["path", { d: "M4.5 7h15M9 7V4.5h6V7M7 7l.75 13h8.5L17 7" }],
    ["path", { d: "M10 10.5v6M14 10.5v6" }],
  ],
  accept: [
    ["path", { d: "m5 12.5 4.2 4.2L19 7" }],
  ],
  discard: [
    ["path", { d: "M7 7l10 10M17 7 7 17" }],
  ],
  disputed: [
    ["path", { d: "M12 4 3.5 19h17L12 4Z" }],
    ["path", { d: "M12 9v4M12 16.5h.01" }],
  ],
};

const createControlIcon = (iconName) => {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  for (const [tag, attributes] of CONTROL_ICONS[iconName] || []) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, value));
    svg.appendChild(node);
  }
  return svg;
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

const resultKey = (source) => String(
  source.id || source.doi_url || source.paper_url || source.url || source.title || "",
);

const selectedResults = () => fullResults.filter(
  (source) => selectedResultKeys.has(resultKey(source)),
);

const selectedLibrarySources = () => librarySources.filter(
  (source) => selectedLibrarySourceKeys.has(resultKey(source)),
);

const selectedClaims = () => [...selectedClaimIds]
  .map((id) => claims.find((claim) => claim.id === id))
  .filter(Boolean);

const activeView = () => views.find((view) => view.id === activeViewId) || null;
const viewTypeLabel = (value) => ({
  wiki: "Wiki",
  article: "Article",
  graph: "Claim graph",
}[value] || value);

const currentReviewContext = () => {
  const panelId = document.querySelector(".panel-view.is-active")?.id;
  if (panelId === "sources-panel") return "library";
  if (panelId === "evidence-panel") return "evidence";
  if (panelId === "claims-panel") return "claims";
  if (panelId === "views-panel") return "views";
  if (panelId === "create-panel") return "artifact";
  if (panelId === "plans-panel") return "plans";
  if (panelId === "config-panel") return "config";
  return "search";
};

const activeReviewSources = () => (
  currentReviewContext() === "library" ? selectedLibrarySources()
    : currentReviewContext() === "search" ? selectedResults() : []
);

const activeReviewArtifact = () => (
  currentReviewContext() === "views" && activeView()?.artifact
    ? activeView().artifact
    : ["search", "artifact"].includes(currentReviewContext())
      ? artifacts.find((artifact) => artifact.id === collectArtifactSelect.value) || null
      : null
);

const selectedEvidence = () => (
  activeSourceWorkspace
    ? activeSourceWorkspace.evidence.filter((item) => selectedEvidenceIds.has(item.id))
    : currentReviewContext() === "evidence"
      ? libraryEvidence.filter((item) => selectedEvidenceIds.has(item.id))
      : []
);

const updateSelectAllState = (input, selectedCount, totalCount) => {
  if (!input) return;
  input.checked = totalCount > 0 && selectedCount === totalCount;
  input.indeterminate = selectedCount > 0 && selectedCount < totalCount;
  input.disabled = totalCount === 0;
};

const renderChatContext = () => {
  const sourceCount = chatContextSources.size;
  const evidenceCount = chatContextEvidence.size;
  const total = sourceCount + evidenceCount;
  const currentView = currentReviewContext() === "views" ? activeView() : null;
  chatContextSummaryEl.textContent = total
    ? `${sourceCount} Source${sourceCount === 1 ? "" : "s"} · ${evidenceCount} Evidence`
    : currentView ? `Current View included · ${currentView.title}` : "No context attached";
  chatContextTrayEl.replaceChildren();
  const appendChip = (type, key, label, collection) => {
    const chip = document.createElement("div");
    chip.className = "chat-context-chip";
    const text = document.createElement("span");
    text.textContent = `${type} · ${label}`;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "semantic-action is-destructive";
    remove.textContent = "×";
    remove.setAttribute("aria-label", `Remove ${label} from chat context`);
    remove.addEventListener("click", () => {
      collection.delete(key);
      chatContextStatusEl.textContent = "";
      renderChatContext();
    });
    chip.append(text, remove);
    chatContextTrayEl.appendChild(chip);
  };
  chatContextSources.forEach((source, key) => appendChip(
    "Source", key, source.title || "Untitled Source", chatContextSources,
  ));
  chatContextEvidence.forEach((entry, key) => appendChip(
    "Evidence", key, entry.locator || entry.quote || "Evidence", chatContextEvidence,
  ));
  const selectionCount = activeReviewSources().length + selectedEvidence().length;
  chatContextAddBtn.disabled = selectionCount === 0;
  chatContextClearBtn.disabled = total === 0;
};

const addSelectionToChatContext = () => {
  const sources = activeReviewSources();
  const evidence = selectedEvidence();
  const newSourceEntries = sources.filter(
    (source) => !chatContextSources.has(resultKey(source)),
  );
  const newEvidenceEntries = evidence.filter(
    (item) => !chatContextEvidence.has(item.id),
  );
  const nextTotal = chatContextSources.size + chatContextEvidence.size
    + newSourceEntries.length + newEvidenceEntries.length;
  if (nextTotal > CHAT_CONTEXT_LIMIT) {
    chatContextStatusEl.textContent = (
      `Context supports ${CHAT_CONTEXT_LIMIT} items. Remove or deselect ${nextTotal - CHAT_CONTEXT_LIMIT}, then try again.`
    );
    return;
  }
  const nextSnapshotCount = [...chatContextEvidence.values()].filter(
    (item) => item.evidence_type === "snapshot",
  ).length + newEvidenceEntries.filter(
    (item) => item.evidence_type === "snapshot",
  ).length;
  if (nextSnapshotCount > CHAT_SNAPSHOT_LIMIT) {
    chatContextStatusEl.textContent = (
      `Chat supports ${CHAT_SNAPSHOT_LIMIT} Snapshot Evidence items at a time. Remove or deselect ${nextSnapshotCount - CHAT_SNAPSHOT_LIMIT}, then try again.`
    );
    return;
  }
  newSourceEntries.forEach((source) => chatContextSources.set(resultKey(source), source));
  newEvidenceEntries.forEach((item) => chatContextEvidence.set(item.id, {
    ...item,
    source_title: item.source_title || activeSourceWorkspace?.source.title || "",
    source_id: item.source_id || activeSourceWorkspace?.source.id || "",
  }));
  chatContextStatusEl.textContent = newSourceEntries.length || newEvidenceEntries.length
    ? "Added to chat context." : "This item is already in chat context.";
  renderChatContext();
};

chatContextAddBtn.addEventListener("click", addSelectionToChatContext);
chatContextClearBtn.addEventListener("click", () => {
  chatContextSources.clear();
  chatContextEvidence.clear();
  chatContextStatusEl.textContent = "Chat context cleared.";
  renderChatContext();
});

resultsSelectAllInput.addEventListener("change", () => {
  fullResults.forEach((source) => {
    const key = resultKey(source);
    if (resultsSelectAllInput.checked) selectedResultKeys.add(key);
    else selectedResultKeys.delete(key);
  });
  renderResults();
});

librarySelectAllInput.addEventListener("change", () => {
  librarySources.forEach((source) => {
    const key = resultKey(source);
    if (librarySelectAllInput.checked) selectedLibrarySourceKeys.add(key);
    else selectedLibrarySourceKeys.delete(key);
  });
  renderLibrary();
  renderReviewWorkspace();
});

evidenceLibrarySelectAllInput.addEventListener("change", () => {
  visibleEvidence().forEach((item) => {
    if (evidenceLibrarySelectAllInput.checked) selectedEvidenceIds.add(item.id);
    else selectedEvidenceIds.delete(item.id);
  });
  renderEvidenceLibrary();
  renderReviewWorkspace();
});

evidenceTagFilterInput.addEventListener("change", () => {
  renderEvidenceLibrary();
  const filtered = visibleEvidence();
  evidenceStatusEl.textContent = evidenceTagFilterInput.value
    ? `${filtered.length} of ${libraryEvidence.length} Evidence · Tag: ${evidenceTagFilterInput.value}`
    : `${libraryEvidence.length} Evidence`;
});

claimsSelectAllInput.addEventListener("change", () => {
  visibleClaims().forEach((claim) => {
    if (viewAddingClaims && viewDraftClaimIds.includes(claim.id)) return;
    if (claimsSelectAllInput.checked) selectedClaimIds.add(claim.id);
    else selectedClaimIds.delete(claim.id);
  });
  renderClaims();
  renderReviewWorkspace();
});

claimsTagFilterInput.addEventListener("change", () => {
  renderClaims();
  updateClaimsStatus();
});

claimsReviewFilterInput.addEventListener("change", () => {
  renderClaims();
  updateClaimsStatus();
});

const copySelectedEvidenceToClaimDraft = () => {
  libraryEvidence.forEach((item) => {
    if (selectedEvidenceIds.has(item.id)) {
      incomingClaimEvidenceIds.add(item.id);
      if (!incomingClaimEvidenceStances.has(item.id)) {
        incomingClaimEvidenceStances.set(item.id, "supports");
      }
    }
  });
  if (incomingClaimEvidenceIds.size && claimBasisInput.value === "background") {
    claimBasisInput.value = "reported";
  }
  renderIncomingTrays();
};

evidenceCreateClaimBtn.addEventListener("click", () => {
  if (!selectedEvidenceIds.size) return;
  copySelectedEvidenceToClaimDraft();
  evidenceReturnToClaim = false;
  showPanel("claims-panel");
  claimStatementInput.focus();
});

claimAddEvidenceBtn.addEventListener("click", () => {
  evidenceReturnToClaim = true;
  renderEvidenceLibrary();
  showPanel("evidence-panel");
});

evidenceHandoffApplyBtn.addEventListener("click", () => {
  copySelectedEvidenceToClaimDraft();
  evidenceReturnToClaim = false;
  renderEvidenceLibrary();
  showPanel("claims-panel");
});

evidenceHandoffCancelBtn.addEventListener("click", () => {
  evidenceReturnToClaim = false;
  renderEvidenceLibrary();
  showPanel("claims-panel");
});

claimsBuildViewBtn.addEventListener("click", () => {
  activeViewId = "";
  viewAddingClaims = false;
  setViewDetailMode(false);
  selectedClaimIds.forEach((id) => incomingViewClaimIds.add(id));
  claimsReturnToView = false;
  renderIncomingTrays();
  showPanel("views-panel");
  viewTitleInput.focus();
});

viewAddClaimsBtn.addEventListener("click", () => {
  incomingViewClaimIds.clear();
  renderIncomingTrays();
  viewsStatusEl.textContent = "Incoming Claims cleared.";
});

claimsHandoffApplyBtn.addEventListener("click", () => {
  if (viewAddingClaims && activeViewId) {
    selectedClaimIds.forEach((id) => {
      if (!viewDraftClaimIds.includes(id)) {
        viewDraftClaimIds.push(id);
        if (["wiki", "article"].includes(viewEditTypeInput.value)) {
          viewDraftBlocks.push({
            id: crypto.randomUUID().replaceAll("-", ""),
            block_type: "claim", content: "", claim_id: id,
          });
        }
      }
    });
  } else {
    selectedClaimIds.forEach((id) => incomingViewClaimIds.add(id));
  }
  claimsReturnToView = false;
  viewAddingClaims = false;
  renderClaims();
  renderIncomingTrays();
  showPanel("views-panel");
  if (activeViewId) {
    setViewDetailMode(true);
    renderViewDetail();
  }
});

claimsHandoffCancelBtn.addEventListener("click", () => {
  claimsReturnToView = false;
  viewAddingClaims = false;
  renderClaims();
  showPanel("views-panel");
  if (activeViewId) {
    setViewDetailMode(true);
    renderViewDetail();
  }
});

reviewStageAdvanceBtn.addEventListener("click", () => {
  const context = currentReviewContext();
  reviewStageStatusEl.textContent = "";
  if (context === "claims") {
    if (!selectedClaimIds.size) return;
    activeViewId = "";
    setViewDetailMode(false);
    selectedClaimIds.forEach((id) => incomingViewClaimIds.add(id));
    renderIncomingTrays();
    showPanel("views-panel");
    viewTitleInput.focus();
  }
});

evidenceSelectAllInput.addEventListener("change", () => {
  (activeSourceWorkspace?.evidence || []).forEach((item) => {
    if (evidenceSelectAllInput.checked) selectedEvidenceIds.add(item.id);
    else selectedEvidenceIds.delete(item.id);
  });
  if (!evidenceSelectAllInput.checked && annotationTarget?.type === "evidence") {
    annotationTarget = { type: "source", id: activeSourceWorkspace.source.id };
  }
  renderReviewWorkspace();
});

const setChatExpanded = (expanded) => {
  chatExpanded = Boolean(expanded);
  chatWorkspace.hidden = !chatExpanded;
  chatExpandBtn.setAttribute("aria-expanded", String(chatExpanded));
  if (chatExpanded) {
    chatWorkspaceContextEl.textContent = contextModeLabelEl.textContent;
    chatWorkspaceBody.append(reviewCopilotSection, contextChatForm);
    if (window.innerWidth <= 1270) {
      contextPanel.classList.remove("is-open");
      contextPanelToggleBtn.setAttribute("aria-expanded", "false");
    }
    window.requestAnimationFrame(() => contextChatInput.focus());
  } else {
    contextPanelBody.appendChild(reviewCopilotSection);
    contextPanel.appendChild(contextChatForm);
  }
  contextChatEl.scrollTop = contextChatEl.scrollHeight;
};

chatExpandBtn.addEventListener("click", () => setChatExpanded(true));
chatCollapseBtn.addEventListener("click", () => setChatExpanded(false));

const renderReviewWorkspace = () => {
  const context = currentReviewContext();
  const selected = activeReviewSources();
  const evidenceSelection = selectedEvidence();
  const libraryEvidenceMode = context === "evidence";
  const activeArtifact = activeReviewArtifact();
  const currentView = activeView();
  const contextNames = {
    search: "Search",
    library: "Sources",
    evidence: "Evidence",
    claims: "Claims",
    views: "Views",
    artifact: "Project",
    plans: "Plans",
    config: "Config",
  };
  const nextReviewContextKey = context === "views" && currentView
    ? `views:${currentView.id}` : context;
  const contextChanged = activeReviewContextKey !== nextReviewContextKey;
  activeReviewContextKey = nextReviewContextKey;
  reviewConversations[activeReviewContextKey] ||= [];
  const selectionCount = libraryEvidenceMode
    ? evidenceSelection.length
    : context === "artifact"
    ? Number(activeArtifact?.source_count || 0)
    : context === "claims" ? selectedClaims().length
    : context === "views"
      ? (currentView?.claims?.length || incomingViewClaimIds.size) : selected.length;
  contextModeLabelEl.textContent = context === "library"
    ? `Sources · ${librarySources.length} Source${librarySources.length === 1 ? "" : "s"}`
    : context === "evidence"
      ? `Evidence · ${libraryEvidence.length} total`
    : context === "claims"
      ? `Claims · ${claims.length} total`
    : context === "views"
      ? currentView
        ? `View · ${currentView.title}`
        : `Views · ${views.length} total`
    : context === "artifact"
      ? `Project · ${activeArtifact?.title || "No active Project"}`
      : context === "plans"
        ? `Plans · ${savedPlans.length} saved`
        : context === "config"
          ? "Config · Local settings"
          : `Search · ${selected.length || "No"} selection${selected.length === 1 ? "" : "s"}`;
  contextSelectionLabelEl.textContent = context === "evidence"
    ? "Selected Evidence"
    : context === "artifact"
    ? "Active Project"
    : context === "claims"
      ? "Selected Claims"
    : context === "views"
      ? currentView ? "Current View" : "View draft"
    : context === "plans"
      ? "Saved Plans"
      : context === "config"
        ? "Scope"
        : "Selection";
  contextSelectedCountEl.textContent = context === "evidence"
    ? `${evidenceSelection.length} selected`
    : context === "artifact"
    ? `${selectionCount} linked`
    : context === "claims"
      ? `${selectedClaims().length} selected`
    : context === "views"
      ? currentView
        ? `${currentView.claims?.length || 0} Claims`
        : `${incomingViewClaimIds.size} incoming`
    : context === "plans"
      ? `${savedPlans.length} saved`
      : context === "config"
        ? "Operational"
        : `${selected.length} selected`;
  contextToggleCountEl.textContent = String(
    context === "search" || context === "library"
      ? selected.length : selectionCount,
  );
  contextPanelToggleBtn.classList.toggle("has-selection", selectionCount > 0);
  reviewActionsSection.hidden = context !== "search";
  evidenceSelectionOverviewEl.hidden = context !== "evidence";
  if (context === "evidence") {
    const sourceCount = new Set(evidenceSelection.map((item) => item.source_id).filter(Boolean)).size;
    const snapshotCount = evidenceSelection.filter((item) => item.evidence_type === "snapshot").length;
    const textCount = evidenceSelection.length - snapshotCount;
    const linkedCount = evidenceSelection.filter((item) => Number(item.claim_count || 0) > 0).length;
    evidenceProfileSummaryEl.textContent = `${evidenceSelection.length} item${evidenceSelection.length === 1 ? "" : "s"}`;
    evidenceProfileSourcesEl.textContent = String(sourceCount);
    evidenceProfileTextEl.textContent = String(textCount);
    evidenceProfileSnapshotsEl.textContent = String(snapshotCount);
    evidenceProfileLinkedEl.textContent = String(linkedCount);
  }
  reviewStageActionsSection.hidden = context !== "claims";
  if (context === "claims") {
    reviewStageAdvanceBtn.disabled = selectedClaims().length === 0;
    reviewStageAdvanceBtn.textContent = selectedClaims().length
      ? `Build View from ${selectedClaims().length} Claim${selectedClaims().length === 1 ? "" : "s"}`
      : "Build View";
  }
  reviewKnowledgeSection.hidden = context !== "library" || !activeSourceWorkspace;
  const copilotAvailable = ["search", "library", "evidence", "claims", "views", "artifact"].includes(context);
  if (!copilotAvailable && chatExpanded) setChatExpanded(false);
  reviewCopilotSection.hidden = !copilotAvailable;
  contextChatForm.hidden = !copilotAvailable;
  if (chatExpanded) chatWorkspaceContextEl.textContent = contextModeLabelEl.textContent;
  contextChatInput.placeholder = context === "library"
    ? "Discuss selected Sources…"
    : context === "evidence"
      ? "Discuss selected Evidence…"
    : context === "claims"
      ? "Discuss selected Claims and their Evidence…"
    : context === "views"
      ? "Discuss this View and its Claims…"
    : context === "artifact"
      ? "Discuss this Project…"
      : "Discuss this selection with the LLM…";
  contextSelectionListEl.replaceChildren();

  const appendContextItem = (label, removeCallback = null, openCallback = null) => {
    const row = document.createElement("div");
    row.className = "context-selection-item";
    const title = document.createElement(openCallback ? "button" : "span");
    title.textContent = label;
    if (openCallback) {
      title.type = "button";
      title.className = "context-selection-open";
      title.title = "Inspect Source";
      title.addEventListener("click", openCallback);
    }
    row.appendChild(title);
    if (removeCallback) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Remove ${label} from selection`);
      remove.addEventListener("click", removeCallback);
      row.appendChild(remove);
    }
    contextSelectionListEl.appendChild(row);
  };

  if (context === "evidence") {
    evidenceSelection.forEach((item) => appendContextItem(
      `${item.source_title || "Untitled Source"} · ${item.locator || "Evidence"}`,
      () => {
        selectedEvidenceIds.delete(item.id);
        renderEvidenceLibrary();
        renderReviewWorkspace();
      },
      () => openEvidenceDetail(item.id),
    ));
    if (!evidenceSelection.length) {
      const empty = document.createElement("p");
      empty.textContent = "No Evidence selected.";
      contextSelectionListEl.appendChild(empty);
    }
  } else if (["search", "library"].includes(context) && !selected.length) {
    const empty = document.createElement("p");
      empty.textContent = context === "search"
      ? "No search results selected."
      : "No Sources selected.";
    contextSelectionListEl.appendChild(empty);
  } else if (["search", "library"].includes(context)) {
    selected.forEach((source) => {
      appendContextItem(source.title || "Untitled Source", () => {
        if (context === "library") {
          selectedLibrarySourceKeys.delete(resultKey(source));
          renderLibrary();
        } else {
          selectedResultKeys.delete(resultKey(source));
          renderResults();
        }
        renderReviewWorkspace();
      }, context === "library" ? () => openSourceReader(source.id) : null);
    });
  } else if (context === "artifact") {
    if (activeArtifact) {
      appendContextItem(activeArtifact.title);
      const purpose = document.createElement("p");
      purpose.textContent = activeArtifact.purpose;
      contextSelectionListEl.appendChild(purpose);
    } else {
      const empty = document.createElement("p");
      empty.textContent = "No active Project.";
      contextSelectionListEl.appendChild(empty);
    }
  } else if (context === "claims") {
    const chosenClaims = selectedClaims();
    chosenClaims.forEach((claim) => appendContextItem(claim.statement, () => {
      selectedClaimIds.delete(claim.id);
      renderClaims();
      renderReviewWorkspace();
    }));
    if (!chosenClaims.length) {
      const empty = document.createElement("p");
      empty.textContent = "No Claims selected.";
      contextSelectionListEl.appendChild(empty);
    }
  } else if (context === "views") {
    if (currentView) {
      appendContextItem(currentView.title);
      const detail = document.createElement("p");
      detail.textContent = [
        currentView.artifact?.title ? `Project: ${currentView.artifact.title}` : "Standalone View",
        currentView.purpose || currentView.artifact?.purpose || "No Purpose added.",
        `${currentView.claims?.length || 0} Claims`,
      ].join(" · ");
      contextSelectionListEl.appendChild(detail);
    } else {
      const draft = document.createElement("p");
      draft.textContent = incomingViewClaimIds.size
        ? `${incomingViewClaimIds.size} incoming Claim${incomingViewClaimIds.size === 1 ? "" : "s"} ready to organize.`
        : "Open a saved View or add Claims to a new View draft.";
      contextSelectionListEl.appendChild(draft);
    }
  } else if (context === "plans") {
    savedPlans.slice(0, 6).forEach((plan) => appendContextItem(plan.name));
    if (!savedPlans.length) {
      const empty = document.createElement("p");
      empty.textContent = "No saved Plans.";
      contextSelectionListEl.appendChild(empty);
    }
  } else {
    const scope = document.createElement("p");
    scope.textContent = "Configuration controls infrastructure and is not part of the knowledge review context.";
    contextSelectionListEl.appendChild(scope);
  }

  contextCollectSelectedBtn.disabled = selected.length === 0;
  contextCollectSelectedBtn.textContent = selected.length
    ? (
        collectArtifactSelect.value
          ? `Add ${selected.length} Source${selected.length === 1 ? "" : "s"} to Sources & Project(s)`
          : `Add ${selected.length} Source${selected.length === 1 ? "" : "s"} to Sources`
      )
    : "Add selected Sources";
  renderKnowledgeReview();
  renderChatContext();
  if (contextChanged && copilotAvailable) renderReviewConversation();
};

const renderResults = () => {
  resultsEl.innerHTML = "";
  updateSelectAllState(resultsSelectAllInput, selectedResultKeys.size, fullResults.length);
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
    const key = resultKey(paper);
    const isSelected = selectedResultKeys.has(key);
    card.classList.toggle("is-selected", isSelected);

    const selection = document.createElement("label");
    selection.className = "result-selection";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = isSelected;
    checkbox.setAttribute("aria-label", `Select ${paper.title || "this Source"}`);
    const selectionText = document.createElement("span");
    selectionText.textContent = "Select";
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedResultKeys.add(key);
      } else {
        selectedResultKeys.delete(key);
      }
      card.classList.toggle("is-selected", checkbox.checked);
      updateSelectAllState(resultsSelectAllInput, selectedResultKeys.size, fullResults.length);
      renderReviewWorkspace();
    });
    selection.append(checkbox, selectionText);

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
    card.append(selection, title, meta, abstract);
    if (intelligence.childElementCount) card.appendChild(intelligence);
    if (actions.childElementCount) card.appendChild(actions);
    resultsEl.appendChild(card);
  });
  renderPaginationControls();
  renderReviewWorkspace();
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
    aiCopilotInstructionsInput.value = data.ai_copilot_instructions || "";
    aiCopilotTemperatureInput.value = String(data.ai_copilot_temperature ?? 0.2);
    aiCopilotMaxTokensInput.value = String(data.ai_copilot_max_tokens || 1200);
    renderCopilotAdvancedParameters(data.ai_copilot_advanced_parameters ?? { top_p: 0.9 });
    aiCopilotPromptPreviewEl.textContent = data.ai_copilot_prompt_preview || "";
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
    defaultSearchMode = data.default_search_mode === "intelligent"
      ? "intelligent"
      : "keyword";
    renderDefaultSearchMode();
    setSearchMode(defaultSearchMode === "intelligent" ? "smart" : "keyword");
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
        ai_copilot_instructions: aiCopilotInstructionsInput.value.trim(),
        ai_copilot_temperature: Number(aiCopilotTemperatureInput.value || 0),
        ai_copilot_max_tokens: Number(aiCopilotMaxTokensInput.value || 1200),
        ai_copilot_advanced_parameters: copilotAdvancedParameters(),
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
    aiCopilotInstructionsInput.value = data.ai_copilot_instructions || "";
    aiCopilotTemperatureInput.value = String(data.ai_copilot_temperature ?? 0.2);
    aiCopilotMaxTokensInput.value = String(data.ai_copilot_max_tokens || 1200);
    renderCopilotAdvancedParameters(data.ai_copilot_advanced_parameters ?? { top_p: 0.9 });
    aiCopilotPromptPreviewEl.textContent = data.ai_copilot_prompt_preview || "";
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
    setConfigStatus(
      error.message === "no_search_backends"
        ? "Select at least one search backend."
        : error.message === "save_failed"
          ? "Could not save config."
          : error.message,
    );
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
    const replay = data.debug_replay || {};
    const replayVerification = replay.unverified_count
      ? `${replay.verified_count || 0} previously verified and ${replay.unverified_count} unverified`
      : `${replay.verified_count || fullResults.length} previously verified`;
    const webDiagnostics = data.search_diagnostics?.websearch;
    const cacheHint = webDiagnostics?.cache_hits > 0
      && webDiagnostics?.external_requests === 0
      ? " Reused cached Web results."
      : "";
    const warningHint = warningMessages.length ? ` ${warningMessages.join(" ")}` : "";
    statusEl.textContent = data.debug_replay
      ? `Debug Replay: loaded ${data.count} saved Source(s) for “${data.query}” from the baseline Project. No provider, Web, Embedding, or LLM requests were made; active search filters were not applied.${sourceHint}`
      : `Found ${data.count} paper(s) for "${data.query}"${timeHint}.` + sourceHint + cacheHint + warningHint;
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
  selectedResultKeys.clear();
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
  selectedResultKeys.clear();
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
    intelligentBudgetEl.textContent = data.debug_replay
      ? "Debug Replay: 0 retrieval rounds · 0 embedding batches · 0 LLM requests"
      : `Actual pipeline work: ${budget.retrieval || 0} retrieval round(s) · ${budget.embedding || 0} embedding batch(es) · ${budget.chat || 0} LLM request(s)`;
    const expandedQueries = data.expanded_queries || [];
    if (academicEnabled && !data.debug_replay) {
      renderExpandedQueries(
        expandedQueries,
        stages.expand?.status || "complete",
      );
    } else if (data.debug_replay) {
      intelligentExpandedEl.hidden = true;
      intelligentExpandedEl.replaceChildren();
    }
    fullResults = data.results || [];
    updateUsage(data.usage);
    renderResults();
    if (fullResults.length) setFiltersCollapsed(true);
    const counts = data.candidate_counts || {};
    const sourceSummary = Object.entries(data.source_counts || {})
      .map(([source, count]) => `${source}: ${count}`)
      .join(", ");
    const sourceHint = sourceSummary ? ` Sources: ${sourceSummary}.` : "";
    const replay = data.debug_replay || {};
    const replayVerification = replay.unverified_count
      ? `${replay.verified_count || 0} previously verified and ${replay.unverified_count} unverified`
      : `${replay.verified_count || fullResults.length} previously verified`;
    const degraded = (data.warnings || []).length
      ? (
          stages.verify?.message
            ? ` LLM verification failed: ${stages.verify.message} Fallback results may be included.`
            : " Some AI stages degraded; fallback results may be included."
        )
      : "";
    statusEl.textContent = data.debug_replay
      ? `Debug Replay: loaded ${fullResults.length} baseline Source(s): ${replayVerification}. No retrieval, Embedding, or LLM verification requests were made; active search filters were not applied.${sourceHint}`
      : `Found ${fullResults.length} verified result(s) from ${counts.academic || 0} academic and ${counts.web || 0} Web candidate(s).${sourceHint}${degraded}`;
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

defaultSearchModeButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const requestedMode = button.dataset.defaultSearchMode;
    if (!requestedMode || requestedMode === defaultSearchMode) return;
    defaultSearchModeButtons.forEach((item) => {
      item.disabled = true;
    });
    try {
      const response = await fetch("/api/config/default-search-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: requestedMode }),
      });
      if (!response.ok) throw new Error("save_failed");
      const data = await response.json();
      defaultSearchMode = data.default_search_mode;
      renderDefaultSearchMode();
    } catch (_error) {
      button.title = "Could not save the default search mode";
    } finally {
      defaultSearchModeButtons.forEach((item) => {
        item.disabled = false;
      });
    }
  });
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
  document.querySelector("#search-panel .panel")?.scrollTo({
    top: 0,
    behavior: "smooth",
  });
});

const renderArtifactOptions = () => {
  const preferred = collectArtifactSelect.value
    || localStorage.getItem("knowte-active-artifact")
    || "";
  collectArtifactSelect.replaceChildren();
  const noArtifactOption = document.createElement("option");
  noArtifactOption.value = "";
  noArtifactOption.textContent = "Sources only";
  collectArtifactSelect.appendChild(noArtifactOption);
  artifacts.forEach((artifact) => {
    const option = document.createElement("option");
    option.value = artifact.id;
    option.textContent = `Sources + ${artifact.title}`;
    collectArtifactSelect.appendChild(option);
  });
  collectArtifactSelect.value = artifacts.some((item) => item.id === preferred)
    ? preferred
    : "";
  const claimPreferred = claimArtifactInput.value;
  claimArtifactInput.replaceChildren(new Option("Claims only", ""));
  artifacts.forEach((artifact) => {
    claimArtifactInput.appendChild(new Option(`Claims + ${artifact.title}`, artifact.id));
  });
  claimArtifactInput.value = artifacts.some((item) => item.id === claimPreferred)
    ? claimPreferred : "";
  const activeProjectId = collectArtifactSelect.value
    || localStorage.getItem("knowte-active-artifact") || "";
  const viewPreferred = viewProjectInput.value || activeProjectId;
  const editPreferred = viewEditProjectInput.value;
  viewProjectInput.replaceChildren(new Option("Standalone View", ""));
  viewEditProjectInput.replaceChildren(new Option("Standalone View", ""));
  artifacts.forEach((artifact) => {
    viewProjectInput.appendChild(new Option(artifact.title, artifact.id));
    viewEditProjectInput.appendChild(new Option(artifact.title, artifact.id));
  });
  viewProjectInput.value = artifacts.some((item) => item.id === viewPreferred)
    ? viewPreferred : "";
  viewEditProjectInput.value = artifacts.some((item) => item.id === editPreferred)
    ? editPreferred : "";
};

const renderContextPanel = () => {
  renderReviewWorkspace();
};

const renderTagChips = (container, tags = [], { editable = false, onEdit = null } = {}) => {
  container.replaceChildren();
  container.classList.add("entity-tag-strip");
  tags.forEach((tag) => {
    const chip = document.createElement("span");
    chip.className = "entity-tag-chip";
    chip.textContent = tag.name;
    container.appendChild(chip);
  });
  if (!tags.length) {
    const empty = document.createElement("small");
    empty.textContent = "No Tags";
    container.appendChild(empty);
  }
  if (editable && onEdit) {
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "entity-tag-edit";
    edit.textContent = "+ Tag";
    edit.addEventListener("click", onEdit);
    container.appendChild(edit);
  }
};

const openTagEditor = async (entityType, entityId, tags, afterSave) => {
  activeTagEditor = {
    entityType, entityId, names: tags.map((tag) => tag.name), afterSave,
  };
  tagEditorTypeEl.textContent = entityType[0].toUpperCase() + entityType.slice(1);
  const response = await fetch("/api/tags");
  const data = response.ok ? await response.json() : { tags: [] };
  tagEditorSuggestions.replaceChildren();
  (data.tags || []).forEach((tag) => {
    const option = document.createElement("option");
    option.value = tag.name;
    tagEditorSuggestions.appendChild(option);
  });
  renderTagEditor();
  tagEditorDialog.showModal();
  tagEditorInput.focus();
};

const renderTagEditor = () => {
  if (!activeTagEditor) return;
  tagEditorSelectedEl.replaceChildren();
  activeTagEditor.names.forEach((name) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "entity-tag-chip is-removable";
    chip.textContent = `${name} ×`;
    chip.addEventListener("click", () => {
      activeTagEditor.names = activeTagEditor.names.filter((item) => item !== name);
      renderTagEditor();
    });
    tagEditorSelectedEl.appendChild(chip);
  });
  if (!activeTagEditor.names.length) {
    const empty = document.createElement("small");
    empty.textContent = "No Tags";
    tagEditorSelectedEl.appendChild(empty);
  }
};

const saveTagEditor = async () => {
  if (!activeTagEditor) return;
  tagEditorSaveBtn.disabled = true;
  try {
    const response = await fetch("/api/tags/entity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entity_type: activeTagEditor.entityType,
        entity_id: activeTagEditor.entityId,
        tags: activeTagEditor.names,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Could not save Tags.");
    const afterSave = activeTagEditor.afterSave;
    tagEditorDialog.close();
    activeTagEditor = null;
    await afterSave?.(data.tags || []);
  } finally {
    tagEditorSaveBtn.disabled = false;
  }
};

tagEditorForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const name = tagEditorInput.value.trim();
  if (!name || !activeTagEditor) return;
  if (!activeTagEditor.names.some((item) => item.toLocaleLowerCase() === name.toLocaleLowerCase())) {
    activeTagEditor.names.push(name);
  }
  tagEditorInput.value = "";
  renderTagEditor();
  tagEditorInput.focus();
});
tagEditorSaveBtn.addEventListener("click", saveTagEditor);
tagEditorCloseBtn.addEventListener("click", () => tagEditorDialog.close());
tagEditorDialog.addEventListener("click", (event) => {
  if (event.target === tagEditorDialog) tagEditorDialog.close();
});

const renderArtifacts = () => {
  artifactListEl.replaceChildren();
  if (!artifacts.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = "No Projects yet. Create one with a concrete Purpose, then collect Sources for it from Search.";
    artifactListEl.appendChild(empty);
    return;
  }
  artifacts.forEach((artifact) => {
    const card = document.createElement("article");
    card.className = "artifact-card";

    const head = document.createElement("div");
    head.className = "artifact-card-head";
    const title = document.createElement("strong");
    title.textContent = artifact.title;
    const state = document.createElement("span");
    state.className = "artifact-state";
    state.textContent = artifact.status;
    head.append(title, state);

    const purpose = document.createElement("p");
    purpose.textContent = artifact.purpose;
    const meta = document.createElement("small");
    meta.textContent = `${artifact.source_count || 0} linked Source${artifact.source_count === 1 ? "" : "s"}`;
    const tagStrip = document.createElement("div");
    renderTagChips(tagStrip, artifact.tags, {
      editable: true,
      onEdit: () => openTagEditor("artifact", artifact.id, artifact.tags || [], async () => {
        await fetchArtifacts();
      }),
    });
    const linkedSources = librarySources.filter((source) => (
      source.artifacts || []
    ).some((linkedArtifact) => linkedArtifact.id === artifact.id));

    const actions = document.createElement("div");
    actions.className = "artifact-card-actions";
    const collect = document.createElement("button");
    collect.type = "button";
    collect.textContent = collectArtifactSelect.value === artifact.id
      ? "Active in Search"
      : "Collect Sources";
    collect.disabled = collectArtifactSelect.value === artifact.id;
    collect.addEventListener("click", () => {
      collectArtifactSelect.value = artifact.id;
      localStorage.setItem("knowte-active-artifact", artifact.id);
      renderArtifacts();
      showPanel("search-panel");
      statusEl.textContent = `“${artifact.title}” is selected as the Review workspace target.`;
      input.focus();
    });
    actions.appendChild(collect);
    const toggleSources = document.createElement("button");
    toggleSources.type = "button";
    const isExpanded = expandedArtifactIds.has(artifact.id);
    toggleSources.textContent = isExpanded
      ? "Hide Sources"
      : `Show Sources (${artifact.source_count || 0})`;
    toggleSources.setAttribute("aria-expanded", String(isExpanded));
    toggleSources.disabled = !artifact.source_count;
    toggleSources.addEventListener("click", () => {
      if (expandedArtifactIds.has(artifact.id)) {
        expandedArtifactIds.delete(artifact.id);
      } else {
        expandedArtifactIds.add(artifact.id);
      }
      renderArtifacts();
    });
    actions.appendChild(toggleSources);

    card.append(head, purpose, tagStrip, meta, actions);
    if (isExpanded) {
      const sourceList = document.createElement("div");
      sourceList.className = "artifact-source-list";
      linkedSources.forEach((source) => {
        const row = document.createElement("div");
        row.className = "artifact-source-row";
        const titleLink = document.createElement("a");
        titleLink.textContent = source.title;
        titleLink.href = source.paper_url || source.url || "#";
        if (titleLink.getAttribute("href") !== "#") {
          titleLink.target = "_blank";
          titleLink.rel = "noopener noreferrer";
        }
        const sourceMeta = document.createElement("small");
        sourceMeta.textContent = [
          source.source || source.source_type,
          source.year || "Undated",
          source.capture_state,
        ].filter(Boolean).join(" · ");
        row.append(titleLink, sourceMeta);
        sourceList.appendChild(row);
      });
      if (!linkedSources.length) {
        const loading = document.createElement("small");
        loading.textContent = "Linked Sources are still loading.";
        sourceList.appendChild(loading);
      }
      card.appendChild(sourceList);
    }
    artifactListEl.appendChild(card);
  });
};

const fetchArtifacts = async () => {
  try {
    const response = await fetch("/api/artifacts");
    if (!response.ok) throw new Error("Could not load Projects.");
    const data = await response.json();
    artifacts = data.artifacts || [];
    renderArtifactOptions();
    renderArtifacts();
    renderContextPanel();
    if (companionInboxItems.length) renderCompanionInbox();
  } catch (error) {
    artifactStatusEl.textContent = error.message;
  }
};

const syncTagFilterOptions = (select, items) => {
  const previous = select.value;
  const names = [...new Set(items.flatMap(
    (item) => (item.tags || []).map((tag) => tag.name).filter(Boolean),
  ))].sort((left, right) => left.localeCompare(right));
  select.replaceChildren(new Option("All Tags", ""));
  names.forEach((name) => select.appendChild(new Option(name, name)));
  select.value = names.includes(previous) ? previous : "";
};

const matchesTagFilter = (item, selectedTag) => (
  !selectedTag || (item.tags || []).some((tag) => tag.name === selectedTag)
);

const visibleEvidence = () => libraryEvidence.filter(
  (item) => matchesTagFilter(item, evidenceTagFilterInput.value),
);

const visibleClaims = () => claims.filter(
  (item) => matchesTagFilter(item, claimsTagFilterInput.value)
    && (!claimsReviewFilterInput.value
      || item.review_state === claimsReviewFilterInput.value),
);

const updateClaimsStatus = () => {
  const filtered = visibleClaims();
  const filters = [];
  if (claimsReviewFilterInput.value) filters.push(
    claimsReviewFilterInput.value === "disputed" ? "Disputed" : "Accepted",
  );
  if (claimsTagFilterInput.value) filters.push(`Tag: ${claimsTagFilterInput.value}`);
  claimsStatusEl.textContent = filters.length
    ? `${filtered.length} of ${claims.length} Claims · ${filters.join(" · ")}`
    : `${claims.length} Claim${claims.length === 1 ? "" : "s"}`;
};

const renderEvidenceLibrary = () => {
  evidenceLibraryListEl.replaceChildren();
  syncTagFilterOptions(evidenceTagFilterInput, libraryEvidence);
  const filteredEvidence = visibleEvidence();
  const selectedCount = libraryEvidence.filter(
    (item) => selectedEvidenceIds.has(item.id),
  ).length;
  const selectedVisibleCount = filteredEvidence.filter(
    (item) => selectedEvidenceIds.has(item.id),
  ).length;
  updateSelectAllState(
    evidenceLibrarySelectAllInput, selectedVisibleCount, filteredEvidence.length,
  );
  libraryProposeClaimsBtn.disabled = selectedCount === 0;
  evidenceCreateClaimBtn.disabled = selectedCount === 0;
  libraryProposeClaimsBtn.textContent = selectedCount
    ? `Propose Claims via LLM · ${selectedCount}` : "Propose Claims via LLM";
  evidenceCreateClaimBtn.textContent = selectedCount
    ? `Propose Claims manually · ${selectedCount}` : "Propose Claims manually";
  evidenceHandoffReturnEl.hidden = !evidenceReturnToClaim;
  if (!libraryEvidence.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = "No Evidence yet. Inspect a captured Source to select text or a region.";
    evidenceLibraryListEl.appendChild(empty);
    return;
  }
  if (!filteredEvidence.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = `No Evidence tagged “${evidenceTagFilterInput.value}”.`;
    evidenceLibraryListEl.appendChild(empty);
    return;
  }
  filteredEvidence.forEach((item) => {
    const card = document.createElement("article");
    card.className = "evidence-library-card";
    card.dataset.evidenceId = item.id;
    card.classList.toggle("is-selected", selectedEvidenceIds.has(item.id));
    const selection = document.createElement("label");
    selection.className = "evidence-selection";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = selectedEvidenceIds.has(item.id);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) selectedEvidenceIds.add(item.id);
      else selectedEvidenceIds.delete(item.id);
      renderEvidenceLibrary();
      renderReviewWorkspace();
      const selectedCount = libraryEvidence.filter(
        (evidence) => selectedEvidenceIds.has(evidence.id),
      ).length;
      evidenceStatusEl.textContent = `${selectedCount} of ${libraryEvidence.length} Evidence selected`;
    });
    selection.append(checkbox, document.createTextNode("Select"));
    const source = document.createElement("strong");
    source.textContent = item.source_title;
    const content = item.evidence_type === "snapshot"
      ? document.createElement("img") : document.createElement("blockquote");
    if (item.evidence_type === "snapshot") {
      content.src = `/api/evidence/${item.id}/snapshot`;
      content.alt = `Snapshot from ${item.source_title}`;
    } else {
      content.textContent = item.quote;
    }
    const meta = document.createElement("small");
    meta.textContent = [item.locator, item.source_provider, `${item.claim_count} Claims`]
      .filter(Boolean).join(" · ");
    const tags = document.createElement("div");
    renderTagChips(tags, item.tags || []);
    card.append(selection, source, content, meta, tags);
    evidenceLibraryListEl.appendChild(card);
  });
};

const renderIncomingTrays = () => {
  const incomingEvidence = [...incomingClaimEvidenceIds]
    .map((id) => libraryEvidence.find((item) => item.id === id))
    .filter(Boolean);
  claimIncomingTrayEl.hidden = incomingEvidence.length === 0;
  claimIncomingTitleEl.textContent = `Incoming Evidence · ${incomingEvidence.length}`;
  claimIncomingItemsEl.replaceChildren();
  claimCreateBtn.disabled = incomingEvidence.length === 0
    && claimBasisInput.value !== "background";
  incomingEvidence.forEach((item) => {
    const row = document.createElement("div");
    row.className = "incoming-item";
    const content = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.source_title || "Untitled Source";
    const detail = document.createElement("small");
    detail.textContent = `${item.locator || "Evidence"} · ${item.evidence_type}`;
    content.append(title, detail);
    const actions = document.createElement("div");
    const stance = document.createElement("select");
    stance.setAttribute("aria-label", `Evidence stance for ${item.locator || item.source_title}`);
    ["supports", "contradicts", "limits"].forEach((value) => {
      stance.appendChild(new Option(value, value));
    });
    stance.value = incomingClaimEvidenceStances.get(item.id) || "supports";
    stance.addEventListener("change", () => {
      incomingClaimEvidenceStances.set(item.id, stance.value);
    });
    const preview = document.createElement("button");
    preview.type = "button";
    preview.textContent = "Preview";
    preview.addEventListener("click", () => openEvidenceDetail(item.id));
    const open = document.createElement("button");
    open.type = "button";
    open.className = "semantic-action is-navigate";
    open.textContent = "Open in Evidence";
    open.addEventListener("click", () => {
      evidenceReturnToClaim = true;
      renderEvidenceLibrary();
      showPanel("evidence-panel");
      window.requestAnimationFrame(() => {
        evidenceLibraryListEl.querySelector(`[data-evidence-id="${item.id}"]`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "semantic-action is-destructive";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      incomingClaimEvidenceIds.delete(item.id);
      incomingClaimEvidenceStances.delete(item.id);
      renderIncomingTrays();
    });
    actions.append(stance, preview, open, remove);
    row.append(content, actions);
    claimIncomingItemsEl.appendChild(row);
  });

  const incomingClaims = [...incomingViewClaimIds]
    .map((id) => claims.find((claim) => claim.id === id))
    .filter(Boolean);
  viewIncomingTrayEl.hidden = incomingClaims.length === 0;
  viewCreateBtn.disabled = incomingClaims.length === 0;
  viewIncomingTitleEl.textContent = `Incoming Claims · ${incomingClaims.length}`;
  viewIncomingItemsEl.replaceChildren();
  incomingClaims.forEach((claim) => {
    const row = document.createElement("div");
    row.className = "incoming-item";
    const content = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = claim.statement;
    const detail = document.createElement("small");
    detail.textContent = claim.review_state === "disputed"
      ? `${claim.basis} · disputed` : claim.basis;
    content.append(title, detail);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "semantic-action is-destructive";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      incomingViewClaimIds.delete(claim.id);
      renderIncomingTrays();
    });
    const open = document.createElement("button");
    open.type = "button";
    open.className = "semantic-action is-navigate";
    open.textContent = "Open in Claims";
    open.addEventListener("click", () => {
      claimsReturnToView = true;
      selectedClaimIds.add(claim.id);
      renderClaims();
      showPanel("claims-panel");
      window.requestAnimationFrame(() => {
        claimsListEl.querySelector(`[data-claim-id="${claim.id}"]`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });
    const actions = document.createElement("div");
    actions.className = "incoming-item-actions incoming-view-actions";
    actions.append(open, remove);
    row.append(content, actions);
    viewIncomingItemsEl.appendChild(row);
  });
};

const renderClaims = () => {
  claimsListEl.replaceChildren();
  syncTagFilterOptions(claimsTagFilterInput, claims);
  const filteredClaims = visibleClaims();
  const selectableClaims = viewAddingClaims
    ? filteredClaims.filter((claim) => !viewDraftClaimIds.includes(claim.id))
    : filteredClaims;
  const selectedVisibleCount = selectableClaims.filter(
    (claim) => selectedClaimIds.has(claim.id),
  ).length;
  updateSelectAllState(claimsSelectAllInput, selectedVisibleCount, selectableClaims.length);
  claimsSelectAllInput.disabled = selectableClaims.length === 0;
  claimsRelateBtn.disabled = selectedClaimIds.size !== 2;
  claimsBuildViewBtn.disabled = selectedClaimIds.size === 0;
  claimsSelectedCountEl.textContent = `${selectedClaimIds.size} selected`;
  claimsBuildViewBtn.textContent = selectedClaimIds.size
    ? `Build View · ${selectedClaimIds.size}` : "Build View";
  claimsHandoffReturnEl.hidden = !claimsReturnToView;
  claimsHandoffApplyBtn.disabled = claimsReturnToView && selectedClaimIds.size === 0;
  renderIncomingTrays();
  const relationSelection = selectedClaims();
  claimsRelateBtn.title = relationSelection.length === 2
    ? `First selected → second selected: ${relationSelection[0].statement} → ${relationSelection[1].statement}`
    : "Select two Claims; the relation runs from the first selected to the second.";
  claimsProposalsToggleBtn.textContent = `Review proposals · ${claimProposals.length}`;
  if (!claims.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = "No Claims yet. Select Evidence, then propose Claims manually or via LLM.";
    claimsListEl.appendChild(empty);
  } else if (!filteredClaims.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    if (claimsReviewFilterInput.value && claimsTagFilterInput.value) {
      empty.textContent = "No Claims match the selected Status and Tag.";
    } else if (claimsReviewFilterInput.value === "disputed") {
      empty.textContent = "No disputed Claims yet.";
    } else if (claimsReviewFilterInput.value === "accepted") {
      empty.textContent = "No accepted Claims yet.";
    } else {
      empty.textContent = `No Claims tagged “${claimsTagFilterInput.value}”.`;
    }
    claimsListEl.appendChild(empty);
  }
  filteredClaims.forEach((claim) => {
    const card = document.createElement("article");
    card.className = "claim-card";
    card.dataset.claimId = claim.id;
    card.classList.toggle("is-selected", selectedClaimIds.has(claim.id));
    const selection = document.createElement("label");
    selection.className = "claim-selection evidence-selection";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    const alreadyInView = viewAddingClaims && viewDraftClaimIds.includes(claim.id);
    checkbox.disabled = alreadyInView;
    checkbox.checked = selectedClaimIds.has(claim.id);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) selectedClaimIds.add(claim.id);
      else selectedClaimIds.delete(claim.id);
      renderClaims();
      renderReviewWorkspace();
    });
    selection.append(checkbox, document.createTextNode(alreadyInView ? "In View" : "Select"));
    card.classList.toggle("is-withdrawn", claim.lifecycle !== "active");
    const statement = document.createElement("p");
    statement.className = "claim-statement";
    statement.textContent = claim.statement;
    const badges = document.createElement("div");
    badges.className = "claim-badges";
    [
      claim.basis,
      claim.review_state === "disputed" ? "disputed" : null,
      claim.lifecycle !== "active" ? claim.lifecycle : null,
    ].filter(Boolean).forEach((value) => {
      const badge = document.createElement("span");
      badge.textContent = value.replaceAll("_", " ");
      badges.appendChild(badge);
    });
    const evidence = document.createElement("div");
    evidence.className = "claim-evidence-list";
    claim.evidence.forEach((link) => {
      const row = document.createElement("small");
      row.textContent = `${link.stance} · ${link.source_title} · ${link.locator}`;
      evidence.appendChild(row);
    });
    if (!claim.evidence.length) {
      const row = document.createElement("small");
      row.textContent = claim.intentionally_ungrounded
        ? "Intentionally ungrounded" : "Missing Evidence";
      evidence.appendChild(row);
    }
    const meta = document.createElement("small");
    meta.textContent = `${claim.revisions.length} revision${claim.revisions.length === 1 ? "" : "s"} · ${claim.artifacts.length} Project${claim.artifacts.length === 1 ? "" : "s"}`;
    const tags = document.createElement("div");
    renderTagChips(tags, claim.tags || [], {
      editable: true,
      onEdit: () => openTagEditor("claim", claim.id, claim.tags || [], fetchClaims),
    });
    const actions = document.createElement("div");
    actions.className = "claim-card-actions";
    const revise = document.createElement("button");
    revise.type = "button";
    revise.className = "semantic-action is-edit";
    revise.textContent = "Revise";
    revise.addEventListener("click", async () => {
      const next = window.prompt("Revise Claim", claim.statement);
      if (!next || next.trim() === claim.statement) return;
      const response = await fetch(`/api/claims/${claim.id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ statement: next.trim(), basis: claim.basis }),
      });
      if (response.ok) await fetchClaims();
    });
    const withdraw = document.createElement("button");
    withdraw.type = "button";
    withdraw.className = "semantic-action is-destructive";
    withdraw.textContent = claim.lifecycle === "withdrawn" ? "Restore" : "Withdraw";
    withdraw.addEventListener("click", async () => {
      const lifecycle = claim.lifecycle === "withdrawn" ? "active" : "withdrawn";
      const response = await fetch(`/api/claims/${claim.id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lifecycle }),
      });
      if (response.ok) await fetchClaims();
    });
    actions.append(revise, withdraw);
    card.append(selection, badges, statement, evidence, tags, meta, actions);
    claimsListEl.appendChild(card);
  });
};

const renderClaimProposals = () => {
  claimProposalListEl.replaceChildren();
  claimProposalBoardEl.hidden = claimProposals.length === 0;
  claimsProposalsToggleBtn.textContent = `Review proposals · ${claimProposals.length}`;
  claimProposals.forEach((proposal) => {
    const payload = proposal.payload || {};
    const card = document.createElement("article");
    card.className = "claim-proposal-card";
    const statement = document.createElement("textarea");
    statement.rows = 3;
    statement.value = payload.statement || "";
    const fields = document.createElement("div");
    fields.className = "claim-proposal-fields";
    const basis = document.createElement("select");
    ["background", "reported", "inference"]
      .forEach((value) => basis.appendChild(new Option(value, value)));
    basis.value = payload.basis || "reported";
    const basisField = document.createElement("label");
    const basisLabel = document.createElement("span");
    basisLabel.textContent = "Basis";
    basisField.append(basisLabel, basis);
    fields.append(basisField);
    const evidence = document.createElement("div");
    evidence.className = "proposal-evidence-list";
    (payload.evidence || []).forEach((link) => {
      const sourceItem = libraryEvidence.find((item) => item.id === link.evidence_id);
      const row = document.createElement("small");
      row.textContent = `${link.stance || "supports"} · ${sourceItem?.source_title || link.evidence_id} · ${sourceItem?.locator || ""}`;
      evidence.appendChild(row);
    });
    const rationale = document.createElement("section");
    rationale.className = "proposal-explanation proposal-rationale";
    const rationaleLabel = document.createElement("strong");
    rationaleLabel.textContent = "Rationale";
    const rationaleBody = document.createElement("p");
    rationaleBody.textContent = payload.rationale || "No rationale supplied.";
    rationale.append(rationaleLabel, rationaleBody);
    const caveats = document.createElement("section");
    caveats.className = "proposal-explanation proposal-caveats";
    const caveatsLabel = document.createElement("strong");
    caveatsLabel.textContent = "Caveats";
    const caveatsBody = document.createElement("p");
    caveatsBody.textContent = (payload.caveats || []).join(" · ") || "No caveats supplied.";
    caveats.append(caveatsLabel, caveatsBody);
    const actions = document.createElement("div");
    actions.className = "claim-card-actions claim-proposal-actions";
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "proposal-accept";
    const acceptLabel = document.createElement("span");
    acceptLabel.textContent = "Accept";
    accept.append(createControlIcon("accept"), acceptLabel);
    const resolveProposal = async (reviewState) => {
      [accept, keepDisputed].forEach((button) => { button.disabled = true; });
      const artifact = artifacts.find((item) => item.id === collectArtifactSelect.value) || null;
      const response = await fetch(`/api/claim-proposals/${proposal.id}/accept`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          statement: statement.value.trim(), basis: basis.value, review_state: reviewState,
          artifact_ids: artifact?.id ? [artifact.id] : [],
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        claimsStatusEl.textContent = data.message || "Could not accept Proposal.";
        [accept, keepDisputed].forEach((button) => { button.disabled = false; });
        return;
      }
      await Promise.all([fetchClaims(), fetchClaimProposals()]);
    };
    accept.addEventListener("click", () => resolveProposal("accepted"));
    const keepDisputed = document.createElement("button");
    keepDisputed.type = "button";
    keepDisputed.className = "proposal-disputed";
    const disputedLabel = document.createElement("span");
    disputedLabel.textContent = "Keep disputed";
    keepDisputed.append(createControlIcon("disputed"), disputedLabel);
    keepDisputed.addEventListener("click", () => resolveProposal("disputed"));
    const discard = document.createElement("button");
    discard.type = "button";
    discard.className = "proposal-discard";
    const discardLabel = document.createElement("span");
    discardLabel.textContent = "Discard";
    discard.append(createControlIcon("discard"), discardLabel);
    discard.addEventListener("click", async () => {
      if (!window.confirm("Discard this Claim proposal?")) return;
      const response = await fetch(`/api/claim-proposals/${proposal.id}`, { method: "DELETE" });
      if (response.ok) await fetchClaimProposals();
    });
    actions.append(discard, keepDisputed, accept);
    card.append(statement, fields, evidence, rationale, caveats, actions);
    claimProposalListEl.appendChild(card);
  });
};

const fetchEvidenceLibrary = async () => {
  const response = await fetch("/api/evidence");
  if (!response.ok) throw new Error("Could not load Evidence.");
  libraryEvidence = (await response.json()).evidence || [];
  const available = new Set(libraryEvidence.map((item) => item.id));
  [...selectedEvidenceIds].forEach((id) => {
    if (!available.has(id)) selectedEvidenceIds.delete(id);
  });
  renderEvidenceLibrary();
};

const fetchClaims = async () => {
  const response = await fetch("/api/claims");
  if (!response.ok) throw new Error("Could not load Claims.");
  claims = (await response.json()).claims || [];
  const available = new Set(claims.map((claim) => claim.id));
  [...selectedClaimIds].forEach((id) => {
    if (!available.has(id)) selectedClaimIds.delete(id);
  });
  renderClaims();
  updateClaimsStatus();
};

const fetchClaimProposals = async () => {
  const response = await fetch("/api/claim-proposals");
  if (!response.ok) throw new Error("Could not load Claim proposals.");
  claimProposals = (await response.json()).proposals || [];
  renderClaimProposals();
};

const renderViews = () => {
  viewsListEl.replaceChildren();
  renderIncomingTrays();
  if (!views.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = "No Views yet. Select Claims, then build a Wiki, Comparison, Timeline, Claim graph, or Report.";
    viewsListEl.appendChild(empty);
    return;
  }
  views.forEach((view) => {
    const card = document.createElement("article");
    card.className = "view-card";
    const head = document.createElement("div");
    head.className = "view-card-head";
    const title = document.createElement("strong");
    title.textContent = view.title;
    const type = document.createElement("span");
    type.className = "claim-badge";
    type.textContent = viewTypeLabel(view.view_type);
    head.append(title, type);
    const purpose = document.createElement("p");
    purpose.textContent = view.purpose || "No Purpose added.";
    const count = document.createElement("small");
    count.textContent = `${view.claims?.length || 0} Claim${view.claims?.length === 1 ? "" : "s"}`;
    const claimList = document.createElement("div");
    claimList.className = "view-claim-list";
    (view.claims || []).slice(0, 5).forEach((claim) => {
      const item = document.createElement("span");
      item.textContent = claim.statement;
      claimList.appendChild(item);
    });
    const actions = document.createElement("div");
    actions.className = "view-card-actions";
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = "Open View";
    open.addEventListener("click", () => openView(view.id));
    actions.appendChild(open);
    card.append(head, purpose, count, claimList, actions);
    viewsListEl.appendChild(card);
  });
};

const setViewDetailMode = (show) => {
  viewDetailEl.hidden = !show;
  viewIndexWorkspaceEl.hidden = show;
  if (!show) {
    activeViewId = "";
    viewDraftClaimIds = [];
    viewDetailEditor.hidden = true;
  }
  renderReviewWorkspace();
  renderChatContext();
};

const viewClaimCitation = (evidenceItem) => {
  const citation = document.createElement("button");
  citation.type = "button";
  citation.textContent = `${evidenceItem.stance} · ${evidenceItem.source_title || "Source"} · ${evidenceItem.locator || "Evidence"}`;
  citation.addEventListener("click", () => openEvidenceDetail(evidenceItem.evidence_id));
  return citation;
};

const viewClaimsInDraftOrder = (view) => viewDraftClaimIds.map((claimId) =>
  view.claims.find((item) => item.id === claimId)
  || claims.find((item) => item.id === claimId),
).filter(Boolean);

const renderDocumentView = (view, viewClaims) => {
  const documentEl = document.createElement("article");
  documentEl.className = `view-document is-${view.view_type}`;
  const claimById = new Map(viewClaims.map((claim) => [claim.id, claim]));
  (view.blocks || []).forEach((block) => {
    if (block.block_type === "heading") {
      const heading = document.createElement("h3");
      heading.textContent = block.content;
      documentEl.appendChild(heading);
      return;
    }
    if (block.block_type === "paragraph") {
      const paragraph = document.createElement("p");
      paragraph.textContent = block.content;
      documentEl.appendChild(paragraph);
      return;
    }
    const claim = claimById.get(block.claim_id);
    if (!claim) return;
    const reference = document.createElement("section");
    reference.className = "view-document-claim";
    const label = document.createElement("small");
    label.textContent = `${claim.basis} · ${claim.review_state}`;
    const statement = document.createElement("p");
    statement.textContent = claim.statement;
    const citations = document.createElement("div");
    citations.className = "view-claim-citations";
    (claim.evidence || []).forEach((item) => citations.appendChild(viewClaimCitation(item)));
    if (!(claim.evidence || []).length) {
      const missing = document.createElement("small");
      missing.textContent = "Background knowledge · no local Evidence";
      citations.appendChild(missing);
    }
    reference.append(label, statement, citations);
    documentEl.appendChild(reference);
  });
  viewDetailClaimsEl.appendChild(documentEl);
};

const renderViewBlockEditor = () => {
  const documentMode = ["wiki", "article"].includes(viewEditTypeInput.value);
  viewBlockEditorShell.hidden = !documentMode;
  viewBlockEditorEl.replaceChildren();
  if (!documentMode) return;
  const claimById = new Map(claims.map((claim) => [claim.id, claim]));
  viewDraftBlocks.forEach((block, index) => {
    const row = document.createElement("article");
    row.className = "view-block-editor-row";
    const kind = document.createElement("span");
    kind.textContent = block.block_type;
    const content = block.block_type === "paragraph"
      ? document.createElement("textarea") : document.createElement("input");
    if (block.block_type === "claim") {
      content.value = claimById.get(block.claim_id)?.statement || "Missing Claim";
      content.disabled = true;
    } else {
      content.value = block.content;
      content.addEventListener("input", () => { block.content = content.value; });
    }
    const controls = document.createElement("div");
    const up = document.createElement("button");
    up.type = "button"; up.textContent = "↑"; up.disabled = index === 0;
    up.addEventListener("click", () => {
      [viewDraftBlocks[index - 1], viewDraftBlocks[index]] = [viewDraftBlocks[index], viewDraftBlocks[index - 1]];
      renderViewBlockEditor();
    });
    const down = document.createElement("button");
    down.type = "button"; down.textContent = "↓"; down.disabled = index === viewDraftBlocks.length - 1;
    down.addEventListener("click", () => {
      [viewDraftBlocks[index], viewDraftBlocks[index + 1]] = [viewDraftBlocks[index + 1], viewDraftBlocks[index]];
      renderViewBlockEditor();
    });
    const remove = document.createElement("button");
    remove.type = "button"; remove.textContent = "×";
    remove.className = "semantic-action is-destructive";
    remove.addEventListener("click", () => {
      viewDraftBlocks.splice(index, 1);
      if (block.block_type === "claim") {
        viewDraftClaimIds = viewDraftClaimIds.filter((id) => id !== block.claim_id);
      }
      renderViewBlockEditor();
      renderViewDetail();
    });
    controls.append(up, down, remove);
    row.append(kind, content, controls);
    viewBlockEditorEl.appendChild(row);
  });
};

const renderComparisonView = (viewClaims) => {
  const wrapper = document.createElement("div");
  wrapper.className = "view-comparison-wrap";
  const table = document.createElement("table");
  table.className = "view-comparison";
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  const corner = document.createElement("th");
  corner.textContent = "Dimension";
  headRow.appendChild(corner);
  viewClaims.forEach((claim, index) => {
    const cell = document.createElement("th");
    cell.textContent = `Claim ${String(index + 1).padStart(2, "0")}`;
    headRow.appendChild(cell);
  });
  head.appendChild(headRow);
  const body = document.createElement("tbody");
  [
    ["Proposition", (claim) => claim.statement],
    ["Basis", (claim) => claim.basis],
    ["Review", (claim) => claim.review_state],
    ["Evidence", (claim) => `${claim.evidence?.length || 0} linked item${claim.evidence?.length === 1 ? "" : "s"}`],
    ["Project", (claim) => claim.artifacts?.map((item) => item.title).join(", ") || "Global knowledge"],
  ].forEach(([label, value]) => {
    const row = document.createElement("tr");
    const labelCell = document.createElement("th");
    labelCell.textContent = label;
    row.appendChild(labelCell);
    viewClaims.forEach((claim) => {
      const cell = document.createElement("td");
      cell.textContent = value(claim);
      row.appendChild(cell);
    });
    body.appendChild(row);
  });
  table.append(head, body);
  wrapper.appendChild(table);
  viewDetailClaimsEl.appendChild(wrapper);
};

const renderTimelineView = (viewClaims) => {
  const timeline = document.createElement("div");
  timeline.className = "view-timeline";
  const dated = viewClaims.map((claim, index) => {
    const year = claim.statement.match(/\b(?:19|20)\d{2}\b/)?.[0] || "";
    return { claim, index, year };
  }).sort((left, right) => (left.year || "9999").localeCompare(right.year || "9999") || left.index - right.index);
  dated.forEach(({ claim, index, year }) => {
    const item = document.createElement("article");
    item.className = "view-timeline-item";
    const marker = document.createElement("div");
    marker.className = "view-timeline-marker";
    marker.textContent = year || String(index + 1).padStart(2, "0");
    const body = document.createElement("div");
    const badge = document.createElement("span");
    badge.className = "claim-badge";
    badge.textContent = claim.basis;
    const statement = document.createElement("p");
    statement.textContent = claim.statement;
    const citations = document.createElement("div");
    citations.className = "view-claim-citations";
    (claim.evidence || []).forEach((item) => citations.appendChild(viewClaimCitation(item)));
    body.append(badge, statement, citations);
    item.append(marker, body);
    timeline.appendChild(item);
  });
  viewDetailClaimsEl.appendChild(timeline);
};

const renderGraphView = (viewClaims) => {
  const workspace = document.createElement("section");
  workspace.className = "view-graph-workspace";
  const canvas = document.createElement("div");
  canvas.className = "view-claim-graph";
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("aria-hidden", "true");
  const positions = new Map();
  const count = Math.max(1, viewClaims.length);
  if (!viewClaims.some((claim) => claim.id === activeGraphClaimId)) {
    activeGraphClaimId = viewClaims[0]?.id || "";
  }
  viewClaims.forEach((claim, index) => {
    const angle = (-Math.PI / 2) + (index * Math.PI * 2 / count);
    positions.set(claim.id, { x: 50 + Math.cos(angle) * 35, y: 50 + Math.sin(angle) * 34 });
  });
  const relationKeys = new Set();
  viewClaims.forEach((claim) => (claim.relations || []).forEach((relation) => {
    if (!positions.has(relation.subject_claim_id) || !positions.has(relation.object_claim_id)) return;
    const key = `${relation.subject_claim_id}:${relation.object_claim_id}:${relation.relation_type}`;
    if (relationKeys.has(key)) return;
    relationKeys.add(key);
    const start = positions.get(relation.subject_claim_id);
    const end = positions.get(relation.object_claim_id);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", start.x); line.setAttribute("y1", start.y);
    line.setAttribute("x2", end.x); line.setAttribute("y2", end.y);
    line.setAttribute("marker-end", "url(#view-arrow)");
    svg.appendChild(line);
  }));
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
  marker.setAttribute("id", "view-arrow"); marker.setAttribute("viewBox", "0 0 10 10");
  marker.setAttribute("refX", "9"); marker.setAttribute("refY", "5");
  marker.setAttribute("markerWidth", "5"); marker.setAttribute("markerHeight", "5");
  marker.setAttribute("orient", "auto-start-reverse");
  const arrow = document.createElementNS("http://www.w3.org/2000/svg", "path");
  arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
  marker.appendChild(arrow); defs.appendChild(marker); svg.prepend(defs);
  canvas.appendChild(svg);
  viewClaims.forEach((claim, index) => {
    const position = positions.get(claim.id);
    const node = document.createElement("button");
    node.type = "button";
    node.className = "view-graph-node";
    node.classList.toggle("is-active", claim.id === activeGraphClaimId);
    node.style.left = `${position.x}%`; node.style.top = `${position.y}%`;
    node.textContent = `${String(index + 1).padStart(2, "0")} · ${claim.statement}`;
    node.addEventListener("click", () => {
      activeGraphClaimId = claim.id;
      renderViewDetail();
    });
    canvas.appendChild(node);
  });
  workspace.appendChild(canvas);
  const selected = viewClaims.find((claim) => claim.id === activeGraphClaimId) || viewClaims[0];
  if (selected) {
    activeGraphClaimId ||= selected.id;
    const detail = document.createElement("aside");
    detail.className = "view-graph-detail";
    const label = document.createElement("small");
    label.textContent = `${selected.basis} · ${selected.review_state}`;
    const statement = document.createElement("p"); statement.textContent = selected.statement;
    const relations = document.createElement("div"); relations.className = "view-graph-relations";
    (selected.relations || []).forEach((item) => {
      const chip = document.createElement("span"); chip.textContent = item.relation_type.replaceAll("_", " "); relations.appendChild(chip);
    });
    if (!(selected.relations || []).length) {
      const empty = document.createElement("span");
      empty.textContent = "No saved relations";
      relations.appendChild(empty);
    }
    detail.append(label, statement, relations);
    workspace.appendChild(detail);
  }
  viewDetailClaimsEl.appendChild(workspace);
};

const renderReportView = (viewClaims) => {
  const report = document.createElement("article");
  report.className = "view-report";
  const summary = document.createElement("section");
  const summaryTitle = document.createElement("h3");
  summaryTitle.textContent = "Executive summary";
  const summaryBody = document.createElement("p");
  const evidenceCount = viewClaims.reduce((total, claim) => total + (claim.evidence?.length || 0), 0);
  summaryBody.textContent = `${viewClaims.length} reviewed Claims compose this report, grounded in ${evidenceCount} Evidence link${evidenceCount === 1 ? "" : "s"}.`;
  summary.append(summaryTitle, summaryBody);
  const findings = document.createElement("section");
  const findingsTitle = document.createElement("h3");
  findingsTitle.textContent = "Key findings";
  findings.appendChild(findingsTitle);
  viewClaims.forEach((claim, index) => {
    const finding = document.createElement("div");
    finding.className = "view-report-finding";
    const title = document.createElement("strong");
    title.textContent = `${index + 1}. ${claim.statement}`;
    const citations = document.createElement("div");
    citations.className = "view-claim-citations";
    (claim.evidence || []).forEach((item) => citations.appendChild(viewClaimCitation(item)));
    if (!(claim.evidence || []).length) {
      const note = document.createElement("small");
      note.textContent = "Background knowledge · no local Evidence";
      citations.appendChild(note);
    }
    finding.append(title, citations);
    findings.appendChild(finding);
  });
  report.append(summary, findings);
  viewDetailClaimsEl.appendChild(report);
};

const renderViewDetail = () => {
  const view = activeView();
  if (!view) {
    setViewDetailMode(false);
    return;
  }
  viewDetailTypeEl.textContent = viewTypeLabel(view.view_type);
  viewDetailProjectEl.textContent = view.artifact?.title
    ? `Project · ${view.artifact.title}` : "Standalone View";
  viewDetailTitleEl.textContent = view.title;
  viewDetailPurposeEl.textContent = view.purpose
    || view.artifact?.purpose
    || "No Purpose added.";
  viewDetailClaimsEl.replaceChildren();
  const editing = !viewDetailEditor.hidden;
  const orderedClaims = viewClaimsInDraftOrder(view);
  if (!editing && ["wiki", "article"].includes(view.view_type)) {
    renderDocumentView(view, orderedClaims);
    return;
  }
  if (!editing && view.view_type === "graph") {
    renderGraphView(orderedClaims);
    return;
  }
  renderViewBlockEditor();
  if (editing && ["wiki", "article"].includes(viewEditTypeInput.value)) return;
  viewDraftClaimIds.forEach((claimId, index) => {
    const claim = view.claims.find((item) => item.id === claimId)
      || claims.find((item) => item.id === claimId);
    if (!claim) return;
    const article = document.createElement("article");
    article.className = "view-reader-claim";
    const marker = document.createElement("span");
    marker.className = "view-claim-number";
    marker.textContent = String(index + 1).padStart(2, "0");
    const body = document.createElement("div");
    const badges = document.createElement("div");
    badges.className = "claim-badges";
    [claim.basis, claim.review_state === "disputed" ? "disputed" : null]
      .filter(Boolean).forEach((value) => {
        const badge = document.createElement("span");
        badge.textContent = value;
        badges.appendChild(badge);
      });
    const statement = document.createElement("p");
    statement.className = "view-reader-statement";
    statement.textContent = claim.statement;
    const citations = document.createElement("div");
    citations.className = "view-claim-citations";
    (claim.evidence || []).forEach((evidenceItem) => {
      citations.appendChild(viewClaimCitation(evidenceItem));
    });
    if (!(claim.evidence || []).length) {
      const background = document.createElement("small");
      background.textContent = "Background Claim · no local Evidence";
      citations.appendChild(background);
    }
    body.append(badges, statement, citations);
    article.append(marker, body);
    if (editing) {
      const controls = document.createElement("div");
      controls.className = "view-claim-order-actions";
      const up = document.createElement("button");
      up.type = "button";
      up.textContent = "↑";
      up.title = "Move up";
      up.disabled = index === 0;
      up.addEventListener("click", () => {
        [viewDraftClaimIds[index - 1], viewDraftClaimIds[index]] = [
          viewDraftClaimIds[index], viewDraftClaimIds[index - 1],
        ];
        renderViewDetail();
      });
      const down = document.createElement("button");
      down.type = "button";
      down.textContent = "↓";
      down.title = "Move down";
      down.disabled = index === viewDraftClaimIds.length - 1;
      down.addEventListener("click", () => {
        [viewDraftClaimIds[index], viewDraftClaimIds[index + 1]] = [
          viewDraftClaimIds[index + 1], viewDraftClaimIds[index],
        ];
        renderViewDetail();
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.title = "Remove Claim from View";
      remove.disabled = viewDraftClaimIds.length === 1;
      remove.addEventListener("click", () => {
        viewDraftClaimIds.splice(index, 1);
        renderViewDetail();
      });
      controls.append(up, down, remove);
      article.appendChild(controls);
    }
    viewDetailClaimsEl.appendChild(article);
  });
};

const openView = (viewId) => {
  const view = views.find((item) => item.id === viewId);
  if (!view) return;
  activeViewId = view.id;
  viewDraftClaimIds = (view.claims || []).map((claim) => claim.id);
  viewDraftBlocks = (view.blocks || []).map((block) => ({ ...block }));
  activeGraphClaimId = "";
  viewDetailEditor.hidden = true;
  viewDetailStatusEl.textContent = "";
  setViewDetailMode(true);
  renderViewDetail();
  const panel = viewDetailEl.closest(".panel");
  if (panel) {
    panel.scrollTop = 0;
    panel.scrollLeft = 0;
  }
};

const fetchViews = async () => {
  const response = await fetch("/api/views");
  if (!response.ok) throw new Error("Could not load Views.");
  views = (await response.json()).views || [];
  renderViews();
  viewsStatusEl.textContent = `${views.length} View${views.length === 1 ? "" : "s"}`;
  if (activeViewId) {
    if (activeView()) renderViewDetail();
    else setViewDetailMode(false);
  }
  renderReviewWorkspace();
  renderChatContext();
};

const renderLibrary = () => {
  updateSelectAllState(
    librarySelectAllInput,
    selectedLibrarySourceKeys.size,
    librarySources.length,
  );
  libraryListEl.hidden = Boolean(activeSourceWorkspace);
  sourceReaderEl.hidden = !activeSourceWorkspace;
  libraryAbstractToggleBtn.hidden = Boolean(activeSourceWorkspace);
  libraryPanelInnerEl.classList.toggle("is-reader-focused", Boolean(activeSourceWorkspace));
  libraryPanelInnerEl.classList.toggle(
    "is-reader-details-expanded",
    Boolean(activeSourceWorkspace) && readerDetailsExpanded,
  );
  if (activeSourceWorkspace) {
    renderSourceReader();
    return;
  }
  libraryListEl.replaceChildren();
  libraryListEl.classList.toggle("is-abstract-hidden", libraryAbstractsHidden);
  if (!librarySources.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = "No Sources saved yet. Select search results, then collect them from the Review workspace.";
    libraryListEl.appendChild(empty);
    return;
  }
  librarySources.forEach((source) => {
    const card = document.createElement("article");
    card.className = "library-card";
    const key = resultKey(source);
    const isSelected = selectedLibrarySourceKeys.has(key);
    card.classList.toggle("is-selected", isSelected);

    const selection = document.createElement("label");
    selection.className = "library-selection";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = isSelected;
    checkbox.setAttribute("aria-label", `Select ${source.title || "this Source"}`);
    const selectionText = document.createElement("span");
    selectionText.textContent = "Select";
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedLibrarySourceKeys.add(key);
      } else {
        selectedLibrarySourceKeys.delete(key);
      }
      card.classList.toggle("is-selected", checkbox.checked);
      updateSelectAllState(
        librarySelectAllInput, selectedLibrarySourceKeys.size, librarySources.length,
      );
      renderReviewWorkspace();
    });
    selection.append(checkbox, selectionText);

    const title = document.createElement("h3");
    const primaryUrl = source.paper_url || source.url;
    if (primaryUrl) {
      const link = document.createElement("a");
      link.href = primaryUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = source.title;
      title.appendChild(link);
    } else {
      title.textContent = source.title;
    }

    const meta = document.createElement("p");
    meta.className = "result-meta";
    const sourceLabel = source.source ? ` · ${source.source}` : "";
    meta.textContent = `${source.authors || "Unknown"} · ${source.year || "Undated"}${sourceLabel}`;

    const abstract = document.createElement("p");
    abstract.className = "library-abstract";
    abstract.textContent = source.abstract || "No abstract or snippet was captured.";
    const sourceTags = document.createElement("div");
    renderTagChips(sourceTags, source.tags, {
      editable: true,
      onEdit: () => openTagEditor("source", source.id, source.tags || [], async () => {
        await fetchLibrary();
      }),
    });

    const footer = document.createElement("div");
    footer.className = "library-card-footer";
    const links = document.createElement("div");
    links.className = "result-actions";
    const actionLinks = source.source_type === "web"
      ? [createResultAction("Web", primaryUrl, "web")]
      : [
          createResultAction("Paper", primaryUrl, "paper"),
          createResultAction("PDF", source.pdf_url, "pdf"),
          createResultAction("DOI", source.doi_url, "doi"),
        ];
    actionLinks.filter(Boolean).forEach((action) => links.appendChild(action));

    const associations = document.createElement("div");
    associations.className = "library-associations";
    if (source.artifacts?.length) {
      source.artifacts.forEach((artifact) => {
        const chip = document.createElement("span");
        chip.textContent = artifact.title;
        associations.appendChild(chip);
      });
    } else {
      const global = document.createElement("span");
      global.textContent = "Global only";
      associations.appendChild(global);
    }
    const inspect = document.createElement("button");
    inspect.type = "button";
    inspect.className = "abstract-toggle source-inspect";
    inspect.textContent = "Inspect";
    inspect.addEventListener("click", async () => {
      inspect.disabled = true;
      inspect.textContent = "Opening…";
      const opened = await openSourceReader(source.id);
      if (!opened) {
        inspect.disabled = false;
        inspect.textContent = "Inspect";
      }
    });
    links.appendChild(inspect);
    footer.append(links, associations);
    card.append(selection, title, meta, abstract, sourceTags, footer);
    libraryListEl.appendChild(card);
  });
};

const pdfScrollAnchor = () => {
  const pages = [...sourceReaderSegmentsEl.querySelectorAll(".pdf-page")];
  if (!pages.length) return null;
  const scrollTop = sourceReaderSegmentsEl.scrollTop;
  const page = [...pages].reverse().find((item) => item.offsetTop <= scrollTop + 8)
    || pages[0];
  return {
    page: Number(page.dataset.pageNumber),
    offset: Math.max(0, scrollTop - page.offsetTop) / Math.max(1, page.offsetHeight),
  };
};

const restorePdfScrollAnchor = (anchor) => {
  if (!anchor) return;
  const page = sourceReaderSegmentsEl.querySelector(
    `.pdf-page[data-page-number="${anchor.page}"]`,
  );
  if (page) {
    sourceReaderSegmentsEl.scrollTop = page.offsetTop + anchor.offset * page.offsetHeight;
  }
};

const openSourceReader = async (sourceId, { preserveState = false } = {}) => {
  const scrollAnchor = preserveState ? pdfScrollAnchor() : null;
  if (scrollAnchor) pendingPdfScrollAnchor = scrollAnchor;
  libraryStatusEl.textContent = "Opening Source…";
  try {
    const response = await fetch(`/api/library/sources/${sourceId}/workspace`);
    if (response.status === 404) {
      throw new Error(
        "Source Reader is not loaded by the running server. Restart Knowte, then try again.",
      );
    }
    let data = await response.json();
    if (!response.ok) throw new Error(data.message || "Could not open Source.");
    if (!data.capture) {
      libraryStatusEl.textContent = "Preparing Source content…";
      const captureResponse = await fetch(
        `/api/library/sources/${sourceId}/capture`,
        { method: "POST" },
      );
      const captured = await captureResponse.json();
      if (!captureResponse.ok) {
        throw new Error(captured.message || "Could not prepare Source content.");
      }
      data = captured;
    }
    activeSourceWorkspace = data;
    if (!preserveState) {
      readerDetailsExpanded = false;
      pendingEvidenceSelection = null;
      annotationTarget = { type: "source", id: sourceId };
    }
    libraryStatusEl.textContent = "";
    renderLibrary();
    renderReviewWorkspace();
    if (!scrollAnchor) sourceReaderEl.scrollIntoView({ block: "start", behavior: "smooth" });
    return true;
  } catch (error) {
    libraryStatusEl.textContent = error instanceof TypeError
      ? "Connection to Knowte was interrupted. Restart Knowte, then reload this page."
      : error.message;
    return false;
  }
};

const renderSourceReader = () => {
  if (!activeSourceWorkspace) return;
  const source = activeSourceWorkspace.source;
  sourceReaderTitleEl.textContent = source.title;
  sourceReaderMetaEl.textContent = [
    source.source || "Source",
    source.year || "Undated",
    activeSourceWorkspace.capture?.media_type === "application/pdf"
      ? `${activeSourceWorkspace.segments.length} page PDF`
      : activeSourceWorkspace.capture ? "Webpage content" : "Content unavailable",
  ].filter(Boolean).join(" · ");
  sourceCaptureBtn.querySelector(".tool-label").textContent = "Refresh";
  sourceDetailsToggleBtn.querySelector(".tool-label").textContent = "Details";
  sourceDetailsToggleBtn.classList.toggle("is-active", readerDetailsExpanded);
  sourceDetailsToggleBtn.setAttribute(
    "aria-expanded", String(readerDetailsExpanded),
  );
  sourceOpenOriginalEl.href = source.pdf_url || source.paper_url || source.url || "#";
  sourceOpenOriginalEl.querySelector("span:last-child").textContent = (
    activeSourceWorkspace.capture?.media_type === "application/pdf"
      ? "Original PDF" : "Original web"
  );
  sourceReaderSegmentsEl.replaceChildren();
  sourceReaderSegmentsEl.classList.remove("pdf-source-viewer", "is-snapshot-mode");
  sourceViewerToolbarEl.hidden = false;
  sourceViewerPdfControlsEl.hidden = true;
  if (!activeSourceWorkspace.capture) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = "Source content is unavailable. Refresh to try again.";
    sourceReaderSegmentsEl.appendChild(empty);
    return;
  }
  if (activeSourceWorkspace.capture.media_type === "application/pdf") {
    sourceViewerPdfControlsEl.hidden = false;
    renderPdfSource();
    return;
  }
  activeSourceWorkspace.segments.forEach((segment) => {
    const article = document.createElement("article");
    const blockType = segment.block_type || "paragraph";
    article.className = `capture-segment capture-block-${blockType}`;
    article.dataset.segmentId = segment.id;
    const label = document.createElement("small");
    label.textContent = segment.locator;
    const tagName = blockType === "heading"
      ? `h${Math.min(6, Math.max(3, Number(segment.metadata?.level || 3) + 2))}`
      : blockType === "quote" ? "blockquote"
        : blockType === "code" ? "pre" : "p";
    const text = document.createElement(tagName);
    text.className = "capture-segment-text";
    text.textContent = segment.text;
    article.append(label, text);
    sourceReaderSegmentsEl.appendChild(article);
  });
};

const ensurePdfJs = async () => {
  if (!pdfjsLib) {
    pdfjsLib = await import("./vendor/pdfjs/pdf.mjs");
    pdfjsLib.GlobalWorkerOptions.workerSrc = "./vendor/pdfjs/pdf.worker.mjs";
  }
  return pdfjsLib;
};

const destroyPdfDocument = (documentProxy) => {
  if (!documentProxy || typeof documentProxy.destroy !== "function") return;
  try {
    Promise.resolve(documentProxy.destroy()).catch(() => {});
  } catch (_error) {
    // A superseded PDF document may already have been torn down.
  }
};

const segmentForPage = (pageNumber) => (
  activeSourceWorkspace?.segments.find((segment) => segment.ordinal === pageNumber)
);

const setEvidenceTool = (tool) => {
  evidenceTool = tool;
  evidenceTextToolBtn.classList.toggle("is-active", tool === "text");
  evidenceSnapshotToolBtn.classList.toggle("is-active", tool === "snapshot");
  evidenceTextToolBtn.setAttribute("aria-pressed", String(tool === "text"));
  evidenceSnapshotToolBtn.setAttribute("aria-pressed", String(tool === "snapshot"));
  sourceReaderSegmentsEl.classList.toggle("is-snapshot-mode", tool === "snapshot");
  if (tool === "snapshot") window.getSelection()?.removeAllRanges();
};

const cancelSnapshotTool = () => {
  setEvidenceTool("text");
  sourceReaderSegmentsEl.querySelectorAll(".snapshot-selection-box").forEach(
    (box) => box.remove(),
  );
  if (pendingEvidenceSelection?.evidence_type === "snapshot") {
    pendingEvidenceSelection = null;
    renderReviewWorkspace();
  }
};

const prepareSnapshotOverlay = (overlay, canvas, pageNumber) => {
  let start = null;
  let selectionBox = null;
  const point = (event) => {
    const bounds = overlay.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(event.clientX - bounds.left, bounds.width)),
      y: Math.max(0, Math.min(event.clientY - bounds.top, bounds.height)),
      width: bounds.width,
      height: bounds.height,
    };
  };
  overlay.addEventListener("pointerdown", (event) => {
    if (evidenceTool !== "snapshot") return;
    event.preventDefault();
    start = point(event);
    selectionBox?.remove();
    selectionBox = document.createElement("div");
    selectionBox.className = "snapshot-selection-box";
    overlay.appendChild(selectionBox);
    overlay.setPointerCapture(event.pointerId);
  });
  overlay.addEventListener("pointermove", (event) => {
    if (!start || !selectionBox) return;
    const current = point(event);
    const left = Math.min(start.x, current.x);
    const top = Math.min(start.y, current.y);
    const width = Math.abs(current.x - start.x);
    const height = Math.abs(current.y - start.y);
    Object.assign(selectionBox.style, {
      left: `${left}px`, top: `${top}px`,
      width: `${width}px`, height: `${height}px`,
    });
  });
  overlay.addEventListener("pointerup", (event) => {
    if (!start || !selectionBox) return;
    const current = point(event);
    const left = Math.min(start.x, current.x);
    const top = Math.min(start.y, current.y);
    const width = Math.abs(current.x - start.x);
    const height = Math.abs(current.y - start.y);
    start = null;
    if (width < 12 || height < 12) {
      selectionBox.remove();
      selectionBox = null;
      return;
    }
    const scaleX = canvas.width / current.width;
    const scaleY = canvas.height / current.height;
    const crop = document.createElement("canvas");
    crop.width = Math.max(1, Math.round(width * scaleX));
    crop.height = Math.max(1, Math.round(height * scaleY));
    crop.getContext("2d").drawImage(
      canvas,
      Math.round(left * scaleX), Math.round(top * scaleY),
      crop.width, crop.height,
      0, 0, crop.width, crop.height,
    );
    const segment = segmentForPage(pageNumber);
    pendingEvidenceSelection = {
      evidence_type: "snapshot",
      segment_id: segment?.id,
      quote: "",
      locator: `Page ${pageNumber}`,
      image_data: crop.toDataURL("image/png"),
      anchor: {
        page: pageNumber,
        region: {
          x: left / current.width,
          y: top / current.height,
          width: width / current.width,
          height: height / current.height,
        },
      },
    };
    renderReviewWorkspace();
    openEvidenceQuickEditor({ left: event.clientX, bottom: event.clientY });
  });
};

const renderPdfSource = async () => {
  const scrollAnchor = pdfScrollAnchor() || pendingPdfScrollAnchor;
  const token = ++pdfRenderToken;
  sourceReaderStatusEl.textContent = "Loading faithful PDF view…";
  sourceReaderSegmentsEl.classList.add("pdf-source-viewer");
  const renderedPages = document.createDocumentFragment();
  setEvidenceTool(evidenceTool);
  try {
    const pdf = await ensurePdfJs();
    destroyPdfDocument(activePdfDocument);
    activePdfDocument = null;
    const sourceId = activeSourceWorkspace.source.id;
    const loadingTask = pdf.getDocument({
      url: `/api/library/sources/${sourceId}/content`,
      cMapUrl: "./vendor/pdfjs/cmaps/",
      cMapPacked: true,
      standardFontDataUrl: "./vendor/pdfjs/standard_fonts/",
    });
    const documentProxy = await loadingTask.promise;
    if (token !== pdfRenderToken) {
      destroyPdfDocument(documentProxy);
      return;
    }
    activePdfDocument = documentProxy;
    const firstPage = await documentProxy.getPage(1);
    const baseViewport = firstPage.getViewport({ scale: 1 });
    const availableWidth = Math.max(320, sourceReaderSegmentsEl.clientWidth - 34);
    const fitScale = Math.min(1.6, availableWidth / baseViewport.width);
    const scale = fitScale * pdfZoom;
    pdfZoomLabelEl.textContent = pdfZoom === 1
      ? "Fit" : `${Math.round(pdfZoom * 100)}%`;

    for (let pageNumber = 1; pageNumber <= documentProxy.numPages; pageNumber += 1) {
      if (token !== pdfRenderToken) return;
      const page = pageNumber === 1 ? firstPage : await documentProxy.getPage(pageNumber);
      const viewport = page.getViewport({ scale });
      const pageEl = document.createElement("article");
      pageEl.className = "pdf-page";
      pageEl.dataset.pageNumber = String(pageNumber);
      pageEl.style.width = `${viewport.width}px`;
      pageEl.style.height = `${viewport.height}px`;
      pageEl.style.setProperty("--total-scale-factor", String(scale));

      const canvas = document.createElement("canvas");
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(viewport.width * pixelRatio);
      canvas.height = Math.floor(viewport.height * pixelRatio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      const context = canvas.getContext("2d", { alpha: false });
      await page.render({
        canvasContext: context,
        viewport,
        transform: pixelRatio === 1 ? null : [pixelRatio, 0, 0, pixelRatio, 0, 0],
      }).promise;

      const textLayerEl = document.createElement("div");
      textLayerEl.className = "textLayer";
      const textLayer = new pdf.TextLayer({
        textContentSource: await page.getTextContent(),
        container: textLayerEl,
        viewport,
      });
      await textLayer.render();

      const snapshotOverlay = document.createElement("div");
      snapshotOverlay.className = "snapshot-overlay";
      prepareSnapshotOverlay(snapshotOverlay, canvas, pageNumber);
      const pageLabel = document.createElement("span");
      pageLabel.className = "pdf-page-label";
      pageLabel.textContent = `${pageNumber} / ${documentProxy.numPages}`;
      pageEl.append(canvas, textLayerEl, snapshotOverlay, pageLabel);
      renderedPages.appendChild(pageEl);
    }
    sourceReaderSegmentsEl.replaceChildren(renderedPages);
    sourceReaderStatusEl.textContent = (
      `${documentProxy.numPages} pages · Select text or capture a region`
    );
    restorePdfScrollAnchor(scrollAnchor);
    pendingPdfScrollAnchor = null;
  } catch (error) {
    sourceReaderStatusEl.textContent = `Could not render PDF: ${error.message}`;
  }
};

const renderKnowledgeReview = () => {
  if (!activeSourceWorkspace || currentReviewContext() !== "library") return;
  const selectedEvidenceArtifact = evidenceArtifactSelect.value;
  const isSnapshotDraft = pendingEvidenceSelection?.evidence_type === "snapshot";
  evidenceSelectionQuoteEl.hidden = !pendingEvidenceSelection || isSnapshotDraft;
  evidenceSelectionQuoteEl.textContent = pendingEvidenceSelection?.quote || "";
  evidenceSnapshotPreviewEl.hidden = !isSnapshotDraft;
  evidenceSnapshotPreviewEl.src = isSnapshotDraft
    ? pendingEvidenceSelection.image_data : "";
  evidenceSelectionLocationEl.textContent = pendingEvidenceSelection?.locator
    || "Select text in the Source reader.";
  createEvidenceBtn.disabled = !pendingEvidenceSelection;
  evidenceArtifactSelect.replaceChildren(new Option("Evidence only", ""));
  artifacts.forEach((artifact) => {
    evidenceArtifactSelect.appendChild(new Option(
      `Evidence + ${artifact.title}`, artifact.id,
    ));
  });
  evidenceArtifactSelect.value = artifacts.some(
    (artifact) => artifact.id === selectedEvidenceArtifact,
  ) ? selectedEvidenceArtifact : "";
  createEvidenceBtn.textContent = evidenceArtifactSelect.value
    ? "Create Evidence & link Project"
    : "Create Evidence";
  reviewEvidenceListEl.replaceChildren();
  updateSelectAllState(
    evidenceSelectAllInput,
    activeSourceWorkspace.evidence.filter((item) => selectedEvidenceIds.has(item.id)).length,
    activeSourceWorkspace.evidence.length,
  );
  activeSourceWorkspace.evidence.forEach((item) => {
    const card = document.createElement("article");
    card.className = "review-evidence-item";
    card.classList.toggle("is-selected", selectedEvidenceIds.has(item.id));
    const selection = document.createElement("label");
    selection.className = "evidence-selection";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = selectedEvidenceIds.has(item.id);
    checkbox.setAttribute("aria-label", `Select Evidence from ${item.locator}`);
    selection.append(checkbox, document.createTextNode("Select"));
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedEvidenceIds.add(item.id);
        annotationTarget = { type: "evidence", id: item.id };
      } else {
        selectedEvidenceIds.delete(item.id);
        if (annotationTarget?.type === "evidence" && annotationTarget.id === item.id) {
          annotationTarget = { type: "source", id: activeSourceWorkspace.source.id };
        }
      }
      renderReviewWorkspace();
    });
    card.appendChild(selection);
    if (item.evidence_type === "snapshot") {
      const thumbnail = document.createElement("img");
      thumbnail.src = `/api/evidence/${item.id}/snapshot`;
      thumbnail.alt = "";
      const label = document.createElement("span");
      label.textContent = `Snapshot · ${item.locator}`;
      card.append(thumbnail, label);
    } else {
      const quote = document.createElement("p");
      quote.textContent = `“${item.quote}”`;
      const meta = document.createElement("small");
      meta.textContent = item.locator;
      card.append(quote, meta);
    }
    const tags = document.createElement("div");
    renderTagChips(tags, item.tags || []);
    card.appendChild(tags);
    const footer = document.createElement("div");
    footer.className = "review-evidence-item-footer";
    const annotationCount = document.createElement("span");
    annotationCount.textContent = `${item.annotations.length} Annotation${item.annotations.length === 1 ? "" : "s"}`;
    const open = document.createElement("button");
    open.type = "button";
    open.className = "evidence-icon-action";
    open.appendChild(createControlIcon("inspect"));
    open.title = "Open Evidence";
    open.setAttribute("aria-label", "Open Evidence");
    open.addEventListener("click", (event) => {
      event.stopPropagation();
      openEvidenceDetail(item.id);
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "evidence-icon-action is-danger";
    remove.appendChild(createControlIcon("delete"));
    remove.title = "Delete Evidence";
    remove.setAttribute("aria-label", "Delete Evidence");
    remove.addEventListener("click", async (event) => {
      event.stopPropagation();
      await deleteEvidenceItem(item.id);
    });
    const actions = document.createElement("div");
    actions.className = "review-evidence-item-actions";
    actions.append(open, remove);
    footer.append(annotationCount, actions);
    card.appendChild(footer);
    card.classList.toggle(
      "is-active",
      annotationTarget?.type === "evidence" && annotationTarget.id === item.id,
    );
    reviewEvidenceListEl.appendChild(card);
  });
  if (!activeSourceWorkspace.evidence.length) {
    reviewEvidenceListEl.textContent = "No Evidence yet.";
  }
  if (!annotationTarget) {
    annotationTarget = { type: "source", id: activeSourceWorkspace.source.id };
  }
  const targetEvidence = activeSourceWorkspace.evidence.find(
    (item) => annotationTarget.type === "evidence" && item.id === annotationTarget.id,
  );
  annotationTargetLabelEl.textContent = targetEvidence
    ? `Evidence · ${targetEvidence.locator}` : "Source";
  const annotations = targetEvidence?.annotations
    || activeSourceWorkspace.annotations || [];
  reviewAnnotationListEl.replaceChildren();
  const annotationSummary = document.createElement("p");
  annotationSummary.textContent = `${annotations.length} Annotation${annotations.length === 1 ? "" : "s"} attached`;
  reviewAnnotationListEl.appendChild(annotationSummary);
  renderChatContext();
};

const activeEvidenceDetail = () => (
  activeSourceWorkspace?.evidence.find((item) => item.id === activeEvidenceDetailId)
  || libraryEvidence.find((item) => item.id === activeEvidenceDetailId)
);

const refreshEvidenceDetailData = async () => {
  if (activeSourceWorkspace?.source?.id) {
    await openSourceReader(activeSourceWorkspace.source.id, { preserveState: true });
  } else {
    await fetchEvidenceLibrary();
    renderReviewWorkspace();
  }
  renderEvidenceDetail();
};

const renderEvidenceDetail = () => {
  const item = activeEvidenceDetail();
  if (!item) {
    evidenceDetailDialog.close();
    return;
  }
  evidenceDetailMetaEl.textContent = item.locator;
  renderTagChips(evidenceDetailTagsEl, item.tags || []);
  evidenceDetailContentEl.replaceChildren();
  if (item.evidence_type === "snapshot") {
    const image = document.createElement("img");
    image.src = `/api/evidence/${item.id}/snapshot`;
    image.alt = `Snapshot Evidence from ${item.locator}`;
    evidenceDetailContentEl.appendChild(image);
  } else {
    const quote = document.createElement("blockquote");
    quote.textContent = item.quote || "No captured text is available for this Evidence.";
    evidenceDetailContentEl.appendChild(quote);
  }
  const annotations = item.annotations || [];
  evidenceDetailAnnotationCountEl.textContent = (
    `${annotations.length} Annotation${annotations.length === 1 ? "" : "s"}`
  );
  evidenceDetailAnnotationListEl.replaceChildren();
  annotations.forEach((annotation) => {
    const row = document.createElement("article");
    const body = document.createElement("p");
    body.textContent = annotation.body;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Delete";
    remove.addEventListener("click", async () => {
      if (!window.confirm("Delete this Annotation?")) return;
      const response = await fetch(`/api/annotations/${annotation.id}`, {
        method: "DELETE",
      });
      if (!response.ok) return;
      await refreshEvidenceDetailData();
    });
    row.append(body, remove);
    evidenceDetailAnnotationListEl.appendChild(row);
  });
  if (!annotations.length) {
    evidenceDetailAnnotationListEl.textContent = "No Annotations attached.";
  }
};

const openEvidenceDetail = (evidenceId) => {
  activeEvidenceDetailId = evidenceId;
  renderEvidenceDetail();
  evidenceDetailDialog.showModal();
};

evidenceDetailCloseBtn.addEventListener("click", () => evidenceDetailDialog.close());
evidenceDetailDialog.addEventListener("click", (event) => {
  if (event.target === evidenceDetailDialog) evidenceDetailDialog.close();
});
evidenceDetailEditTagsBtn.addEventListener("click", async () => {
  const item = activeEvidenceDetail();
  if (!item) return;
  openTagEditor("evidence", item.id, item.tags || [], async () => {
    await refreshEvidenceDetailData();
  });
});
const deleteEvidenceItem = async (evidenceId, { closeDetail = false } = {}) => {
  if (!window.confirm("Delete this Evidence and its Annotations?")) return false;
  const response = await fetch(`/api/evidence/${evidenceId}`, { method: "DELETE" });
  if (!response.ok) return;
  if (closeDetail) evidenceDetailDialog.close();
  if (activeEvidenceDetailId === evidenceId) activeEvidenceDetailId = null;
  selectedEvidenceIds.delete(evidenceId);
  chatContextEvidence.delete(evidenceId);
  if (annotationTarget?.type === "evidence" && annotationTarget.id === evidenceId) {
    annotationTarget = activeSourceWorkspace?.source?.id
      ? { type: "source", id: activeSourceWorkspace.source.id }
      : null;
  }
  if (activeSourceWorkspace?.source?.id) {
    await openSourceReader(activeSourceWorkspace.source.id, { preserveState: true });
  } else {
    await fetchEvidenceLibrary();
    renderReviewWorkspace();
  }
  return true;
};
evidenceDetailDeleteBtn.addEventListener("click", async () => {
  const item = activeEvidenceDetail();
  if (item) await deleteEvidenceItem(item.id, { closeDetail: true });
});

sourceReaderBackBtn.addEventListener("click", async () => {
  pdfRenderToken += 1;
  const documentToDestroy = activePdfDocument;
  activePdfDocument = null;
  activeSourceWorkspace = null;
  pendingEvidenceSelection = null;
  annotationTarget = null;
  readerDetailsExpanded = false;
  await fetchEvidenceLibrary();
  renderLibrary();
  renderReviewWorkspace();
  destroyPdfDocument(documentToDestroy);
});

sourceDetailsToggleBtn.addEventListener("click", () => {
  readerDetailsExpanded = !readerDetailsExpanded;
  libraryPanelInnerEl.classList.toggle(
    "is-reader-details-expanded", readerDetailsExpanded,
  );
  sourceDetailsToggleBtn.classList.toggle("is-active", readerDetailsExpanded);
  sourceDetailsToggleBtn.setAttribute(
    "aria-expanded", String(readerDetailsExpanded),
  );
});

sourceCaptureBtn.addEventListener("click", async () => {
  sourceCaptureBtn.disabled = true;
  sourceReaderStatusEl.textContent = "Refreshing Source content…";
  try {
    const response = await fetch(
      `/api/library/sources/${activeSourceWorkspace.source.id}/capture`,
      { method: "POST" },
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Refresh failed.");
    activeSourceWorkspace = data;
    sourceReaderStatusEl.textContent = `${data.segments.length} addressable segments refreshed.`;
    renderLibrary();
    renderReviewWorkspace();
  } catch (error) {
    sourceReaderStatusEl.textContent = error.message;
  } finally {
    sourceCaptureBtn.disabled = false;
  }
});

const captureCurrentReaderSelection = ({ showEditor = false } = {}) => {
  if (evidenceTool !== "text") return;
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || !selection.rangeCount) return;
  const range = selection.getRangeAt(0);
  const origin = range.commonAncestorContainer.nodeType === Node.TEXT_NODE
    ? range.commonAncestorContainer.parentElement : range.commonAncestorContainer;
  const pdfPage = origin.closest?.(".pdf-page");
  if (pdfPage) {
    if (!pdfPage.contains(range.startContainer) || !pdfPage.contains(range.endContainer)) {
      return;
    }
    const quote = range.toString().trim();
    if (!quote) return;
    const pageNumber = Number(pdfPage.dataset.pageNumber);
    const segment = segmentForPage(pageNumber);
    pendingEvidenceSelection = {
      evidence_type: "text",
      segment_id: segment?.id,
      quote,
      locator: `Page ${pageNumber}`,
      anchor: { page: pageNumber, exact: quote },
    };
    renderReviewWorkspace();
    if (showEditor) openEvidenceQuickEditor(range.getBoundingClientRect());
    return;
  }
  const segmentText = origin.closest?.(".capture-segment-text");
  if (!segmentText || !segmentText.contains(range.startContainer)
      || !segmentText.contains(range.endContainer)) return;
  const prefix = document.createRange();
  prefix.selectNodeContents(segmentText);
  prefix.setEnd(range.startContainer, range.startOffset);
  const quote = range.toString();
  const startOffset = prefix.toString().length;
  const segment = segmentText.closest(".capture-segment");
  pendingEvidenceSelection = {
    evidence_type: "text",
    segment_id: segment.dataset.segmentId,
    quote,
    start_offset: startOffset,
    end_offset: startOffset + quote.length,
    locator: segment.querySelector("small").textContent,
  };
  renderReviewWorkspace();
  if (showEditor) openEvidenceQuickEditor(range.getBoundingClientRect());
};

sourceReaderSegmentsEl.addEventListener("mouseup", () => captureCurrentReaderSelection());

evidenceTextToolBtn.addEventListener("click", cancelSnapshotTool);
evidenceSnapshotToolBtn.addEventListener("click", () => {
  if (evidenceTool === "snapshot") {
    cancelSnapshotTool();
  } else {
    setEvidenceTool("snapshot");
  }
});
evidenceArtifactSelect.addEventListener("change", () => {
  createEvidenceBtn.textContent = evidenceArtifactSelect.value
    ? "Create Evidence & link Project"
    : "Create Evidence";
});
pdfZoomOutBtn.addEventListener("click", () => {
  pdfZoom = Math.max(0.55, Math.round((pdfZoom - 0.15) * 100) / 100);
  renderPdfSource();
});
pdfZoomInBtn.addEventListener("click", () => {
  pdfZoom = Math.min(2.2, Math.round((pdfZoom + 0.15) * 100) / 100);
  renderPdfSource();
});

const savePendingEvidence = async ({ artifactId = "", tags = [], annotation = "" } = {}) => {
  if (!pendingEvidenceSelection) throw new Error("No Evidence is selected.");
  reviewKnowledgeStatusEl.textContent = "Creating Evidence…";
  const response = await fetch("/api/evidence", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...pendingEvidenceSelection, artifact_id: artifactId }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "Could not create Evidence.");
  if (tags.length) {
    const tagResponse = await fetch("/api/tags/entity", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entity_type: "evidence", entity_id: data.id, tags }),
    });
    if (!tagResponse.ok) throw new Error("Evidence was created, but Tags could not be saved.");
  }
  if (annotation) {
    const annotationResponse = await fetch("/api/annotations", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_type: "evidence", target_id: data.id, body: annotation }),
    });
    if (!annotationResponse.ok) throw new Error("Evidence was created, but Annotation could not be saved.");
  }
  annotationTarget = { type: "evidence", id: data.id };
  const sourceId = activeSourceWorkspace.source.id;
  await openSourceReader(sourceId, { preserveState: true });
  pendingEvidenceSelection = null;
  renderReviewWorkspace();
  reviewKnowledgeStatusEl.textContent = "Evidence created.";
  return data;
};

createEvidenceBtn.addEventListener("click", async () => {
  try {
    await savePendingEvidence({ artifactId: evidenceArtifactSelect.value });
  } catch (error) {
    reviewKnowledgeStatusEl.textContent = error.message;
  }
});

evidenceQuickDiscardBtn.addEventListener("click", () => {
  closeEvidenceQuickEditor({ discard: true });
  cancelSnapshotTool();
});

evidenceQuickSaveBtn.addEventListener("click", async () => {
  evidenceQuickSaveBtn.disabled = true;
  evidenceQuickStatusEl.textContent = "Saving…";
  try {
    await savePendingEvidence({
      artifactId: evidenceQuickArtifactSelect.value,
      tags: evidenceQuickTagsInput.value.split(",").map((tag) => tag.trim()).filter(Boolean),
      annotation: evidenceQuickAnnotationInput.value.trim(),
    });
    evidenceQuickStatusEl.textContent = "Saved.";
    window.setTimeout(() => closeEvidenceQuickEditor(), 700);
  } catch (error) {
    evidenceQuickStatusEl.textContent = error.message;
  } finally {
    evidenceQuickSaveBtn.disabled = false;
  }
});

const runInternalCaptureShortcut = (mode) => {
  if (mode === "text") {
    captureCurrentReaderSelection({ showEditor: true });
  }
  if (mode === "snapshot") {
    if (!activeSourceWorkspace) return;
    if (activeSourceWorkspace.capture?.media_type === "application/pdf") {
      setEvidenceTool("snapshot");
      sourceReaderStatusEl.textContent = "Drag a region on the PDF. Press Esc to cancel.";
    } else {
      sourceReaderStatusEl.textContent = "Region capture is available in Original web through Web Companion.";
    }
  }
};

window.addEventListener("knowte:capture-shortcut", (event) => {
  runInternalCaptureShortcut(event.detail?.mode);
});

window.addEventListener("keydown", (event) => {
  if (event.altKey && event.shiftKey && event.code === "KeyK") {
    event.preventDefault();
    runInternalCaptureShortcut("text");
  }
  if (event.altKey && event.shiftKey && event.code === "KeyX") {
    event.preventDefault();
    runInternalCaptureShortcut("snapshot");
  }
  if (event.key === "Escape" && !evidenceQuickEditor.hidden) {
    closeEvidenceQuickEditor({ discard: true });
    cancelSnapshotTool();
  }
});

createAnnotationBtn.addEventListener("click", async () => {
  const body = annotationBodyEl.value.trim();
  if (!body || !annotationTarget) return;
  reviewKnowledgeStatusEl.textContent = "Adding Annotation…";
  try {
    const target = { ...annotationTarget };
    const response = await fetch("/api/annotations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_type: target.type, target_id: target.id, body,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Could not add Annotation.");
    annotationBodyEl.value = "";
    annotationTarget = target;
    await openSourceReader(activeSourceWorkspace.source.id, { preserveState: true });
    renderReviewWorkspace();
    reviewKnowledgeStatusEl.textContent = "Annotation added.";
  } catch (error) {
    reviewKnowledgeStatusEl.textContent = error.message;
  }
});

const fetchLibrary = async () => {
  libraryStatusEl.textContent = "Loading Sources…";
  try {
    const response = await fetch("/api/library/sources");
    if (!response.ok) throw new Error("Could not load Sources.");
    const data = await response.json();
    librarySources = data.sources || [];
    await fetchEvidenceLibrary();
    const availableKeys = new Set(librarySources.map(resultKey));
    [...selectedLibrarySourceKeys].forEach((key) => {
      if (!availableKeys.has(key)) selectedLibrarySourceKeys.delete(key);
    });
    renderLibrary();
    renderArtifacts();
    renderContextPanel();
    libraryStatusEl.textContent = `${librarySources.length} saved Source${librarySources.length === 1 ? "" : "s"}`;
  } catch (error) {
    libraryStatusEl.textContent = error instanceof TypeError
      ? "Connection to Knowte was interrupted. Restart Knowte, then reload this page."
      : error.message;
  }
};

libraryProposeClaimsBtn.addEventListener("click", async () => {
  if (!selectedEvidenceIds.size) return;
  if (selectedEvidenceIds.size > 12) {
    evidenceStatusEl.textContent = "Select at most 12 Evidence items for one Claim proposal run.";
    return;
  }
  libraryProposeClaimsBtn.disabled = true;
  libraryProposeClaimsBtn.textContent = "Proposing…";
  copySelectedEvidenceToClaimDraft();
  evidenceStatusEl.textContent = "The model is developing Claim proposals from selected Evidence…";
  try {
    const artifact = artifacts.find(
      (item) => item.id === collectArtifactSelect.value,
    ) || null;
    const response = await fetch("/api/claim-proposals/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ evidence_ids: [...selectedEvidenceIds], artifact }),
    });
    const data = await response.json().catch(() => ({}));
    updateUsage(data.usage);
    if (!response.ok) throw new Error(data.message || "Could not propose Claims.");
    await fetchClaimProposals();
    showPanel("claims-panel");
    claimProposalBoardEl.hidden = false;
    evidenceStatusEl.textContent = `${data.proposals.length} Claim proposal${data.proposals.length === 1 ? "" : "s"} awaiting review.`;
  } catch (error) {
    evidenceStatusEl.textContent = error instanceof TypeError
      ? "Connection to Knowte was interrupted before Claims could be proposed. Restart Knowte, then try again."
      : error.message;
  } finally {
    renderEvidenceLibrary();
  }
});

claimCreateBtn.addEventListener("click", async () => {
  const statement = claimStatementInput.value.trim();
  if (!statement) return;
  claimCreateBtn.disabled = true;
  claimCreateStatusEl.textContent = "Creating Claim…";
  try {
    const response = await fetch("/api/claims", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        statement,
        basis: claimBasisInput.value,
        evidence: [...incomingClaimEvidenceIds].map((evidenceId) => ({
          evidence_id: evidenceId,
          stance: incomingClaimEvidenceStances.get(evidenceId) || "supports",
        })),
        artifact_ids: claimArtifactInput.value ? [claimArtifactInput.value] : [],
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Could not create Claim.");
    claimStatementInput.value = "";
    incomingClaimEvidenceIds.clear();
    incomingClaimEvidenceStances.clear();
    claimBasisInput.value = "background";
    await Promise.all([fetchClaims(), fetchEvidenceLibrary()]);
    renderIncomingTrays();
    claimCreateStatusEl.textContent = "Claim created.";
  } catch (error) {
    claimCreateStatusEl.textContent = error.message;
  } finally {
    renderIncomingTrays();
  }
});

claimBasisInput.addEventListener("change", renderIncomingTrays);

claimsProposalsToggleBtn.addEventListener("click", () => {
  claimProposalBoardEl.hidden = !claimProposalBoardEl.hidden;
  if (!claimProposalBoardEl.hidden) {
    claimProposalBoardEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});

claimsRelateBtn.addEventListener("click", async () => {
  const selected = selectedClaims();
  if (selected.length !== 2) return;
  const response = await fetch("/api/claim-relations", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      subject_claim_id: selected[0].id,
      object_claim_id: selected[1].id,
      relation_type: claimsRelationTypeInput.value,
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    claimsStatusEl.textContent = data.message || "Could not relate Claims.";
    return;
  }
  selectedClaimIds.clear();
  await fetchClaims();
  claimsStatusEl.textContent = `Created ${data.relation_type} relation.`;
});

viewDetailBackBtn.addEventListener("click", () => {
  if (!viewDetailEditor.hidden && !window.confirm("Leave without saving View changes?")) return;
  setViewDetailMode(false);
  renderViews();
});

viewDetailEditBtn.addEventListener("click", () => {
  const view = activeView();
  if (!view) return;
  viewDraftClaimIds = view.claims.map((claim) => claim.id);
  viewDraftBlocks = (view.blocks || []).map((block) => ({ ...block }));
  viewDetailEditor.hidden = false;
  viewEditTitleInput.value = view.title;
  viewEditPurposeInput.value = view.purpose || "";
  viewEditProjectInput.value = view.artifact_id || "";
  viewEditTypeInput.value = view.view_type;
  viewDetailStatusEl.textContent = "Editing View structure and metadata.";
  renderViewDetail();
  viewEditTitleInput.focus();
});

viewEditCancelBtn.addEventListener("click", () => {
  const view = activeView();
  if (!view) return;
  viewDraftClaimIds = view.claims.map((claim) => claim.id);
  viewDraftBlocks = (view.blocks || []).map((block) => ({ ...block }));
  viewDetailEditor.hidden = true;
  viewDetailStatusEl.textContent = "Changes discarded.";
  renderViewDetail();
});

const appendDraftBlock = (blockType) => {
  viewDraftBlocks.push({
    id: crypto.randomUUID().replaceAll("-", ""),
    block_type: blockType,
    content: blockType === "heading" ? "New section" : "Write a synthesis paragraph…",
    claim_id: "",
  });
  renderViewBlockEditor();
};

viewAddHeadingBtn.addEventListener("click", () => appendDraftBlock("heading"));
viewAddParagraphBtn.addEventListener("click", () => appendDraftBlock("paragraph"));
viewEditTypeInput.addEventListener("change", () => {
  if (["wiki", "article"].includes(viewEditTypeInput.value) && !viewDraftBlocks.length) {
    viewDraftBlocks = [{
      id: crypto.randomUUID().replaceAll("-", ""),
      block_type: "heading",
      content: viewEditTypeInput.value === "wiki" ? "Overview" : "Article",
      claim_id: "",
    }, ...viewDraftClaimIds.map((claimId) => ({
      id: crypto.randomUUID().replaceAll("-", ""),
      block_type: "claim", content: "", claim_id: claimId,
    }))];
  }
  renderViewBlockEditor();
  renderViewDetail();
});

viewDetailAddClaimsBtn.addEventListener("click", () => {
  const view = activeView();
  if (!view) return;
  if (viewDetailEditor.hidden) {
    viewDraftClaimIds = view.claims.map((claim) => claim.id);
    viewDraftBlocks = (view.blocks || []).map((block) => ({ ...block }));
    viewDetailEditor.hidden = false;
  }
  viewAddingClaims = true;
  claimsReturnToView = true;
  selectedClaimIds.clear();
  renderClaims();
  showPanel("claims-panel");
});

viewDetailEditor.addEventListener("submit", async (event) => {
  event.preventDefault();
  const view = activeView();
  if (!view) return;
  viewDetailStatusEl.textContent = "Saving View…";
  try {
    const response = await fetch(`/api/views/${view.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: viewEditTitleInput.value.trim(),
        purpose: viewEditPurposeInput.value.trim(),
        artifact_id: viewEditProjectInput.value,
        view_type: viewEditTypeInput.value,
        claim_ids: viewDraftClaimIds,
        blocks: ["wiki", "article"].includes(viewEditTypeInput.value)
          ? viewDraftBlocks.map(({ id, block_type, content, claim_id }) => ({ id, block_type, content, claim_id }))
          : [],
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Could not update View.");
    viewDetailEditor.hidden = true;
    await fetchViews();
    viewDetailStatusEl.textContent = "View saved.";
  } catch (error) {
    viewDetailStatusEl.textContent = error.message;
  }
});

viewDetailDeleteBtn.addEventListener("click", async () => {
  const view = activeView();
  if (!view || !window.confirm(`Delete View “${view.title}”? Claims and Evidence will not be deleted.`)) return;
  const response = await fetch(`/api/views/${view.id}`, { method: "DELETE" });
  if (!response.ok) {
    viewDetailStatusEl.textContent = "Could not delete View.";
    return;
  }
  setViewDetailMode(false);
  await fetchViews();
  viewsStatusEl.textContent = "View deleted. Claims and Evidence were preserved.";
});

viewForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!incomingViewClaimIds.size) {
    viewsStatusEl.textContent = "Add at least one incoming Claim before creating a View.";
    return;
  }
  viewCreateBtn.disabled = true;
  viewsStatusEl.textContent = "Creating View…";
  try {
    const response = await fetch("/api/views", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: viewTitleInput.value.trim(),
        view_type: viewTypeInput.value,
        purpose: viewPurposeInput.value.trim(),
        artifact_id: viewProjectInput.value,
        claim_ids: [...incomingViewClaimIds],
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Could not create View.");
    viewForm.reset();
    incomingViewClaimIds.clear();
    activeViewId = data.id;
    await fetchViews();
    openView(data.id);
    viewDetailStatusEl.textContent = "View created.";
  } catch (error) {
    viewsStatusEl.textContent = error.message;
  } finally {
    renderIncomingTrays();
    renderReviewWorkspace();
  }
});

artifactForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  artifactCreateBtn.disabled = true;
  artifactCreateBtn.textContent = "Creating…";
  artifactStatusEl.textContent = "";
  try {
    const response = await fetch("/api/artifacts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: artifactTitleInput.value.trim(),
        purpose: artifactPurposeInput.value.trim(),
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || "Could not create the Project.");
    }
    artifactForm.reset();
    await fetchArtifacts();
    collectArtifactSelect.value = data.id;
    localStorage.setItem("knowte-active-artifact", data.id);
    renderArtifacts();
    artifactStatusEl.textContent = `Created “${data.title}”. It is now active in Search.`;
  } catch (error) {
    artifactStatusEl.textContent = error.message;
  } finally {
    artifactCreateBtn.disabled = false;
    artifactCreateBtn.textContent = "Create Project";
  }
});

collectArtifactSelect.addEventListener("change", () => {
  if (collectArtifactSelect.value) {
    localStorage.setItem("knowte-active-artifact", collectArtifactSelect.value);
  } else {
    localStorage.removeItem("knowte-active-artifact");
  }
  renderArtifacts();
  renderContextPanel();
});

const collectSelectedResults = async (artifactId = null) => {
  const selected = selectedResults();
  if (!selected.length) return;
  contextCollectSelectedBtn.disabled = true;
  contextActionStatusEl.textContent = "Collecting selected Sources…";
  try {
    const response = await fetch("/api/library/sources/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sources: selected, artifact_id: artifactId }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || "Could not collect the selected Sources.");
    }
    contextActionStatusEl.textContent = artifactId
      ? `${data.count} Source(s) saved; ${data.artifact_links_created} new Project link(s) created.`
      : `${data.count} Source(s) saved; ${data.sources_created} newly added.`;
    await Promise.all([fetchLibrary(), fetchArtifacts()]);
  } catch (error) {
    contextActionStatusEl.textContent = error.message;
  } finally {
    renderReviewWorkspace();
  }
};

contextCollectSelectedBtn.addEventListener("click", () => {
  collectSelectedResults(collectArtifactSelect.value || null);
});

const appendReviewMessage = (
  text,
  role,
  recommendations = [],
  sources = activeReviewSources(),
) => {
  const message = document.createElement("div");
  message.className = `context-chat-message is-${role}`;
  const body = document.createElement("p");
  body.textContent = text;
  message.appendChild(body);
  if (recommendations.length) {
    const list = document.createElement("div");
    list.className = "context-recommendations";
    recommendations.slice(0, 12).forEach((item) => {
      if (!item || typeof item !== "object") return;
      const row = document.createElement("div");
      const decision = String(item.decision || "inspect").toUpperCase();
      const index = Number(item.source_index);
      const source = Number.isInteger(index) ? sources[index - 1] : null;
      row.textContent = `${decision}${source?.title ? ` · ${source.title}` : ""}: ${item.reason || "No reason provided."}`;
      list.appendChild(row);
    });
    message.appendChild(list);
  }
  contextChatEl.appendChild(message);
  contextChatEl.scrollTop = contextChatEl.scrollHeight;
};

const renderReviewConversation = () => {
  contextChatEl.replaceChildren();
  const conversation = reviewConversations[activeReviewContextKey] || [];
  conversation.forEach((message) => {
    appendReviewMessage(
      message.content,
      message.role,
      message.recommendations || [],
      message.sources || [],
    );
  });
};

contextChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = contextChatInput.value.trim();
  if (!question) return;
  const contextKey = activeReviewContextKey;
  const selected = [...chatContextSources.values()];
  const evidence = [...chatContextEvidence.values()];
  const selectedClaimContext = currentReviewContext() === "claims"
    ? selectedClaims()
    : currentReviewContext() === "views"
      ? activeView()?.claims || [...incomingViewClaimIds]
        .map((id) => claims.find((claim) => claim.id === id)).filter(Boolean)
      : [];
  const artifact = activeReviewArtifact();
  const conversation = reviewConversations[contextKey] || [];
  const recentConversation = conversation.slice(-8).map((message) => ({
    role: message.role,
    content: message.content,
    context_refs: [
      ...(message.sources || []).map((source) => ({ type: "source", id: source.id || "" })),
      ...(message.evidence || []).map((item) => ({ type: "evidence", id: item.id || "" })),
    ],
  }));
  appendReviewMessage(question, "user", [], selected);
  conversation.push({ role: "user", content: question, sources: selected, evidence });
  contextChatInput.value = "";
  contextChatSendBtn.disabled = true;
  contextChatSendBtn.textContent = "Thinking…";
  try {
    const response = await fetch("/api/review/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        context: currentReviewContext(),
        sources: selected,
        evidence,
        claims: selectedClaimContext,
        artifact,
        conversation: recentConversation,
      }),
    });
    const data = await response.json().catch(() => ({}));
    updateUsage(data.usage);
    if (!response.ok) {
      throw new Error(data.message || "The review copilot is unavailable.");
    }
    const answer = data.answer || "The model returned no written assessment.";
    appendReviewMessage(answer, "assistant", data.recommendations || [], selected);
    conversation.push({
      role: "assistant",
      content: answer,
      recommendations: data.recommendations || [],
      sources: selected,
      evidence,
    });
  } catch (error) {
    appendReviewMessage(error.message, "error");
  } finally {
    contextChatSendBtn.disabled = false;
    contextChatSendBtn.textContent = "Send";
  }
});

contextPanelToggleBtn.addEventListener("click", () => {
  const isOpen = contextPanel.classList.toggle("is-open");
  contextPanelToggleBtn.setAttribute("aria-expanded", String(isOpen));
});

contextPanelCloseBtn.addEventListener("click", () => {
  contextPanel.classList.remove("is-open");
  contextPanelToggleBtn.setAttribute("aria-expanded", "false");
});

libraryAbstractToggleBtn.addEventListener("click", () => {
  libraryAbstractsHidden = !libraryAbstractsHidden;
  libraryListEl.classList.toggle("is-abstract-hidden", libraryAbstractsHidden);
  libraryAbstractToggleBtn.setAttribute("aria-pressed", String(libraryAbstractsHidden));
  libraryAbstractToggleBtn.textContent = libraryAbstractsHidden
    ? "Show abstracts"
    : "Hide abstracts";
});

const showPanel = (target) => {
  navLinks.forEach((link) => {
    link.classList.toggle("is-active", link.dataset.target === target);
  });
  panels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === target);
  });
  renderReviewWorkspace();
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
    renderReviewWorkspace();
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
    if (target === "sources-panel") fetchLibrary();
    if (target === "evidence-panel") fetchEvidenceLibrary();
    if (target === "claims-panel") {
      Promise.all([fetchClaims(), fetchClaimProposals(), fetchEvidenceLibrary()]);
    }
    if (target === "views-panel") Promise.all([fetchViews(), fetchClaims()]);
    if (target === "create-panel") fetchArtifacts();
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
  aiCopilotInstructionsInput,
  aiCopilotTemperatureInput,
  aiCopilotMaxTokensInput,
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
    fetch("/api/companion/theme", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme }),
    }).catch(() => {});
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
fetchArtifacts();
fetchClaims();
fetchClaimProposals();
fetchViews();
fetchLibrary();
fetchCompanionInbox();
window.setInterval(fetchCompanionInbox, 5000);
renderSelectedAreas();
renderPresetState();
initTheme();
setFiltersCollapsed(false);
renderPaginationControls();
