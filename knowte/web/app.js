const form = document.querySelector("#search-form");
const input = form.querySelector("input[name='keywords']");
const searchSubmitBtn = document.querySelector("#search-submit");
const savePlanBtn = document.querySelector("#save-plan");
const discussSearchBtn = document.querySelector("#discuss-search");
const searchStrategyEl = document.querySelector("#search-strategy");
const searchStrategyListEl = document.querySelector("#search-strategy-list");
const searchStrategyWaitingEl = document.querySelector("#search-strategy-waiting");
const searchStrategyWaitingListEl = document.querySelector("#search-strategy-waiting-list");
const searchStrategyAddBtn = document.querySelector("#search-strategy-add");
const searchStrategyStatusEl = document.querySelector("#search-strategy-status");
const searchStrategyStaleEl = document.querySelector("#search-strategy-stale");
const searchStrategyUseAnywayBtn = document.querySelector("#search-strategy-use-anyway");
const searchStrategyDiscussAgainBtn = document.querySelector("#search-strategy-discuss-again");
const searchImportEl = document.querySelector("#search-import");
const importContentInput = document.querySelector("#import-content");
const parseImportBtn = document.querySelector("#parse-import");
const documentFilesInput = document.querySelector("#document-files");
const documentUploadBtn = document.querySelector("#document-upload");
const documentUploadList = document.querySelector("#document-upload-list");
const documentUploadStatus = document.querySelector("#document-upload-status");
let documentUploads = [];
let documentsUploading = false;
const renderDocumentUploads = () => {
  documentUploadList.replaceChildren();
  documentUploads.forEach((item) => {
    const row = document.createElement("div"); row.className = "document-upload-row";
    const name = document.createElement("small");
    name.textContent = `${item.file.name} · ${(item.file.size / 1024 / 1024).toFixed(2)} MB${item.status ? ` · ${item.status}` : ""}`;
    const title = document.createElement("input"); title.type = "text"; title.value = item.title;
    title.setAttribute("aria-label", `Title for ${item.file.name}`);
    title.disabled = documentsUploading || item.done;
    title.addEventListener("input", () => { item.title = title.value; });
    const remove = document.createElement("button"); remove.type = "button"; remove.textContent = "×";
    remove.setAttribute("aria-label", `Remove ${item.file.name}`); remove.disabled = documentsUploading;
    remove.addEventListener("click", () => { documentUploads = documentUploads.filter((entry) => entry !== item); renderDocumentUploads(); });
    row.append(name, title, remove); documentUploadList.append(row);
  });
  documentUploadBtn.disabled = documentsUploading || !documentUploads.some((item) => !item.done);
};
const queueDocuments = (files) => {
  if (documentsUploading) return;
  const errors = [];
  for (const file of files) {
    if (!/\.(pdf|md|markdown|txt|docx)$/i.test(file.name) || !file.size || file.size > 20 * 1024 * 1024) {
      errors.push(`${file.name}: use PDF, Markdown, TXT or DOCX, between 1 byte and 20 MB.`); continue;
    }
    documentUploads.push({ file, title: file.name.replace(/\.[^.]+$/, ""), done: false, status: "" });
  }
  documentUploadStatus.textContent = errors.join("\n"); renderDocumentUploads();
};
documentFilesInput.addEventListener("change", () => { queueDocuments(documentFilesInput.files); documentFilesInput.value = ""; });
const documentDropZone = document.querySelector("#document-drop-zone");
documentDropZone.addEventListener("dragover", (event) => event.preventDefault());
documentDropZone.addEventListener("drop", (event) => { event.preventDefault(); queueDocuments(event.dataTransfer.files); });
documentUploadBtn.addEventListener("click", async () => {
  documentsUploading = true; renderDocumentUploads();
  documentUploadStatus.textContent = "Parsing and importing documents…";
  let imported = 0;
  try {
    for (const item of documentUploads.filter((entry) => !entry.done)) {
      try {
        const data = await new Promise((resolve, reject) => {
          const reader = new FileReader(); reader.onload = () => resolve(String(reader.result).split(",")[1]);
          reader.onerror = () => reject(new Error("Could not read file")); reader.readAsDataURL(item.file);
        });
        const response = await fetch("/api/library/documents", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename: item.file.name, title: item.title, data }) });
        const result = await response.json();
        if (!response.ok) throw new Error(result.message || "Import failed");
        item.done = true; imported += 1;
        item.status = result.duplicate ? "Already in Sources" : result.text_available ? "Added to Sources" : "Added · use region capture or a native PDF model";
      } catch (error) { item.status = error.message; }
      renderDocumentUploads();
    }
    if (imported) { await fetchLibrary(); setTabActivity("sources-panel", "result"); }
    documentUploadStatus.textContent = `${imported} document(s) ready in Sources. Inspect there to read and create Evidence.`;
  } catch (error) { documentUploadStatus.textContent = error.message; }
  finally { documentsUploading = false; renderDocumentUploads(); }
});
const importStatusEl = document.querySelector("#import-status");
const copyImportPromptBtn = document.querySelector("#copy-import-prompt");
const importPromptPreviewEl = document.querySelector("#import-prompt-preview");
const searchModeButtons = document.querySelectorAll("[data-search-mode]");
const defaultSearchModeButtons = document.querySelectorAll(
  "[data-default-search-mode]",
);
const searchModeHint = document.querySelector("#search-mode-hint");
const searchAIReviewInput = document.querySelector("#search-ai-review");
let searchAIReview = false;
let lastSearchQueries = [];
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
const searxngProxyInput = document.querySelector("#searxng-proxy");
const webIgnoreYearFilterInput = document.querySelector("#web-ignore-year-filter");
const saveConfigBtn = document.querySelector("#save-config");
const exportConfigBtn = document.querySelector("#export-config");
const exportConfigRedactInput = document.querySelector("#export-config-redact");
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
const aiSearchTimeoutInput = document.querySelector("#ai-search-timeout");
const evidenceRequestModeInput = document.querySelector("#evidence-request-mode");
const ai_evidence_source_limitInput = document.querySelector("#ai-evidence-source-limit");
const ai_claim_evidence_limitInput = document.querySelector("#ai-claim-evidence-limit");
const aiClaimComparisonLimitInput = document.querySelector("#ai-claim-comparison-limit");
const aiWikiClaimLimitInput = document.querySelector("#ai-wiki-claim-limit");
const ai_copilot_context_limitInput = document.querySelector("#ai-copilot-context-limit");
const aiStageTimeoutInput = document.querySelector("#ai-stage-timeout");
const aiCopilotInstructionsInput = document.querySelector("#ai-copilot-instructions");
const aiCopilotTemperatureInput = document.querySelector("#ai-copilot-temperature");
const aiCopilotMaxTokensInput = document.querySelector("#ai-copilot-max-tokens");
const aiCopilotParameterList = document.querySelector("#ai-copilot-parameter-list");
const aiCopilotAddParameterBtn = document.querySelector("#ai-copilot-add-parameter");
const aiCopilotPromptSharedEl = document.querySelector("#ai-copilot-prompt-shared");
const aiCopilotPromptSharedBlockEl = document.querySelector("#ai-copilot-prompt-shared-block");
const aiCopilotPromptPreviewEl = document.querySelector("#ai-copilot-prompt-preview");
const aiCopilotPromptStageInput = document.querySelector("#ai-copilot-prompt-stage");
const aiCopilotPromptStageLabelEl = document.querySelector("#ai-copilot-prompt-stage-label");
const aiCopilotPromptNoteEl = document.querySelector("#ai-copilot-prompt-note");
const aiProviderInput = document.querySelector("#ai-provider");
const aiCustomRecipeInput = document.querySelector("#ai-custom-recipe");
const aiCustomRecipeSection = document.querySelector("#ai-custom-recipe-section");
const aiProfileListEl = document.querySelector("#ai-profile-list");
const aiProfileAddBtn = document.querySelector("#ai-profile-add");
const aiRoleGridEl = document.querySelector("#ai-role-grid");
const contextModelSelect = document.querySelector("#context-model-select");
const searchModelControl = document.querySelector("#search-model-control");
const searchModelSelect = document.querySelector("#search-model-select");
const evidenceModelSelect = document.querySelector("#evidence-model-select");
const sourceDiscoveryModelSelect = document.querySelector("#source-discovery-model-select");
const claimsModelSelect = document.querySelector("#claims-model-select");
const wikiModelSelect = document.querySelector("#wiki-model-select");
const articleModelSelect = document.querySelector("#article-model-select");
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

const setTabActivity = (target, state = "idle") => {
  const link = [...navLinks].find((item) => item.dataset.target === target);
  if (!link) return;
  link.classList.toggle("is-processing", state === "processing");
  link.classList.toggle("has-result", state === "result" && !link.classList.contains("is-active"));
  link.title = state === "processing"
    ? "Proposal in progress"
    : state === "result" && !link.classList.contains("is-active")
      ? "New proposals ready for review"
      : "";
};
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
const sourceEvidenceProposerEl = document.querySelector(".source-evidence-proposer");
const sourceDiscoveryLauncherEl = document.querySelector(".source-discovery-launcher");
const evidenceLibraryListEl = document.querySelector("#evidence-library-list");
const libraryProposeClaimsBtn = document.querySelector("#library-propose-claims");
const claimProposalFocusInput = document.querySelector("#claim-proposal-focus");
const evidenceCreateClaimBtn = document.querySelector("#evidence-create-claim");
const evidenceBatchTagBtn = document.querySelector("#evidence-batch-tag");
const evidenceStatusEl = document.querySelector("#evidence-status");
const resultsSelectAllInput = document.querySelector("#results-select-all");
const librarySelectAllInput = document.querySelector("#library-select-all");
const libraryBatchTagBtn = document.querySelector("#library-batch-tag");
const libraryBatchDeleteBtn = document.querySelector("#library-batch-delete");
const evidenceBatchDeleteBtn = document.querySelector("#evidence-batch-delete");
const libraryTagFilterInput = document.querySelector("#library-tag-filter");
const libraryTagAllFilterInput = document.querySelector("#library-tag-all-filter");
const selectedSourceTagFilters = new Set();
const selectedSourceAllTagFilters = new Set();
const evidenceProposalFocusInput = document.querySelector("#evidence-proposal-focus");
const evidenceReadScope = document.querySelector("#evidence-read-scope");
const evidenceRelatedLimit = document.querySelector("#evidence-related-limit");
const evidenceRelatedReport = document.querySelector("#evidence-related-report");
let savedEvidenceRequestMode = "combined";
const updateEvidenceReadScope = () => {
  const related = evidenceReadScope.value === "related";
  document.querySelector("#evidence-related-limit-label").hidden = !related;
  const note = document.querySelector("#evidence-related-cost");
  note.hidden = false;
  const individual = savedEvidenceRequestMode === "individual";
  const selected = selectedLibrarySourceKeys.size;
  const count = related ? Number(evidenceRelatedLimit.value) : selected;
  const calls = selected ? (individual ? count : 1) + (related ? 1 : 0) : 0;
  const estimate = document.createElement("strong");
  estimate.textContent = `Estimated model calls: ${related && individual && selected ? "up to " : ""}${calls}`;
  const explanation = document.createElement("span");
  explanation.textContent = `${individual ? "One by one" : "Combined"}`
    + (related ? ` · 1 page selection + ${individual ? "up to " + count : "1"} extraction. Fewer if no relevant pages or a request fails.` : ` · ${selected} selected Source${selected === 1 ? "" : "s"}.`);
  note.replaceChildren(estimate, explanation);
};
evidenceReadScope.addEventListener("change", updateEvidenceReadScope);
evidenceRelatedLimit.addEventListener("change", updateEvidenceReadScope);
const proposeEvidenceBtn = document.querySelector("#propose-evidence");
const sourceDiscoveryFocusInput = document.querySelector("#source-discovery-focus");
const sourceDiscoveryRunBtn = document.querySelector("#source-discovery-run");
const sourceDiscoveryResultsEl = document.querySelector("#source-discovery-results");
const sourceDiscoveryListEl = document.querySelector("#source-discovery-list");
const sourceDiscoverySummaryEl = document.querySelector("#source-discovery-summary");
const sourceDiscoveryStatusEl = document.querySelector("#source-discovery-status");
const sourceDiscoveryCloseBtn = document.querySelector("#source-discovery-close");
const sourceDiscoveryAddBtn = document.querySelector("#source-discovery-add");
const evidenceProposalsToggleBtn = document.querySelector("#evidence-proposals-toggle");
const evidenceProposalBoardEl = document.querySelector("#evidence-proposal-board");
const evidenceProposalListEl = document.querySelector("#evidence-proposal-list");
const evidenceLibrarySelectAllInput = document.querySelector("#evidence-library-select-all");
const evidenceTagFilterInput = document.querySelector("#evidence-tag-filter");
const evidenceTagAllFilterInput = document.querySelector("#evidence-tag-all-filter");
const claimsSelectAllInput = document.querySelector("#claims-select-all");
const claimsListControlsEl = document.querySelector("#claims-list-controls");
const claimsBatchTagBtn = document.querySelector("#claims-batch-tag");
const claimsTagFilterInput = document.querySelector("#claims-tag-filter");
const claimsTagAllFilterInput = document.querySelector("#claims-tag-all-filter");
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
const projectImportFileInput = document.querySelector("#project-import-file");
const claimsListEl = document.querySelector("#claims-list");
const claimsStatusEl = document.querySelector("#claims-status");
const claimStatementInput = document.querySelector("#claim-statement");
const claimBasisInput = document.querySelector("#claim-basis");
const claimArtifactInput = document.querySelector("#claim-artifact");
const claimCreateBtn = document.querySelector("#claim-create");
const claimCreateStatusEl = document.querySelector("#claim-create-status");
const claimsProposalsToggleBtn = document.querySelector("#claims-proposals-toggle");
const claimsAuditToggleBtn = document.querySelector("#claims-audit-toggle");
const claimAuditBoardEl = document.querySelector("#claim-audit-board");
const claimAuditCloseBtn = document.querySelector("#claim-audit-close");
const claimAuditScopeInput = document.querySelector("#claim-audit-scope");
const claimAuditModelSelect = document.querySelector("#claim-audit-model");
const claimAuditTagsEl = document.querySelector("#claim-audit-tags");
const claimAuditAnyTagsEl = document.querySelector("#claim-audit-any-tags");
const claimAuditAllTagsEl = document.querySelector("#claim-audit-all-tags");
const claimAuditEstimateEl = document.querySelector("#claim-audit-estimate");
const claimAuditProgressEl = document.querySelector("#claim-audit-progress");
const claimAuditProgressLabelEl = document.querySelector("#claim-audit-progress-label");
const claimAuditProgressCountEl = document.querySelector("#claim-audit-progress-count");
const claimAuditProgressBarEl = document.querySelector("#claim-audit-progress-bar");
const claimAuditRawEl = document.querySelector("#claim-audit-raw");
const claimAuditPreviewBtn = document.querySelector("#claim-audit-preview");
const claimAuditStartBtn = document.querySelector("#claim-audit-start");
const claimAuditPauseBtn = document.querySelector("#claim-audit-pause");
const claimAuditResumeBtn = document.querySelector("#claim-audit-resume");
const claimAuditCancelBtn = document.querySelector("#claim-audit-cancel");
const claimsRelateBtn = document.querySelector("#claims-relate");
const claimsSelectedCountEl = document.querySelector("#claims-selected-count");
const claimsRelationTypeInput = document.querySelector("#claims-relation-type");
const claimProposalBoardEl = document.querySelector("#claim-proposal-board");
const claimProposalListEl = document.querySelector("#claim-proposal-list");
const claimProposalReportEl = document.querySelector("#claim-proposal-report");
const claimProposalReportSummaryEl = document.querySelector("#claim-proposal-report-summary");
const claimProposalReportBodyEl = document.querySelector("#claim-proposal-report-body");
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
const wikiWorkspaceEl = document.querySelector("#wiki-workspace");
const wikiModeWikiBtn = document.querySelector("#wiki-mode-wiki");
const wikiModeGraphBtn = document.querySelector("#wiki-mode-graph");
const wikiOrganizeBtn = document.querySelector("#wiki-organize");
const wikiEditStructureBtn = document.querySelector("#wiki-edit-structure");
const wikiResetStructureBtn = document.querySelector("#wiki-reset-structure");
const wikiExportBtn = document.querySelector("#wiki-export");
const wikiImportFileInput = document.querySelector("#wiki-import-file");
const wikiImportsToggleBtn = document.querySelector("#wiki-imports-toggle");
const wikiImportReviewEl = document.querySelector("#wiki-import-review");
const wikiImportCloseBtn = document.querySelector("#wiki-import-close");
const wikiImportListEl = document.querySelector("#wiki-import-list");
const wikiProposalsToggleBtn = document.querySelector("#wiki-proposals-toggle");
const wikiHealthEl = document.querySelector("#wiki-health");
const wikiMainEl = document.querySelector("#wiki-main");
const wikiTreeEl = document.querySelector("#wiki-tree");
const wikiPageEl = document.querySelector("#wiki-page");
const wikiGraphEl = document.querySelector("#wiki-graph");
const wikiProposalReviewEl = document.querySelector("#wiki-proposal-review");
const wikiProposalCloseBtn = document.querySelector("#wiki-proposal-close");
const wikiProposalListEl = document.querySelector("#wiki-proposal-list");
const wikiReadingComposerEl = document.querySelector("#wiki-reading-composer");
const wikiReadingCloseBtn = document.querySelector("#wiki-reading-close");
const wikiReadingGoalInput = document.querySelector("#wiki-reading-goal");
const wikiReadingScopeEl = document.querySelector("#wiki-reading-scope");
const wikiReadingRunBtn = document.querySelector("#wiki-reading-run");
const wikiReadingEl = document.querySelector("#wiki-reading");
const wikiStatusEl = document.querySelector("#wiki-status");
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
let excludedSearchResults = [];
let sourceDiscoveryResults = [];
let sourceDiscoveryExcluded = [];
let sourceDiscoveryOpen = false;
let sourceDiscoveryBusy = false;
let sourceDiscoveryEmptyMessage = "No related candidates were returned by Semantic Scholar.";
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
let searchStrategyActions = [];
let searchStrategyWaitingActions = [];
let searchStrategyIntent = "";
let searchStrategyStaleAcknowledged = false;
const SEARCH_STRATEGY_TOP_LIMIT = 5;
const SEARCH_STRATEGY_CANDIDATE_LIMIT = 15;
let searchStrategyAttentionTimer = null;
let aiModelProfiles = [];
let aiRoleAssignments = {};
const AI_ROLE_DEFINITIONS = [
  ["embedding", "Embedding", "embeddings"],
  ["intelligent_search", "Search · AI Review / Discuss", "chat"],
  ["source_discovery", "Related Source discovery", "chat"],
  ["copilot", "Review Copilot", "chat"],
  ["evidence", "Evidence proposal", "chat"],
  ["claims", "Claim proposal", "chat"],
  ["wiki", "Wiki organization", "chat"],
  ["article", "Article generation", "chat"],
];

let skillPreviewRequest = 0;
const renderCopilotPromptPreview = async () => {
  const request = ++skillPreviewRequest;
  const stage = aiCopilotPromptStageInput?.value || "search_strategy";
  try {
    const response = await fetch("/api/skills");
    if (!response.ok) throw new Error("Could not load stage skills.");
    const data = await response.json();
    if (request !== skillPreviewRequest) return;
    aiCopilotPromptStageInput.replaceChildren();
    (data.skills || []).forEach((skill) => {
      const option = new Option(skill.label, skill.id);
      aiCopilotPromptStageInput.add(option);
    });
    aiCopilotPromptStageInput.value = stage;
    if (!aiCopilotPromptStageInput.value) aiCopilotPromptStageInput.value = "search_strategy";
    const info = data.skills.find((skill) => skill.id === aiCopilotPromptStageInput.value);
    if (!info) throw new Error("Stage skill is unavailable.");
    aiCopilotPromptSharedBlockEl.hidden = false;
    aiCopilotPromptSharedEl.textContent = info.rules;
    aiCopilotPromptStageLabelEl.textContent = `Stage skill · ${info.mode === "custom" ? "Custom" : "Built-in"}`;
    aiCopilotPromptPreviewEl.textContent = info.error
      ? "Custom Skill could not be loaded. Fix the file and reload, or use the built-in Skill."
      : info.skill;
    aiCopilotPromptNoteEl.textContent = info.error || "Custom instructions guide the stage; product rules and output contracts always apply. File edits take effect on the next request. Reload checks the file and refreshes this preview.";
    aiCopilotPromptNoteEl.classList.toggle("skill-error", Boolean(info.error));
    document.querySelector("#skill-path").textContent = info.path;
    document.querySelector("#skill-contract").textContent = JSON.stringify(info.contract, null, 2);
    const preferences = (info.id.startsWith("copilot_") || info.id === "search_strategy")
      ? aiCopilotInstructionsInput.value.trim() : "";
    document.querySelector("#skill-assembled").textContent = info.error ? "Blocked until the custom Skill is fixed or disabled." : `${info.system}\n\nUSER MESSAGE — Stage guidance:\n${info.guidance}${preferences ? `\n\nUser preferences:\n${preferences}` : ""}\n\n[Task input is appended at runtime]`;
    document.querySelector("#skill-customize").textContent = info.custom_exists ? "Use custom" : "Create custom copy";
    document.querySelector("#skill-customize").disabled = info.mode === "custom" && !info.error;
    document.querySelector("#skill-builtin").disabled = info.mode === "built-in";
    document.querySelector("#skill-reveal").textContent = data.platform === "darwin" ? "Show in Finder" : "Open folder";
  } catch (error) {
    aiCopilotPromptNoteEl.textContent = error.message;
  }
};

document.querySelectorAll("[data-skill-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const response = await fetch("/api/skills", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage: aiCopilotPromptStageInput.value, action: button.dataset.skillAction }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Could not update the Skill.");
      await renderCopilotPromptPreview();
    } catch (error) {
      aiCopilotPromptNoteEl.textContent = error.message;
      aiCopilotPromptNoteEl.classList.add("skill-error");
      button.disabled = false;
    } finally {
      if (!["customize", "builtin"].includes(button.dataset.skillAction)) button.disabled = false;
    }
  });
});

aiCopilotPromptStageInput?.addEventListener("change", renderCopilotPromptPreview);
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
let latestClaimProposalReport = null;
let claimAudits = [];
let activeClaimAudit = null;
let claimAuditBoardOpen = false;
let claimAuditAdvancing = false;
let claimAuditPreviewKey = "";
let evidenceProposals = [];
let claimProposalQueueOpen = false;
let evidenceProposalQueueOpen = false;
let views = [];
let activeViewId = "";
let viewDraftClaimIds = [];
let viewDraftBlocks = [];
let viewAddingClaims = false;
let activeGraphClaimId = "";
let wikiState = { pages: [], claims: [], graph: { nodes: [], edges: [] }, unorganized_claim_ids: [], stale_claim_ids: [], awaiting_review: 0 };
let wikiProposals = [];
let wikiImports = [];
let wikiProposalRunning = false;
let activeWikiProposalId = "";
const activeWikiProposalPageKeys = new Map();
let draggedWikiPatchPageKey = "";
let draggedWikiPatchClaimId = "";
let activeWikiPageId = "";
let wikiMode = "wiki";
let currentWikiReading = null;
let currentWikiReadingGoal = "";
let activeArticleProjectId = "";
const selectedResultKeys = new Set();
const selectedLibrarySourceKeys = new Set();
const selectedDiscoverySourceKeys = new Set();
const selectedEvidenceIds = new Set();
const selectedClaimIds = new Set();
const selectedEvidenceTagFilters = new Set();
const selectedEvidenceAllTagFilters = new Set();
const selectedClaimTagFilters = new Set();
const selectedClaimAllTagFilters = new Set();
const selectedClaimAuditAnyTags = new Set();
const selectedClaimAuditAllTags = new Set();
const incomingClaimEvidenceIds = new Set();
const incomingClaimEvidenceStances = new Map();
let incomingLLMEvidenceIds = null;
const incomingViewClaimIds = new Set();
let evidenceReturnToClaim = false;
let claimsReturnToView = false;
const chatContextSources = new Map();
const chatContextEvidence = new Map();
let CHAT_CONTEXT_LIMIT = 12;
let evidenceSourceLimit = 6;
let claimEvidenceLimit = 30;
let wikiClaimLimit = 100;
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
let readerTextSelectionArmed = false;
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
const chatInputHistories = {};
const chatInputHistoryCursors = {};
const chatInputDrafts = {};
const expandedArtifactIds = new Set();
const projectDetails = new Map();
const projectClaimScopes = new Map();
const projectClaimRecommendations = new Map();
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
          body: JSON.stringify({ artifact_id: "" }),
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
    card.append(title, meta, quote, actions);
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
        theme: themeToggleBtn?.dataset.mode || "auto",
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

const newAIProfile = () => ({
  id: globalThis.crypto?.randomUUID?.() || `model-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  name: "New model", provider: "openai_compatible", base_url: "", model: "",
  capabilities: ["chat"], enable_thinking: false,
  custom_recipe: {}, api_key: "", api_key_configured: false,
  remove_api_key: false, proxy_mode: "auto", proxy_url: "",
});

const availableAICapabilities = (profile) => {
  const provider = String(profile.provider || "openai_compatible").toLowerCase();
  const model = String(profile.model || "").trim().toLowerCase();
  const base = String(profile.base_url || "").trim().toLowerCase();
  const available = new Set(["chat", "embeddings"]);
  if (provider === "deepseek") return new Set(["chat"]);
  if (provider === "openai") {
    if (["gpt-4.1", "gpt-5", "o3", "o4"].some((prefix) => model.startsWith(prefix))) {
      available.add("native_documents"); available.add("web_search");
    }
  } else if (provider === "google") {
    if (model.startsWith("gemini-")) {
      available.add("native_documents"); available.add("url_fetch");
    }
  } else if (provider === "anthropic") {
    available.delete("embeddings");
    if (model.startsWith("claude-")) {
      available.add("native_documents"); available.add("web_search");
    }
  } else if (provider === "qwen") {
    const searchFamilies = ["qwen3.8", "qwen3.7", "qwen3.6", "qwen3.5", "qwen3-max", "qwen-max", "qwen-plus", "qwen-turbo"];
    if (searchFamilies.some((prefix) => model.startsWith(prefix))) available.add("web_search");
    if (model === "qwen3.8-max" && base.includes("cn-beijing.maas.aliyuncs.com")) {
      available.add("native_documents");
    }
  } else if (provider === "kimi") {
    available.delete("embeddings"); available.add("file_extraction");
    if (model.startsWith("kimi-k2.6")) available.add("web_search");
  } else if (provider === "custom") {
    return new Set(["chat", "embeddings", "native_documents", "file_extraction", "web_search", "url_fetch"]);
  }
  return available;
};

const aiThinkingAvailable = (profile) => {
  const provider = String(profile.provider || "openai_compatible").toLowerCase();
  const model = String(profile.model || "").trim().toLowerCase();
  if (["openai_compatible", "deepseek", "custom"].includes(provider)) return true;
  if (provider === "qwen") return model.startsWith("qwen3") || model.startsWith("qwq");
  if (provider === "kimi") return model.startsWith("kimi-k2.6");
  return false;
};

const renderAIRoles = (useAssignedModels = false) => {
  aiRoleGridEl.replaceChildren();
  const firstChatProfile = aiModelProfiles.find(
    (profile) => (profile.capabilities || []).includes("chat"),
  );
  AI_ROLE_DEFINITIONS.filter(([, , capability]) => capability === "chat")
    .forEach(([role]) => {
      if (!aiRoleAssignments[role] && firstChatProfile) {
        aiRoleAssignments[role] = firstChatProfile.id;
      }
    });
  AI_ROLE_DEFINITIONS.forEach(([role, label, capability]) => {
    const field = document.createElement("label");
    field.className = "ai-role-field";
    const name = document.createElement("span");
    name.textContent = label;
    const select = document.createElement("select");
    select.dataset.aiRole = role;
    select.appendChild(new Option(
      role === "embedding" ? "No embedding model" : "Select a model", "",
    ));
    aiModelProfiles
      .filter((profile) => (profile.capabilities || []).includes(capability))
      .forEach((profile) => select.appendChild(new Option(
        profile.name || profile.model || "Unnamed model", profile.id,
      )));
    select.value = aiRoleAssignments[role] || "";
    select.addEventListener("change", () => {
      aiRoleAssignments[role] = select.value;
      updateProfileDirtyState();
    });
    field.append(name, select);
    aiRoleGridEl.appendChild(field);
  });
  const selectedCopilotModel = (useAssignedModels ? "" : contextModelSelect.value)
    || aiRoleAssignments.copilot || "";
  contextModelSelect.replaceChildren(new Option("Select a Copilot model", ""));
  aiModelProfiles.filter((profile) => (profile.capabilities || []).includes("chat"))
    .forEach((profile) => contextModelSelect.appendChild(new Option(
      profile.name || profile.model || "Unnamed model", profile.id,
    )));
  contextModelSelect.value = [...contextModelSelect.options].some(
    (option) => option.value === selectedCopilotModel,
  ) ? selectedCopilotModel : "";
  renderActionModelSelectors(useAssignedModels);
};

const renderActionModelSelectors = (useAssignedModels = false) => {
  const definitions = [
    [searchModelSelect, "intelligent_search", "Select a Search model"],
    [sourceDiscoveryModelSelect, "source_discovery", "Select a discovery model"],
    [evidenceModelSelect, "evidence", "Select an Evidence model"],
    [claimsModelSelect, "claims", "Select a Claims model"],
    [claimAuditModelSelect, "claims", "Select a Claims model"],
    [wikiModelSelect, "wiki", "Select a Wiki model"],
    [articleModelSelect, "article", "Select an Article model"],
  ];
  const chatProfiles = aiModelProfiles.filter(
    (profile) => (profile.capabilities || []).includes("chat"),
  );
  definitions.forEach(([select, role, placeholder]) => {
    if (!select) return;
    const current = (useAssignedModels ? "" : select.value) || aiRoleAssignments[role] || "";
    select.replaceChildren(new Option(placeholder, ""));
    chatProfiles.forEach((profile) => select.appendChild(new Option(
      profile.name || profile.model || "Unnamed model", profile.id,
    )));
    select.value = [...select.options].some((option) => option.value === current)
      ? current : "";
  });
};

const renderAIProfiles = () => {
  aiProfileListEl.replaceChildren();
  aiModelProfiles.forEach((profile, index) => {
    const card = document.createElement("details");
    card.className = "ai-profile-card";
    card.open = aiModelProfiles.length === 1;
    const summary = document.createElement("summary");
    const title = document.createElement("strong");
    title.textContent = profile.name || profile.model || `Model ${index + 1}`;
    const meta = document.createElement("small");
    meta.textContent = [profile.provider?.replaceAll("_", "-"), profile.model].filter(Boolean).join(" · ");
    summary.append(title, meta);
    const body = document.createElement("div");
    body.className = "ai-profile-body";
    const field = (label, input) => {
      const wrapper = document.createElement("div");
      wrapper.className = "config-row";
      const caption = document.createElement("span");
      caption.textContent = label;
      if (["INPUT", "SELECT", "TEXTAREA"].includes(input.tagName)) {
        input.setAttribute("aria-label", label);
      }
      wrapper.append(caption, input);
      return wrapper;
    };
    const nameInput = document.createElement("input");
    nameInput.value = profile.name || "";
    nameInput.addEventListener("input", () => {
      profile.name = nameInput.value; title.textContent = nameInput.value || profile.model || "Unnamed model";
      renderAIRoles(); updateProfileDirtyState();
    });
    const provider = document.createElement("select");
    [["openai_compatible", "OpenAI-compatible"], ["openai", "OpenAI"], ["google", "Google Gemini"], ["anthropic", "Anthropic"], ["deepseek", "DeepSeek"], ["qwen", "Alibaba Model Studio · Qwen"], ["kimi", "Moonshot · Kimi"], ["custom", "Custom Recipe"]]
      .forEach(([value, text]) => provider.appendChild(new Option(text, value)));
    provider.value = profile.provider || "openai_compatible";
    const base = document.createElement("input");
    base.value = profile.base_url || ""; base.placeholder = "https://provider.example/v1";
    const model = document.createElement("input");
    model.value = profile.model || ""; model.placeholder = "Provider model ID";
    const proxyMode = document.createElement("select");
    [["auto", "Auto · local direct, public system proxy"], ["system", "System proxy"], ["direct", "Direct · never use a proxy"], ["custom", "Custom proxy"]]
      .forEach(([value, text]) => proxyMode.appendChild(new Option(text, value)));
    proxyMode.value = profile.proxy_mode || "auto";
    const proxyUrl = document.createElement("input");
    proxyUrl.value = profile.proxy_url || "";
    proxyUrl.placeholder = "http://127.0.0.1:7890";
    const proxyUrlField = field("Proxy URL", proxyUrl);
    proxyUrlField.hidden = proxyMode.value !== "custom";
    const key = document.createElement("input");
    key.type = "password"; key.autocomplete = "new-password";
    key.setAttribute("aria-label", "API key");
    key.placeholder = profile.api_key_configured && !profile.remove_api_key
      ? "Configured; enter a new key to replace" : "Optional for local services";
    const keyRow = document.createElement("div");
    keyRow.className = "secret-input-row";
    const removeKey = document.createElement("button");
    removeKey.type = "button"; removeKey.className = "secret-remove";
    removeKey.textContent = profile.remove_api_key ? "Undo" : "Remove";
    removeKey.hidden = !profile.api_key_configured;
    removeKey.addEventListener("click", () => {
      profile.remove_api_key = !profile.remove_api_key;
      key.disabled = profile.remove_api_key; key.value = "";
      removeKey.textContent = profile.remove_api_key ? "Undo" : "Remove";
      updateProfileDirtyState();
    });
    keyRow.append(key, removeKey);
    const capabilityBox = document.createElement("div");
    capabilityBox.className = "ai-capability-list";
    const capabilityInputs = new Map();
    const capabilityDefinitions = [
      ["chat", "Chat"], ["embeddings", "Embeddings"],
      ["native_documents", "Native PDF"], ["file_extraction", "File extraction"],
      ["web_search", "Web search"], ["url_fetch", "URL fetch"],
    ];
    capabilityDefinitions
      .forEach(([value, text]) => {
        const label = document.createElement("label");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox"; checkbox.checked = (profile.capabilities || []).includes(value);
        capabilityInputs.set(value, checkbox);
        checkbox.addEventListener("change", () => {
          const set = new Set(profile.capabilities || []);
          checkbox.checked ? set.add(value) : set.delete(value);
          profile.capabilities = [...set]; renderAIRoles(); updateProfileDirtyState();
        });
        label.append(checkbox, document.createTextNode(text)); capabilityBox.appendChild(label);
      });
    const capabilityNote = document.createElement("small");
    capabilityNote.className = "ai-capability-note";
    capabilityNote.textContent = "Unavailable capabilities are locked for this provider, model, and endpoint.";
    capabilityBox.appendChild(capabilityNote);
    const refreshCapabilities = () => {
      const available = availableAICapabilities(profile);
      const enabled = new Set(profile.capabilities || []);
      capabilityInputs.forEach((input, capability) => {
        const supported = available.has(capability);
        input.disabled = !supported;
        input.closest("label")?.classList.toggle("unavailable", !supported);
        input.closest("label")?.setAttribute(
          "title", supported ? "Implemented for this configuration" : "Not implemented for this configuration",
        );
        if (!supported) enabled.delete(capability);
        input.checked = supported && enabled.has(capability);
      });
      profile.capabilities = [...enabled];
    };
    refreshCapabilities();
    const thinking = document.createElement("label");
    thinking.className = "config-check";
    const thinkingInput = document.createElement("input");
    thinkingInput.type = "checkbox"; thinkingInput.checked = Boolean(profile.enable_thinking);
    thinking.append(thinkingInput, document.createTextNode("Enable Thinking"));
    const refreshThinking = () => {
      const supported = aiThinkingAvailable(profile);
      thinkingInput.disabled = !supported;
      thinking.classList.toggle("unavailable", !supported);
      thinking.title = supported
        ? "Implemented for this configuration"
        : "Knowte has no verified Thinking toggle for this configuration";
      if (!supported) {
        thinkingInput.checked = false;
        profile.enable_thinking = false;
      }
    };
    refreshThinking();
    const recipe = document.createElement("textarea");
    recipe.rows = 10; recipe.spellcheck = false;
    recipe.value = JSON.stringify(profile.custom_recipe || {}, null, 2);
    const recipeField = field("Custom request recipe", recipe);
    recipeField.hidden = provider.value !== "custom";
    const removeProfile = document.createElement("button");
    removeProfile.type = "button"; removeProfile.className = "ai-profile-remove";
    removeProfile.textContent = "Remove model";
    removeProfile.addEventListener("click", () => {
      aiModelProfiles.splice(index, 1);
      Object.keys(aiRoleAssignments).forEach((role) => {
        if (aiRoleAssignments[role] === profile.id) aiRoleAssignments[role] = "";
      });
      renderAIProfiles(); renderAIRoles(); updateProfileDirtyState();
    });
    provider.addEventListener("change", () => {
      profile.provider = provider.value; recipeField.hidden = provider.value !== "custom";
      const defaults = {
        openai: "https://api.openai.com/v1",
        google: "https://generativelanguage.googleapis.com/v1beta",
        anthropic: "https://api.anthropic.com/v1",
        deepseek: "https://api.deepseek.com",
        qwen: "https://dashscope.aliyuncs.com/compatible-mode/v1",
        kimi: "https://api.moonshot.cn/v1",
      };
      if (!base.value.trim() && defaults[provider.value]) {
        base.value = defaults[provider.value]; profile.base_url = base.value;
      }
      const presetCapabilities = {
        deepseek: ["chat"],
        qwen: ["chat", "native_documents", "web_search"],
        kimi: ["chat", "file_extraction", "web_search"],
        openai: ["chat", "native_documents", "web_search"],
        google: ["chat", "native_documents", "url_fetch"],
        anthropic: ["chat", "native_documents", "web_search"],
      };
      if (presetCapabilities[provider.value]) {
        profile.capabilities = [...presetCapabilities[provider.value]];
      }
      refreshCapabilities();
      refreshThinking();
      meta.textContent = [provider.value.replaceAll("_", "-"), profile.model].filter(Boolean).join(" · ");
      renderAIRoles(); updateProfileDirtyState();
    });
    base.addEventListener("input", () => { profile.base_url = base.value; refreshCapabilities(); refreshThinking(); renderAIRoles(); updateProfileDirtyState(); });
    model.addEventListener("input", () => { profile.model = model.value; meta.textContent = [profile.provider?.replaceAll("_", "-"), model.value].filter(Boolean).join(" · "); refreshCapabilities(); refreshThinking(); renderAIRoles(); updateProfileDirtyState(); });
    proxyMode.addEventListener("change", () => {
      profile.proxy_mode = proxyMode.value;
      proxyUrlField.hidden = proxyMode.value !== "custom";
      updateProfileDirtyState();
    });
    proxyUrl.addEventListener("input", () => { profile.proxy_url = proxyUrl.value; updateProfileDirtyState(); });
    key.addEventListener("input", () => { profile.api_key = key.value; profile.remove_api_key = false; updateProfileDirtyState(); });
    thinkingInput.addEventListener("change", () => { profile.enable_thinking = thinkingInput.checked; updateProfileDirtyState(); });
    recipe.addEventListener("input", () => { profile.custom_recipe_text = recipe.value; updateProfileDirtyState(); });
    body.append(
      field("Profile name", nameInput), field("Provider", provider),
      field("Base URL", base), field("Model ID", model), field("API key", keyRow),
      field("Proxy routing", proxyMode), proxyUrlField,
      field("Capabilities", capabilityBox), thinking, recipeField, removeProfile,
    );
    card.append(summary, body); aiProfileListEl.appendChild(card);
  });
  renderAIRoles();
};

aiProfileAddBtn.addEventListener("click", () => {
  aiModelProfiles.push(newAIProfile());
  renderAIProfiles();
  aiProfileListEl.lastElementChild.open = true;
  updateProfileDirtyState();
});

const serializedAIProfiles = () => aiModelProfiles.map((profile) => ({
  id: profile.id, name: String(profile.name || "").trim(), provider: profile.provider,
  base_url: String(profile.base_url || "").trim(), model: String(profile.model || "").trim(),
  proxy_mode: profile.proxy_mode || "auto", proxy_url: String(profile.proxy_url || "").trim(),
  capabilities: [...(profile.capabilities || [])], enable_thinking: Boolean(profile.enable_thinking),
  custom_recipe: JSON.parse(profile.custom_recipe_text ?? JSON.stringify(profile.custom_recipe || {})),
  ...(profile.api_key ? { api_key: profile.api_key } : {}),
  remove_api_key: Boolean(profile.remove_api_key),
}));

const serializeProfileState = (overrides = {}) => JSON.stringify({
  email: overrides.email ?? emailInput.value.trim(),
  max_papers: overrides.max_papers ?? parseMaxPapers(maxPapersInput.value || "100"),
  intelligent_max_results: overrides.intelligent_max_results
    ?? Number(intelligentMaxResultsInput.value || 20),
  enabled_backends: overrides.enabled_backends ?? Array.from(
    backendGrid.querySelectorAll("input[type='checkbox']:checked"),
  ).map((box) => box.value).sort(),
  api_key_update: s2KeyInput.value.trim(),
  api_key_clear: semanticscholarKeyRemovalPending,
  ai_model_profiles: overrides.ai_model_profiles ?? serializedAIProfiles(),
  ai_role_assignments: overrides.ai_role_assignments ?? aiRoleAssignments,
  ai_verify_batch_size: overrides.ai_verify_batch_size
    ?? Number(aiVerifyBatchSizeInput.value || 5),
  ai_verify_concurrency: overrides.ai_verify_concurrency
    ?? Number(aiVerifyConcurrencyInput.value || 1),
  ai_search_timeout_seconds: overrides.ai_search_timeout_seconds
    ?? Number(aiSearchTimeoutInput.value || 45),
  ai_evidence_source_limit: overrides.ai_evidence_source_limit ?? Number(ai_evidence_source_limitInput.value || 6),
  ai_claim_evidence_limit: overrides.ai_claim_evidence_limit ?? Number(ai_claim_evidence_limitInput.value || 30),
  ai_claim_comparison_limit: overrides.ai_claim_comparison_limit ?? Number(aiClaimComparisonLimitInput.value || 100),
  ai_wiki_claim_limit: overrides.ai_wiki_claim_limit ?? Number(aiWikiClaimLimitInput.value || 100),
  ai_copilot_context_limit: overrides.ai_copilot_context_limit ?? Number(ai_copilot_context_limitInput.value || 12),
  ai_evidence_request_mode: overrides.ai_evidence_request_mode ?? evidenceRequestModeInput.value,
  ai_stage_timeout_seconds: overrides.ai_stage_timeout_seconds
    ?? Number(aiStageTimeoutInput.value || 45),
  ai_copilot_instructions: overrides.ai_copilot_instructions
    ?? aiCopilotInstructionsInput.value.trim(),
  ai_copilot_temperature: overrides.ai_copilot_temperature
    ?? Number(aiCopilotTemperatureInput.value || 0),
  ai_copilot_max_tokens: overrides.ai_copilot_max_tokens
    ?? Number(aiCopilotMaxTokensInput.value || 1200),
  ai_copilot_advanced_parameters: overrides.ai_copilot_advanced_parameters
    ?? copilotAdvancedParameters(),
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
  excludedSearchResults = [];
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

const renderSearchStrategy = () => {
  searchStrategyListEl.replaceChildren();
  searchStrategyWaitingListEl.replaceChildren();
  const renderAction = (action, index, collection, container, isWaiting) => {
    const row = document.createElement("div");
    row.className = "search-strategy-row";
    const makeField = (labelText, control, className) => {
      const field = document.createElement("label");
      field.className = `search-strategy-field ${className}`;
      const label = document.createElement("span");
      label.textContent = labelText;
      field.append(label, control);
      return field;
    };
    const query = document.createElement("input");
    query.type = "text";
    query.value = action.query || "";
    query.placeholder = "Retrieval query";
    query.setAttribute("aria-label", `${isWaiting ? "Waiting" : "Active"} search action ${index + 1} query`);
    query.addEventListener("input", () => { action.query = query.value; });
    action.target = "academic";
    const purpose = document.createElement("textarea");
    purpose.rows = 2;
    purpose.value = action.purpose || "";
    purpose.placeholder = "Purpose (optional)";
    purpose.setAttribute("aria-label", `${isWaiting ? "Waiting" : "Active"} search action ${index + 1} purpose`);
    purpose.addEventListener("input", () => { action.purpose = purpose.value; });
    const controls = document.createElement("div");
    controls.className = "search-strategy-row-actions";
    const transfer = document.createElement("button");
    transfer.type = "button";
    transfer.className = "search-strategy-transfer";
    transfer.innerHTML = isWaiting
      ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6" /></svg><span>Move in</span>'
      : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M6 13l6 6 6-6" /></svg><span>Move out</span>';
    transfer.setAttribute(
      "aria-label",
      `${isWaiting ? "Move into" : "Move out of"} active Search list`,
    );
    transfer.addEventListener("click", () => {
      if (isWaiting && searchStrategyActions.length >= SEARCH_STRATEGY_TOP_LIMIT) {
        searchStrategyStatusEl.textContent = "The Search list already has 5 candidates. Move one out before moving another in.";
        searchStrategyStatusEl.dataset.state = "error";
        searchStrategyStatusEl.classList.remove("is-attention");
        void searchStrategyStatusEl.offsetWidth;
        searchStrategyStatusEl.classList.add("is-attention");
        if (searchStrategyAttentionTimer !== null) {
          window.clearTimeout(searchStrategyAttentionTimer);
        }
        searchStrategyAttentionTimer = window.setTimeout(() => {
          searchStrategyStatusEl.classList.remove("is-attention");
          searchStrategyAttentionTimer = null;
        }, 1000);
        return;
      }
      const [moved] = collection.splice(index, 1);
      if (isWaiting) searchStrategyActions.push(moved);
      else searchStrategyWaitingActions.push(moved);
      renderSearchStrategy();
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "search-strategy-remove";
    remove.textContent = "×";
    remove.setAttribute("aria-label", `Delete ${isWaiting ? "waiting" : "active"} search action ${index + 1}`);
    remove.addEventListener("click", () => {
      collection.splice(index, 1);
      renderSearchStrategy();
    });
    controls.append(transfer, remove);
    row.append(
      makeField("Query", query, "search-strategy-query"),
      controls,
      makeField("Purpose", purpose, "search-strategy-purpose"),
    );
    container.appendChild(row);
  };
  searchStrategyActions.forEach(
    (action, index) => renderAction(
      action, index, searchStrategyActions, searchStrategyListEl, false,
    ),
  );
  searchStrategyWaitingActions.forEach(
    (action, index) => renderAction(
      action, index, searchStrategyWaitingActions, searchStrategyWaitingListEl, true,
    ),
  );
  const waitingCount = searchStrategyWaitingActions.length;
  searchStrategyWaitingEl.hidden = waitingCount === 0;
  searchStrategyAddBtn.disabled = searchStrategyActions.length + waitingCount >= SEARCH_STRATEGY_CANDIDATE_LIMIT;
  searchStrategyStatusEl.dataset.state = "";
  searchStrategyStatusEl.textContent = searchStrategyActions.length || waitingCount
    ? `${searchStrategyActions.length} active${waitingCount ? ` · ${waitingCount} waiting` : ""}. Search runs active candidates only, up to 5.`
    : "No strategy actions yet. Search will use the original intent directly.";
  updateSearchStrategyIntentState();
};

const normalizedSearchIntent = () => input.value.trim().replace(/\s+/g, " ");

const isSearchStrategyStale = () => Boolean(
  searchStrategyActions.length
  && searchStrategyIntent
  && normalizedSearchIntent() !== searchStrategyIntent
);

function updateSearchStrategyIntentState() {
  const stale = isSearchStrategyStale();
  if (!stale) searchStrategyStaleAcknowledged = false;
  searchStrategyStaleEl.hidden = !stale || searchStrategyStaleAcknowledged;
}

const importPrompt = () => {
  const intent = input.value.trim() || "<describe what you want to discover>";
  return `Find real, independently verifiable sources that help answer my research question.

Research request:
${intent}

Maximum sources: 10. Follow any area or date requirements stated in the research request.

Choose source types according to the question: papers and reports for original findings, documentation and code repositories for implementation, and substantive web pages or blogs for explanation and independent analysis. Prefer primary sources where possible. Do not restrict results to academic papers or force a quota for each type.

Requirements:
- Include only Sources that you believe really exist.
- If browsing is available, verify the links and metadata. Never claim to have read a source you could not access.
- Every item must contain at least one resolvable URL, DOI, or arXiv ID.
- Do not invent missing metadata; use an empty string, empty array, or 0 instead.
- Keep Source metadata separate from your explanation of relevance.
- Do not put your own summary into the Source abstract.
- Avoid duplicate versions of the same work.
- Return JSON only, without Markdown fences or additional prose.

Use this exact structure:
{"knowte_import_version":1,"request":${JSON.stringify(intent)},"sources":[{"title":"Exact Source title","source_type":"paper","url":"https://...","doi":"","arxiv_id":"","authors":["Author name"],"year":0,"why_relevant":"What this source contributes to answering the question, and any important limitation"}]}

Valid source_type values: paper, report, documentation, web, book, dataset, other.
Use web for blogs and general web pages; use other for code repositories. Return fewer than 10 sources if there are not enough useful, verifiable results.

Example only — answer my research request above, not this example question:
{"knowte_import_version":1,"request":"How does PPO constrain policy updates, and how can I implement it?","sources":[{"title":"Proximal Policy Optimization Algorithms","source_type":"paper","url":"https://arxiv.org/abs/1707.06347","doi":"","arxiv_id":"1707.06347","authors":[],"year":2017,"why_relevant":"Introduces PPO objectives; useful for understanding the motivation for limiting policy updates."},{"title":"Proximal Policy Optimization","source_type":"documentation","url":"https://spinningup.openai.com/en/latest/algorithms/ppo.html","doi":"","arxiv_id":"","authors":[],"year":0,"why_relevant":"Explains PPO-Clip and practical training steps, bridging the objective and implementation."},{"title":"CleanRL","source_type":"other","url":"https://github.com/vwxyzjn/cleanrl","doi":"","arxiv_id":"","authors":[],"year":0,"why_relevant":"Provides runnable PPO implementations for examining training details; implementation choices are not universal theoretical guarantees."}]}`;
};

const updateImportPrompt = () => { importPromptPreviewEl.textContent = importPrompt(); };

const setSearchMode = (mode) => {
  // Keep legacy execution modes so old Config and Plans retain their behavior.
  const nextMode = mode === "search" ? (searchAIReview ? "smart" : "keyword")
    : ["smart", "import"].includes(mode) ? mode : "keyword";
  const modeChanged = nextMode !== searchMode;
  searchMode = nextMode;
  if (searchMode !== "import") searchAIReview = searchMode === "smart";
  searchAIReviewInput.checked = searchAIReview;
  document.querySelector("#search-ai-review-control").hidden = searchMode === "import";
  searchModeButtons.forEach((button) => {
    const active = button.dataset.searchMode === (searchMode === "import" ? "import" : "search");
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  searchStrategyEl.hidden = searchMode === "import"
    || !(searchStrategyActions.length || searchStrategyWaitingActions.length);
  searchImportEl.hidden = searchMode !== "import";
  filtersEl.hidden = searchMode === "import";
  discussSearchBtn.hidden = searchMode === "import";
  if (searchModelControl) searchModelControl.hidden = searchMode === "import";
  form.classList.toggle("has-model-control", searchMode !== "import");
  searchSubmitBtn.hidden = searchMode === "import";
  savePlanBtn.hidden = searchMode === "import";
  if (searchMode === "smart") {
    input.placeholder = "Describe what you want to understand...";
    searchSubmitBtn.textContent = "Search";
    searchModeHint.textContent = "Search academic sources, then rank and review results against your intent.";
  } else if (searchMode === "import") {
    input.placeholder = "Describe what you asked the external service to find…";
    searchModeHint.textContent = "Import links or structured results from people, tools, or external LLMs.";
    intelligentProgressEl.hidden = true;
    updateImportPrompt();
  } else {
    input.placeholder = "Enter keywords, authors, or domains...";
    searchSubmitBtn.textContent = "Search";
    searchModeHint.textContent = "Search academic sources without model review. Discuss can help prepare queries using the selected model.";
    intelligentProgressEl.hidden = true;
  }
  if (modeChanged) {
    clearDisplayedSearchResults();
    statusEl.textContent = searchMode === "smart"
      ? "AI Review on. Search directly or discuss academic queries first."
      : searchMode === "import"
        ? "Import mode ready. Paste human-curated links or structured external results."
        : "AI Review off. Search uses active candidates, or your original input if there are none.";
  }
};

const renderDefaultSearchMode = () => {
  defaultSearchModeButtons.forEach((button) => {
    const isDefault = button.dataset.defaultSearchMode === (defaultSearchMode === "import" ? "import" : "search");
    const label = isDefault ? "Default search mode" : "Set as default";
    const modeName = ({
      search: "Search",
      import: "Import",
      keyword: "Keyword",
    })[button.dataset.defaultSearchMode] || "Search";
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

const selectedResults = () => [...fullResults, ...excludedSearchResults].filter(
  (source) => selectedResultKeys.has(resultKey(source)),
);
const selectedPrimaryResultCount = () => fullResults.filter(
  (source) => selectedResultKeys.has(resultKey(source)),
).length;

const selectedLibrarySources = () => librarySources.filter(
  (source) => selectedLibrarySourceKeys.has(resultKey(source)),
);

const selectedClaims = () => [...selectedClaimIds]
  .map((id) => claims.find((claim) => claim.id === id))
  .filter(claim => claim && !claim.needs_review);

const exportKnowledge = async (type, ids, statusEl, button) => {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Exporting…";
  statusEl.textContent = `Preparing ${type === "wiki" ? "Wiki" : "Project"} export…`;
  try {
    const response = await fetch("/api/exports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type, ids }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || "Could not create the export.");
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const filename = disposition.match(/filename="([^"]+)"/)?.[1]
      || `knowte-${type}-export.zip`;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = filename; document.body.appendChild(link); link.click();
    link.remove(); URL.revokeObjectURL(url);
    statusEl.textContent = `${filename} downloaded.`;
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    button.textContent = original;
    button.disabled = type === "wiki"
      ? !wikiState.claims.some((claim) => claim.lifecycle === "active")
      : false;
  }
};

const activeView = () => views.find((view) => view.id === activeViewId) || null;
const activeWikiPage = () => wikiState.pages.find((page) => page.id === activeWikiPageId) || null;
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
  currentReviewContext() === "evidence"
    ? libraryEvidence.filter((item) => selectedEvidenceIds.has(item.id))
    : currentReviewContext() === "library" && activeSourceWorkspace
      ? activeSourceWorkspace.evidence.filter((item) => selectedEvidenceIds.has(item.id))
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
  const currentWikiPage = currentReviewContext() === "views" ? activeWikiPage() : null;
  chatContextSummaryEl.textContent = total
    ? `${sourceCount} Source${sourceCount === 1 ? "" : "s"} · ${evidenceCount} Evidence`
    : currentWikiPage ? `Wiki Page included · ${currentWikiPage.title}` : "No context attached";
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
  visibleSources().forEach((source) => {
    const key = resultKey(source);
    if (librarySelectAllInput.checked) selectedLibrarySourceKeys.add(key);
    else selectedLibrarySourceKeys.delete(key);
  });
  renderLibrary();
  renderReviewWorkspace();
});

evidenceLibrarySelectAllInput.addEventListener("change", () => {
  if (evidenceProposalQueueOpen) return selectAllReview("evidence", evidenceLibrarySelectAllInput.checked);
  visibleEvidence().forEach((item) => {
    if (evidenceLibrarySelectAllInput.checked) selectedEvidenceIds.add(item.id);
    else selectedEvidenceIds.delete(item.id);
  });
  renderEvidenceLibrary();
  renderReviewWorkspace();
});

evidenceTagFilterInput.addEventListener("change", () => {
  if (evidenceProposalQueueOpen) return renderEvidenceProposals();
  renderEvidenceLibrary();
  const filtered = visibleEvidence();
  evidenceStatusEl.textContent = selectedEvidenceTagFilters.size || selectedEvidenceAllTagFilters.size
    ? `${filtered.length} of ${libraryEvidence.length} Evidence · Any: ${[...selectedEvidenceTagFilters].map(name => name === "__has_related__" ? "Has Claims" : name === "__no_related__" ? "No Claims" : name).join(", ") || "—"} · All: ${[...selectedEvidenceAllTagFilters].map(name => name === "__has_related__" ? "Has Claims" : name === "__no_related__" ? "No Claims" : name).join(", ") || "—"}`
    : `${libraryEvidence.length} Evidence`;
});

evidenceTagAllFilterInput.addEventListener("change", () => {
  evidenceTagFilterInput.dispatchEvent(new Event("change"));
});

evidenceBatchTagBtn.addEventListener("click", () => {
  const ids = libraryEvidence
    .filter((item) => selectedEvidenceIds.has(item.id))
    .map((item) => item.id);
  if (!ids.length) return;
  openBatchTagEditor("evidence", ids, async () => {
    await fetchEvidenceLibrary();
    renderEvidenceLibrary();
    renderReviewWorkspace();
    evidenceStatusEl.textContent = `Added Tags to ${ids.length} Evidence`;
  });
});

libraryTagFilterInput.addEventListener("change", () => { renderLibrary(); renderReviewWorkspace(); });
libraryTagAllFilterInput.addEventListener("change", () => { renderLibrary(); renderReviewWorkspace(); });
libraryBatchTagBtn.addEventListener("click", () => {
  const ids = librarySources.filter(item => selectedLibrarySourceKeys.has(resultKey(item))).map(item => item.id);
  if (ids.length) openBatchTagEditor("source", ids, async () => { await fetchLibrary(); renderReviewWorkspace(); });
});
libraryBatchDeleteBtn.addEventListener("click", () => deleteSelectedKnowledge("source",
  librarySources.filter(item => selectedLibrarySourceKeys.has(resultKey(item))).map(item => item.id)));
evidenceBatchDeleteBtn.addEventListener("click", () => deleteSelectedKnowledge("evidence", [...selectedEvidenceIds]));

claimsBatchTagBtn.addEventListener("click", () => {
  const ids = claims
    .filter((item) => selectedClaimIds.has(item.id))
    .map((item) => item.id);
  if (!ids.length) return;
  openBatchTagEditor("claim", ids, async () => {
    await fetchClaims();
    renderClaims();
    renderReviewWorkspace();
    claimsStatusEl.textContent = `Added Tags to ${ids.length} Claims`;
  });
});

claimsSelectAllInput.addEventListener("change", () => {
  if (claimProposalQueueOpen) return selectAllReview("claim", claimsSelectAllInput.checked);
  visibleClaims().forEach((claim) => {
    if (viewAddingClaims && viewDraftClaimIds.includes(claim.id)) return;
    if (claimsSelectAllInput.checked) selectedClaimIds.add(claim.id);
    else selectedClaimIds.delete(claim.id);
  });
  renderClaims();
  renderReviewWorkspace();
});

claimsTagFilterInput.addEventListener("change", () => {
  if (claimProposalQueueOpen) return renderClaimProposals();
  renderClaims();
  updateClaimsStatus();
  renderReviewWorkspace();
});

claimsTagAllFilterInput.addEventListener("change", () => {
  claimsTagFilterInput.dispatchEvent(new Event("change"));
});

claimsReviewFilterInput.addEventListener("change", () => {
  renderClaims();
  updateClaimsStatus();
});

document.addEventListener("click", (event) => {
  document.querySelectorAll(".tag-multiselect details[open]").forEach((details) => {
    if (!details.contains(event.target)) details.open = false;
  });
});

const copySelectedEvidenceToClaimDraft = (viaLLM = false) => {
  incomingLLMEvidenceIds = viaLLM ? [...selectedEvidenceIds] : null;
  if (viaLLM) { renderIncomingTrays(); return; }
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

reviewStageAdvanceBtn.addEventListener("click", async () => {
  const context = currentReviewContext();
  reviewStageStatusEl.textContent = "";
  if (context === "claims") {
    const projectId = collectArtifactSelect.value;
    if (!selectedClaimIds.size || !projectId) return;
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/claims`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_ids: [...selectedClaimIds] }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      reviewStageStatusEl.textContent = body.message || "Could not add Claims to the Project.";
      return;
    }
    await fetchArtifacts();
    reviewStageStatusEl.textContent = `Added ${body.linked} Claim${body.linked === 1 ? "" : "s"} to the active Project.`;
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
  const currentWikiPage = activeWikiPage();
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
  const nextReviewContextKey = context === "views" && currentWikiPage
    ? `views:${currentWikiPage.id}` : context;
  const contextChanged = activeReviewContextKey !== nextReviewContextKey;
  if (contextChanged) {
    chatInputDrafts[activeReviewContextKey] = contextChatInput.value;
  }
  activeReviewContextKey = nextReviewContextKey;
  reviewConversations[activeReviewContextKey] ||= [];
  chatInputHistories[activeReviewContextKey] ||= [];
  if (contextChanged) {
    contextChatInput.value = chatInputDrafts[activeReviewContextKey] || "";
    chatInputHistoryCursors[activeReviewContextKey] =
      chatInputHistories[activeReviewContextKey].length;
  }
  const selectionCount = libraryEvidenceMode
    ? evidenceSelection.length
    : context === "artifact"
    ? Number(activeArtifact?.claim_count || 0)
    : context === "claims" ? selectedClaims().length
    : context === "views"
      ? (currentWikiPage?.claim_ids?.length || incomingViewClaimIds.size) : selected.length;
  contextModeLabelEl.textContent = context === "library"
    ? `Sources · ${librarySources.length} Source${librarySources.length === 1 ? "" : "s"}`
    : context === "evidence"
      ? `Evidence · ${libraryEvidence.length} total`
    : context === "claims"
      ? `Claims · ${claims.length} total`
    : context === "views"
      ? currentWikiPage
        ? `Wiki · ${currentWikiPage.title}`
        : "Global Wiki"
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
      ? currentWikiPage ? "Current Page" : "Global Wiki"
    : context === "plans"
      ? "Saved Plans"
      : context === "config"
        ? "Scope"
        : "Selection";
  contextSelectedCountEl.textContent = context === "evidence"
    ? `${evidenceSelection.length} selected`
    : context === "artifact"
    ? `${selectionCount} Claims`
    : context === "claims"
      ? `${selectedClaims().length} selected`
    : context === "views"
      ? currentWikiPage
        ? `${currentWikiPage.claim_ids?.length || 0} Claims`
        : `${wikiState.claims.filter((claim) => claim.lifecycle === "active").length} Claims`
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
    const activeProject = artifacts.find((item) => item.id === collectArtifactSelect.value);
    reviewStageAdvanceBtn.disabled = selectedClaims().length === 0 || !activeProject;
    reviewStageAdvanceBtn.textContent = selectedClaims().length
      ? `Add ${selectedClaims().length} Claim${selectedClaims().length === 1 ? "" : "s"} to Project`
      : "Add to Project";
    reviewStageAdvanceBtn.title = activeProject
      ? `Add to ${activeProject.title}` : "Choose a Project from the target menu";
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
      ? currentWikiPage
        ? "Discuss this Wiki Page and its Claims…"
        : "Discuss the global Wiki structure…"
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
    if (currentWikiPage) {
      appendContextItem(currentWikiPage.title);
      const detail = document.createElement("p");
      detail.textContent = [
        "Global Wiki",
        `${currentWikiPage.claim_ids?.length || 0} Claims`,
        `${wikiState.unorganized_claim_ids?.length || 0} unorganized`,
      ].join(" · ");
      contextSelectionListEl.appendChild(detail);
    } else {
      const draft = document.createElement("p");
      draft.textContent = "Every reviewed active Claim belongs to the global Wiki; organization only changes its structure.";
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
    ? `Add ${selected.length} Source${selected.length === 1 ? "" : "s"} to Library`
    : "Add selected Sources";
  renderKnowledgeReview();
  renderChatContext();
  if (contextChanged && copilotAvailable) renderReviewConversation();
};

const createRelevanceCard = (paper, selectionKeys, onSelection) => {
    const card = document.createElement("article");
    card.className = "result-card";
    const key = resultKey(paper);
    const isSelected = selectionKeys.has(key);
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
        selectionKeys.add(key);
      } else {
        selectionKeys.delete(key);
      }
      card.classList.toggle("is-selected", checkbox.checked);
      onSelection();
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
    const citations = Number.isInteger(paper.citation_count) && paper.citation_count >= 0
      ? paper.citation_count.toLocaleString() : "Unknown";
    meta.textContent = `${paper.authors || "Unknown"} · ${paper.year || "Undated"}${sourceLabel} · Citations: ${citations}`;
    if (paper.import_status) {
      const importState = document.createElement("span");
      importState.className = `import-state is-${paper.import_status}`;
      importState.textContent = paper.import_status[0].toUpperCase() + paper.import_status.slice(1);
      meta.append(" · ", importState);
    }

    const abstract = document.createElement("p");
    abstract.className = "result-abstract";
    abstract.textContent = paper.abstract;

    const intelligence = document.createElement("div");
    intelligence.className = "result-intelligence";
    if (paper.relevance_tier) {
      const tier = document.createElement("span");
      tier.className = `relevance-tier is-${paper.relevance_tier}`;
      tier.textContent = ({
        strong: "Strong match", possible: "Possible match", excluded: "Excluded",
      })[paper.relevance_tier] || "Possible match";
      intelligence.appendChild(tier);
    }
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
      reason.textContent = `Assessment${score}: ${paper.match_reason}`;
      intelligence.appendChild(reason);
    }
    if (paper.verification_basis) {
      const basis = document.createElement("small");
      basis.className = "verification-basis";
      basis.textContent = `Basis: ${paper.verification_basis}`;
      intelligence.appendChild(basis);
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
    return card;
};

const sortSearchResults = (results, order) => {
  const number = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : -1;
  return results.map((paper, index) => ({ paper, index })).sort((a, b) => {
    let difference = 0;
    if (order === "recent") {
      difference = number(b.paper.year || null) - number(a.paper.year || null);
    } else if (order === "citations") {
      difference = number(b.paper.citation_count) - number(a.paper.citation_count);
    } else {
      const tiers = { strong: 2, possible: 1, excluded: 0 };
      difference = (tiers[b.paper.relevance_tier] ?? -1) - (tiers[a.paper.relevance_tier] ?? -1)
        || number(b.paper.verification_score) - number(a.paper.verification_score)
        || number(b.paper.semantic_score) - number(a.paper.semantic_score);
    }
    return difference || a.index - b.index;
  }).map(({ paper }) => paper);
};

const resultsSortSelect = document.querySelector("#results-sort");
resultsSortSelect.addEventListener("change", () => {
  pageSelectTop.value = "1";
  renderResults();
});

const renderResults = () => {
  resultsEl.innerHTML = "";
  updateSelectAllState(resultsSelectAllInput, selectedPrimaryResultCount(), fullResults.length);
  const totalPages = Math.max(1, Math.ceil(fullResults.length / pageSize));
  const currentPage = Math.min(
    totalPages,
    Math.max(1, Number(pageSelectTop.value || "1")),
  );
  const start = (currentPage - 1) * pageSize;
  const visible = sortSearchResults(fullResults, resultsSortSelect.value).slice(start, start + pageSize);

  if (!fullResults.length && !excludedSearchResults.length) {
    const empty = document.createElement("div");
    empty.className = "result-empty";
    empty.textContent = "No papers surfaced. Try widening the signal.";
    resultsEl.appendChild(empty);
    renderPaginationControls();
    return;
  }

  visible.forEach((paper) => resultsEl.appendChild(createRelevanceCard(
    paper, selectedResultKeys, () => {
      updateSelectAllState(resultsSelectAllInput, selectedPrimaryResultCount(), fullResults.length);
      renderReviewWorkspace();
    },
  )));
  if (excludedSearchResults.length) {
    const excluded = document.createElement("details");
    excluded.className = "excluded-results";
    const summary = document.createElement("summary");
    summary.textContent = `Excluded by LLM verification · ${excludedSearchResults.length}`;
    const list = document.createElement("div");
    list.className = "excluded-results-list";
    sortSearchResults(excludedSearchResults, resultsSortSelect.value).forEach((paper) => list.appendChild(createRelevanceCard(
      paper, selectedResultKeys, renderReviewWorkspace,
    )));
    excluded.append(summary, list);
    resultsEl.appendChild(excluded);
  }
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

const renderProviderConfig = () => {
  aiCustomRecipeSection.hidden = aiProviderInput.value !== "custom";
};

aiProviderInput.addEventListener("change", () => {
  const defaults = {
    openai: "https://api.openai.com/v1",
    google: "https://generativelanguage.googleapis.com/v1beta",
    anthropic: "https://api.anthropic.com/v1",
  };
  if (!aiBaseUrlInput.value.trim() && defaults[aiProviderInput.value]) {
    aiBaseUrlInput.value = defaults[aiProviderInput.value];
  }
  renderProviderConfig();
  updateProfileDirtyState();
});

const fetchConfig = async () => {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    const libraryBadge = document.querySelector("#library-badge");
    const libraryName = data.library_name || "default";
    libraryBadge.hidden = false;
    libraryBadge.textContent = libraryName;
    libraryBadge.title = `Library: ${libraryName}. API requests are real.`;
    document.title = `Knowte · ${libraryName}`;
    aiModelProfiles = (data.ai_model_profiles || []).map((profile) => ({
      ...profile, api_key: "", remove_api_key: false,
      custom_recipe_text: JSON.stringify(profile.custom_recipe || {}, null, 2),
    }));
    aiRoleAssignments = { ...(data.ai_role_assignments || {}) };
    renderAIProfiles();
    aiProviderInput.value = data.ai_provider || "openai_compatible";
    aiCustomRecipeInput.value = JSON.stringify(data.ai_custom_recipe || {}, null, 2);
    renderProviderConfig();
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
    aiSearchTimeoutInput.value = String(
      data.ai_search_timeout_seconds || data.ai_timeout_seconds || 45,
    );
    evidenceRequestModeInput.value = data.ai_evidence_request_mode || "combined";
    savedEvidenceRequestMode = evidenceRequestModeInput.value;
    evidenceSourceLimit = Number(data.ai_evidence_source_limit || 6);
    ai_evidence_source_limitInput.value = String(evidenceSourceLimit);
    claimEvidenceLimit = Number(data.ai_claim_evidence_limit || 30);
    aiWikiClaimLimitInput.value = String(data.ai_wiki_claim_limit || 100);
    wikiClaimLimit = Number(data.ai_wiki_claim_limit || 100);
    ai_claim_evidence_limitInput.value = String(claimEvidenceLimit);
    aiClaimComparisonLimitInput.value = String(data.ai_claim_comparison_limit || 100);
    CHAT_CONTEXT_LIMIT = Number(data.ai_copilot_context_limit || 12);
    ai_copilot_context_limitInput.value = String(CHAT_CONTEXT_LIMIT);
    updateEvidenceReadScope();
    aiStageTimeoutInput.value = String(
      data.ai_stage_timeout_seconds || data.ai_timeout_seconds || 45,
    );
    aiCopilotInstructionsInput.value = data.ai_copilot_instructions || "";
    aiCopilotTemperatureInput.value = String(data.ai_copilot_temperature ?? 0.2);
    aiCopilotMaxTokensInput.value = String(data.ai_copilot_max_tokens || 1200);
    renderCopilotAdvancedParameters(data.ai_copilot_advanced_parameters ?? { top_p: 0.9 });
    renderCopilotPromptPreview();
    semanticscholarKeyRemovalPending = false;
    aiApiKeyRemovalPending = false;
    aiEmbeddingApiKeyRemovalPending = false;
    renderSecretControls();
    s2KeyInput.disabled = false;
    if (searxngInput) {
      searxngInput.value = data.searxng_url || DEFAULT_SEARXNG_URL;
    }
    if (searxngProxyInput) searxngProxyInput.value = data.searxng_proxy || "";
    if (webIgnoreYearFilterInput) {
      webIgnoreYearFilterInput.checked = Boolean(data.web_ignore_year_filter);
    }
    configuredMaxPapers = parseMaxPapers(data.max_papers);
    configuredIntelligentMaxResults = Number(data.intelligent_max_results || 20);
    defaultSearchMode = ["intelligent", "import"].includes(data.default_search_mode)
      ? data.default_search_mode : "keyword";
    searchAIReview = data.search_ai_review ?? (defaultSearchMode === "intelligent");
    renderDefaultSearchMode();
    setSearchMode(defaultSearchMode === "import" ? "import" : "search");
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
    const configPayload = {
      email,
      ...(semanticscholar_api_key || clear_semanticscholar_api_key
        ? { semanticscholar_api_key }
        : {}),
      enabled_backends,
      max_papers,
      intelligent_max_results,
      ai_model_profiles: serializedAIProfiles(),
      ai_role_assignments: aiRoleAssignments,
      ai_verify_batch_size: Number(aiVerifyBatchSizeInput.value || 5),
      ai_verify_concurrency: Number(aiVerifyConcurrencyInput.value || 1),
      ai_search_timeout_seconds: Number(aiSearchTimeoutInput.value || 45),
      ai_evidence_source_limit: Number(ai_evidence_source_limitInput.value || 6),
      ai_claim_evidence_limit: Number(ai_claim_evidence_limitInput.value || 30),
      ai_claim_comparison_limit: Number(aiClaimComparisonLimitInput.value || 100),
      ai_wiki_claim_limit: Number(aiWikiClaimLimitInput.value || 100),
      ai_copilot_context_limit: Number(ai_copilot_context_limitInput.value || 12),
      ai_stage_timeout_seconds: Number(aiStageTimeoutInput.value || 45),
      ai_evidence_request_mode: evidenceRequestModeInput.value,
      ai_copilot_instructions: aiCopilotInstructionsInput.value.trim(),
      ai_copilot_temperature: Number(aiCopilotTemperatureInput.value || 0),
      ai_copilot_max_tokens: Number(aiCopilotMaxTokensInput.value || 1200),
      ai_copilot_advanced_parameters: copilotAdvancedParameters(),
    };
    const submitConfig = (body) => fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let response = await submitConfig(configPayload);
    let data = await response.json().catch(() => ({}));
    if (
      response.status === 409
      && data.error === "obsolete_config_confirmation_required"
    ) {
      const labels = (data.obsolete_config_items || [])
        .map((item) => `• ${item.label || item.key}`)
        .join("\n");
      const confirmed = await confirmAction(
        "This Config contains settings from older Knowte versions:\n\n"
          + `${labels}\n\nRemove them and save? `
          + "Cancel if you want to export the current Config first.",
      );
      if (!confirmed) {
        setConfigStatus("Config was not saved. Older settings were kept.");
        return false;
      }
      response = await submitConfig({
        ...configPayload,
        confirm_remove_obsolete_config: true,
      });
      data = await response.json().catch(() => ({}));
    }
    if (!response.ok) {
      if (data.error === "no_search_backends") {
        throw new Error("no_search_backends");
      }
      throw new Error("save_failed");
    }
    aiModelProfiles = (data.ai_model_profiles || []).map((profile) => ({
      ...profile, api_key: "", remove_api_key: false,
      custom_recipe_text: JSON.stringify(profile.custom_recipe || {}, null, 2),
    }));
    aiRoleAssignments = { ...(data.ai_role_assignments || {}) };
    renderAIProfiles();
    aiProviderInput.value = data.ai_provider || "openai_compatible";
    aiCustomRecipeInput.value = JSON.stringify(data.ai_custom_recipe || {}, null, 2);
    renderProviderConfig();
    setConfigStatus("Config saved.", 1000);
    renderAIRoles(true);
    projectClaimScopes.forEach((state) => {
      state.recommendationModel = aiRoleAssignments.article || "";
      state.wikiModel = aiRoleAssignments.wiki || "";
    });
    renderArtifacts();
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
    aiSearchTimeoutInput.value = String(
      data.ai_search_timeout_seconds || data.ai_timeout_seconds || 45,
    );
    evidenceRequestModeInput.value = data.ai_evidence_request_mode || "combined";
    savedEvidenceRequestMode = evidenceRequestModeInput.value;
    evidenceSourceLimit = Number(data.ai_evidence_source_limit || 6);
    ai_evidence_source_limitInput.value = String(evidenceSourceLimit);
    claimEvidenceLimit = Number(data.ai_claim_evidence_limit || 30);
    ai_claim_evidence_limitInput.value = String(claimEvidenceLimit);
    aiClaimComparisonLimitInput.value = String(data.ai_claim_comparison_limit || 100);
    CHAT_CONTEXT_LIMIT = Number(data.ai_copilot_context_limit || 12);
    ai_copilot_context_limitInput.value = String(CHAT_CONTEXT_LIMIT);
    updateEvidenceReadScope();
    aiStageTimeoutInput.value = String(
      data.ai_stage_timeout_seconds || data.ai_timeout_seconds || 45,
    );
    aiCopilotInstructionsInput.value = data.ai_copilot_instructions || "";
    aiCopilotTemperatureInput.value = String(data.ai_copilot_temperature ?? 0.2);
    aiCopilotMaxTokensInput.value = String(data.ai_copilot_max_tokens || 1200);
    renderCopilotAdvancedParameters(data.ai_copilot_advanced_parameters ?? { top_p: 0.9 });
    renderCopilotPromptPreview();
    renderSecretControls();
    aiWikiClaimLimitInput.value = String(data.ai_wiki_claim_limit || 100);
    wikiClaimLimit = Number(data.ai_wiki_claim_limit || 100);
    if (searxngInput) {
      searxngInput.value = data.searxng_url || DEFAULT_SEARXNG_URL;
    }
    if (searxngProxyInput) searxngProxyInput.value = data.searxng_proxy || "";
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
exportConfigBtn.addEventListener("click", async () => {
  exportConfigBtn.disabled = true;
  try {
    const response = await fetch("/api/config/export", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ redact_secrets: exportConfigRedactInput.checked }),
    });
    if (!response.ok) throw new Error("Could not export config.");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = "knowte-config.yml";
    document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    setConfigStatus(exportConfigRedactInput.checked
      ? "Config exported with secrets hidden." : "Config exported with stored secrets.", 1800);
  } catch (error) {
    setConfigStatus(error.message);
  } finally {
    exportConfigBtn.disabled = false;
  }
});

searxngSetupBtn.addEventListener("click", async () => {
  const willSaveConfig = isConfigDirty();
  const confirmed = await confirmAction(
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
  const confirmed = await confirmAction(
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
  const confirmed = await confirmAction(
    "Remove the Knowte-managed SearXNG container and its generated configuration?"
      + (removeImage
        ? " The exact cached image will also be removed if Docker confirms that no other container uses it."
        : " The image will remain cached for faster setup."),
  );
  if (confirmed) await runSearxngAction("remove", { remove_image: removeImage });
});

const mergeSearchQueryResults = (pages, query, limit) => {
  const unique = new Map();
  const length = Math.max(0, ...pages.map((page) => (page.results || []).length));
  for (let index = 0; index < length; index += 1) {
    pages.forEach((page) => {
      const item = page.results?.[index];
      if (!item) return;
      const key = String(item.doi_url || item.paper_url || item.url || item.id || item.title).replace(/\/$/, "").toLowerCase();
      if (!unique.has(key)) unique.set(key, item);
    });
  }
  const results = [...unique.values()].slice(0, limit);
  return {
    ...pages[0], query, results, count: results.length,
    usage: pages.at(-1)?.usage,
    warnings: [...new Set(pages.flatMap((page) => page.warnings || []))],
    source_counts: results.reduce((counts, item) => { const key = item.source || "Unknown"; counts[key] = (counts[key] || 0) + 1; return counts; }, {}),
    can_find_more: limit < 1000 && (unique.size > limit || pages.some((page) => page.can_find_more)),
  };
};

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
  statusEl.scrollIntoView({ behavior: "smooth", block: "center" });

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
    const pages = [];
    let response;
    const queries = lastSearchQueries.length ? lastSearchQueries : [lastQuery];
    for (const [index, query] of queries.entries()) {
      params.set("q", query);
      statusEl.textContent = `Searching query ${index + 1}/${queries.length}: ${query} · AI Review off`;
      response = await fetch(`/api/search?${params}`, { signal: controller.signal });
      if (searchController !== controller) return;
      if (!response.ok) break;
      pages.push(await response.json());
    }
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
    const data = pages.length === 1 ? pages[0] : mergeSearchQueryResults(pages, lastQuery, activeLimit);
    fullResults = data.results || [];
    excludedSearchResults = [];
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
    const sourceHint = (sourceSummary ? ` Sources: ${sourceSummary}.` : "")
      + (queries.length > 1 ? ` Searched ${queries.length} active queries; duplicates removed.` : "");
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
  const available = new Set(["arxiv", "openalex", "semanticscholar"]);
  const selected = (planSourceOverride || configuredBackends()).filter((source) => available.has(source));
  return selected.length ? selected : configuredBackends();
};

const beginSearch = async (query, areas, yearFrom, yearTo, backends = activeBackends()) => {
  if (!query) {
    statusEl.textContent = "Enter a signal to wake the archive.";
    return;
  }

  const wantsWeb = false;
  const academicBackends = new Set(["arxiv", "openalex", "semanticscholar"]);
  lastQuery = query;
  lastAreas = areas;
  lastYearFrom = yearFrom;
  lastYearTo = yearTo;
  lastBackends = [...backends];
  lastSearchQueries = [...new Set(searchStrategyActions.slice(0, SEARCH_STRATEGY_TOP_LIMIT)
    .map((action) => action.query.trim()).filter(Boolean))];
  if (!lastSearchQueries.length) lastSearchQueries = [query];
  activeLimit = configuredMaxPapers;
  activeWebPages = 1;
  lastSearchHasWeb = wantsWeb;
  lastSearchHasAcademic = backends.some((backend) => academicBackends.has(backend));
  canFindMoreWeb = false;
  fullResults = [];
  excludedSearchResults = [];
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
  const webEnabled = false;
  if (!academicEnabled) {
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
  excludedSearchResults = [];
  selectedResultKeys.clear();
  canFindMore = false;
  canFindMoreWeb = false;
  pageSelectTop.value = "1";
  resultsEl.innerHTML = "";
  intelligentProgressEl.hidden = false;
  intelligentProgressEl.scrollIntoView({ behavior: "smooth", block: "start" });
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
    statusEl.textContent = `Searching with AI Review for “${query}”…\n${elapsedSeconds}s elapsed.`;
  };
  renderElapsed();
  elapsedTimer = window.setInterval(renderElapsed, 1000);
  const controller = new AbortController();
  searchController = controller;
  const runId = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  let lastProgressStage = "";
  const renderProgressStage = (stage) => {
    if (!stage || stage === lastProgressStage) return;
    lastProgressStage = stage;
    const academicOrder = ["recall", "embed", "verify"];
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
      model_profile_id: searchModelSelect?.value || "",
    });
    if (searchStrategyActions.length) {
      params.set("strategy", JSON.stringify(searchStrategyActions.slice(0, SEARCH_STRATEGY_TOP_LIMIT).map(
        ({ query: actionQuery, target }) => ({ query: actionQuery.trim(), target }),
      ).filter((item) => item.query)));
    }
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
      throw new Error(data.message || "Search with AI Review could not complete.");
    }
    const stages = data.stages || {};
    if (academicEnabled) {
      ["recall", "embed", "verify"].forEach((stageName) => {
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
    intelligentExpandedEl.hidden = true;
    intelligentExpandedEl.replaceChildren();
    fullResults = data.results || [];
    excludedSearchResults = data.excluded_results || [];
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
      : `Found ${fullResults.length} relevant result(s) from ${counts.academic || 0} academic candidate(s); ${excludedSearchResults.length} excluded.${sourceHint}${degraded}`;
  } catch (error) {
    if (token !== intelligentRunToken) return;
    if (error.name === "AbortError") {
      statusEl.textContent = "Search with AI Review stopped.";
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

searchStrategyAddBtn.addEventListener("click", () => {
  if (searchStrategyActions.length + searchStrategyWaitingActions.length >= SEARCH_STRATEGY_CANDIDATE_LIMIT) return;
  if (!searchStrategyActions.length && !searchStrategyWaitingActions.length) {
    searchStrategyIntent = normalizedSearchIntent();
    searchStrategyStaleAcknowledged = false;
  }
  const collection = searchStrategyActions.length < SEARCH_STRATEGY_TOP_LIMIT
    ? searchStrategyActions : searchStrategyWaitingActions;
  collection.push({ query: "", target: "academic", purpose: "" });
  searchStrategyEl.hidden = false;
  renderSearchStrategy();
});

discussSearchBtn.addEventListener("click", async () => {
  const intent = input.value.trim();
  if (!intent) {
    statusEl.textContent = "Enter a search intent before discussing it.";
    input.focus();
    return;
  }
  contextPanel.classList.add("is-open", "is-search-strategy-focus");
  contextPanelToggleBtn.setAttribute("aria-expanded", "true");
  window.setTimeout(() => contextPanel.classList.remove("is-search-strategy-focus"), 1300);
  contextModeLabelEl.textContent = "Search strategy";
  contextChatInput.placeholder = "Discuss this search strategy…";
  contextChatInput.focus({ preventScroll: true });
  contextPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  discussSearchBtn.disabled = true;
  discussSearchBtn.textContent = "Discussing…";
  searchStrategyStatusEl.textContent = "Copilot is proposing academic queries…";
  try {
    const { yearFrom, yearTo } = normalizeSearchYears();
    const response = await fetch("/api/search/strategy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        intent,
        model_profile_id: searchModelSelect?.value || "",
        backends: activeBackends(),
        areas: [...getEffectiveAreas()],
        year_from: yearFrom,
        year_to: yearTo,
      }),
    });
    const data = await response.json().catch(() => ({}));
    updateUsage(data.usage);
    if (!response.ok) throw new Error(data.message || "Copilot could not propose a strategy.");
    searchStrategyActions = (data.actions || []).slice(0, SEARCH_STRATEGY_TOP_LIMIT);
    searchStrategyWaitingActions = [];
    searchStrategyIntent = normalizedSearchIntent();
    searchStrategyStaleAcknowledged = false;
    searchStrategyEl.hidden = false;
    renderSearchStrategy();
    const strategyMessage = `I proposed ${searchStrategyActions.length} academic quer${searchStrategyActions.length === 1 ? "y" : "ies"}. You can edit them directly or continue discussing the strategy here.`;
    appendReviewMessage(strategyMessage, "assistant");
    reviewConversations.search.push({ role: "assistant", content: strategyMessage });
  } catch (error) {
    searchStrategyStatusEl.textContent = error.message;
    appendReviewMessage(error.message, "error");
  } finally {
    discussSearchBtn.disabled = false;
    discussSearchBtn.textContent = "Discuss";
  }
});

copyImportPromptBtn.addEventListener("click", async () => {
  updateImportPrompt();
  try {
    await navigator.clipboard.writeText(importPromptPreviewEl.textContent);
    copyImportPromptBtn.textContent = "✓ Copied";
    window.setTimeout(() => { copyImportPromptBtn.textContent = "Copy suggested prompt"; }, 1000);
  } catch (_error) {
    importStatusEl.textContent = "Could not access the clipboard. Expand Preview prompt and copy it manually.";
  }
});

parseImportBtn.addEventListener("click", async () => {
  const content = importContentInput.value.trim();
  if (!content) {
    importStatusEl.textContent = "Paste at least one URL, DOI, arXiv ID, or structured result.";
    return;
  }
  parseImportBtn.disabled = true;
  importStatusEl.textContent = "Parsing and checking candidates…";
  try {
    const response = await fetch("/api/search/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Could not parse imported results.");
    fullResults = data.results || [];
    selectedResultKeys.clear();
    pageSelectTop.value = "1";
    renderResults();
    renderReviewWorkspace();
    importStatusEl.textContent = fullResults.length
      ? `Parsed ${fullResults.length} candidate${fullResults.length === 1 ? "" : "s"}. Review and select them below.`
      : "No resolvable candidates were found. Check the format or identifiers.";
    statusEl.textContent = `Imported ${fullResults.length} candidate Source${fullResults.length === 1 ? "" : "s"}.`;
  } catch (error) {
    importStatusEl.textContent = error.message;
  } finally {
    parseImportBtn.disabled = false;
  }
});

input.addEventListener("input", () => {
  if (searchMode === "import") updateImportPrompt();
  if (searchStrategyActions.length || searchStrategyWaitingActions.length) {
    searchStrategyStaleAcknowledged = false;
    updateSearchStrategyIntentState();
  }
});

searchStrategyUseAnywayBtn.addEventListener("click", () => {
  searchStrategyStaleAcknowledged = true;
  searchStrategyStaleEl.hidden = true;
  searchStrategyStatusEl.dataset.state = "";
  searchStrategyStatusEl.textContent = "Using the current strategy with the revised intent. Search runs active candidates only.";
});

searchStrategyDiscussAgainBtn.addEventListener("click", () => {
  discussSearchBtn.click();
});

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
  if (searchMode === "import") return;
  if (isSearchStrategyStale() && !searchStrategyStaleAcknowledged) {
      searchStrategyStaleEl.hidden = false;
      searchStrategyStatusEl.dataset.state = "error";
      searchStrategyStatusEl.textContent = "Review the outdated strategy before searching.";
      searchStrategyEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
  }
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
    const requestedMode = button.dataset.defaultSearchMode === "search"
      ? (searchAIReview ? "intelligent" : "keyword") : "import";
    if (!requestedMode || requestedMode === defaultSearchMode) return;
    defaultSearchModeButtons.forEach((item) => {
      item.disabled = true;
    });
    try {
      const response = await fetch("/api/config/default-search-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: requestedMode, ai_review: searchAIReview }),
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

searchAIReviewInput.addEventListener("change", async () => {
  const previous = searchAIReview;
  searchAIReview = searchAIReviewInput.checked;
  setSearchMode("search");
  searchAIReviewInput.disabled = true;
  try {
    const response = await fetch("/api/config/default-search-mode", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: defaultSearchMode, ai_review: searchAIReview }),
    });
    if (!response.ok) throw new Error("Could not save AI Review preference.");
    const data = await response.json(); defaultSearchMode = data.default_search_mode;
    renderDefaultSearchMode();
  } catch (error) {
    searchAIReview = previous; setSearchMode("search"); statusEl.textContent = error.message;
  } finally { searchAIReviewInput.disabled = false; }
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
    statusEl.textContent = "Search with AI Review stopped.";
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
  noArtifactOption.textContent = "Choose a Project";
  collectArtifactSelect.appendChild(noArtifactOption);
  artifacts.forEach((artifact) => {
    const option = document.createElement("option");
    option.value = artifact.id;
    option.textContent = artifact.title;
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

const openBatchTagEditor = async (entityType, entityIds, afterSave) => {
  activeTagEditor = {
    entityType, entityIds: [...entityIds], names: [], additive: true, afterSave,
  };
  const entityLabel = entityType === "evidence" ? "Evidence"
    : entityType === "claim" ? "Claims" : entityType === "source" ? "Sources" : "items";
  tagEditorTypeEl.textContent = `${entityIds.length} selected ${entityLabel} · add Tags`;
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
  tagEditorSaveBtn.disabled = Boolean(activeTagEditor.additive)
    && activeTagEditor.names.length === 0;
};

const saveTagEditor = async () => {
  if (!activeTagEditor) return;
  tagEditorSaveBtn.disabled = true;
  try {
    const response = await fetch(
      activeTagEditor.additive ? "/api/tags/batch" : "/api/tags/entity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(activeTagEditor.additive ? {
        entity_type: activeTagEditor.entityType,
        entity_ids: activeTagEditor.entityIds,
        tags: activeTagEditor.names,
      } : {
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
  } catch (error) {
    await appDialog(error.message || "Could not save Tags.", {title: "Tags not saved", confirmLabel: "Close"});
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

const projectScopeState = (projectId) => {
  if (!projectClaimScopes.has(projectId)) {
    projectClaimScopes.set(projectId, {
      query: "", anyTags: new Set(), allTags: new Set(), selected: new Set(),
      busy: false, activeAction: "", recommendationModel: "", wikiModel: "",
    });
  }
  return projectClaimScopes.get(projectId);
};

const fetchProjectRecommendations = async (projectId) => {
  const response = await fetch(
    `/api/project-claim-recommendations?project_id=${encodeURIComponent(projectId)}`,
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || "Could not load recommendations.");
  projectClaimRecommendations.set(projectId, data.proposals || []);
};

const projectTagMenu = (label, selected, other, rerender) => {
  const control = document.createElement("div");
  control.className = "tag-filter-control tag-multiselect";
  control.innerHTML = `<span>${label}</span><details><summary><span>0 selected</span></summary><div class="tag-multiselect-menu"></div></details>`;
  syncTagFilterOptions(control, claims, selected, other);
  control.addEventListener("change", rerender);
  return control;
};

const appDialog = (message, { value, title = "Confirm", confirmLabel = "Continue", destructive = false, highlights = [] } = {}) => new Promise((resolve) => {
  const dialog = document.createElement("dialog"); dialog.className = "app-dialog";
  dialog.setAttribute("aria-label", title);
  const heading = document.createElement("h2"); heading.textContent = title;
  const description = document.createElement("p"); description.textContent = message;
  if (highlights.length) {
    description.replaceChildren();
    let remaining = message;
    for (const text of highlights) {
      const index = remaining.indexOf(text);
      if (index < 0) continue;
      description.appendChild(document.createTextNode(remaining.slice(0, index)));
      const mark = document.createElement("strong"); mark.className = "deletion-impact"; mark.textContent = text;
      description.appendChild(mark); remaining = remaining.slice(index + text.length);
    }
    description.appendChild(document.createTextNode(remaining));
  }
  dialog.append(heading, description);
  let input;
  if (value !== undefined) {
    input = document.createElement("textarea"); input.value = value; input.rows = 3;
    input.setAttribute("aria-label", message); dialog.appendChild(input);
  }
  const actions = document.createElement("div"); actions.className = "app-dialog-actions";
  const cancel = document.createElement("button"); cancel.type = "button"; cancel.className = "secondary-action"; cancel.textContent = "Cancel";
  const accept = document.createElement("button"); accept.type = "button";
  accept.className = `semantic-action ${destructive ? "is-destructive" : "is-accept"}`; accept.textContent = confirmLabel;
  let result = value === undefined ? false : null;
  cancel.addEventListener("click", () => dialog.close());
  accept.addEventListener("click", () => { result = input ? input.value : true; dialog.close(); });
  dialog.addEventListener("close", () => { dialog.remove(); resolve(result); }, {once:true});
  actions.append(cancel, accept); dialog.appendChild(actions); document.body.appendChild(dialog);
  dialog.showModal(); (input || cancel).focus();
});
const confirmAction = (message, options = {}) => appDialog(message, {destructive: /^(Delete|Discard|Withdraw|Cancel this)/.test(message), ...options});
const promptText = (message, value = "") => appDialog(message, {value, title: "Edit", confirmLabel: "Save"});

const renderWikiSummary = (container, text, pages, navigate) => {
  container.replaceChildren();
  const pattern = /\[\[claim:([^|\]\s]+)\|([^\]\n]+)\]\]/g;
  let offset = 0;
  for (const match of String(text || "").matchAll(pattern)) {
    container.appendChild(document.createTextNode(text.slice(offset, match.index)));
    const home = pages.find((page) => (page.claim_ids || []).includes(match[1]));
    if (home) {
      const link = document.createElement("button"); link.type = "button";
      link.className = "wiki-cross-reference"; link.textContent = match[2];
      link.title = `Open in ${home.title}`;
      link.addEventListener("click", () => navigate(home, match[1]));
      container.appendChild(link);
    } else container.appendChild(document.createTextNode(match[2]));
    offset = match.index + match[0].length;
  }
  container.appendChild(document.createTextNode(String(text || "").slice(offset)));
};

const focusWikiClaim = (container, claimId) => {
  const target = [...container.querySelectorAll("[data-wiki-claim-id]")]
    .find((node) => node.dataset.wikiClaimId === claimId);
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.focus({ preventScroll: true });
  }
};

const renderProjectWikiPages = (container, pages, claims, gaps = []) => {
  pages.forEach((page) => {
    const section = document.createElement("section");
    let depth = 0; let parent = page.parent_key; const seen = new Set();
    while (parent && depth < 6 && !seen.has(parent)) {
      seen.add(parent); depth += 1;
      parent = pages.find((candidate) => candidate.key === parent)?.parent_key || "";
    }
    section.style.setProperty("--project-wiki-depth", depth);
    const title = document.createElement("h4"); title.textContent = page.title;
    const summary = document.createElement("p");
    renderWikiSummary(summary, page.summary || "", pages, (_, id) => focusWikiClaim(container, id));
    const pageClaims = document.createElement("div");
    (page.claim_ids || []).forEach((claimId) => {
      const claim = claims.find((item) => item.id === claimId);
      if (!claim) return;
      const row = document.createElement("button"); row.type = "button"; row.textContent = claim.statement;
      row.dataset.wikiClaimId = claim.id;
      row.addEventListener("click", () => { selectedClaimIds.clear(); selectedClaimIds.add(claim.id); showPanel("claims-panel"); });
      pageClaims.appendChild(row);
    });
    section.append(title); if (page.summary) section.append(summary); section.append(pageClaims);
    container.appendChild(section);
  });
  if (gaps.length) {
    const section = document.createElement("section");
    const title = document.createElement("h4"); title.textContent = "Knowledge gaps";
    const list = document.createElement("ul");
    gaps.forEach((gap) => { const item = document.createElement("li"); item.textContent = gap; list.appendChild(item); });
    section.append(title, list); container.appendChild(section);
  }
};

const renderProjectClaimScope = (card, artifact, detail) => {
  const state = projectScopeState(artifact.id);
  const linkedIds = new Set((detail.claims || []).map((claim) => claim.id));
  const available = claims.filter((claim) => (
    claim.lifecycle === "active" && !linkedIds.has(claim.id)
  ));
  const normalizedQuery = state.query.trim().toLocaleLowerCase();
  const filtered = available.filter((claim) => {
    if (normalizedQuery && !`${claim.statement} ${(claim.tags || []).map((tag) => tag.name).join(" ")}`.toLocaleLowerCase().includes(normalizedQuery)) return false;
    return matchesTagFilter(claim, state.anyTags, state.allTags);
  });
  [...state.selected].forEach((id) => {
    if (!filtered.some((claim) => claim.id === id)) state.selected.delete(id);
  });

  const scope = document.createElement("section");
  scope.className = "project-claim-scope";
  const heading = document.createElement("div");
  heading.className = "project-scope-head";
  heading.innerHTML = `<div><strong>Claim scope</strong><small>Filter the global Wiki, then select manually or ask AI to recommend from the same pool.</small></div>`;
  const query = document.createElement("input");
  query.type = "search";
  query.placeholder = "Filter Claim text…";
  query.value = state.query;
  query.addEventListener("input", () => {
    state.query = query.value;
    renderArtifacts();
    requestAnimationFrame(() => card.querySelector(".project-claim-scope input[type=search]")?.focus());
  });
  const filters = document.createElement("div");
  filters.className = "project-scope-filters";
  const rerender = () => renderArtifacts();
  filters.append(
    query,
    projectTagMenu("Any of", state.anyTags, state.allTags, rerender),
    projectTagMenu("All of", state.allTags, state.anyTags, rerender),
  );
  const scopeStats = document.createElement("small");
  scopeStats.className = "project-scope-stats";
  scopeStats.textContent = `${filtered.length} candidate${filtered.length === 1 ? "" : "s"} · ${state.selected.size} selected`;
  const tools = document.createElement("div");
  tools.className = "project-scope-tools";
  const add = document.createElement("button");
  add.type = "button"; add.className = "semantic-action is-accept";
  add.textContent = "Add Claims Manually";
  add.disabled = state.busy || state.selected.size === 0;
  add.addEventListener("click", async () => {
    state.busy = true; renderArtifacts();
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(artifact.id)}/claims`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_ids: [...state.selected] }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || "Could not add Claims.");
      state.selected.clear();
      const refreshed = await fetch(`/api/projects/${encodeURIComponent(artifact.id)}`).then((item) => item.json());
      projectDetails.set(artifact.id, refreshed);
      await fetchArtifacts();
    } catch (error) { artifactStatusEl.textContent = error.message; }
    finally { state.busy = false; renderArtifacts(); }
  });
  const recommend = document.createElement("button");
  recommend.type = "button"; recommend.className = "primary-action";
  recommend.textContent = "Recommend Claims via LLM";
  recommend.disabled = state.busy || filtered.length === 0;
  recommend.classList.toggle("is-active", state.activeAction === "recommend");
  recommend.addEventListener("click", () => {
    state.activeAction = state.activeAction === "recommend" ? "" : "recommend";
    renderArtifacts();
  });
  const organize = document.createElement("button");
  organize.type = "button"; organize.className = "semantic-action is-edit";
  organize.textContent = "Organize Project Wiki";
  organize.disabled = state.busy || !(detail.claims || []).length;
  organize.classList.toggle("is-active", state.activeAction === "wiki");
  organize.addEventListener("click", () => {
    state.activeAction = state.activeAction === "wiki" ? "" : "wiki";
    renderArtifacts();
  });
  const article = document.createElement("button");
  article.type = "button"; article.className = "semantic-action is-edit";
  article.textContent = "Generate Article";
  article.disabled = !(detail.claims || []).length;
  article.addEventListener("click", () => {
    state.activeAction = "";
    aiComposer.hidden = true;
    activeArticleProjectId = artifact.id;
    wikiReadingEl.hidden = true;
    wikiReadingComposerEl.hidden = false;
    card.appendChild(wikiReadingComposerEl);
    wikiReadingScopeEl.textContent = `${detail.claims?.length || 0} Project Claim${detail.claims?.length === 1 ? "" : "s"}`;
    artifactStatusEl.textContent = "";
    wikiReadingGoalInput.focus();
  });
  tools.append(add, recommend, organize, article);

  const aiComposer = document.createElement("section");
  aiComposer.className = "project-action-composer";
  aiComposer.hidden = !["recommend", "wiki"].includes(state.activeAction);
  if (!aiComposer.hidden) {
    const isRecommendation = state.activeAction === "recommend";
    const copy = document.createElement("div");
    const composerTitle = document.createElement("strong");
    composerTitle.textContent = isRecommendation ? "Recommend Claims" : "Organize Project Wiki";
    const composerNote = document.createElement("small");
    composerNote.textContent = isRecommendation
      ? `The model will rank the ${filtered.length} Claims in the current filtered scope.`
      : `The model will propose a Wiki structure for this Project's ${detail.claims?.length || 0} Claims.`;
    copy.append(composerTitle, composerNote);
    const modelField = document.createElement("label");
    modelField.className = "project-model-field";
    const modelLabel = document.createElement("span"); modelLabel.textContent = "Model";
    const model = document.createElement("select");
    model.setAttribute("aria-label", isRecommendation
      ? "Model for Project Claim recommendations" : "Model for Project Wiki organization");
    const preferredModel = isRecommendation ? state.recommendationModel : state.wikiModel;
    aiModelProfiles.filter((profile) => (profile.capabilities || []).includes("chat")).forEach((profile) => {
      const option = document.createElement("option");
      option.value = profile.id; option.textContent = profile.name || profile.model;
      option.selected = profile.id === (preferredModel || (isRecommendation
        ? aiRoleAssignments.article : aiRoleAssignments.wiki));
      model.appendChild(option);
    });
    model.addEventListener("change", () => {
      if (isRecommendation) state.recommendationModel = model.value;
      else state.wikiModel = model.value;
    });
    modelField.append(modelLabel, model);
    const run = document.createElement("button");
    run.type = "button"; run.className = "primary-action";
    run.textContent = state.busy ? "Working…" : isRecommendation
      ? "Run recommendation" : "Propose Wiki structure";
    run.disabled = state.busy || !model.value;
    run.addEventListener("click", async () => {
      state.busy = true; renderArtifacts();
      artifactStatusEl.textContent = isRecommendation
        ? "Finding Claims that fit this Project…" : "Organizing this Project's Claims…";
      try {
        const response = await fetch(
          isRecommendation ? "/api/project-claim-recommendations/generate"
            : "/api/project-wiki-proposals/generate", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(isRecommendation ? {
              project_id: artifact.id, candidate_ids: filtered.map((claim) => claim.id),
              model_profile_id: model.value,
            } : { project_id: artifact.id, model_profile_id: model.value }),
          },
        );
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.message || (isRecommendation
          ? "Could not recommend Claims." : "Could not organize the Project Wiki."));
        if (isRecommendation) {
          await fetchProjectRecommendations(artifact.id);
          artifactStatusEl.textContent = `${data.proposals?.length || 0} recommendation${data.proposals?.length === 1 ? "" : "s"} awaiting review.`;
        } else {
          const refreshed = await fetch(`/api/projects/${encodeURIComponent(artifact.id)}`).then((entry) => entry.json());
          projectDetails.set(artifact.id, refreshed);
          artifactStatusEl.textContent = "Project Wiki structure awaiting review.";
        }
        state.activeAction = "";
      } catch (error) { artifactStatusEl.textContent = error.message; }
      finally { state.busy = false; renderArtifacts(); }
    });
    aiComposer.append(copy, modelField, run);
  }

  const candidateList = document.createElement("div");
  candidateList.className = "project-candidate-list";
  filtered.slice(0, 100).forEach((claim) => {
    const row = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox"; checkbox.checked = state.selected.has(claim.id);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) state.selected.add(claim.id); else state.selected.delete(claim.id);
      renderArtifacts();
    });
    const statement = document.createElement("span"); statement.textContent = claim.statement;
    row.append(checkbox, statement); candidateList.appendChild(row);
  });
  if (!filtered.length) candidateList.innerHTML = "<small>No available Claims in this scope.</small>";

  const review = document.createElement("div");
  review.className = "project-recommendation-list";
  const proposals = projectClaimRecommendations.get(artifact.id) || [];
  const refreshReview = async (fetchData = false) => {
    if (fetchData) {
      await fetchProjectRecommendations(artifact.id);
      const response = await fetch(`/api/projects/${encodeURIComponent(artifact.id)}`);
      if (!response.ok) throw new Error("Could not refresh Project");
      projectDetails.set(artifact.id, await response.json());
      await fetchArtifacts();
    } else renderArtifacts();
  };
  if (proposals.length) {
    const reviewHead = document.createElement("strong");
    reviewHead.textContent = `Awaiting review · ${proposals.length}`;
    review.appendChild(reviewHead);
    const batch = createReviewBatchBar(`project-claims-${artifact.id}`, proposals,
      (proposal, accepted) => sendReviewDecision(`/api/project-claim-recommendations/${proposal.id}`, accepted), refreshReview, artifactStatusEl);
    review.append(batch.bar);
    proposals.forEach((proposal) => {
      const item = document.createElement("article");
      addReviewSelection(item, proposal, batch.state, batch.update);
      const statement = document.createElement("p"); statement.textContent = proposal.claim.statement;
      const rationale = document.createElement("small"); rationale.textContent = proposal.payload.rationale || "Recommended for this Project.";
      const actions = document.createElement("div");
      const discard = document.createElement("button"); discard.type = "button"; discard.className = "semantic-action is-discard"; discard.textContent = "× Discard";
      const accept = document.createElement("button"); accept.type = "button"; accept.className = "semantic-action is-accept"; accept.textContent = "✓ Add Claim";
      const decide = async (accepted) => {
        const response = await fetch(`/api/project-claim-recommendations/${proposal.id}${accepted ? "/accept" : ""}`, { method: accepted ? "POST" : "DELETE" });
        if (!response.ok) { const body = await response.json().catch(() => ({})); artifactStatusEl.textContent = body.message || "Could not review recommendation."; return; }
        await fetchProjectRecommendations(artifact.id);
        if (accepted) {
          const refreshed = await fetch(`/api/projects/${encodeURIComponent(artifact.id)}`).then((entry) => entry.json());
          projectDetails.set(artifact.id, refreshed); await fetchArtifacts();
        }
        renderArtifacts();
      };
      discard.addEventListener("click", () => decide(false)); accept.addEventListener("click", () => decide(true));
      actions.append(discard, accept); item.append(statement, rationale, actions); review.appendChild(item);
    });
  }
  const wikiReview = document.createElement("div");
  wikiReview.className = "project-recommendation-list project-wiki-review";
  const wikiBatch = createReviewBatchBar(`project-wiki-${artifact.id}`, detail.wiki_proposals || [],
    (proposal, accepted) => sendReviewDecision(`/api/project-wiki-proposals/${proposal.id}`, accepted), refreshReview, artifactStatusEl, {singleAccept: true});
  if (detail.wiki_proposals?.length) wikiReview.append(wikiBatch.bar);
  (detail.wiki_proposals || []).forEach((proposal) => {
    const item = document.createElement("article");
    addReviewSelection(item, proposal, wikiBatch.state, wikiBatch.update);
    const title = document.createElement("strong"); title.textContent = "Project Wiki awaiting review";
    const pages = document.createElement("small"); pages.textContent = `${proposal.payload.pages?.length || 0} sections · ${proposal.payload.summary || "Review the proposed structure before applying it."}`;
    const actions = document.createElement("div");
    const discard = document.createElement("button"); discard.type = "button"; discard.className = "semantic-action is-discard"; discard.textContent = "× Discard";
    const accept = document.createElement("button"); accept.type = "button"; accept.className = "semantic-action is-accept"; accept.textContent = "✓ Apply Wiki";
    const decide = async (accepted) => {
      const response = await fetch(`/api/project-wiki-proposals/${proposal.id}${accepted ? "/accept" : ""}`, { method: accepted ? "POST" : "DELETE" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) { artifactStatusEl.textContent = data.message || "Could not review the Project Wiki."; return; }
      const refreshed = await fetch(`/api/projects/${encodeURIComponent(artifact.id)}`).then((entry) => entry.json());
      projectDetails.set(artifact.id, refreshed); renderArtifacts();
    };
    discard.addEventListener("click", () => decide(false)); accept.addEventListener("click", () => decide(true));
    const preview = document.createElement("div"); preview.className = "project-wiki-display";
    renderProjectWikiPages(preview, proposal.payload.pages || [], detail.claims || [], proposal.payload.gaps || []);
    actions.append(discard, accept); item.append(title, pages, preview, actions); wikiReview.appendChild(item);
  });
  scope.append(heading, filters, scopeStats, tools, aiComposer, candidateList, review, wikiReview);
  card.appendChild(scope);
};

const renderArtifacts = () => {
  artifactListEl.replaceChildren();
  if (!artifacts.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = "No Projects yet. Create one with a concrete Purpose, then select Claims from the global Wiki.";
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
    meta.textContent = [
      `${artifact.source_count || 0} Sources`,
      `${artifact.evidence_count || 0} Evidence`,
      `${artifact.claim_count || 0} Claims`,
      `${artifact.document_count || 0} Articles`,
    ].join(" · ");
    const tagStrip = document.createElement("div");
    renderTagChips(tagStrip, artifact.tags, {
      editable: true,
      onEdit: () => openTagEditor("artifact", artifact.id, artifact.tags || [], async () => {
        await fetchArtifacts();
      }),
    });
    const actions = document.createElement("div");
    actions.className = "artifact-card-actions";
    const toggleSources = document.createElement("button");
    toggleSources.type = "button";
    const isExpanded = expandedArtifactIds.has(artifact.id);
    toggleSources.textContent = isExpanded
      ? "Hide knowledge"
      : "Open Project";
    toggleSources.setAttribute("aria-expanded", String(isExpanded));
    toggleSources.addEventListener("click", async () => {
      if (expandedArtifactIds.has(artifact.id)) {
        expandedArtifactIds.delete(artifact.id);
      } else {
        const response = await fetch(`/api/projects/${encodeURIComponent(artifact.id)}`);
        const detail = await response.json().catch(() => ({}));
        if (!response.ok) {
          artifactStatusEl.textContent = detail.message || "Could not open the Project.";
          return;
        }
        projectDetails.set(artifact.id, detail);
        await fetchProjectRecommendations(artifact.id);
        expandedArtifactIds.add(artifact.id);
        collectArtifactSelect.value = artifact.id;
        localStorage.setItem("knowte-active-artifact", artifact.id);
      }
      renderArtifacts();
      renderContextPanel();
    });
    actions.appendChild(toggleSources);
    const exportProject = document.createElement("button");
    exportProject.type = "button";
    exportProject.className = "semantic-action is-export";
    exportProject.textContent = "⇩ Export";
    exportProject.disabled = artifact.import_state === "awaiting_review";
    exportProject.addEventListener("click", () => exportKnowledge(
      "project", [artifact.id], artifactStatusEl, exportProject,
    ));
    actions.append(exportProject);
    if (artifact.import_state === "awaiting_review") {
      const reviewImport = document.createElement("button");
      reviewImport.type = "button";
      reviewImport.className = "semantic-action is-review";
      reviewImport.textContent = "Review import";
      reviewImport.addEventListener("click", async () => {
        reviewImport.disabled = true;
        try {
          const response = await fetch(`/api/projects/${encodeURIComponent(artifact.id)}`);
          const project = await response.json();
          if (!response.ok) throw new Error(project.message || "Could not load this import.");
          card.querySelector(".project-import-review")?.remove();
          const review = document.createElement("section");
          review.className = "project-import-review";
          const counts = project.import?.summary?.counts || {};
          const heading = document.createElement("strong");
          heading.textContent = "Shared knowledge awaiting review";
          const summary = document.createElement("p");
          summary.textContent = `${counts.sources || 0} Sources · ${counts.evidence || 0} Evidence · ${counts.claims || 0} Claims`;
          const note = document.createElement("small");
          note.textContent = "Accepting deduplicates the package into your global Library and makes its active Claims part of the Wiki.";
          const controls = document.createElement("div");
          const close = document.createElement("button");
          close.type = "button"; close.textContent = "Not now";
          close.addEventListener("click", () => review.remove());
          const accept = document.createElement("button");
          accept.type = "button"; accept.className = "semantic-action is-accept";
          accept.textContent = "✓ Accept into Library";
          accept.addEventListener("click", async () => {
            accept.disabled = true;
            artifactStatusEl.textContent = "Importing reviewed knowledge…";
            const accepted = await fetch(
              `/api/projects/${encodeURIComponent(artifact.id)}/import/accept`,
              { method: "POST" },
            );
            const body = await accepted.json().catch(() => ({}));
            if (!accepted.ok) {
              accept.disabled = false;
              artifactStatusEl.textContent = body.message || "Could not accept the import.";
              return;
            }
            await Promise.all([fetchArtifacts(), fetchLibrary(), fetchEvidenceLibrary(), fetchClaims(), fetchWiki()]);
            artifactStatusEl.textContent = `Imported ${body.created.claims} new Claim${body.created.claims === 1 ? "" : "s"}; reused ${body.reused.claims}.`;
          });
          controls.append(close, accept);
          review.append(heading, summary, note, controls);
          card.appendChild(review);
        } catch (error) {
          artifactStatusEl.textContent = error.message;
        } finally {
          reviewImport.disabled = false;
        }
      });
      actions.appendChild(reviewImport);
    }

    card.append(head, purpose, tagStrip, meta, actions);
    if (isExpanded) {
      const detail = projectDetails.get(artifact.id) || {};
      const claimList = document.createElement("div");
      claimList.className = "project-knowledge-list";
      const claimHeading = document.createElement("strong");
      claimHeading.textContent = `Claims · ${(detail.claims || []).length}`;
      claimList.appendChild(claimHeading);
      (detail.claims || []).forEach((claim) => {
        const row = document.createElement("button");
        row.type = "button";
        row.textContent = claim.statement;
        row.addEventListener("click", () => {
          selectedClaimIds.clear(); selectedClaimIds.add(claim.id);
          showPanel("claims-panel");
        });
        claimList.appendChild(row);
      });
      const projectWiki = document.createElement("div");
      projectWiki.className = "project-wiki-display";
      if (detail.wiki) {
        const wikiHeading = document.createElement("strong");
        wikiHeading.textContent = detail.wiki.title || `${artifact.title} Wiki`;
        projectWiki.appendChild(wikiHeading);
        const pages = detail.wiki.graph_state?.pages || [];
        renderProjectWikiPages(projectWiki, pages, detail.claims || [], detail.wiki.graph_state?.gaps || []);
      }
      const documents = document.createElement("div");
      documents.className = "project-knowledge-list";
      const documentHeading = document.createElement("strong");
      documentHeading.textContent = `Articles · ${(detail.documents || []).length}`;
      documents.appendChild(documentHeading);
      (detail.documents || []).forEach((article) => {
        const row = document.createElement("button");
        row.type = "button";
        row.textContent = article.title;
        row.addEventListener("click", () => {
          activeArticleProjectId = artifact.id;
          renderWikiReading(article.content, { saved: true, documentId: article.id, goal: article.goal });
          card.appendChild(wikiReadingEl);
        });
        documents.appendChild(row);
      });
      renderProjectClaimScope(card, artifact, detail);
      card.append(detail.wiki ? projectWiki : claimList, documents);
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

const syncTagFilterOptions = (control, items, selectedTags, otherSelectedTags, relationLabel = "") => {
  const names = [...(relationLabel ? ["__has_related__", "__no_related__"] : []), ...[...new Set(items.flatMap(
    (item) => (item.tags || []).map((tag) => tag.name).filter(Boolean),
  ))].sort((left, right) => left.localeCompare(right))];
  [...selectedTags].forEach((name) => {
    if (!names.includes(name)) selectedTags.delete(name);
  });
  const details = control.querySelector("details");
  const summary = details.querySelector("summary span");
  const menu = details.querySelector(".tag-multiselect-menu");
  const updateState = () => {
    summary.textContent = `${selectedTags.size} selected`;
    menu.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
      checkbox.checked = selectedTags.has(checkbox.value);
    });
    const clear = menu.querySelector("button");
    if (clear) clear.disabled = selectedTags.size === 0;
  };
  const signature = JSON.stringify([names, relationLabel]);
  if (control.dataset.tagOptions === signature) {
    updateState();
    return;
  }
  control.dataset.tagOptions = signature;
  const wasOpen = details.open;
  menu.replaceChildren();
  const note = document.createElement("small");
  note.textContent = relationLabel ? "Link status" : "Tags";
  note.className = "tag-filter-group-title";
  menu.appendChild(note);
  names.forEach((name) => {
    if (relationLabel && name === names[2]) {
      const heading = document.createElement("small"); heading.textContent = "Tags";
      heading.className = "tag-filter-group-title is-separated"; menu.appendChild(heading);
    }
    const option = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = name;
    checkbox.checked = selectedTags.has(name);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        selectedTags.add(name);
        otherSelectedTags.delete(name);
      } else selectedTags.delete(name);
      control.dispatchEvent(new Event("change"));
    });
    const label = name === "__has_related__" ? `Has ${relationLabel}` : name === "__no_related__" ? `No ${relationLabel}` : name;
    if (relationLabel && name.startsWith("__")) option.className = "tag-filter-status";
    option.append(checkbox, document.createTextNode(label));
    menu.appendChild(option);
  });
  const clear = document.createElement("button");
  clear.type = "button";
  clear.textContent = "Clear";
  clear.disabled = selectedTags.size === 0;
  clear.addEventListener("click", () => {
    selectedTags.clear();
    control.dispatchEvent(new Event("change"));
  });
  menu.appendChild(clear);
  updateState();
  details.open = wasOpen;
};

const matchesTagFilter = (item, anyTags, allTags, relationCount) => {
  const itemTags = new Set((item.tags || []).map((tag) => tag.name));
  if (relationCount !== undefined) itemTags.add(Number(relationCount) > 0 ? "__has_related__" : "__no_related__");
  const matchesAny = anyTags.size === 0
    || [...anyTags].some((name) => itemTags.has(name));
  const matchesAll = [...allTags].every((name) => itemTags.has(name));
  return matchesAny && matchesAll;
};

const visibleEvidence = () => libraryEvidence.filter(
  (item) => matchesTagFilter(
    item, selectedEvidenceTagFilters, selectedEvidenceAllTagFilters, item.claim_count || 0,
  ),
);

const visibleSources = () => librarySources.filter(item => matchesTagFilter(
  item, selectedSourceTagFilters, selectedSourceAllTagFilters, item.evidence_count || 0,
));

const visibleClaims = () => claims.filter(
  (item) => !item.needs_review && matchesTagFilter(
    item, selectedClaimTagFilters, selectedClaimAllTagFilters,
  )
    && (!claimsReviewFilterInput.value
      || item.review_state === claimsReviewFilterInput.value),
);

const claimAuditScope = () => claimAuditScopeInput.value === "tags" ? {
  any_tags: [...selectedClaimAuditAnyTags],
  all_tags: [...selectedClaimAuditAllTags],
} : {};

const renderClaimAudit = () => {
  claimAuditBoardEl.hidden = !claimAuditBoardOpen;
  document.querySelector(".claims-workspace")?.classList.toggle(
    "is-auditing", claimAuditBoardOpen,
  );
  if (!claimAuditBoardOpen) return;
  claimAuditTagsEl.hidden = claimAuditScopeInput.value !== "tags";
  syncTagFilterOptions(
    claimAuditAnyTagsEl, claims,
    selectedClaimAuditAnyTags, selectedClaimAuditAllTags,
  );
  syncTagFilterOptions(
    claimAuditAllTagsEl, claims,
    selectedClaimAuditAllTags, selectedClaimAuditAnyTags,
  );
  const audit = activeClaimAudit;
  const running = ["ready", "running"].includes(audit?.status);
  const paused = audit?.status === "paused";
  const finished = ["completed", "cancelled", "failed"].includes(audit?.status);
  claimAuditPreviewBtn.hidden = Boolean(audit && !finished);
  claimAuditStartBtn.hidden = Boolean(audit && !finished);
  claimAuditPauseBtn.hidden = !running;
  claimAuditResumeBtn.hidden = !paused && audit?.status !== "failed";
  claimAuditCancelBtn.hidden = !running && !paused && audit?.status !== "failed";
  claimAuditProgressEl.hidden = !audit;
  claimAuditRawEl.hidden = !audit?.last_response;
  claimAuditRawEl.textContent = audit?.last_response || "";
  if (audit) {
    claimAuditProgressBarEl.max = Math.max(1, Number(audit.candidate_count || 0));
    claimAuditProgressBarEl.value = Number(audit.completed_count || 0);
    claimAuditProgressCountEl.textContent = `${audit.completed_count} / ${audit.candidate_count} pairs`;
    claimAuditProgressLabelEl.textContent = ({
      ready: "Ready to scan",
      running: "Checking Claims and relations…",
      paused: "Audit paused",
      completed: `Audit complete · ${audit.proposal_count} change${audit.proposal_count === 1 ? "" : "s"} proposed`,
      cancelled: "Audit cancelled",
      failed: audit.error || "Audit failed",
    })[audit.status] || audit.status;
    claimAuditEstimateEl.textContent = `${audit.claim_count} Claims in scope · ${audit.candidate_count} candidate pairs · ${Math.ceil(audit.candidate_count / 8)} estimated model calls. This is a candidate-based check, not every possible pair.`;
  }
};

const fetchClaimAudits = async () => {
  const response = await fetch("/api/claim-audits");
  if (!response.ok) throw new Error("Could not load Claim audits.");
  claimAudits = (await response.json()).audits || [];
  activeClaimAudit = claimAudits.find(
    (audit) => ["ready", "running", "paused", "failed"].includes(audit.status),
  ) || claimAudits[0] || null;
  renderClaimAudit();
  if (["ready", "running"].includes(activeClaimAudit?.status)) advanceClaimAudit();
};

let claimAuditPendingAction = "";
const setClaimAuditStatus = async (action) => {
  if (!activeClaimAudit) return;
  if (claimAuditAdvancing) {
    claimAuditPendingAction = action;
    claimAuditProgressLabelEl.textContent = action === "pause"
      ? "Pausing after the current batch…" : "Cancelling after the current batch…";
    return;
  }
  const response = await fetch(`/api/claim-audits/${activeClaimAudit.id}/${action}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    claimAuditEstimateEl.textContent = data.message || `Could not ${action} audit.`;
    return;
  }
  activeClaimAudit = data;
  renderClaimAudit();
  if (action === "resume") advanceClaimAudit();
};

const advanceClaimAudit = async () => {
  if (claimAuditAdvancing || !["ready", "running"].includes(activeClaimAudit?.status)) return;
  claimAuditAdvancing = true;
  setTabActivity("claims-panel", "processing");
  renderClaimAudit();
  try {
    const response = await fetch(`/api/claim-audits/${activeClaimAudit.id}/run`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
    });
    const data = await response.json().catch(() => ({}));
    updateUsage(data.usage);
    if (data.audit) activeClaimAudit = data.audit;
    const returned = Array.isArray(data.proposals) ? data.proposals : [];
    if (returned.length) {
      claimProposals = [...new Map(
        [...returned, ...claimProposals].map((proposal) => [proposal.id, proposal]),
      ).values()];
      renderClaimProposals();
    }
    if (!response.ok) throw new Error(data.message || "Claim audit failed.");
  } catch (error) {
    claimAuditEstimateEl.textContent = error.message;
  } finally {
    claimAuditAdvancing = false;
    if (claimAuditPendingAction) {
      const action = claimAuditPendingAction;
      claimAuditPendingAction = "";
      await setClaimAuditStatus(action);
    }
    renderClaimAudit();
    if (["ready", "running"].includes(activeClaimAudit?.status)) {
      window.setTimeout(advanceClaimAudit, 250);
    } else {
      setTabActivity("claims-panel", activeClaimAudit?.status === "completed" ? "result" : "idle");
      if (activeClaimAudit?.status === "completed") await fetchClaimProposals();
    }
  }
};

const updateClaimsStatus = () => {
  const filtered = visibleClaims();
  const filters = [];
  if (claimsReviewFilterInput.value) filters.push(
    claimsReviewFilterInput.value === "disputed" ? "Disputed" : "Accepted",
  );
  if (selectedClaimTagFilters.size) filters.push(
    `Any: ${[...selectedClaimTagFilters].join(", ")}`,
  );
  if (selectedClaimAllTagFilters.size) filters.push(
    `All: ${[...selectedClaimAllTagFilters].join(", ")}`,
  );
  claimsStatusEl.textContent = filters.length
    ? `${filtered.length} of ${claims.length} Claims · ${filters.join(" · ")}`
    : `${claims.length} Claim${claims.length === 1 ? "" : "s"}`;
};

const renderEvidenceLibrary = () => {
  if (evidenceProposalQueueOpen) return renderEvidenceProposals();
  evidenceLibraryListEl.replaceChildren();
  syncTagFilterOptions(
    evidenceTagFilterInput, libraryEvidence,
    selectedEvidenceTagFilters, selectedEvidenceAllTagFilters, "Claims",
  );
  syncTagFilterOptions(
    evidenceTagAllFilterInput, libraryEvidence,
    selectedEvidenceAllTagFilters, selectedEvidenceTagFilters, "Claims",
  );
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
  evidenceBatchTagBtn.disabled = selectedCount === 0;
  evidenceBatchDeleteBtn.disabled = selectedCount === 0;
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
    empty.textContent = `No Evidence matches Any: ${[...selectedEvidenceTagFilters].join(", ") || "—"} · All: ${[...selectedEvidenceAllTagFilters].join(", ") || "—"}.`;
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
      renderEvidenceText(content, item.quote);
    }
    const meta = document.createElement("small");
    meta.textContent = [item.locator, item.source_provider, `${item.claim_count} Claims`]
      .filter(Boolean).join(" · ");
    const tags = document.createElement("div");
    renderTagChips(tags, item.tags || []);
    const footer = document.createElement("div");
    footer.className = "evidence-library-card-footer";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "evidence-icon-action";
    open.appendChild(createControlIcon("inspect"));
    open.title = "Open Evidence";
    open.setAttribute("aria-label", "Open Evidence");
    open.addEventListener("click", () => openEvidenceDetail(item.id));
    footer.append(meta, open);
    card.append(selection, source, content, footer, tags);
    evidenceLibraryListEl.appendChild(card);
  });
};

const openEvidenceInWorkspace = (evidenceId) => {
  const item = libraryEvidence.find((evidence) => evidence.id === evidenceId);
  if (!item) return;
  claimProposalQueueOpen = false;
  evidenceProposalQueueOpen = false;
  selectedEvidenceTagFilters.clear();
  selectedEvidenceAllTagFilters.clear();
  renderClaimProposals();
  renderEvidenceLibrary();
  showPanel("evidence-panel");
  window.requestAnimationFrame(() => {
    const card = evidenceLibraryListEl.querySelector(
      `[data-evidence-id="${CSS.escape(evidenceId)}"]`,
    );
    if (!card) return;
    card.classList.add("is-located");
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => card.classList.remove("is-located"), 1800);
  });
};

const renderIncomingTrays = () => {
  const incomingEvidence = [...incomingClaimEvidenceIds]
    .map((id) => libraryEvidence.find((item) => item.id === id))
    .filter(Boolean);
  const viaLLM = incomingLLMEvidenceIds !== null;
  const incomingCount = viaLLM ? incomingLLMEvidenceIds.length : incomingEvidence.length;
  claimIncomingTrayEl.hidden = incomingCount === 0;
  claimIncomingTitleEl.textContent = `Incoming Evidence · ${incomingCount}`;
  claimIncomingItemsEl.hidden = viaLLM;
  claimIncomingTrayEl.querySelector("small").hidden = viaLLM;
  claimAddEvidenceBtn.hidden = viaLLM;
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

const syncProposalQueueButton = (button, count, isOpen) => {
  button.textContent = `Awaiting review · ${count}`;
  button.disabled = count === 0;
  button.classList.toggle("has-pending", count > 0);
  button.classList.toggle("is-open", count > 0 && isOpen);
  button.setAttribute("aria-expanded", String(count > 0 && isOpen));
  button.title = count > 0
    ? `${isOpen ? "Hide" : "Show"} ${count} item${count === 1 ? "" : "s"} awaiting review`
    : "Nothing is awaiting review";
};

const renderClaims = () => {
  if (claimProposalQueueOpen) return renderClaimProposals();
  claimsListEl.replaceChildren();
  syncTagFilterOptions(
    claimsTagFilterInput, claims,
    selectedClaimTagFilters, selectedClaimAllTagFilters,
  );
  syncTagFilterOptions(
    claimsTagAllFilterInput, claims,
    selectedClaimAllTagFilters, selectedClaimTagFilters,
  );
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
  claimsBatchTagBtn.disabled = selectedClaimIds.size === 0;
  claimsSelectedCountEl.textContent = `${selectedClaimIds.size} selected`;
  claimsHandoffReturnEl.hidden = !claimsReturnToView;
  claimsHandoffApplyBtn.disabled = claimsReturnToView && selectedClaimIds.size === 0;
  renderIncomingTrays();
  const relationSelection = selectedClaims();
  claimsRelateBtn.title = relationSelection.length === 2
    ? `First selected → second selected: ${relationSelection[0].statement} → ${relationSelection[1].statement}`
    : "Select two Claims; the relation runs from the first selected to the second.";
  syncProposalQueueButton(
    claimsProposalsToggleBtn, claimProposals.length, claimProposalQueueOpen,
  );
  if (!claims.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = "No Claims yet. Select Evidence, then propose Claims manually or via LLM.";
    claimsListEl.appendChild(empty);
  } else if (!filteredClaims.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    if (claimsReviewFilterInput.value
      && (selectedClaimTagFilters.size || selectedClaimAllTagFilters.size)) {
      empty.textContent = "No Claims match the selected Status and Tag.";
    } else if (claimsReviewFilterInput.value === "disputed") {
      empty.textContent = "No disputed Claims yet.";
    } else if (claimsReviewFilterInput.value === "accepted") {
      empty.textContent = "No accepted Claims yet.";
    } else {
      empty.textContent = `No Claims match Any: ${[...selectedClaimTagFilters].join(", ") || "—"} · All: ${[...selectedClaimAllTagFilters].join(", ") || "—"}.`;
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
    renderEvidenceText(statement, claim.statement);
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
      const next = await promptText("Revise Claim", claim.statement);
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

const reviewSelections = new Map();
let claimReviewCategory = "proposals";
const isEvidenceChangeReview = item => item.payload?.operation === "review_evidence_change";
for (const [id, category] of [["claim-review-new", "proposals"], ["claim-review-changed", "changed"]]) {
  document.getElementById(id).addEventListener("click", () => {
    claimReviewCategory = category;
    const state = reviewState("claim"); state.selected.clear(); state.any.clear(); state.all.clear();
    renderClaimProposals();
  });
}
const sendReviewDecision = async (url, accepted) => {
  const response = await fetch(`${url}${accepted ? "/accept" : ""}`, {method: accepted ? "POST" : "DELETE"});
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.message || "Could not review item"); }
};
const reviewState = (key) => {
  if (!reviewSelections.has(key)) reviewSelections.set(key, {selected: new Set(), any: new Set(), all: new Set(), busy: false});
  return reviewSelections.get(key);
};
const reviewItems = (kind) => (kind === "evidence" ? evidenceProposals : claimProposals.filter(item => isEvidenceChangeReview(item) === (claimReviewCategory === "changed"))).map(item => {
  const payload = item.payload || {};
  const relatedTags = kind === "claim" ? [payload.target_claim_id, payload.subject_claim_id, payload.object_claim_id, payload.source_claim_id]
    .flatMap(id => claims.find(claim => claim.id === id)?.tags || []) : [];
  return {...item, tags: [...(payload.tags || []).map(tag => typeof tag === "string" ? {name: tag} : tag), ...relatedTags]};
});
const visibleReviewItems = (kind) => {
  const state = reviewState(kind);
  return reviewItems(kind).filter(item => matchesTagFilter(item, state.any, state.all));
};
const selectAllReview = (kind, checked) => {
  const state = reviewState(kind);
  visibleReviewItems(kind).forEach(item => checked ? state.selected.add(item.id) : state.selected.delete(item.id));
  (kind === "evidence" ? renderEvidenceProposals : renderClaimProposals)();
};
const addReviewSelection = (card, item, state, update) => {
  const label = document.createElement("label"); label.className = "master-select proposal-select";
  const checkbox = document.createElement("input"); checkbox.type = "checkbox";
  checkbox.checked = state.selected.has(item.id); checkbox.disabled = state.busy;
  card.classList.toggle("is-selected", checkbox.checked);
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) state.selected.add(item.id); else state.selected.delete(item.id);
    card.classList.toggle("is-selected", checkbox.checked); update();
  });
  label.append(checkbox, document.createTextNode("Select")); card.append(label);
};
const createReviewBatchBar = (key, items, decide, refresh, status, {singleAccept = false, externalSelectAll = null, discardVerb = "Discard", canDispute = null} = {}) => {
  const state = reviewState(key);
  const ids = new Set(items.map(item => item.id));
  [...state.selected].forEach(id => { if (!ids.has(id)) state.selected.delete(id); });
  const bar = document.createElement("div"); bar.className = "review-batch-bar";
  const count = document.createElement("span");
  const selectAll = externalSelectAll || document.createElement("input");
  if (!externalSelectAll) {
    selectAll.type = "checkbox";
    const label = document.createElement("label"); label.className = "master-select";
    label.append(selectAll, document.createTextNode("Select all")); bar.append(label);
    selectAll.addEventListener("change", () => {
      items.forEach(item => selectAll.checked ? state.selected.add(item.id) : state.selected.delete(item.id)); refresh();
    });
  }
  const accept = document.createElement("button"); accept.type = "button"; accept.className = "semantic-action is-accept";
  accept.append(createControlIcon("accept"), document.createTextNode("Accept selected"));
  const discard = document.createElement("button"); discard.type = "button"; discard.className = "semantic-action is-destructive";
  discard.append(createControlIcon("discard"), document.createTextNode(`${discardVerb} selected`));
  const disputed = canDispute ? document.createElement("button") : null;
  if (disputed) {
    disputed.type = "button"; disputed.className = "proposal-disputed";
    disputed.append(createControlIcon("disputed"), document.createTextNode("Keep selected disputed"));
  }
  const update = () => {
    count.textContent = `${state.selected.size} selected · ${items.length} awaiting review`;
    updateSelectAllState(selectAll, state.selected.size, items.length);
    selectAll.disabled = state.busy || !items.length;
    accept.disabled = state.busy || !state.selected.size || (singleAccept && state.selected.size !== 1);
    discard.disabled = state.busy || !state.selected.size;
    if (disputed) {
      const unsupported = items.some(item => state.selected.has(item.id) && !canDispute(item));
      disputed.disabled = state.busy || !state.selected.size || unsupported;
      disputed.title = unsupported ? "Only new Claims and Evidence changed reviews can be kept disputed. Deselect other proposal types first." : "Keep selected Claims as disputed";
    }
  };
  const run = async (accepted) => {
    const selected = items.filter(item => state.selected.has(item.id));
    if (accepted && key === "claim") selected.sort((a, b) => Number(["create_relation", "revise_relation"].includes(a.payload?.operation)) - Number(["create_relation", "revise_relation"].includes(b.payload?.operation)));
    if (!selected.length || state.busy) return;
    if (accepted === "disputed" && (!canDispute || selected.some(item => !canDispute(item)))) return;
    if (accepted && singleAccept && selected.length !== 1) return;
    if (!await confirmAction(`${accepted === "disputed" ? "Keep disputed:" : accepted ? "Accept" : discardVerb} ${selected.length} selected proposal(s)?${discardVerb === "Withdraw" && !accepted ? " The Claims will be withdrawn; their history and links remain." : ""}`)) return;
    state.busy = true; update();
    status.textContent = `Processing 0 of ${selected.length} selected proposals…`;
    const controls = [...(bar.parentElement?.querySelectorAll("button, input, select, textarea") || [])]
      .map(control => [control, control.disabled]);
    controls.forEach(([control]) => { control.disabled = true; });
    let completed = 0;
    const errors = [];
    for (const item of selected) {
      try { await decide(item, accepted); state.selected.delete(item.id); completed++; }
      catch (error) { errors.push(error.message); }
      status.textContent = `Processed ${completed + errors.length} of ${selected.length} selected proposals…`;
    }
    state.busy = false;
    try { await refresh(true); } catch (error) { errors.push(error.message); }
    controls.forEach(([control, disabled]) => { control.disabled = disabled; });
    status.textContent = `${completed} ${accepted === "disputed" ? "kept disputed" : accepted ? "accepted" : discardVerb === "Withdraw" ? "withdrawn" : "discarded"}.` + (errors.length ? ` ${errors.length} failed; unsuccessful items remain pending. ${errors.join(" · ")}` : "");
    update();
  };
  accept.addEventListener("click", () => run(true)); discard.addEventListener("click", () => run(false));
  bar.append(count, discard);
  if (disputed) { disputed.addEventListener("click", () => run("disputed")); bar.append(disputed); }
  bar.append(accept);
  if (singleAccept) {
    const note = document.createElement("small"); note.textContent = "Structure patches may overlap. Apply one at a time; multiple drafts can be discarded together."; bar.append(note);
  }
  update(); return {bar, state, update};
};
const setupEntityReview = (kind, container) => {
  const isEvidence = kind === "evidence";
  const state = reviewState(kind), items = reviewItems(kind);
  const any = isEvidence ? evidenceTagFilterInput : claimsTagFilterInput;
  const all = isEvidence ? evidenceTagAllFilterInput : claimsTagAllFilterInput;
  delete any.dataset.tagOptions; delete all.dataset.tagOptions;
  syncTagFilterOptions(any, items, state.any, state.all);
  syncTagFilterOptions(all, items, state.all, state.any);
  const visible = visibleReviewItems(kind);
  const refresh = async (fetchData = false) => {
    if (fetchData) await Promise.all(isEvidence ? [fetchLibrary(), fetchEvidenceLibrary(), fetchEvidenceProposals()] : [fetchClaims(), fetchClaimProposals(), fetchWiki()]);
    else (isEvidence ? renderEvidenceProposals : renderClaimProposals)();
  };
  const decide = async (item, accepted) => {
    const payload = item.payload || {};
    const operation = payload.operation || "create_claim";
    if (operation === "review_evidence_change") {
      const response = await fetch(`/api/claim-proposals/${item.id}/accept`, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({statement: payload.statement, change_token: payload.change_token, review_state: accepted === "disputed" ? "disputed" : accepted ? "accepted" : "withdrawn"})});
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.message || "Could not review changed Evidence"); }
      return;
    }
    const edits = isEvidence ? {quote: payload.quote, tags: payload.tags || []}
      : operation === "create_claim" ? {statement: payload.statement, basis: payload.basis, review_state: accepted === "disputed" ? "disputed" : "accepted", artifact_ids: collectArtifactSelect.value ? [collectArtifactSelect.value] : []}
        : operation === "merge_claims" ? {merged_statement: payload.merged_statement || payload.target_statement} : {};
    const response = await fetch(`/api/${kind}-proposals/${item.id}${accepted ? "/accept" : ""}`, {
      method: accepted ? "POST" : "DELETE", headers: {"Content-Type": "application/json"},
      ...(accepted ? {body: JSON.stringify(edits)} : {}),
    });
    if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.message || "Could not review proposal"); }
  };
  const batch = createReviewBatchBar(kind, visible, decide, refresh, isEvidence ? evidenceStatusEl : claimsStatusEl,
    {externalSelectAll: isEvidence ? evidenceLibrarySelectAllInput : claimsSelectAllInput, discardVerb: !isEvidence && claimReviewCategory === "changed" ? "Withdraw" : "Discard",
      canDispute: isEvidence ? null : item => ["create_claim", "review_evidence_change"].includes(item.payload?.operation || "create_claim")});
  const originalUpdate = batch.update;
  batch.update = () => {
    originalUpdate();
    if (!isEvidence) claimsSelectedCountEl.textContent = `${state.selected.size} pending selected`;
  };
  batch.update();
  container.append(batch.bar);
  if (!visible.length) { const empty = document.createElement("p"); empty.textContent = "No pending proposals match these Tags."; container.append(empty); }
  return {...batch, items: visible};
};
const revealClaimProposal = (id) => {
  const state = reviewState("claim"); state.any.clear(); state.all.clear();
  claimReviewCategory = "proposals";
  renderClaimProposals();
  document.getElementById(`claim-proposal-${id}`)?.scrollIntoView({behavior: "smooth", block: "center"});
};
const renderClaimProposals = () => {
  claimProposalListEl.replaceChildren();
  if (!claimProposals.length) claimProposalQueueOpen = false;
  const changedCount = claimProposals.filter(isEvidenceChangeReview).length;
  document.getElementById("claim-review-new").textContent = `Proposals · ${claimProposals.length - changedCount}`;
  document.getElementById("claim-review-changed").textContent = `Evidence changed · ${changedCount}`;
  document.getElementById("claim-review-new").setAttribute("aria-pressed", String(claimReviewCategory === "proposals"));
  document.getElementById("claim-review-changed").setAttribute("aria-pressed", String(claimReviewCategory === "changed"));
  claimProposalBoardEl.querySelector(".claim-section-head small").textContent = claimReviewCategory === "changed"
    ? "Recheck the existing Claim. Accept confirms it; Withdraw keeps history but removes active status."
    : "Kept until you Accept, Keep disputed, or Discard.";
  claimProposalBoardEl.hidden = !claimProposalQueueOpen || claimProposals.length === 0;
  claimsListEl.hidden = claimProposalQueueOpen && claimProposals.length > 0;
  claimsListControlsEl.hidden = false;
  claimsBatchTagBtn.hidden = claimProposalQueueOpen;
  claimsReviewFilterInput.closest("label").hidden = claimProposalQueueOpen;
  claimsRelateBtn.disabled = claimProposalQueueOpen || selectedClaimIds.size !== 2;
  if (!claimProposalQueueOpen) {
    delete claimsTagFilterInput.dataset.tagOptions; delete claimsTagAllFilterInput.dataset.tagOptions;
    renderClaims();
  }
  syncProposalQueueButton(
    claimsProposalsToggleBtn, claimProposals.length, claimProposalQueueOpen,
  );
  claimProposalReportEl.hidden = !latestClaimProposalReport;
  claimProposalReportBodyEl.replaceChildren();
  if (latestClaimProposalReport) {
    const {
      summary, skipped = [], comparisonClaimCount = 0, comparisonScope = {},
    } = latestClaimProposalReport;
    claimProposalReportSummaryEl.textContent = `Latest run · ${skipped.length} skipped`;
    if (summary) {
      const paragraph = document.createElement("p");
      paragraph.textContent = summary;
      claimProposalReportBodyEl.appendChild(paragraph);
    }
    const context = document.createElement("small");
    context.textContent = `${comparisonClaimCount} existing Claims sent for comparison in the same model call · locally retrieved per Evidence from ${comparisonScope.total_claim_count ?? claims.length} total. ${comparisonScope.covered_evidence_count ?? 0}/${comparisonScope.evidence_count ?? 0} Evidence items have comparison candidates. ${comparisonScope.truncated ? `Limited to ${comparisonScope.limit} of ${comparisonScope.candidate_count} matching Claims. ` : ""}This is a partial check, not exhaustive library-wide deduplication.`;
    claimProposalReportBodyEl.appendChild(context);
    skipped.forEach((item) => {
      const row = document.createElement("div");
      row.className = "claim-proposal-skip";
      const ids = Array.isArray(item.evidence_ids) ? item.evidence_ids : [];
      row.textContent = `${ids.length} Evidence · ${item.reason || "No durable change proposed."}`;
      claimProposalReportBodyEl.appendChild(row);
    });
  }
  const batch = claimProposalQueueOpen ? setupEntityReview("claim", claimProposalListEl) : null;
  (batch?.items || []).forEach((proposal) => {
    const payload = proposal.payload || {};
    const operation = payload.operation || "create_claim";
    const card = document.createElement("article");
    card.className = `claim-proposal-card claim-operation-${operation.replaceAll("_", "-")}`;
    card.id = `claim-proposal-${proposal.id}`;
    addReviewSelection(card, proposal, batch.state, batch.update);
    const operationLabel = document.createElement("div");
    operationLabel.className = "claim-proposal-operation";
    operationLabel.textContent = ({
      review_evidence_change: "Recheck existing Claim · Evidence changed",
      create_claim: payload.basis === "inference" ? "New inference" : "New reported Claim",
      link_evidence: "Update existing Claim",
      create_relation: "New Claim relation",
      revise_relation: payload.relation_type === "remove" ? "Remove existing relation" : "Revise existing relation",
      merge_claims: payload.audit_judgment === "revises"
        ? "Audited revision" : "Possible duplicate",
    })[operation] || "Claim change";
    const statement = document.createElement("textarea");
    statement.rows = 3;
    statement.value = operation === "merge_claims"
      ? (payload.merged_statement || payload.target_statement || "")
      : (payload.statement || "");
    statement.addEventListener("input", () => { payload[operation === "merge_claims" ? "merged_statement" : "statement"] = statement.value; payload._draftEdited = true; });
    const statementPreview = document.createElement("p");
    statementPreview.className = "claim-statement";
    renderEvidenceText(statementPreview, statement.value);
    const statementEditor = document.createElement("details");
    statementEditor.className = "evidence-quote-editor";
    const statementEditorLabel = document.createElement("summary");
    statementEditorLabel.textContent = "Edit statement";
    statementEditor.append(statementEditorLabel, statement);
    statement.addEventListener("input", () => renderEvidenceText(statementPreview, statement.value));
    const fields = document.createElement("div");
    fields.className = "claim-proposal-fields";
    const basis = document.createElement("select");
    ["background", "reported", "inference"]
      .forEach((value) => basis.appendChild(new Option(value, value)));
    basis.value = payload.basis || "reported";
    basis.addEventListener("change", () => { payload.basis = basis.value; payload._draftEdited = true; });
    const basisField = document.createElement("label");
    const basisLabel = document.createElement("span");
    basisLabel.textContent = "Basis";
    basisField.append(basisLabel, basis);
    fields.append(basisField);
    const target = document.createElement("div");
    target.className = "claim-proposal-target";
    if (operation === "link_evidence") {
      const targetLabel = document.createElement("small");
      targetLabel.textContent = "Attach selected Evidence to";
      const targetStatement = document.createElement("strong");
      renderEvidenceText(targetStatement, payload.target_statement || payload.target_claim_id || "Existing Claim");
      target.append(targetLabel, targetStatement);
    } else if (["create_relation", "revise_relation"].includes(operation)) {
      const subject = document.createElement("strong");
      renderEvidenceText(subject, payload.subject_statement || payload.subject_claim_id || "Claim");
      const relation = document.createElement("span");
      relation.className = "claim-relation-preview";
      relation.textContent = `→ ${payload.relation_type || "related"} →`;
      const object = document.createElement("strong");
      renderEvidenceText(object, payload.object_statement || payload.object_claim_id || "Claim");
      target.append(subject, relation, object);
      if (payload.existing_relation) {
        const before = document.createElement("small");
        const old = payload.existing_relation;
        before.textContent = `Previously: ${old.relation_type}${old.subject_claim_id !== payload.subject_claim_id ? " · opposite direction" : ""}`;
        target.prepend(before);
      }
      const waiting = ["subject_claim_id", "object_claim_id"].filter(key => String(payload[key] || "").startsWith("proposal:"));
      if (payload.blocked_reason || waiting.length) {
        const notice = document.createElement("p"); notice.className = "claim-proposal-context";
        notice.textContent = payload.blocked_reason || `Awaiting acceptance of ${waiting.length} endpoint Claim(s). Review those Claims first.`;
        target.append(notice);
        for (const key of payload.blocked_reason ? [] : waiting) {
          const open = document.createElement("button"); open.type = "button"; open.className = "semantic-action is-navigate";
          open.textContent = "Review endpoint Claim";
          open.addEventListener("click", () => revealClaimProposal(payload[key].slice(9)));
          target.append(open);
        }
      }
    } else if (operation === "merge_claims") {
      const targetLabel = document.createElement("small");
      targetLabel.textContent = "Keep and consolidate into";
      const targetStatement = document.createElement("strong");
      renderEvidenceText(targetStatement, payload.target_statement || payload.target_claim_id);
      const sourceLabel = document.createElement("small");
      sourceLabel.textContent = "Merge redundant Claim";
      const sourceStatement = document.createElement("strong");
      renderEvidenceText(sourceStatement, payload.source_statement || payload.source_claim_id);
      target.append(targetLabel, targetStatement, sourceLabel, sourceStatement);
    }
    const evidence = document.createElement("div");
    evidence.className = "proposal-evidence-list";
    (payload.evidence || []).forEach((link) => {
      const sourceItem = libraryEvidence.find((item) => item.id === link.evidence_id);
      const row = document.createElement(sourceItem ? "button" : "div");
      row.className = "proposal-evidence-link";
      if (sourceItem) row.type = "button";
      const heading = document.createElement("span");
      heading.textContent = `${link.stance || "supports"} · ${sourceItem?.source_title || "Evidence unavailable"}`;
      const detail = document.createElement("small");
      renderEvidenceText(detail, sourceItem
        ? [sourceItem.locator, sourceItem.evidence_type === "snapshot"
          ? "Snapshot" : sourceItem.quote].filter(Boolean).join(" · ")
        : String(link.evidence_id || "Unknown Evidence"));
      row.append(heading, detail);
      if (sourceItem) row.addEventListener("click", () => openEvidenceInWorkspace(sourceItem.id));
      evidence.appendChild(row);
    });
    const rationale = document.createElement("section");
    rationale.className = "proposal-explanation proposal-rationale";
    const rationaleLabel = document.createElement("strong");
    rationaleLabel.textContent = "Rationale";
    const rationaleBody = document.createElement("p");
    renderEvidenceText(rationaleBody, payload.rationale || (operation === "review_evidence_change" ? "Linked Evidence was edited. Check whether this Claim and its Evidence relationships still hold." : "No rationale supplied."));
    rationale.append(rationaleLabel, rationaleBody);
    const caveatItems = (payload.caveats || []).filter(Boolean);
    const caveats = document.createElement("section");
    caveats.className = "proposal-explanation proposal-caveats";
    const caveatsLabel = document.createElement("strong");
    caveatsLabel.textContent = "Caveats";
    const caveatsBody = document.createElement("p");
    renderEvidenceText(caveatsBody, caveatItems.join(" · "));
    caveats.append(caveatsLabel, caveatsBody);
    const actions = document.createElement("div");
    actions.className = "claim-card-actions claim-proposal-actions";
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "proposal-accept";
    const acceptLabel = document.createElement("span");
    acceptLabel.textContent = "Accept";
    accept.append(createControlIcon("accept"), acceptLabel);
    const resolveProposal = async (reviewState = "accepted") => {
      [accept, keepDisputed].forEach((button) => { button.disabled = true; });
      const artifact = artifacts.find((item) => item.id === collectArtifactSelect.value) || null;
      const edits = operation === "create_claim" ? {
        statement: statement.value.trim(), basis: basis.value, review_state: reviewState,
        artifact_ids: artifact?.id ? [artifact.id] : [],
      } : operation === "review_evidence_change" ? {
        statement: statement.value.trim(), change_token: payload.change_token, review_state: reviewState,
      } : operation === "merge_claims" ? {
        merged_statement: statement.value.trim(),
      } : {};
      const response = await fetch(`/api/claim-proposals/${proposal.id}/accept`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(edits),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        claimsStatusEl.textContent = data.message || "Could not accept Proposal.";
        [accept, keepDisputed].forEach((button) => { button.disabled = false; });
        return;
      }
      await Promise.all([fetchClaims(), fetchClaimProposals(), fetchWiki()]);
    };
    accept.addEventListener("click", () => resolveProposal("accepted"));
    const keepDisputed = document.createElement("button");
    keepDisputed.type = "button";
    keepDisputed.className = "proposal-disputed";
    const disputedLabel = document.createElement("span");
    disputedLabel.textContent = "Keep disputed";
    keepDisputed.append(createControlIcon("disputed"), disputedLabel);
    keepDisputed.addEventListener("click", () => resolveProposal("disputed"));
    keepDisputed.hidden = !["create_claim", "review_evidence_change"].includes(operation);
    acceptLabel.textContent = operation === "link_evidence"
      ? "Attach Evidence"
      : operation === "create_relation" ? "Create relation"
        : operation === "revise_relation" ? "Apply relation change"
        : operation === "merge_claims" ? "Merge Claims" : "Accept";
    if (["create_relation", "revise_relation"].includes(operation)) {
      accept.disabled = Boolean(payload.blocked_reason) || ["subject_claim_id", "object_claim_id"].some(key => String(payload[key] || "").startsWith("proposal:"));
    }
    const discard = document.createElement("button");
    discard.type = "button";
    discard.className = "proposal-discard";
    const discardLabel = document.createElement("span");
    discardLabel.textContent = "Discard";
    if (operation === "review_evidence_change") discardLabel.textContent = "Withdraw Claim";
    discard.append(createControlIcon("discard"), discardLabel);
    discard.addEventListener("click", async () => {
      if (operation === "review_evidence_change") {
        if (await confirmAction("Withdraw this Claim? Its history and links will be retained.")) await resolveProposal("withdrawn");
        return;
      }
      if (!await confirmAction("Discard this Claim proposal?")) return;
      const response = await fetch(`/api/claim-proposals/${proposal.id}`, { method: "DELETE" });
      if (response.ok) await fetchClaimProposals();
    });
    actions.append(discard, keepDisputed, accept);
    card.append(operationLabel);
    if (operation === "review_evidence_change") {
      card.append(statementPreview, statementEditor);
      for (const change of payload.changes || []) {
        const section = document.createElement("section"); section.className = "evidence-change-comparison";
        const title = document.createElement("strong"); title.textContent = `Evidence · v${change.before_revision} → v${change.revision}`;
        if (change.deleted) title.textContent = `Evidence · v${change.before_revision} → Deleted`;
        const before = document.createElement("blockquote"); renderEvidenceText(before, change.before_quote);
        const beforeLabel = document.createElement("small"); beforeLabel.textContent = `Before · ${change.before_locator || "No locator"}`;
        const after = document.createElement("blockquote"); renderEvidenceText(after, change.quote);
        if (change.deleted) after.textContent = "This Evidence was deleted. Reassess whether the remaining basis supports this Claim.";
        const afterLabel = document.createElement("small"); afterLabel.textContent = `Now · ${change.locator || "No locator"}`;
        const open = document.createElement("button"); open.className = "semantic-action is-navigate"; open.type = "button"; open.textContent = "Open Evidence";
        open.addEventListener("click", () => openEvidenceDetail(change.evidence_id));
        open.hidden = Boolean(change.deleted);
        section.append(title, beforeLabel, before, afterLabel, after, open); card.append(section);
      }
    } else if (operation === "create_claim") {
      card.append(statementPreview, statementEditor, fields);
      const relatedDrafts = claimProposals.filter(item => ["subject_claim_id", "object_claim_id"].some(key => item.payload?.[key] === `proposal:${proposal.id}`));
      for (const draft of relatedDrafts) {
        const link = document.createElement("button"); link.type = "button"; link.className = "semantic-action is-navigate";
        link.textContent = `Review relation · ${draft.payload.relation_type}`;
        link.addEventListener("click", () => revealClaimProposal(draft.id));
        card.append(link);
      }
    }
    else if (operation === "merge_claims") card.append(target, statementPreview, statementEditor);
    else card.append(target);
    if (payload.evidence?.length) card.append(evidence);
    card.append(rationale);
    if (caveatItems.length) card.append(caveats);
    card.append(actions);
    if (batch.state.busy) card.querySelectorAll("button, input, select, textarea").forEach(control => { control.disabled = true; });
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
  renderReviewWorkspace();
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

const waitForReaderTarget = async (selector, timeout = 6000) => {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    const target = sourceReaderSegmentsEl.querySelector(selector);
    if (target) return target;
    await new Promise((resolve) => window.setTimeout(resolve, 50));
  }
  return null;
};

const locateEvidenceProposal = async (payload) => {
  showPanel("sources-panel");
  const opened = await openSourceReader(payload.source_id);
  if (!opened) return;
  const segment = activeSourceWorkspace?.segments.find(
    (item) => item.id === payload.segment_id,
  );
  const isPdf = activeSourceWorkspace?.capture?.media_type === "application/pdf";
  const selector = isPdf
    ? `.pdf-page[data-page-number="${Number(segment?.ordinal || 1)}"]`
    : `.capture-segment[data-segment-id="${CSS.escape(payload.segment_id || "")}"]`;
  const target = await waitForReaderTarget(selector);
  if (!target) {
    libraryStatusEl.textContent = "The passage is verified, but its visual location could not be rendered.";
    return;
  }
  sourceReaderSegmentsEl.querySelectorAll(".reader-located-passage").forEach(
    (item) => item.classList.remove("reader-located-passage"),
  );
  sourceReaderSegmentsEl.querySelectorAll("mark.reader-quote-mark").forEach(
    (mark) => mark.replaceWith(document.createTextNode(mark.textContent || "")),
  );
  target.classList.add("reader-located-passage");
  sourceReaderSegmentsEl.scrollTo({
    top: Math.max(0, target.offsetTop - 12),
    behavior: "smooth",
  });
  if (!isPdf) {
    const textNode = target.querySelector(".capture-segment-text");
    const fullText = textNode?.textContent || "";
    const quote = payload.quote || "";
    const start = fullText.indexOf(quote);
    if (textNode && start >= 0) {
      const before = document.createTextNode(fullText.slice(0, start));
      const mark = document.createElement("mark");
      mark.className = "reader-quote-mark";
      mark.textContent = quote;
      const after = document.createTextNode(fullText.slice(start + quote.length));
      textNode.replaceChildren(before, mark, after);
    }
  }
};

const fetchClaimProposals = async () => {
  const response = await fetch("/api/claim-proposals");
  if (!response.ok) throw new Error("Could not load Claim proposals.");
  const drafts = new Map(claimProposals.filter(item => item.payload?._draftEdited).map(item => [item.id, item.payload]));
  claimProposals = ((await response.json()).proposals || []).map(item => drafts.has(item.id) && drafts.get(item.id).change_token === item.payload.change_token ? {...item, payload: drafts.get(item.id)} : item);
  renderClaimProposals();
};

const scrollClaimProposalQueueToStart = (behavior = "smooth") => {
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      const target = claimProposalBoardEl.hidden && latestClaimProposalReport
        ? claimProposalReportEl : claimProposalBoardEl;
      if (target.hidden) return;
      const panel = target.closest(".panel");
      if (!panel) {
        target.scrollIntoView({ behavior, block: "start" });
        return;
      }
      const panelRect = panel.getBoundingClientRect();
      const boardRect = target.getBoundingClientRect();
      panel.scrollTo({
        top: Math.max(0, panel.scrollTop + boardRect.top - panelRect.top - 12),
        behavior,
      });
    });
  });
};

const renderEvidenceProposals = () => {
  evidenceProposalListEl.replaceChildren();
  const shownReports = new Set();
  if (!evidenceProposals.length) evidenceProposalQueueOpen = false;
  evidenceProposalBoardEl.hidden = !evidenceProposalQueueOpen || evidenceProposals.length === 0;
  evidenceLibraryListEl.hidden = evidenceProposalQueueOpen && evidenceProposals.length > 0;
  evidenceBatchTagBtn.hidden = evidenceProposalQueueOpen;
  evidenceBatchDeleteBtn.hidden = evidenceProposalQueueOpen;
  claimProposalFocusInput.closest("label").hidden = evidenceProposalQueueOpen;
  libraryProposeClaimsBtn.disabled = evidenceProposalQueueOpen || !selectedEvidenceIds.size;
  evidenceCreateClaimBtn.disabled = evidenceProposalQueueOpen || !selectedEvidenceIds.size;
  if (!evidenceProposalQueueOpen) {
    delete evidenceTagFilterInput.dataset.tagOptions; delete evidenceTagAllFilterInput.dataset.tagOptions;
    renderEvidenceLibrary();
  }
  syncProposalQueueButton(
    evidenceProposalsToggleBtn, evidenceProposals.length, evidenceProposalQueueOpen,
  );
  const batch = evidenceProposalQueueOpen ? setupEntityReview("evidence", evidenceProposalListEl) : null;
  (batch?.items || []).forEach((proposal) => {
    const payload = proposal.payload || {};
    const scope = proposal.scope || {};
    const reportKey = JSON.stringify([scope, (proposal.created_at || "").slice(0, 16)]);
    if ((scope.summary || scope.inputs?.length) && !shownReports.has(reportKey)) {
      shownReports.add(reportKey);
      const report = document.createElement("section");
      report.className = "proposal-explanation";
      const heading = document.createElement("strong"); heading.textContent = "Source coverage";
      const detail = document.createElement("p"); detail.textContent = scope.summary || "";
      const inputs = document.createElement("small");
      inputs.textContent = (scope.inputs || []).map((item) => {
        const title = librarySources.find((source) => source.id === item.source_id)?.title || item.title || "Source";
        const method = {capture: "Captured text", url: "Provider URL Fetch", native_document: "Native document"}[item.input_kind] || item.input_kind;
        return `${title} · ${method}${item.input_kind === "capture" ? ` · ${item.text_characters} characters` : ""}`;
      }).join("\n");
      report.append(heading, detail, inputs); evidenceProposalListEl.append(report);
    }
    const source = librarySources.find((item) => item.id === payload.source_id);
    const card = document.createElement("article");
    card.className = "claim-proposal-card evidence-proposal-card";
    addReviewSelection(card, proposal, batch.state, batch.update);
    if (payload.evidence_type === "snapshot" && payload.image_data?.startsWith("data:image/png;base64,")) {
      const image = document.createElement("img");
      image.src = payload.image_data;
      image.alt = payload.locator || "Original Source image";
      image.style.maxWidth = "100%";
      image.style.maxHeight = "320px";
      image.style.objectFit = "contain";
      card.append(image);
    }
    const sourceLabel = document.createElement("small");
    sourceLabel.textContent = `${source?.title || payload.related_source?.title || "Source"} · ${payload.locator || "Captured passage"}`;
    if (payload.related_source) sourceLabel.textContent += " · New Source — added only on acceptance";
    const quote = document.createElement("textarea");
    quote.rows = 4;
    quote.value = payload.quote || "";
    quote.addEventListener("input", () => { payload.quote = quote.value; payload._draftEdited = true; });
    const quotePreview = document.createElement("blockquote");
    renderEvidenceText(quotePreview, quote.value);
    const quoteEditor = document.createElement("details");
    quoteEditor.className = "evidence-quote-editor";
    const quoteEditorLabel = document.createElement("summary");
    quoteEditorLabel.textContent = "Edit original text";
    quoteEditor.append(quoteEditorLabel, quote);
    quote.addEventListener("input", () => renderEvidenceText(quotePreview, quote.value));
    const rationale = document.createElement("section");
    rationale.className = "proposal-explanation proposal-rationale";
    const rationaleLabel = document.createElement("strong");
    rationaleLabel.textContent = "Rationale";
    const rationaleBody = document.createElement("p");
    rationaleBody.textContent = payload.rationale || "No rationale supplied.";
    rationale.append(rationaleLabel, rationaleBody);
    const caveatItems = (payload.caveats || []).filter(Boolean);
    const caveats = document.createElement("section");
    caveats.className = "proposal-explanation proposal-caveats";
    const caveatsLabel = document.createElement("strong");
    caveatsLabel.textContent = "Caveats";
    const caveatsBody = document.createElement("p");
    caveatsBody.textContent = caveatItems.join(" · ");
    caveats.append(caveatsLabel, caveatsBody);
    const tags = document.createElement("input");
    tags.placeholder = "Comma-separated tags";
    tags.value = (payload.tags || []).join(", ");
    tags.addEventListener("input", () => { payload.tags = tags.value.split(",").map(tag => tag.trim()).filter(Boolean); payload._draftEdited = true; });
    const actions = document.createElement("div");
    actions.className = "claim-card-actions claim-proposal-actions";
    const locate = document.createElement("button");
    locate.type = "button";
    locate.className = "proposal-locate";
    locate.append(createControlIcon("inspect"), document.createTextNode("Locate in Source"));
    const unverified = payload.verification === "external_unverified";
    if (unverified) {
      sourceLabel.textContent += " · Not locally verified — check the original before accepting";
      locate.replaceChildren(createControlIcon("inspect"), document.createTextNode("Open original"));
    }
    locate.addEventListener("click", () => {
      if (unverified) {
        if (source?.document_hash) {
          window.open(`/api/library/sources/${source.id}/content`, "_blank", "noopener,noreferrer");
          return;
        }
        const url = payload.source_url || source?.url;
        if (/^https?:\/\//i.test(url || "")) window.open(url, "_blank", "noopener,noreferrer");
      } else locateEvidenceProposal(payload);
    });
    const discard = document.createElement("button");
    discard.type = "button";
    discard.className = "proposal-discard";
    discard.append(createControlIcon("discard"), document.createTextNode("Discard"));
    discard.addEventListener("click", async () => {
      const response = await fetch(`/api/evidence-proposals/${proposal.id}`, { method: "DELETE" });
      if (response.ok) await fetchEvidenceProposals();
    });
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "proposal-accept";
    accept.append(createControlIcon("accept"), document.createTextNode("Accept"));
    accept.addEventListener("click", async () => {
      accept.disabled = true;
      const response = await fetch(`/api/evidence-proposals/${proposal.id}/accept`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          quote: quote.value.trim(),
          tags: tags.value.split(",").map((item) => item.trim()).filter(Boolean),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        evidenceStatusEl.textContent = data.message || "Could not accept Evidence proposal.";
        accept.disabled = false;
        return;
      }
      await Promise.all([fetchLibrary(), fetchEvidenceLibrary(), fetchEvidenceProposals()]);
    });
    actions.append(locate, discard, accept);
    card.append(sourceLabel, quotePreview, quoteEditor, rationale);
    if (caveatItems.length) card.append(caveats);
    card.append(tags, actions);
    if (batch.state.busy) card.querySelectorAll("button, input, select, textarea").forEach(control => { control.disabled = true; });
    evidenceProposalListEl.appendChild(card);
  });
};

const fetchEvidenceProposals = async () => {
  const response = await fetch("/api/evidence-proposals");
  if (!response.ok) throw new Error("Could not load Evidence proposals.");
  const drafts = new Map(evidenceProposals.filter(item => item.payload?._draftEdited).map(item => [item.id, item.payload]));
  evidenceProposals = ((await response.json()).proposals || []).map(item => drafts.has(item.id) ? {...item, payload: drafts.get(item.id)} : item);
  renderEvidenceProposals();
};

const wikiClaimById = (claimId) => wikiState.claims.find((claim) => claim.id === claimId);

const openClaimFromWiki = (claimId) => {
  if (claims.find(claim => claim.id === claimId)?.needs_review) {
    claimProposalQueueOpen = true; claimReviewCategory = "changed";
    showPanel("claims-panel"); renderClaimProposals(); scrollClaimProposalQueueToStart(); return;
  }
  claimProposalQueueOpen = false;
  renderClaimProposals();
  selectedClaimIds.clear();
  selectedClaimIds.add(claimId);
  renderClaims();
  showPanel("claims-panel");
  window.requestAnimationFrame(() => {
    let card = claimsListEl.querySelector(`[data-claim-id="${claimId}"]`);
    if (!card) {
      claimsReviewFilterInput.value = "";
      selectedClaimTagFilters.clear();
      selectedClaimAllTagFilters.clear();
      renderClaims();
      card = claimsListEl.querySelector(`[data-claim-id="${claimId}"]`);
    }
    card?.scrollIntoView({behavior: "smooth", block: "center"});
  });
};

const wikiPageDepth = (page) => {
  const byId = new Map(wikiState.pages.map((item) => [item.id, item]));
  let depth = 0;
  let cursor = page;
  const seen = new Set();
  while (cursor?.parent_id && depth < 8 && !seen.has(cursor.parent_id)) {
    seen.add(cursor.parent_id);
    cursor = byId.get(cursor.parent_id);
    depth += 1;
  }
  return depth;
};

const renderWikiIncoming = () => {
  const activeCount = wikiState.claims.filter((claim) => claim.lifecycle === "active").length;
  const needsOrganization = (wikiState.unorganized_claim_ids?.length || 0)
    + (wikiState.stale_claim_ids?.length || 0);
  wikiOrganizeBtn.disabled = wikiProposalRunning;
  wikiOrganizeBtn.setAttribute("aria-disabled", String(activeCount === 0));
  wikiOrganizeBtn.classList.toggle("is-unavailable", activeCount === 0);
  wikiOrganizeBtn.title = activeCount === 0
    ? "Review at least one Claim before organizing the Wiki"
    : needsOrganization
      ? `Organize ${needsOrganization} unorganized or stale Claim${needsOrganization === 1 ? "" : "s"}`
      : "Review the complete Wiki organization";
  const canEditStructure = wikiState.pages.length > 0 || wikiProposals.length > 0;
  wikiEditStructureBtn.disabled = wikiProposalRunning || !canEditStructure;
  wikiResetStructureBtn.disabled = wikiProposalRunning || reviewState("wiki").busy || !canEditStructure;
  wikiEditStructureBtn.title = canEditStructure
    ? "Edit the current or awaiting Wiki structure"
    : "Organize the Wiki before editing its structure";
};

const renderWikiPage = () => {
  wikiPageEl.replaceChildren();
  const page = activeWikiPageId === "__stale__"
    ? {
        id: "__stale__", title: "Claims Changed Since the Last Wiki Organization",
        parent_id: null,
        summary: "These Claims changed after the current Wiki structure was accepted. Review whether their Page placement or surrounding structure still fits.",
        claim_ids: wikiState.stale_claim_ids || [],
      }
    : activeWikiPageId === "__unorganized__"
    ? {
        id: "__unorganized__", title: "Unorganized", parent_id: null,
        summary: "Reviewed Claims already in the global Wiki but not yet assigned to a Page.",
        claim_ids: wikiState.unorganized_claim_ids || [],
      }
    : wikiState.pages.find((item) => item.id === activeWikiPageId);
  if (!page) {
    const empty = document.createElement("div");
    empty.className = "wiki-empty";
    const title = document.createElement("strong");
    title.textContent = wikiState.claims.length ? "The Wiki has not been organized yet." : "No Claims yet.";
    const note = document.createElement("p");
    note.textContent = wikiState.claims.length
      ? "Organize the accepted Claims with AI, then review the proposed structure before it becomes the Wiki."
      : "Accepted Claims will become the material for the global Wiki.";
    empty.append(title, note);
    wikiPageEl.appendChild(empty);
    return;
  }
  const head = document.createElement("header");
  const eyebrow = document.createElement("small");
  eyebrow.textContent = "Global Wiki";
  const title = document.createElement("h2");
  title.textContent = page.title;
  const summary = document.createElement("p");
  renderWikiSummary(summary, page.summary || "No overview has been written for this Page.", wikiState.pages, (home, claimId) => {
    activeWikiPageId = home.id;
    renderWiki(); renderReviewWorkspace();
    focusWikiClaim(wikiPageEl, claimId);
  });
  head.append(eyebrow, title, summary);
  const list = document.createElement("div");
  list.className = "wiki-claim-list";
  page.claim_ids.forEach((claimId, index) => {
    const claim = wikiClaimById(claimId);
    if (!claim) return;
    const card = document.createElement("article");
    card.className = "wiki-claim-card";
    card.dataset.wikiClaimId = claim.id; card.tabIndex = -1;
    const meta = document.createElement("small");
    meta.textContent = `${String(index + 1).padStart(2, "0")} · ${claim.basis}${claim.review_state === "disputed" ? " · disputed" : ""}`;
    if (claim.needs_review) meta.textContent += " · Evidence changed — awaiting recheck";
    const statement = document.createElement("button");
    statement.type = "button";
    statement.className = "wiki-claim-statement";
    statement.textContent = claim.statement;
    statement.title = "Open this Claim in Claims";
    statement.addEventListener("click", () => openClaimFromWiki(claim.id));
    const evidence = document.createElement("div");
    evidence.className = "wiki-claim-evidence";
    (claim.evidence || []).slice(0, 4).forEach((item) => {
      const source = document.createElement("span");
      source.textContent = `${item.source_title || "Source"} · ${item.locator || "Evidence"}`;
      evidence.appendChild(source);
    });
    card.append(meta, statement, evidence);
    list.appendChild(card);
  });
  wikiPageEl.append(head, list);
};

const renderWikiTree = () => {
  wikiTreeEl.replaceChildren();
  if (wikiState.unorganized_claim_ids?.length) {
    const unorganized = document.createElement("button");
    unorganized.type = "button";
    unorganized.className = "wiki-tree-item needs-attention";
    unorganized.classList.toggle("is-active", activeWikiPageId === "__unorganized__");
    const title = document.createElement("span"); title.textContent = "Unorganized";
    const count = document.createElement("small");
    count.textContent = String(wikiState.unorganized_claim_ids.length);
    unorganized.append(title, count);
    unorganized.addEventListener("click", () => {
      activeWikiPageId = "__unorganized__";
      renderWiki(); renderReviewWorkspace();
    });
    wikiTreeEl.appendChild(unorganized);
  }
  if (!wikiState.pages.length) return;
  const children = new Map();
  wikiState.pages.forEach((page) => {
    const key = page.parent_id || "root";
    if (!children.has(key)) children.set(key, []);
    children.get(key).push(page);
  });
  const appendPages = (parentId, depth = 0, visited = new Set()) => {
    (children.get(parentId) || []).forEach((page) => {
      if (visited.has(page.id)) return;
      visited.add(page.id);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "wiki-tree-item";
      button.classList.toggle("is-active", page.id === activeWikiPageId);
      button.style.setProperty("--wiki-depth", depth);
      const title = document.createElement("span");
      title.textContent = page.title;
      const count = document.createElement("small");
      count.textContent = String(page.claim_ids.length);
      button.append(title, count);
      button.addEventListener("click", () => {
        activeWikiPageId = page.id;
        renderWiki();
        renderReviewWorkspace();
      });
      wikiTreeEl.appendChild(button);
      appendPages(page.id, depth + 1, new Set(visited));
    });
  };
  appendPages("root");
};

const wikiGraphLayout = (wiki) => {
  const claims = new Map((wiki.graph?.nodes || []).map(claim => [claim.id, claim]));
  const edges = (wiki.graph?.edges || []).filter(edge => claims.has(edge.subject_claim_id)
    && claims.has(edge.object_claim_id) && edge.subject_claim_id !== edge.object_claim_id
    && ["supports", "contradicts", "related"].includes(edge.relation_type))
    .map(edge => ({from: edge.subject_claim_id, to: edge.object_claim_id, type: edge.relation_type, rationale: edge.rationale || ""}));
  const adjacency = new Map([...claims.keys()].map(id => [id, new Set()]));
  edges.forEach(edge => { adjacency.get(edge.from).add(edge.to); adjacency.get(edge.to).add(edge.from); });
  const visited = new Set(), groups = [];
  [...claims.keys()].sort().forEach(seed => {
    if (visited.has(seed) || !adjacency.get(seed).size) return;
    const ids = [seed]; visited.add(seed);
    for (let i = 0; i < ids.length; i++) [...adjacency.get(ids[i])].sort().forEach(id => {
      if (!visited.has(id)) { visited.add(id); ids.push(id); }
    });
    const nodes = ids.map((id, i) => {
      const angle = i * 2.399963229728653, radius = 65 * Math.sqrt(i);
      return {id, item: claims.get(id), x: Math.cos(angle) * radius * 1.8, y: Math.sin(angle) * radius};
    });
    const byId = new Map(nodes.map(node => [node.id, node]));
    const links = edges.filter(edge => byId.has(edge.from));
    // A bounded, deterministic simulation. Hover never restarts it.
    for (let iteration = 0; iteration < 140; iteration++) {
      const forces = new Map(nodes.map(node => [node.id, {x: -node.x * 0.001, y: -node.y * 0.001}]));
      const cells = new Map();
      nodes.forEach(node => {
        const key = Math.floor(node.x / 220) + ":" + Math.floor(node.y / 100);
        if (!cells.has(key)) cells.set(key, []);
        cells.get(key).push(node);
      });
      nodes.forEach(a => {
        const cx = Math.floor(a.x / 220), cy = Math.floor(a.y / 100);
        for (let x = cx - 1; x <= cx + 1; x++) for (let y = cy - 1; y <= cy + 1; y++) {
          (cells.get(x + ":" + y) || []).forEach(b => {
            if (a.id >= b.id) return;
            const dx = b.x - a.x, dy = b.y - a.y;
            const ox = 190 - Math.abs(dx), oy = 62 - Math.abs(dy);
            if (ox <= 0 || oy <= 0) return;
            const fa = forces.get(a.id), fb = forces.get(b.id);
            if (ox / 190 < oy / 62) {
              const push = (dx >= 0 ? 1 : -1) * ox * 0.3;
              fa.x -= push; fb.x += push;
            } else {
              const push = (dy >= 0 ? 1 : -1) * oy * 0.3;
              fa.y -= push; fb.y += push;
            }
          });
        }
      });
      links.forEach(edge => {
        const a = byId.get(edge.from), b = byId.get(edge.to);
        const dx = b.x - a.x, dy = b.y - a.y, distance = Math.hypot(dx, dy) || 1;
        const pull = (distance - 185) * 0.012;
        forces.get(a.id).x += dx / distance * pull; forces.get(a.id).y += dy / distance * pull;
        forces.get(b.id).x -= dx / distance * pull; forces.get(b.id).y -= dy / distance * pull;
      });
      nodes.forEach(node => {
        const force = forces.get(node.id);
        node.x += Math.max(-18, Math.min(18, force.x));
        node.y += Math.max(-18, Math.min(18, force.y));
      });
    }
    // Resolve any residual label collisions without a running animation.
    const placed = [];
    nodes.forEach(node => {
      while (placed.some(other => Math.abs(node.x - other.x) < 180 && Math.abs(node.y - other.y) < 44)) node.y += 46;
      placed.push(node);
    });
    const minX = Math.min(...nodes.map(node => node.x)), minY = Math.min(...nodes.map(node => node.y));
    nodes.forEach(node => { node.x -= minX; node.y -= minY; });
    groups.push({nodes, width: Math.max(...nodes.map(node => node.x)) + 180, height: Math.max(...nodes.map(node => node.y)) + 44});
  });
  groups.sort((a, b) => b.nodes.length - a.nodes.length);
  const shelfWidth = Math.max(650, Math.sqrt(groups.reduce((sum, group) => sum + (group.width + 80) * (group.height + 80), 0)) * 1.3);
  let x = 36, y = 36, rowHeight = 0;
  const nodes = [];
  groups.forEach(group => {
    if (x > 36 && x + group.width > shelfWidth) { x = 36; y += rowHeight + 90; rowHeight = 0; }
    group.nodes.forEach(node => nodes.push({...node, x: node.x + x, y: node.y + y}));
    x += group.width + 100; rowHeight = Math.max(rowHeight, group.height);
  });
  return {nodes, edges, groupCount: groups.length,
    isolated: [...claims.values()].filter(claim => !adjacency.get(claim.id).size),
    width: Math.max(400, ...nodes.map(node => node.x + 210)),
    height: Math.max(240, ...nodes.map(node => node.y + 80))};
};

const wikiGraphOptions = {page: "", types: new Set(["supports", "contradicts", "related"]), selected: "", focused: false};
let wikiGraphResizeObserver = null;
const renderWikiGraph = () => {
  wikiGraphResizeObserver?.disconnect();
  wikiGraphEl.replaceChildren();
  const options = wikiGraphOptions;
  const pages = wikiState.pages || [];
  if (!pages.some(page => page.id === options.page)) options.page = "";
  const page = pages.find(page => page.id === options.page);
  const included = page ? new Set(page.claim_ids || []) : null;
  const claims = (wikiState.graph?.nodes || []).filter(claim => !included || included.has(claim.id));
  const edges = (wikiState.graph?.edges || []).filter(edge => options.types.has(edge.relation_type));
  const graph = wikiGraphLayout({graph: {nodes: claims, edges}});
  if (!claims.some(claim => claim.id === options.selected)) { options.selected = ""; options.focused = false; }
  const toolbar = document.createElement("div"); toolbar.className = "wiki-graph-controls";
  const pageLabel = document.createElement("label"); pageLabel.textContent = "Page";
  const filter = document.createElement("select"); filter.setAttribute("aria-label", "Filter Graph by Page");
  filter.appendChild(new Option("All Claims", ""));
  pages.forEach(page => filter.appendChild(new Option(page.title, page.id)));
  filter.value = options.page;
  filter.addEventListener("change", () => { options.page = filter.value; options.selected = ""; options.focused = false; renderWikiGraph(); });
  pageLabel.appendChild(filter); toolbar.appendChild(pageLabel);
  const button = (text, action) => {
    const item = document.createElement("button"); item.type = "button"; item.className = "reader-toolbar-btn";
    item.textContent = text; item.addEventListener("click", action); return item;
  };
  const info = document.createElement("p"); info.className = "wiki-graph-description";
  info.textContent = `${claims.length} Claims · ${graph.edges.length} relations · ${graph.groupCount} connected groups`;
  const viewport = document.createElement("div"); viewport.className = "wiki-graph-canvas";
  const isMac = /Mac|iPhone|iPad/i.test(navigator.userAgentData?.platform || navigator.platform || "");
  const zoomHint = `Pinch or ${isMac ? "Cmd" : "Ctrl"} + scroll to zoom.`;
  viewport.setAttribute("aria-label", `Claim relations. Drag to pan. ${zoomHint}`);
  const surface = document.createElement("div"); surface.className = "wiki-graph-surface";
  surface.style.width = `${graph.width}px`; surface.style.height = `${graph.height}px`;
  const tooltip = document.createElement("div"); tooltip.className = "wiki-graph-tooltip"; tooltip.hidden = true;
  viewport.append(surface, tooltip);
  const details = document.createElement("section"); details.className = "wiki-graph-detail";
  details.setAttribute("aria-live", "polite");
  const positions = new Map(graph.nodes.map(node => [node.id, node]));
  if (!positions.has(options.selected)) options.focused = false;
  const nodeElements = new Map(), edgeElements = [];
  let scale = 1, tx = 0, ty = 0;
  const transform = () => { surface.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`; };
  const neighborhood = () => {
    const ids = new Set([options.selected]);
    graph.edges.forEach(edge => { if (edge.from === options.selected) ids.add(edge.to); if (edge.to === options.selected) ids.add(edge.from); });
    return ids;
  };
  const fit = () => {
    const visible = graph.nodes.filter(node => !options.focused || neighborhood().has(node.id));
    if (!visible.length) return;
    const x = Math.min(...visible.map(node => node.x)) - 25, y = Math.min(...visible.map(node => node.y)) - 25;
    const width = Math.max(...visible.map(node => node.x + 180)) - x + 25;
    const height = Math.max(...visible.map(node => node.y + 36)) - y + 25;
    scale = Math.max(0.15, Math.min(1.35, (viewport.clientWidth - 32) / width, (viewport.clientHeight - 32) / height));
    tx = (viewport.clientWidth - width * scale) / 2 - x * scale;
    ty = (viewport.clientHeight - height * scale) / 2 - y * scale;
    transform();
  };
  const zoom = (factor, x = viewport.clientWidth / 2, y = viewport.clientHeight / 2) => {
    const next = Math.max(0.15, Math.min(3, scale * factor)), ratio = next / scale;
    tx = x - (x - tx) * ratio; ty = y - (y - ty) * ratio; scale = next; transform();
  };
  toolbar.append(button("−", () => zoom(0.8)), button("+", () => zoom(1.25)), button("Fit", fit));
  toolbar.children[1].setAttribute("aria-label", "Zoom out");
  toolbar.children[2].setAttribute("aria-label", "Zoom in");
  const focus = button("Focus selected", () => { options.focused = !options.focused; updateSelection(); fit(); });
  const clear = button("Clear selection", () => { options.selected = ""; options.focused = false; updateSelection(); fit(); });
  toolbar.append(focus, clear);
  const updateSelection = () => {
    const neighbors = neighborhood(), selected = claims.find(claim => claim.id === options.selected);
    focus.disabled = !selected || !positions.has(selected.id);
    focus.textContent = options.focused ? "Show all" : "Focus selected";
    focus.setAttribute("aria-pressed", String(options.focused)); clear.disabled = !selected;
    nodeElements.forEach((node, id) => {
      node.classList.toggle("is-selected", id === options.selected);
      node.classList.toggle("is-dimmed", Boolean(selected) && !neighbors.has(id));
      node.hidden = options.focused && !neighbors.has(id);
      node.setAttribute("aria-pressed", String(id === options.selected));
    });
    edgeElements.forEach(({element, edge}) => {
      const active = edge.from === options.selected || edge.to === options.selected;
      element.classList.toggle("is-dimmed", Boolean(selected) && !active);
      element.style.display = options.focused && !active ? "none" : "";
    });
    details.replaceChildren();
    const heading = document.createElement("strong"); heading.textContent = selected ? "Selected Claim" : "Explore connections";
    const text = document.createElement("p");
    if (selected) renderEvidenceText(text, selected.statement);
    else text.textContent = `Select a node to read its Claim and inspect its immediate connections. Click it again to deselect. Drag the canvas to pan. ${zoomHint}`;
    details.append(heading, text);
    if (selected) {
      details.appendChild(button("Open in Claims →", () => openClaimFromWiki(selected.id)));
      const list = document.createElement("div"); list.className = "wiki-graph-neighbors";
      graph.edges.filter(edge => edge.from === selected.id || edge.to === selected.id).forEach(edge => {
        const otherId = edge.from === selected.id ? edge.to : edge.from;
        const other = claims.find(claim => claim.id === otherId);
        const entry = button(`${edge.type} ${edge.type === "related" ? "↔" : edge.from === selected.id ? "→" : "←"} ${other.statement}`, () => select(other.id));
        entry.title = edge.rationale || other.statement; entry.dataset.relation = edge.type; list.appendChild(entry);
      });
      if (!list.children.length) { const note = document.createElement("small"); note.textContent = "No visible relations under the current filters."; list.appendChild(note); }
      details.appendChild(list);
    }
  };
  const select = id => {
    const wasFocused = options.focused;
    if (options.selected === id) { options.selected = ""; options.focused = false; }
    else options.selected = id;
    tooltip.hidden = true; updateSelection();
    if (wasFocused) fit();
  };
  const createNode = (claim, floating = false) => {
    const node = button("", () => select(claim.id)); node.className = "wiki-graph-node";
    node.dataset.nodeId = claim.id;
    const dot = document.createElement("i"); dot.setAttribute("aria-hidden", "true");
    const label = document.createElement("span"); label.textContent = claim.statement;
    node.append(dot, label); node.setAttribute("aria-label", claim.statement);
    if (floating) node.title = claim.statement;
    if (floating) node.classList.add("is-unconnected");
    node.addEventListener("pointerenter", () => { renderEvidenceText(tooltip, claim.statement); tooltip.hidden = false; });
    node.addEventListener("pointerleave", () => { tooltip.hidden = true; });
    node.addEventListener("focus", () => { renderEvidenceText(tooltip, claim.statement); tooltip.hidden = false; });
    node.addEventListener("blur", () => { tooltip.hidden = true; });
    nodeElements.set(claim.id, node); return node;
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${graph.width} ${graph.height}`); svg.setAttribute("aria-hidden", "true");
  const defs = document.createElementNS(svg.namespaceURI, "defs");
  ["supports", "contradicts"].forEach(type => {
    const marker = document.createElementNS(svg.namespaceURI, "marker");
    marker.id = `wiki-arrow-${type}`;
    Object.entries({viewBox:"0 0 10 10",refX:"9",refY:"5",markerWidth:"7",markerHeight:"7",orient:"auto"}).forEach(([key,value]) => marker.setAttribute(key,value));
    const arrow = document.createElementNS(svg.namespaceURI, "path"); arrow.setAttribute("d","M 0 0 L 10 5 L 0 10 z");
    marker.appendChild(arrow); defs.appendChild(marker);
  });
  svg.appendChild(defs);
  graph.edges.forEach(edge => {
    const a = positions.get(edge.from), b = positions.get(edge.to);
    const dx = b.x - a.x, dy = b.y - a.y, length = Math.hypot(dx,dy) || 1;
    const x1 = a.x + 10 + dx / length * 9, y1 = a.y + 18 + dy / length * 9;
    const x2 = b.x + 10 - dx / length * 11, y2 = b.y + 18 - dy / length * 11;
    const path = document.createElementNS(svg.namespaceURI, "path");
    const bend = edge.type === "supports" ? 16 : edge.type === "contradicts" ? -16 : 0;
    path.setAttribute("d", `M ${x1} ${y1} Q ${(x1+x2)/2-dy/length*bend} ${(y1+y2)/2+dx/length*bend} ${x2} ${y2}`);
    path.classList.add("wiki-graph-edge"); path.dataset.relation = edge.type;
    if (edge.type !== "related") path.setAttribute("marker-end", `url(#wiki-arrow-${edge.type})`);
    svg.appendChild(path); edgeElements.push({element:path,edge});
  });
  surface.appendChild(svg);
  graph.nodes.forEach(node => {
    const element = createNode(node.item); element.style.left = `${node.x}px`; element.style.top = `${node.y}px`; surface.appendChild(element);
  });
  let drag = null;
  viewport.addEventListener("pointerdown", event => {
    if (event.button !== 0 || event.target.closest("button")) return;
    drag = {x:event.clientX,y:event.clientY,tx,ty}; tooltip.hidden = true;
    viewport.setPointerCapture(event.pointerId); viewport.classList.add("is-dragging");
  });
  viewport.addEventListener("pointermove", event => {
    if (!drag) return; tx = drag.tx + event.clientX - drag.x; ty = drag.ty + event.clientY - drag.y; transform();
  });
  const release = () => { drag = null; viewport.classList.remove("is-dragging"); };
  viewport.addEventListener("pointerup", release); viewport.addEventListener("pointercancel", release);
  viewport.addEventListener("wheel", event => {
    // Trackpad pinch is delivered as a Ctrl-wheel event by browsers.
    if (!event.ctrlKey && !(isMac && event.metaKey)) return;
    event.preventDefault(); const rect = viewport.getBoundingClientRect();
    zoom(Math.exp(-event.deltaY * 0.002), event.clientX - rect.left, event.clientY - rect.top);
  }, {passive:false});
  const legend = document.createElement("div"); legend.className = "wiki-graph-legend";
  ["supports","contradicts","related"].forEach(type => {
    const label = document.createElement("label"); label.dataset.relation = type;
    const input = document.createElement("input"); input.type = "checkbox"; input.checked = options.types.has(type);
    input.addEventListener("change", () => { input.checked ? options.types.add(type) : options.types.delete(type); renderWikiGraph(); });
    const line = document.createElement("span"); line.textContent = type; line.dataset.relation = type;
    label.append(input,line); legend.appendChild(label);
  });
  wikiGraphEl.append(toolbar, info, legend);
  if (graph.nodes.length) wikiGraphEl.appendChild(viewport);
  else { const empty = document.createElement("p"); empty.className = "wiki-graph-description"; empty.textContent = claims.length ? "No relations under these filters. Claims are listed below." : "No Claims in this scope."; wikiGraphEl.appendChild(empty); }
  wikiGraphEl.appendChild(details);
  if (graph.isolated.length) {
    const section = document.createElement("details"); section.className = "wiki-graph-unconnected"; section.open = !graph.nodes.length;
    const heading = document.createElement("summary"); heading.textContent = `Unconnected · ${graph.isolated.length}`;
    const grid = document.createElement("div"); grid.className = "wiki-graph-isolated";
    graph.isolated.forEach(claim => grid.appendChild(createNode(claim,true)));
    section.append(heading,grid); wikiGraphEl.appendChild(section);
  }
  updateSelection();
  if (graph.nodes.length) {
    wikiGraphResizeObserver = new ResizeObserver(fit); wikiGraphResizeObserver.observe(viewport);
    requestAnimationFrame(fit);
  }
};

const wikiPatchScopeClaims = (proposal) => {
  const scoped = Array.isArray(proposal.scope?.claim_ids)
    ? new Set([...proposal.scope.claim_ids, ...(proposal.payload.pages || []).flatMap(page => page.claim_ids || [])]) : null;
  return wikiState.claims.filter((claim) => claim.lifecycle === "active"
    && (!scoped || scoped.has(claim.id)));
};

// Bound local Wiki requests, including reading the response body. Model calls
// use their separately configured timeout and must not use this helper.
const fetchWikiLocal = async (url, options = {}) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const body = await response.json();
    return { ok: response.ok, json: async () => body };
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error(`Wiki request timed out: ${url}. Reload Wiki to check its current state before retrying changes.`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
};

const persistWikiProposal = async (proposal, rerender = true) => {
  wikiRefreshVersion++;
  wikiStatusEl.textContent = "Saving Wiki Patch draft…";
  try {
    const response = await fetchWikiLocal(`/api/wiki/proposals/${encodeURIComponent(proposal.id)}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(proposal.payload),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      wikiStatusEl.textContent = body.message || "Could not save the Wiki Patch draft.";
      return false;
    }
    const index = wikiProposals.findIndex((item) => item.id === proposal.id);
    body._dirty = false;
    wikiRefreshVersion++;
    if (index >= 0) wikiProposals[index] = body;
    wikiStatusEl.textContent = "Wiki Patch draft saved.";
    if (rerender) renderWikiProposals();
    return true;
  } catch (error) {
    wikiStatusEl.textContent = error.message || "Could not save the Wiki Patch draft.";
    return false;
  }
};

const sendWikiPatchDecision = async (proposalId, accepted) => {
  wikiRefreshVersion++;
  const response = await fetchWikiLocal(`/api/wiki/proposals/${encodeURIComponent(proposalId)}${accepted ? "/accept" : ""}`, {method: accepted ? "POST" : "DELETE"});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || `Could not ${accepted ? "apply" : "discard"} the Wiki Patch.`);
  wikiRefreshVersion++;
  if (accepted) wikiState = body;
  wikiProposals = wikiProposals.filter(item => item.id !== proposalId);
  activeWikiProposalPageKeys.delete(proposalId);
  reviewState("wiki").selected.delete(proposalId);
  if (activeWikiProposalId === proposalId) activeWikiProposalId = "";
};

const renderWikiProposals = () => {
  wikiProposalListEl.replaceChildren();
  if (!wikiProposals.length) {
    activeWikiProposalId = "";
    const empty = document.createElement("div"); empty.className = "wiki-empty";
    empty.textContent = "No Wiki Patches are awaiting review.";
    wikiProposalListEl.appendChild(empty);
    return;
  }
  if (!wikiProposals.some((proposal) => proposal.id === activeWikiProposalId)) {
    activeWikiProposalId = wikiProposals[0].id;
  }
  const batch = createReviewBatchBar("wiki", wikiProposals, async (proposal, accepted) => {
    if (accepted && !proposal.payload?.pages?.length) throw new Error("No Pages remain. Use Reset to start over.");
    if (accepted && proposal._dirty && !(await persistWikiProposal(proposal, false))) throw new Error("Could not save edited Wiki draft");
    await sendWikiPatchDecision(proposal.id, accepted);
  }, async fetchData => {
    if (!fetchData) { renderWikiProposals(); return; }
    renderWiki();
    if (currentReviewContext() === "views") renderReviewWorkspace();
  }, wikiStatusEl, {singleAccept: true});
  wikiProposalListEl.append(batch.bar);
  wikiProposals.forEach((proposal) => {
    const card = document.createElement("article");
    card.className = "wiki-proposal-card";
    addReviewSelection(card, proposal, batch.state, batch.update);
    if (proposal.id !== activeWikiProposalId) {
      const compact = document.createElement("div"); compact.className = "wiki-patch-compact";
      const copy = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = proposal.scope?.origin === "manual" ? "Manual structure draft" : "AI-proposed Wiki Patch";
      const note = document.createElement("small");
      note.textContent = `${proposal.payload.pages?.length || 0} Pages · ${proposal.model || "No model"}`;
      copy.append(title, note);
      const open = document.createElement("button"); open.type = "button";
      open.className = "semantic-action is-navigate"; open.textContent = "Review & edit";
      open.addEventListener("click", () => { activeWikiProposalId = proposal.id; renderWikiProposals(); });
      compact.append(copy, open); card.appendChild(compact); wikiProposalListEl.appendChild(card);
      return;
    }

    const pages = proposal.payload.pages || [];
    const pageByKey = new Map(pages.map((page) => [page.key, page]));
    const assignedIds = new Set(pages.flatMap((page) => page.claim_ids || []));
    const scopeClaims = wikiPatchScopeClaims(proposal);
    const unorganizedClaims = scopeClaims.filter((claim) => !assignedIds.has(claim.id));
    let selectedKey = activeWikiProposalPageKeys.get(proposal.id);
    if (selectedKey !== "__unorganized__" && !pageByKey.has(selectedKey)) {
      selectedKey = pages[0]?.key || "__unorganized__";
    }
    activeWikiProposalPageKeys.set(proposal.id, selectedKey);
    const selectedPage = pageByKey.get(selectedKey);
    let saveDraftButton = null;
    const markDirty = () => {
      proposal._dirty = true;
      if (saveDraftButton) saveDraftButton.disabled = false;
    };
    const selectPage = (key) => {
      activeWikiProposalPageKeys.set(proposal.id, key); renderWikiProposals();
    };

    const editorHead = document.createElement("div"); editorHead.className = "wiki-patch-editor-head";
    const headCopy = document.createElement("div");
    const headTitle = document.createElement("strong");
    headTitle.textContent = proposal.scope?.origin === "manual" ? "Manual structure draft" : "AI-proposed Wiki Patch";
    const headNote = document.createElement("small");
    headNote.textContent = "Adjust structure only. Claim content remains managed in Claims.";
    headCopy.append(headTitle, headNote);
    const dirty = document.createElement("span"); dirty.className = "wiki-patch-dirty";
    dirty.textContent = proposal._dirty ? "Unsaved changes" : "Draft saved";
    editorHead.append(headCopy, dirty);

    const editor = document.createElement("div"); editor.className = "wiki-patch-editor";
    const treePanel = document.createElement("aside"); treePanel.className = "wiki-patch-tree";
    const treeHead = document.createElement("div"); treeHead.className = "wiki-patch-tree-head";
    const treeLabel = document.createElement("strong"); treeLabel.textContent = "Pages";
    const addPage = document.createElement("button"); addPage.type = "button";
    addPage.className = "semantic-action is-edit"; addPage.textContent = "＋ Page";
    addPage.addEventListener("click", () => {
      const key = `page-${Date.now().toString(36)}`;
      pages.push({key, title: "Untitled Page", parent_key: "", summary: "", claim_ids: []});
      activeWikiProposalPageKeys.set(proposal.id, key); markDirty(); renderWikiProposals();
    });
    treeHead.append(treeLabel, addPage); treePanel.appendChild(treeHead);
    const tree = document.createElement("div"); tree.className = "wiki-patch-page-tree";
    const children = new Map();
    pages.forEach((page) => {
      const parent = page.parent_key || "root";
      if (!children.has(parent)) children.set(parent, []);
      children.get(parent).push(page);
    });
    const movePage = (page, direction) => {
      const siblings = pages.filter((item) => (item.parent_key || "") === (page.parent_key || ""));
      const siblingIndex = siblings.findIndex((item) => item.key === page.key);
      const target = siblings[siblingIndex + direction];
      if (!target) return;
      const from = pages.indexOf(page); const to = pages.indexOf(target);
      [pages[from], pages[to]] = [pages[to], pages[from]];
      markDirty(); renderWikiProposals();
    };
    const pageDescendants = (pageKey) => {
      const descendants = new Set();
      const visit = (key) => pages.filter((page) => page.parent_key === key).forEach((page) => {
        if (descendants.has(page.key)) return;
        descendants.add(page.key); visit(page.key);
      });
      visit(pageKey); return descendants;
    };
    const moveClaimToPage = (claimId, pageKey, index = null, anchorClaimId = "", afterAnchor = false) => {
      pages.forEach((page) => {
        page.claim_ids = (page.claim_ids || []).filter((id) => id !== claimId);
      });
      const targetPage = pageByKey.get(pageKey);
      if (targetPage) {
        const anchorIndex = anchorClaimId ? targetPage.claim_ids.indexOf(anchorClaimId) : -1;
        const requestedIndex = anchorIndex >= 0 ? anchorIndex + (afterAnchor ? 1 : 0) : index;
        const destination = requestedIndex === null
          ? targetPage.claim_ids.length : Math.max(0, Math.min(requestedIndex, targetPage.claim_ids.length));
        targetPage.claim_ids.splice(destination, 0, claimId);
      }
      draggedWikiPatchClaimId = "";
      markDirty(); renderWikiProposals();
    };
    const dropPage = (targetPage, position) => {
      const draggedPage = pageByKey.get(draggedWikiPatchPageKey);
      if (!draggedPage || draggedPage.key === targetPage.key
          || pageDescendants(draggedPage.key).has(targetPage.key)) return;
      pages.splice(pages.indexOf(draggedPage), 1);
      const targetIndex = pages.indexOf(targetPage);
      if (position === "inside") {
        draggedPage.parent_key = targetPage.key;
        pages.splice(targetIndex + 1, 0, draggedPage);
      } else {
        draggedPage.parent_key = targetPage.parent_key || "";
        pages.splice(targetIndex + (position === "after" ? 1 : 0), 0, draggedPage);
      }
      draggedWikiPatchPageKey = "";
      markDirty(); renderWikiProposals();
    };
    const appendTree = (parentKey, depth = 0) => {
      (children.get(parentKey) || []).forEach((page) => {
        const row = document.createElement("div"); row.className = "wiki-patch-tree-row";
        row.style.setProperty("--patch-depth", depth);
        const handle = document.createElement("span"); handle.className = "wiki-patch-drag-handle";
        handle.textContent = "⠿"; handle.title = "Drag to reorder or nest this Page"; handle.draggable = true;
        handle.addEventListener("dragstart", (event) => {
          draggedWikiPatchPageKey = page.key; draggedWikiPatchClaimId = "";
          event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", `page:${page.key}`);
        });
        handle.addEventListener("dragend", () => { draggedWikiPatchPageKey = ""; });
        const choose = document.createElement("button"); choose.type = "button";
        choose.className = "wiki-patch-page-choice";
        choose.classList.toggle("is-active", selectedKey === page.key);
        choose.textContent = page.title; choose.title = page.title;
        choose.addEventListener("click", () => selectPage(page.key));
        const count = document.createElement("small"); count.textContent = String(page.claim_ids?.length || 0);
        const clearDropState = () => {
          row.classList.remove("drop-before", "drop-inside", "drop-after");
        };
        row.addEventListener("dragover", (event) => {
          if (!draggedWikiPatchPageKey && !draggedWikiPatchClaimId) return;
          if (draggedWikiPatchPageKey
              && (draggedWikiPatchPageKey === page.key
                || pageDescendants(draggedWikiPatchPageKey).has(page.key))) return;
          event.preventDefault(); event.dataTransfer.dropEffect = "move"; clearDropState();
          if (draggedWikiPatchClaimId) {
            row.classList.add("drop-inside");
          } else {
            const rect = row.getBoundingClientRect();
            const ratio = (event.clientY - rect.top) / Math.max(1, rect.height);
            row.classList.add(ratio < 0.28 ? "drop-before" : ratio > 0.72 ? "drop-after" : "drop-inside");
          }
        });
        row.addEventListener("dragleave", (event) => {
          if (!row.contains(event.relatedTarget)) clearDropState();
        });
        row.addEventListener("drop", (event) => {
          event.preventDefault();
          const position = row.classList.contains("drop-before") ? "before"
            : row.classList.contains("drop-after") ? "after" : "inside";
          clearDropState();
          if (draggedWikiPatchClaimId) moveClaimToPage(draggedWikiPatchClaimId, page.key);
          else dropPage(page, position);
        });
        row.append(handle, choose, count); tree.appendChild(row); appendTree(page.key, depth + 1);
      });
    };
    appendTree("root");
    const unorganized = document.createElement("button"); unorganized.type = "button";
    unorganized.className = "wiki-patch-unorganized";
    unorganized.classList.toggle("is-active", selectedKey === "__unorganized__");
    unorganized.textContent = `Unorganized · ${unorganizedClaims.length}`;
    unorganized.addEventListener("click", () => selectPage("__unorganized__"));
    unorganized.addEventListener("dragover", (event) => {
      if (!draggedWikiPatchClaimId) return;
      event.preventDefault(); unorganized.classList.add("drop-inside");
    });
    unorganized.addEventListener("dragleave", () => unorganized.classList.remove("drop-inside"));
    unorganized.addEventListener("drop", (event) => {
      if (!draggedWikiPatchClaimId) return;
      event.preventDefault(); unorganized.classList.remove("drop-inside");
      moveClaimToPage(draggedWikiPatchClaimId, "");
    });
    tree.appendChild(unorganized); treePanel.appendChild(tree);

    const detail = document.createElement("section"); detail.className = "wiki-patch-detail";
    if (selectedPage) {
      const siblings = pages.filter((page) => (page.parent_key || "") === (selectedPage.parent_key || ""));
      const siblingIndex = siblings.findIndex((page) => page.key === selectedPage.key);
      const structureActions = document.createElement("div"); structureActions.className = "wiki-patch-structure-actions";
      const addChild = document.createElement("button"); addChild.type = "button";
      addChild.className = "semantic-action is-edit"; addChild.textContent = "＋ Child Page";
      addChild.addEventListener("click", () => {
        const key = `page-${Date.now().toString(36)}`;
        pages.push({key, title: "Untitled Page", parent_key: selectedPage.key, summary: "", claim_ids: []});
        activeWikiProposalPageKeys.set(proposal.id, key); markDirty(); renderWikiProposals();
      });
      const pageUp = document.createElement("button"); pageUp.type = "button";
      pageUp.className = "semantic-action is-navigate"; pageUp.textContent = "↑ Move up";
      pageUp.disabled = siblingIndex <= 0; pageUp.addEventListener("click", () => movePage(selectedPage, -1));
      const pageDown = document.createElement("button"); pageDown.type = "button";
      pageDown.className = "semantic-action is-navigate"; pageDown.textContent = "↓ Move down";
      pageDown.disabled = siblingIndex < 0 || siblingIndex >= siblings.length - 1;
      pageDown.addEventListener("click", () => movePage(selectedPage, 1));
      const makeChild = document.createElement("button"); makeChild.type = "button";
      makeChild.className = "semantic-action is-edit"; makeChild.textContent = "→ Indent";
      makeChild.disabled = siblingIndex <= 0;
      makeChild.title = "Nest under the previous Page at this level";
      makeChild.addEventListener("click", () => {
        if (siblingIndex <= 0) return;
        selectedPage.parent_key = siblings[siblingIndex - 1].key;
        markDirty(); renderWikiProposals();
      });
      const promote = document.createElement("button"); promote.type = "button";
      promote.className = "semantic-action is-edit"; promote.textContent = "← Outdent";
      promote.disabled = !selectedPage.parent_key;
      promote.title = "Move up one hierarchy level";
      promote.addEventListener("click", () => {
        const parent = pageByKey.get(selectedPage.parent_key);
        selectedPage.parent_key = parent?.parent_key || "";
        markDirty(); renderWikiProposals();
      });
      structureActions.append(addChild, pageUp, pageDown, makeChild, promote);
      detail.appendChild(structureActions);
      const fields = document.createElement("div"); fields.className = "wiki-patch-fields";
      const titleField = document.createElement("label"); titleField.textContent = "Page title";
      const titleInput = document.createElement("input"); titleInput.maxLength = 200; titleInput.value = selectedPage.title;
      titleInput.addEventListener("input", () => { selectedPage.title = titleInput.value; markDirty(); dirty.textContent = "Unsaved changes"; });
      titleField.appendChild(titleInput);
      const parentField = document.createElement("label"); parentField.textContent = "Parent Page";
      const parentSelect = document.createElement("select");
      const descendants = new Set();
      const collectDescendants = (key) => (children.get(key) || []).forEach((item) => { descendants.add(item.key); collectDescendants(item.key); });
      collectDescendants(selectedPage.key);
      [["", "Top level"], ...pages.filter((page) => page.key !== selectedPage.key && !descendants.has(page.key)).map((page) => [page.key, page.title])]
        .forEach(([value, label]) => { const option = document.createElement("option"); option.value = value; option.textContent = label; option.selected = value === (selectedPage.parent_key || ""); parentSelect.appendChild(option); });
      parentSelect.addEventListener("change", () => { selectedPage.parent_key = parentSelect.value; markDirty(); renderWikiProposals(); });
      parentField.appendChild(parentSelect);
      const summaryField = document.createElement("label"); summaryField.className = "wiki-patch-summary"; summaryField.textContent = "Page summary";
      const summaryInput = document.createElement("textarea"); summaryInput.rows = 3; summaryInput.maxLength = 12000; summaryInput.value = selectedPage.summary || "";
      summaryInput.addEventListener("input", () => { selectedPage.summary = summaryInput.value; markDirty(); dirty.textContent = "Unsaved changes"; });
      summaryField.appendChild(summaryInput); fields.append(titleField, parentField, summaryField); detail.appendChild(fields);
      const summaryPreview = document.createElement("p");
      const previewSummary = () => renderWikiSummary(summaryPreview, selectedPage.summary || "", pages, (home) => selectPage(home.key));
      previewSummary(); summaryInput.addEventListener("input", previewSummary);
      detail.appendChild(summaryPreview);
      const deletePage = document.createElement("button"); deletePage.type = "button";
      deletePage.className = "semantic-action is-destructive wiki-patch-delete-page"; deletePage.textContent = "× Delete Page";
      deletePage.title = "Its Claims will become Unorganized";
      deletePage.addEventListener("click", async () => {
        if (!await confirmAction(`Delete “${selectedPage.title}”? Its Claims will become Unorganized.`)) return;
        pages.forEach((page) => { if (page.parent_key === selectedPage.key) page.parent_key = selectedPage.parent_key || ""; });
        proposal.payload.pages = pages.filter((page) => page.key !== selectedPage.key);
        activeWikiProposalPageKeys.set(proposal.id, proposal.payload.pages[0]?.key || "__unorganized__");
        markDirty(); renderWikiProposals();
      });
      detail.appendChild(deletePage);
    } else {
      const title = document.createElement("div"); title.className = "wiki-patch-unorganized-head";
      title.innerHTML = "<strong>Unorganized Claims</strong><small>Move a Claim into a Page when its canonical placement is clear.</small>";
      detail.appendChild(title);
    }

    const claimList = document.createElement("div"); claimList.className = "wiki-patch-claim-list";
    const visibleIds = selectedPage ? selectedPage.claim_ids : unorganizedClaims.map((claim) => claim.id);
    visibleIds.forEach((claimId, claimIndex) => {
      const claim = scopeClaims.find((item) => item.id === claimId);
      if (!claim) return;
      const row = document.createElement("article"); row.className = "wiki-patch-claim-row";
      const handle = document.createElement("span"); handle.className = "wiki-patch-drag-handle";
      handle.textContent = "⠿"; handle.title = "Drag to move this Claim"; handle.draggable = true;
      handle.addEventListener("dragstart", (event) => {
        draggedWikiPatchClaimId = claim.id; draggedWikiPatchPageKey = "";
        event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", `claim:${claim.id}`);
      });
      handle.addEventListener("dragend", () => { draggedWikiPatchClaimId = ""; });
      const statement = document.createElement("button"); statement.type = "button";
      statement.className = "wiki-patch-claim-statement"; statement.textContent = claim.statement;
      statement.title = "Open this Claim in Claims";
      statement.addEventListener("click", () => openClaimFromWiki(claim.id));
      const controls = document.createElement("div");
      if (selectedPage) {
        const up = document.createElement("button"); up.type = "button"; up.textContent = "↑"; up.title = "Move Claim up"; up.disabled = claimIndex === 0;
        const down = document.createElement("button"); down.type = "button"; down.textContent = "↓"; down.title = "Move Claim down"; down.disabled = claimIndex === visibleIds.length - 1;
        up.addEventListener("click", () => { [selectedPage.claim_ids[claimIndex - 1], selectedPage.claim_ids[claimIndex]] = [selectedPage.claim_ids[claimIndex], selectedPage.claim_ids[claimIndex - 1]]; markDirty(); renderWikiProposals(); });
        down.addEventListener("click", () => { [selectedPage.claim_ids[claimIndex], selectedPage.claim_ids[claimIndex + 1]] = [selectedPage.claim_ids[claimIndex + 1], selectedPage.claim_ids[claimIndex]]; markDirty(); renderWikiProposals(); });
        controls.append(up, down);
      }
      row.addEventListener("dragover", (event) => {
        if (!draggedWikiPatchClaimId || draggedWikiPatchClaimId === claim.id) return;
        event.preventDefault(); event.dataTransfer.dropEffect = "move";
        const rect = row.getBoundingClientRect();
        row.classList.toggle("drop-before", event.clientY < rect.top + rect.height / 2);
        row.classList.toggle("drop-after", event.clientY >= rect.top + rect.height / 2);
      });
      row.addEventListener("dragleave", () => row.classList.remove("drop-before", "drop-after"));
      row.addEventListener("drop", (event) => {
        if (!draggedWikiPatchClaimId || draggedWikiPatchClaimId === claim.id) return;
        event.preventDefault();
        const targetPage = pages.find((page) => page.claim_ids.includes(claim.id));
        if (!targetPage) {
          moveClaimToPage(draggedWikiPatchClaimId, "");
          return;
        }
        const afterTarget = row.classList.contains("drop-after");
        row.classList.remove("drop-before", "drop-after");
        moveClaimToPage(draggedWikiPatchClaimId, targetPage.key, null, claim.id, afterTarget);
      });
      row.append(handle, statement, controls); claimList.appendChild(row);
    });
    if (!visibleIds.length) {
      const empty = document.createElement("p"); empty.className = "wiki-patch-empty"; empty.textContent = "No Claims here."; claimList.appendChild(empty);
    }
    detail.appendChild(claimList); editor.append(treePanel, detail);

    const actions = document.createElement("div"); actions.className = "proposal-actions wiki-patch-actions";
    const actionStatus = document.createElement("small");
    actionStatus.className = "knowledge-status wiki-patch-action-status";
    actionStatus.setAttribute("role", "status");
    actionStatus.textContent = proposal._actionStatus || "";
    if (!pages.length) actionStatus.textContent = "No Pages remain. To start over, use Reset in the Wiki toolbar.";
    const discard = document.createElement("button"); discard.type = "button";
    discard.className = "semantic-action is-destructive"; discard.textContent = "× Discard";
    const save = document.createElement("button"); save.type = "button";
    save.className = "semantic-action is-edit"; save.textContent = "Save draft"; save.disabled = !proposal._dirty;
    saveDraftButton = save;
    const accept = document.createElement("button"); accept.type = "button";
    accept.className = "semantic-action is-accept"; accept.textContent = "✓ Apply Wiki Patch";
    accept.disabled = pages.length === 0;
    save.disabled = !proposal._dirty || pages.length === 0;
    const runAction = async (action, progress) => {
      if (batch.state.busy) return;
      batch.state.busy = true;
      actionStatus.textContent = progress;
      wikiStatusEl.textContent = progress;
      const controls = [...wikiProposalListEl.querySelectorAll("button, input, select, textarea")];
      const previous = controls.map(control => control.disabled);
      controls.forEach(control => { control.disabled = true; });
      try { await action(); }
      catch (error) { wikiStatusEl.textContent = error.message || "Could not update Wiki Patch."; }
      finally {
        batch.state.busy = false;
        const remaining = wikiProposals.find(item => item.id === proposal.id);
        if (remaining) remaining._actionStatus = wikiStatusEl.textContent;
        controls.forEach((control, index) => { control.disabled = previous[index]; });
        batch.update();
        if (!wikiProposalReviewEl.hidden) renderWikiProposals();
      }
    };
    discard.addEventListener("click", () => runAction(() => discardWikiProposal(proposal.id), "Discarding Wiki Patch…"));
    save.addEventListener("click", () => runAction(() => persistWikiProposal(proposal), "Saving Wiki Patch draft…"));
    accept.addEventListener("click", () => runAction(async () => {
      if (proposal._dirty && !(await persistWikiProposal(proposal, false))) return;
      await acceptWikiProposal(proposal.id);
    }, "Applying Wiki Patch…"));
    actions.append(discard, save, accept);
    card.append(editorHead, editor, actionStatus, actions); wikiProposalListEl.appendChild(card);
  });
};

const renderWikiImports = () => {
  wikiImportListEl.replaceChildren();
  const batch = createReviewBatchBar("wiki-import", wikiImports,
    (item, accepted) => sendReviewDecision(`/api/wiki/imports/${encodeURIComponent(item.id)}`, accepted),
    async fetchData => fetchData ? Promise.all([fetchLibrary(), fetchEvidenceLibrary(), fetchClaims(), fetchWiki()]) : renderWikiImports(), wikiStatusEl);
  if (wikiImports.length) wikiImportListEl.append(batch.bar);
  wikiImports.forEach((item) => {
    const card = document.createElement("article"); card.className = "wiki-proposal-card";
    addReviewSelection(card, item, batch.state, batch.update);
    const title = document.createElement("strong"); title.textContent = item.filename || "Shared Wiki";
    const counts = item.summary?.counts || {};
    const summary = document.createElement("p");
    summary.textContent = `${counts.sources || 0} Sources · ${counts.evidence || 0} Evidence · ${counts.claims || 0} Claims`;
    const note = document.createElement("small");
    note.textContent = "Accepting trusts this complete Wiki package, deduplicates its Items, and merges its page tree into the global Wiki.";
    const actions = document.createElement("div"); actions.className = "proposal-actions";
    const discard = document.createElement("button");
    discard.type = "button"; discard.className = "semantic-action is-destructive"; discard.textContent = "× Discard";
    discard.addEventListener("click", async () => {
      const response = await fetch(`/api/wiki/imports/${encodeURIComponent(item.id)}`, { method: "DELETE" });
      if (!response.ok) { wikiStatusEl.textContent = "Could not discard Wiki import."; return; }
      await fetchWiki(); wikiStatusEl.textContent = "Wiki import discarded.";
    });
    const accept = document.createElement("button");
    accept.type = "button"; accept.className = "semantic-action is-accept"; accept.textContent = "✓ Accept Wiki";
    accept.addEventListener("click", async () => {
      accept.disabled = true; wikiStatusEl.textContent = "Importing trusted Wiki…";
      const response = await fetch(`/api/wiki/imports/${encodeURIComponent(item.id)}/accept`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) { accept.disabled = false; wikiStatusEl.textContent = body.message || "Could not import Wiki."; return; }
      await Promise.all([fetchLibrary(), fetchEvidenceLibrary(), fetchClaims(), fetchWiki()]);
      wikiStatusEl.textContent = `Wiki imported: ${body.created.claims} new Claims, ${body.reused.claims} reused.`;
    });
    actions.append(discard, accept); card.append(title, summary, note, actions); wikiImportListEl.appendChild(card);
  });
  if (!wikiImports.length) {
    const empty = document.createElement("div"); empty.className = "wiki-empty";
    empty.textContent = "No Wiki imports are awaiting review."; wikiImportListEl.appendChild(empty);
  }
};

const renderWiki = () => {
  if (!wikiProposals.length) {
    activeWikiProposalId = "";
    wikiProposalReviewEl.hidden = true;
  }
  const activeSpecialPageExists = activeWikiPageId === "__unorganized__"
    ? Boolean(wikiState.unorganized_claim_ids?.length)
    : activeWikiPageId === "__stale__"
      ? Boolean(wikiState.stale_claim_ids?.length)
      : false;
  if (!activeSpecialPageExists
      && !wikiState.pages.some((page) => page.id === activeWikiPageId)) {
    activeWikiPageId = wikiState.pages[0]?.id
      || (wikiState.unorganized_claim_ids?.length ? "__unorganized__" : "");
  }
  wikiModeWikiBtn.classList.toggle("is-active", wikiMode === "wiki");
  wikiModeGraphBtn.classList.toggle("is-active", wikiMode === "graph");
  wikiModeWikiBtn.setAttribute("aria-pressed", String(wikiMode === "wiki"));
  wikiModeGraphBtn.setAttribute("aria-pressed", String(wikiMode === "graph"));
  wikiMainEl.hidden = wikiMode !== "wiki" || !wikiProposalReviewEl.hidden || !wikiImportReviewEl.hidden;
  wikiMainEl.classList.toggle("is-empty", wikiState.pages.length === 0);
  wikiGraphEl.hidden = wikiMode !== "graph" || !wikiProposalReviewEl.hidden || !wikiImportReviewEl.hidden;
  wikiHealthEl.replaceChildren();
  const unorganizedCount = wikiState.unorganized_claim_ids?.length || 0;
  const unorganizedChip = document.createElement("span");
  unorganizedChip.textContent = `${unorganizedCount} unorganized`;
  unorganizedChip.classList.toggle("needs-attention", unorganizedCount > 0);
  wikiHealthEl.appendChild(unorganizedChip);
  const staleCount = wikiState.stale_claim_ids?.length || 0;
  const staleChip = document.createElement("button");
  staleChip.type = "button";
  staleChip.textContent = `${staleCount} stale`;
  staleChip.disabled = staleCount === 0;
  staleChip.classList.toggle("needs-attention", staleCount > 0);
  staleChip.classList.toggle("is-active", activeWikiPageId === "__stale__");
  staleChip.title = staleCount
    ? "Show Claims changed since the last Wiki organization"
    : "No Claims changed since the last Wiki organization";
  staleChip.addEventListener("click", () => {
    activeWikiPageId = "__stale__";
    wikiMode = "wiki";
    renderWiki();
    renderReviewWorkspace();
  });
  wikiHealthEl.appendChild(staleChip);
  const eligible = wikiState.claims.filter((claim) => claim.lifecycle === "active" && !claim.needs_review);
  const needsReferences = wikiState.pages.length > 0 && (eligible.length > wikiClaimLimit
    || wikiState.pages.some((page) => page.claim_ids.some((id) => !eligible.some((claim) => claim.id === id))));
  document.getElementById("wiki-call-estimate").textContent = `Estimated model calls: ${eligible.length ? (needsReferences ? 2 : 1) : 0}`;
  document.getElementById("wiki-call-detail").textContent = !eligible.length
    ? "Review at least one Claim before organizing the Wiki."
    : needsReferences
    ? "Select reference pages from the directory, then organize this batch. Read-only context: up to 5 pages × 10 Claims; other knowledge stays unchanged."
    : "Organize this batch in one request; no reference-page selection needed.";
  wikiProposalsToggleBtn.textContent = `Awaiting review · ${wikiProposals.length}`;
  wikiProposalsToggleBtn.classList.toggle("has-pending", wikiProposals.length > 0);
  wikiProposalsToggleBtn.disabled = wikiProposals.length === 0;
  wikiProposalsToggleBtn.setAttribute("aria-expanded", String(!wikiProposalReviewEl.hidden));
  wikiImportsToggleBtn.textContent = `Awaiting imports · ${wikiImports.length}`;
  wikiImportsToggleBtn.classList.toggle("has-pending", wikiImports.length > 0);
  wikiImportsToggleBtn.disabled = wikiImports.length === 0;
  wikiExportBtn.disabled = !wikiState.claims.some((claim) => claim.lifecycle === "active");
  renderWikiIncoming();
  if (!wikiMainEl.hidden) {
    renderWikiTree();
    renderWikiPage();
  }
  if (!wikiGraphEl.hidden) renderWikiGraph();
  if (!wikiProposalReviewEl.hidden) renderWikiProposals();
  if (!wikiImportReviewEl.hidden) renderWikiImports();
};

let wikiRefreshVersion = 0;
const fetchWiki = async () => {
  const version = ++wikiRefreshVersion;
  wikiStatusEl.textContent = "Loading Wiki…";
  const errors = [];
  await Promise.all(["/api/wiki", "/api/wiki/proposals", "/api/wiki/imports"].map(async url => {
    try {
      const response = await fetchWikiLocal(url);
      const body = await response.json();
      if (!response.ok) throw new Error(body.message || `Could not load ${url}`);
      if (version !== wikiRefreshVersion || reviewState("wiki").busy) return;
      if (url === "/api/wiki") wikiState = body;
      else if (url.endsWith("/proposals")) {
        const drafts = new Map(wikiProposals.filter(item => item._dirty).map(item => [item.id, item]));
        wikiProposals = (body.proposals || []).map(item => drafts.get(item.id) || item);
      } else wikiImports = body.imports || [];
      renderWiki();
      if (currentReviewContext() === "views") renderReviewWorkspace();
    } catch (error) {
      errors.push(`${url}: ${error.message}`);
    }
  }));
  if (version !== wikiRefreshVersion) return;
  wikiStatusEl.textContent = errors.join(" · ");
  if (errors.length) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "semantic-action";
    retry.textContent = "Reload Wiki";
    retry.addEventListener("click", () => fetchWiki());
    wikiStatusEl.appendChild(retry);
  }
};

const generateWikiProposal = async () => {
  const activeClaims = wikiState.claims.filter((claim) => claim.lifecycle === "active" && !claim.needs_review);
  if (!activeClaims.length) {
    wikiStatusEl.textContent = "Review at least one Claim before organizing the Wiki.";
    wikiOrganizeBtn.classList.remove("is-attention");
    window.requestAnimationFrame(() => wikiOrganizeBtn.classList.add("is-attention"));
    window.setTimeout(() => wikiOrganizeBtn.classList.remove("is-attention"), 1000);
    return;
  }
  wikiStatusEl.textContent = `Organizing ${Math.min(wikiClaimLimit, activeClaims.length)} of ${activeClaims.length} Claims · stale → unorganized → others…`;
  wikiProposalRunning = true;
  wikiOrganizeBtn.disabled = true;
  setTabActivity("views-panel", "processing");
  try {
    const response = await fetch("/api/wiki/proposals/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_profile_id: wikiModelSelect?.value || "",
      }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.message || "Could not propose a Wiki structure.");
    activeWikiProposalId = body.proposal?.id || "";
    wikiRefreshVersion++;
    setTabActivity("views-panel", "idle");
    setTabActivity("views-panel", "result");
    wikiProposalReviewEl.hidden = false;
    wikiProposals = [body.proposal, ...wikiProposals.filter(item => item.id !== body.proposal.id)];
    wikiImportReviewEl.hidden = true;
    renderWiki();
    wikiStatusEl.textContent = `Wiki Patch ready for review · ${body.proposal?.scope?.claim_ids?.length || 0} Claims processed. Unselected knowledge is preserved.`;
  } catch (error) {
    setTabActivity("views-panel", "idle");
    wikiStatusEl.textContent = error.message;
  } finally {
    wikiProposalRunning = false;
    renderWikiIncoming();
  }
};

const resetWikiStructure = async () => {
  if (wikiResetStructureBtn.disabled || reviewState("wiki").busy || wikiProposalRunning) return;
  const pageCount = wikiState.pages.length;
  const draftCount = wikiProposals.length;
  if (!await confirmAction(
    `Remove all ${pageCount} Wiki Pages and their Claim placements, and discard ${draftCount} awaiting Wiki structure draft(s)? All reviewed active Claims will become Unorganized. Claims, Evidence, Sources, Projects and saved Articles will be preserved.`,
    {title: "Reset Wiki structure", confirmLabel: "Reset", destructive: true,
      highlights: [
        ...(pageCount > 0 ? [`${pageCount} Wiki Pages`] : []),
        ...(draftCount > 0 ? [`${draftCount} awaiting Wiki structure draft(s)`] : []),
      ]},
  )) return;
  const state = reviewState("wiki");
  if (state.busy || wikiProposalRunning) return;
  state.busy = true;
  wikiRefreshVersion++;
  wikiResetStructureBtn.disabled = true;
  wikiStatusEl.textContent = "Resetting Wiki structure…";
  try {
    const response = await fetchWikiLocal("/api/wiki/reset", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({confirmed: true}),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.message || "Could not reset Wiki structure.");
    wikiRefreshVersion++;
    wikiState = body;
    wikiProposals = [];
    state.selected.clear();
    activeWikiProposalId = "";
    activeWikiProposalPageKeys.clear();
    activeWikiPageId = "__unorganized__";
    wikiMode = "wiki";
    wikiProposalReviewEl.hidden = true;
    wikiImportReviewEl.hidden = true;
    wikiStatusEl.textContent = "Wiki structure reset. Knowledge and Projects are preserved; Claims are ready to organize again.";
  } catch (error) {
    wikiStatusEl.textContent = error.message;
  } finally {
    state.busy = false;
    renderWiki();
    if (currentReviewContext() === "views") renderReviewWorkspace();
  }
};

const editWikiStructure = async () => {
  if (reviewState("wiki").busy || wikiEditStructureBtn.disabled) return;
  if (wikiProposals.length) {
    activeWikiProposalId = activeWikiProposalId || wikiProposals[0].id;
    wikiImportReviewEl.hidden = true;
    wikiProposalReviewEl.hidden = false;
    renderWiki();
    wikiStatusEl.textContent = "Continue editing the awaiting Wiki Patch.";
    return;
  }
  wikiEditStructureBtn.disabled = true;
  wikiStatusEl.textContent = "Creating an editable Wiki Patch…";
  try {
    const response = await fetchWikiLocal("/api/wiki/proposals/edit", { method: "POST" });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || "Could not create an editable Wiki Patch.");
    activeWikiProposalId = body.proposal.id;
    wikiRefreshVersion++;
    wikiProposals = [body.proposal, ...wikiProposals.filter(item => item.id !== body.proposal.id)];
    wikiProposalReviewEl.hidden = false;
    wikiImportReviewEl.hidden = true;
    renderWiki();
    wikiStatusEl.textContent = "Wiki structure draft ready to edit.";
  } catch (error) {
    wikiStatusEl.textContent = error.message;
  } finally {
    wikiEditStructureBtn.disabled = false;
  }
};

const acceptWikiProposal = async (proposalId) => {
  wikiStatusEl.textContent = "Applying the reviewed Wiki Patch…";
  await sendWikiPatchDecision(proposalId, true);
  wikiProposalReviewEl.hidden = true;
  renderWiki();
  if (currentReviewContext() === "views") renderReviewWorkspace();
  wikiStatusEl.textContent = "Global Wiki updated.";
};

const discardWikiProposal = async (proposalId) => {
  wikiStatusEl.textContent = "Discarding Wiki Patch…";
  try {
    await sendWikiPatchDecision(proposalId, false);
    wikiProposalReviewEl.hidden = wikiProposals.length === 0;
    renderWiki();
    if (currentReviewContext() === "views") renderReviewWorkspace();
    wikiStatusEl.textContent = "Wiki Patch discarded.";
  } catch (error) {
    wikiStatusEl.textContent = error.message || "Could not discard the Wiki Patch.";
  }
};

const editWikiReading = (reading, options) => {
  const draft = JSON.parse(JSON.stringify(reading));
  const projectClaims = projectDetails.get(activeArticleProjectId)?.claims || [];
  wikiReadingEl.replaceChildren();
  const form = document.createElement("form"); form.className = "article-editor";
  const heading = document.createElement("h3"); heading.textContent = "Edit Article";
  const hint = document.createElement("p"); hint.textContent = "Edit prose and check each paragraph's Claims. This does not change the Claims themselves.";
  form.append(heading, hint);
  const field = (parent, label, value, onInput, single = false) => {
    const wrapper = document.createElement("label"); wrapper.textContent = label;
    const input = document.createElement(single ? "input" : "textarea");
    input.value = value || ""; if (!single) input.rows = 4;
    input.addEventListener("input", () => onInput(input.value));
    wrapper.appendChild(input); parent.appendChild(wrapper); return input;
  };
  field(form, "Title", draft.title, (value) => { draft.title = value; }, true).required = true;
  field(form, "Introduction", draft.introduction, (value) => { draft.introduction = value; });
  draft.sections.forEach((section) => {
    const block = document.createElement("section");
    field(block, "Section title", section.heading, (value) => { section.heading = value; }, true).required = true;
    const paragraphs = document.createElement("div");
    const renderParagraphs = () => {
      paragraphs.replaceChildren();
      section.paragraphs.forEach((paragraph, index) => {
        const row = document.createElement("div"); row.className = "article-edit-paragraph";
        field(row, `Paragraph ${index + 1}`, paragraph.text, (value) => { paragraph.text = value; }).required = true;
        const citations = document.createElement("details");
        const summary = document.createElement("summary");
        const updateSummary = () => { summary.textContent = paragraph.claim_ids.length ? `Claim citations · ${paragraph.claim_ids.length}` : "Uncited · select Claims if this paragraph makes factual assertions"; };
        updateSummary(); citations.appendChild(summary);
        projectClaims.forEach((claim) => {
          const label = document.createElement("label"); label.className = "article-citation-option";
          const checkbox = document.createElement("input"); checkbox.type = "checkbox";
          checkbox.checked = paragraph.claim_ids.includes(claim.id);
          checkbox.addEventListener("change", () => {
            paragraph.claim_ids = checkbox.checked ? [...paragraph.claim_ids, claim.id] : paragraph.claim_ids.filter((id) => id !== claim.id);
            updateSummary();
          });
          const text = document.createElement("span"); text.textContent = claim.statement;
          label.append(checkbox, text); citations.appendChild(label);
        });
        const remove = document.createElement("button"); remove.type = "button";
        remove.className = "semantic-action is-destructive"; remove.textContent = "× Remove paragraph";
        remove.addEventListener("click", () => { section.paragraphs.splice(index, 1); renderParagraphs(); });
        row.append(citations, remove); paragraphs.appendChild(row);
      });
    };
    renderParagraphs();
    const add = document.createElement("button"); add.type = "button"; add.className = "reader-toolbar-btn";
    add.textContent = "+ Paragraph";
    add.addEventListener("click", () => { section.paragraphs.push({ text: "", claim_ids: [] }); renderParagraphs(); });
    block.append(paragraphs, add); form.appendChild(block);
  });
  field(form, "Knowledge gaps (one per line)", (draft.gaps || []).join("\n"), (value) => { draft.gaps = value.split("\n").map((item) => item.trim()).filter(Boolean); });
  const controls = document.createElement("div"); controls.className = "wiki-reading-toolbar";
  const cancel = document.createElement("button"); cancel.type = "button"; cancel.className = "reader-toolbar-btn"; cancel.textContent = "Cancel edits";
  cancel.addEventListener("click", () => renderWikiReading(reading, options));
  const preview = document.createElement("button"); preview.type = "submit"; preview.className = "semantic-action is-edit"; preview.textContent = "Preview edits";
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    draft.selected_claim_ids = [...new Set(draft.sections.flatMap((section) => section.paragraphs.flatMap((paragraph) => paragraph.claim_ids)))];
    renderWikiReading(draft, { ...options, saved: false, dirty: true });
  });
  controls.append(cancel, preview); form.appendChild(controls); wikiReadingEl.appendChild(form);
};

const renderWikiReading = (reading, options = {}) => {
  currentWikiReading = reading;
  wikiReadingEl.replaceChildren();
  const toolbar = document.createElement("div");
  toolbar.className = "wiki-reading-toolbar";
  const back = document.createElement("button"); back.type = "button"; back.className = "reader-toolbar-btn"; back.textContent = "← Project";
  back.addEventListener("click", async () => {
    if (options.dirty && !await confirmAction("Leave without saving the Article edits?")) return;
    wikiReadingEl.hidden = true; await fetchArtifacts();
  });
  const readingActions = document.createElement("div");
  readingActions.className = "wiki-reading-save";
  const notice = document.createElement("small"); notice.textContent = options.saved ? "Saved Article" : options.dirty ? "Unsaved edits" : "Temporary Article · not saved";
  const save = document.createElement("button"); save.type = "button"; save.className = "reader-toolbar-btn"; save.textContent = options.documentId ? "Save changes" : "＋ Save Article";
  save.hidden = Boolean(options.saved);
  save.addEventListener("click", async () => {
    save.disabled = true;
    try {
    const response = await fetch("/api/project-documents", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artifact_id: activeArticleProjectId, document_id: options.documentId || "", title: reading.title, goal: options.goal ?? currentWikiReadingGoal, content: reading }),
    });
    const body = await response.json().catch(() => ({}));
    if (response.ok) {
      notice.textContent = "Saved to Project";
      save.hidden = true;
      options.documentId = body.id; options.saved = true; options.dirty = false;
      const refreshed = await fetch(`/api/projects/${encodeURIComponent(activeArticleProjectId)}`).then((entry) => entry.json());
      projectDetails.set(activeArticleProjectId, refreshed);
      artifactStatusEl.textContent = "Article saved in the Project.";
    } else {
      save.disabled = false;
      artifactStatusEl.textContent = body.message || "Could not save the Article.";
    }
    } catch (error) { artifactStatusEl.textContent = error.message; }
    finally { save.disabled = false; }
  });
  const edit = document.createElement("button"); edit.type = "button"; edit.className = "reader-toolbar-btn"; edit.textContent = "✎ Edit Article";
  edit.addEventListener("click", () => editWikiReading(reading, options));
  readingActions.append(notice, edit, save);
  toolbar.append(back, readingActions);
  const title = document.createElement("h2"); title.textContent = reading.title;
  const intro = document.createElement("p"); intro.className = "wiki-reading-intro"; appendMarkdownInline(intro, reading.introduction);
  wikiReadingEl.append(toolbar, title, intro);
  reading.sections.forEach((section) => {
    const block = document.createElement("section");
    const heading = document.createElement("h3"); heading.textContent = section.heading; block.appendChild(heading);
    section.paragraphs.forEach((paragraph) => {
      const text = document.createElement("p"); appendMarkdownInline(text, paragraph.text);
      const citations = document.createElement("div"); citations.className = "wiki-reading-citations";
      if (!paragraph.claim_ids.length) {
        const uncited = document.createElement("small"); uncited.textContent = "Uncited"; citations.appendChild(uncited);
      }
      paragraph.claim_ids.forEach((claimId) => {
        const claim = wikiClaimById(claimId) || claims.find((item) => item.id === claimId); if (!claim) return;
        const chip = document.createElement("button"); chip.type = "button"; chip.textContent = claim.statement;
        chip.addEventListener("click", () => {
          selectedClaimIds.clear(); selectedClaimIds.add(claimId);
          renderClaims();
          wikiReadingEl.hidden = true;
          showPanel("claims-panel");
        });
        citations.appendChild(chip);
      });
      block.append(text, citations);
    });
    wikiReadingEl.appendChild(block);
  });
  if (reading.gaps?.length) {
    const gaps = document.createElement("aside");
    const heading = document.createElement("strong"); heading.textContent = "Knowledge gaps"; gaps.appendChild(heading);
    reading.gaps.forEach((gap) => { const item = document.createElement("p"); item.textContent = gap; gaps.appendChild(item); });
    wikiReadingEl.appendChild(gaps);
  }
  wikiReadingComposerEl.hidden = true;
  wikiReadingEl.hidden = false;
  requestAnimationFrame(() => {
    if (currentReviewContext() === "artifact" && !wikiReadingEl.hidden) {
      wikiReadingEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
};

const generateWikiReading = async () => {
  const goal = wikiReadingGoalInput.value.trim();
  if (!goal) { artifactStatusEl.textContent = "Describe the goal for this Article."; return; }
  if (!activeArticleProjectId) { artifactStatusEl.textContent = "Choose a Project first."; return; }
  wikiReadingRunBtn.disabled = true;
  wikiReadingRunBtn.textContent = "Writing…";
  artifactStatusEl.textContent = "Writing from this Project's Claims…";
  try {
    currentWikiReadingGoal = goal;
    const response = await fetch("/api/project-articles/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        goal,
        project_id: activeArticleProjectId,
        model_profile_id: articleModelSelect?.value || "",
      }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.message || "Could not generate the Article.");
    wikiReadingComposerEl.hidden = true;
    renderWikiReading(body.article);
    artifactStatusEl.textContent = "Article generated. Save it to keep it in the Project.";
  } catch (error) {
    artifactStatusEl.textContent = error.message;
  } finally {
    wikiReadingRunBtn.disabled = false;
    wikiReadingRunBtn.textContent = "Generate";
  }
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

const renderSourceDiscovery = () => {
  sourceDiscoveryResultsEl.hidden = !sourceDiscoveryOpen;
  if (!sourceDiscoveryOpen) return;
  sourceDiscoveryListEl.replaceChildren();
  const renderGroup = (label, items, className = "") => {
    if (!items.length) return null;
    const section = document.createElement("section");
    section.className = `source-discovery-group ${className}`.trim();
    const heading = document.createElement("h3");
    heading.textContent = `${label} · ${items.length}`;
    section.appendChild(heading);
    items.forEach((paper) => section.appendChild(createRelevanceCard(
      paper, selectedDiscoverySourceKeys, () => {
        sourceDiscoveryAddBtn.disabled = selectedDiscoverySourceKeys.size === 0;
        sourceDiscoveryAddBtn.textContent = selectedDiscoverySourceKeys.size
          ? `Add selected Sources · ${selectedDiscoverySourceKeys.size}`
          : "Add selected Sources";
      },
    )));
    return section;
  };
  const strong = sourceDiscoveryResults.filter((item) => item.relevance_tier === "strong");
  const possible = sourceDiscoveryResults.filter((item) => item.relevance_tier !== "strong");
  [renderGroup("Strong match", strong), renderGroup("Possible match", possible)]
    .filter(Boolean).forEach((section) => sourceDiscoveryListEl.appendChild(section));
  if (sourceDiscoveryExcluded.length) {
    const excluded = document.createElement("details");
    excluded.className = "excluded-results source-discovery-excluded";
    const summary = document.createElement("summary");
    summary.textContent = `Excluded · ${sourceDiscoveryExcluded.length}`;
    const list = renderGroup("Excluded", sourceDiscoveryExcluded, "is-excluded");
    excluded.append(summary, list);
    sourceDiscoveryListEl.appendChild(excluded);
  }
  if (!sourceDiscoveryResults.length && !sourceDiscoveryExcluded.length) {
    const empty = document.createElement("div");
    empty.className = "knowledge-empty";
    empty.textContent = sourceDiscoveryEmptyMessage;
    sourceDiscoveryListEl.appendChild(empty);
  }
  sourceDiscoveryAddBtn.disabled = selectedDiscoverySourceKeys.size === 0;
  sourceDiscoveryAddBtn.textContent = selectedDiscoverySourceKeys.size
    ? `Add selected Sources · ${selectedDiscoverySourceKeys.size}`
    : "Add selected Sources";
};

const renderLibrary = () => {
  updateEvidenceReadScope();
  syncTagFilterOptions(libraryTagFilterInput, librarySources, selectedSourceTagFilters, selectedSourceAllTagFilters, "Evidence");
  syncTagFilterOptions(libraryTagAllFilterInput, librarySources, selectedSourceAllTagFilters, selectedSourceTagFilters, "Evidence");
  const filteredSources = visibleSources();
  updateSelectAllState(
    librarySelectAllInput,
    filteredSources.filter(item => selectedLibrarySourceKeys.has(resultKey(item))).length,
    filteredSources.length,
  );
  const focused = Boolean(activeSourceWorkspace) || sourceDiscoveryOpen;
  if (!focused) libraryStatusEl.textContent = `${filteredSources.length} of ${librarySources.length} Sources`;
  librarySelectAllInput.closest("label").hidden = focused;
  document.querySelector("#library-tag-filters").hidden = focused;
  libraryBatchTagBtn.hidden = focused; libraryBatchDeleteBtn.hidden = focused;
  libraryBatchTagBtn.disabled = selectedLibrarySourceKeys.size === 0;
  libraryBatchDeleteBtn.disabled = selectedLibrarySourceKeys.size === 0;
  libraryListEl.hidden = focused;
  sourceReaderEl.hidden = !activeSourceWorkspace;
  sourceEvidenceProposerEl.hidden = focused;
  sourceDiscoveryLauncherEl.hidden = focused;
  sourceDiscoveryResultsEl.hidden = !sourceDiscoveryOpen || Boolean(activeSourceWorkspace);
  proposeEvidenceBtn.disabled = selectedLibrarySourceKeys.size === 0
    || !evidenceProposalFocusInput.value.trim();
  proposeEvidenceBtn.textContent = selectedLibrarySourceKeys.size
    ? `Propose Evidence via LLM · ${selectedLibrarySourceKeys.size}`
    : "Propose Evidence via LLM";
  sourceDiscoveryRunBtn.disabled = sourceDiscoveryBusy || selectedLibrarySourceKeys.size < 1
    || selectedLibrarySourceKeys.size > 3
    || !sourceDiscoveryModelSelect.value;
  sourceDiscoveryRunBtn.textContent = sourceDiscoveryBusy ? "Exploring…" : selectedLibrarySourceKeys.size
    ? `Explore related · ${selectedLibrarySourceKeys.size}`
    : "Explore related";
  libraryAbstractToggleBtn.hidden = focused;
  libraryPanelInnerEl.classList.toggle("is-reader-focused", Boolean(activeSourceWorkspace));
  libraryPanelInnerEl.classList.toggle(
    "is-reader-details-expanded",
    Boolean(activeSourceWorkspace) && readerDetailsExpanded,
  );
  if (activeSourceWorkspace) {
    renderSourceReader();
    return;
  }
  if (sourceDiscoveryOpen) {
    renderSourceDiscovery();
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
  if (!filteredSources.length) {
    const empty = document.createElement("div"); empty.className = "knowledge-empty";
    empty.textContent = "No Sources match these filters."; libraryListEl.appendChild(empty);
  }
  filteredSources.forEach((source) => {
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
        librarySelectAllInput, filteredSources.filter(item => selectedLibrarySourceKeys.has(resultKey(item))).length, filteredSources.length,
      );
      renderReviewWorkspace();
      renderLibrary();
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
  sourceOpenOriginalEl.href = source.document_hash
    ? `/api/library/sources/${source.id}/content`
    : source.pdf_url || source.paper_url || source.url || "#";
  sourceOpenOriginalEl.querySelector("span:last-child").textContent = source.document_hash ? "Original file" : (
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
  if (tool !== "text" && readerTextSelectionArmed) cancelReaderTextSelectionArm();
  evidenceTextToolBtn.classList.toggle("is-active", tool === "text");
  evidenceSnapshotToolBtn.classList.toggle("is-active", tool === "snapshot");
  evidenceTextToolBtn.setAttribute("aria-pressed", String(tool === "text"));
  evidenceSnapshotToolBtn.setAttribute("aria-pressed", String(tool === "snapshot"));
  sourceReaderSegmentsEl.classList.toggle("is-snapshot-mode", tool === "snapshot");
  if (tool === "snapshot") window.getSelection()?.removeAllRanges();
};

const cancelReaderTextSelectionArm = () => {
  readerTextSelectionArmed = false;
  evidenceTextToolBtn.classList.remove("is-awaiting-selection");
  sourceReaderSegmentsEl.classList.remove("is-awaiting-text-selection");
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
  createEvidenceBtn.textContent = "Create Evidence";
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
      renderEvidenceText(quote, item.quote);
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
  evidenceDetailMetaEl.textContent = `v${item.revision || 1} · ${item.locator || "No locator"}`;
  renderTagChips(evidenceDetailTagsEl, item.tags || []);
  evidenceDetailContentEl.replaceChildren();
  if (item.evidence_type === "snapshot") {
    const image = document.createElement("img");
    image.src = `/api/evidence/${item.id}/snapshot`;
    image.alt = `Snapshot Evidence from ${item.locator}`;
    evidenceDetailContentEl.appendChild(image);
    if (item.quote) {
      const caption = document.createElement("p");
      renderEvidenceText(caption, item.quote);
      evidenceDetailContentEl.appendChild(caption);
    }
  } else {
    const quote = document.createElement("blockquote");
    renderEvidenceText(quote, item.quote || "No captured text is available for this Evidence.");
    evidenceDetailContentEl.appendChild(quote);
  }
  const history = item.history || libraryEvidence.find(entry => entry.id === item.id)?.history || [];
  if (history.length) {
    const versions = document.createElement("details"); versions.className = "evidence-version-history";
    const heading = document.createElement("summary"); heading.textContent = `Previous versions · ${history.length}`; versions.append(heading);
    for (const version of history) {
      const label = document.createElement("small"); label.textContent = `v${version.revision} · ${version.locator || "No locator"}`;
      const quote = document.createElement("blockquote"); renderEvidenceText(quote, version.quote); versions.append(label, quote);
    }
    evidenceDetailContentEl.append(versions);
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
      if (!await confirmAction("Delete this Annotation?")) return;
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
document.getElementById("evidence-detail-edit").addEventListener("click", () => {
  const item = activeEvidenceDetail(); if (!item) return;
  const quote = document.createElement("textarea"); quote.rows = 7; quote.value = item.quote || ""; quote.maxLength = 12000;
  const quoteLabel = document.createElement("label"); quoteLabel.textContent = item.evidence_type === "snapshot" ? "Caption" : "Excerpt"; quoteLabel.append(quote);
  const locator = document.createElement("input"); locator.value = item.locator || ""; locator.maxLength = 300;
  const locatorLabel = document.createElement("label"); locatorLabel.textContent = "Location"; locatorLabel.append(locator);
  const note = document.createElement("small"); note.textContent = "Saving retains the previous version and sends linked Claims to Evidence changed review. Original Source and image are not modified.";
  const save = document.createElement("button"); save.type = "button"; save.textContent = "Save changes"; save.className = "semantic-action is-accept";
  const cancel = document.createElement("button"); cancel.type = "button"; cancel.textContent = "Cancel"; cancel.className = "semantic-action";
  cancel.addEventListener("click", renderEvidenceDetail);
  save.addEventListener("click", async () => {
    save.disabled = true;
    try {
      const response = await fetch(`/api/evidence/${item.id}`, {method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify({quote: quote.value, locator: locator.value, revision: item.revision || 1})});
      const data = await response.json(); if (!response.ok) throw new Error(data.message || "Could not edit Evidence");
      await Promise.all([fetchEvidenceLibrary(), fetchClaims(), fetchClaimProposals(), fetchWiki()]);
      await refreshEvidenceDetailData();
      evidenceStatusEl.textContent = `Evidence saved. ${data.affected_claims} linked Claims awaiting recheck.`;
      if (data.affected_claims) { claimReviewCategory = "changed"; setTabActivity("claims-panel", "result"); }
    } catch (error) { note.textContent = error.message; save.disabled = false; }
  });
  const editor = document.createElement("div"); editor.className = "evidence-content-editor";
  editor.append(quoteLabel, locatorLabel, note, cancel, save); evidenceDetailContentEl.replaceChildren(editor);
});
let knowledgeDeletionBusy = false;
const deleteSelectedKnowledge = async (entityType, ids) => {
  if (!ids.length || knowledgeDeletionBusy) return false;
  knowledgeDeletionBusy = true;
  const status = entityType === "source" ? libraryStatusEl : evidenceStatusEl;
  const request = async (route, payload) => {
    const response = await fetch(route, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Deletion failed");
    return data;
  };
  try {
    const payload = {entity_type:entityType, entity_ids:ids};
    status.textContent = "Checking deletion impact…";
    const plan = await request("/api/knowledge/delete-preview", payload);
    const message = `Delete ${ids.length} selected ${entityType === "source" ? "Sources" : "Evidence items"}?\n\n`
      + `${plan.sources} Sources, ${plan.evidence} Evidence items and ${plan.annotations} Annotations will be deleted. Their Tags and Project links will be removed.\n`
      + `${plan.claims} linked Claims will be retained; ${plan.recheck_claims} active Claims will return to Evidence changed review.\n`
      + `${plan.pending_proposals} dependent pending proposals will be removed.\n\nThis cannot be undone. Export your Wiki or Project first if you need a backup.`;
    const highlights = [
      plan.sources ? `${plan.sources} Sources` : "",
      plan.evidence ? `${plan.evidence} Evidence items` : "",
      plan.annotations ? `${plan.annotations} Annotations` : "",
      plan.claims ? `${plan.claims} linked Claims will be retained` : "",
      plan.recheck_claims ? `${plan.recheck_claims} active Claims will return to Evidence changed review` : "",
      plan.pending_proposals ? `${plan.pending_proposals} dependent pending proposals will be removed` : "",
      "This cannot be undone.",
    ].filter(Boolean);
    if (!await confirmAction(message, {title:"Delete selected items",confirmLabel:"Delete",destructive:true,highlights})) { status.textContent = "Deletion cancelled."; return false; }
    status.textContent = "Deleting selected items…";
    await request("/api/knowledge/delete", {...payload, token:plan.token});
    if (entityType === "source") {
      librarySources.filter(item => ids.includes(item.id)).forEach(item => { selectedLibrarySourceKeys.delete(resultKey(item)); chatContextSources.delete(resultKey(item)); });
      if (ids.includes(activeSourceWorkspace?.source?.id)) {
        activeSourceWorkspace = null; pdfRenderToken += 1;
      }
    }
    const removedEvidence = libraryEvidence.filter(item => entityType === "source" ? ids.includes(item.source_id) : ids.includes(item.id));
    if ((annotationTarget?.type === "source" && entityType === "source" && ids.includes(annotationTarget.id))
        || (annotationTarget?.type === "evidence" && removedEvidence.some(item => item.id === annotationTarget.id))) annotationTarget = null;
    removedEvidence.forEach(item => { selectedEvidenceIds.delete(item.id); chatContextEvidence.delete(item.id); });
    if (removedEvidence.some(item => item.id === activeEvidenceDetailId)) { evidenceDetailDialog.close(); activeEvidenceDetailId = null; }
    await Promise.all([fetchLibrary(), fetchEvidenceLibrary(), fetchClaims(), fetchClaimProposals(), fetchEvidenceProposals(), fetchWiki(), fetchArtifacts()]);
    if (activeSourceWorkspace?.source?.id) await openSourceReader(activeSourceWorkspace.source.id, {preserveState:true});
    if (plan.recheck_claims) { claimReviewCategory = "changed"; setTabActivity("claims-panel", "result"); }
    renderReviewWorkspace(); renderChatContext();
    status.textContent = `Deleted ${ids.length} items. ${plan.recheck_claims} Claims await recheck.`;
    return true;
  } catch (error) { status.textContent = error.message; return false; }
  finally { knowledgeDeletionBusy = false; }
};

const deleteEvidenceItem = async (evidenceId, { closeDetail = false } = {}) => {
  if (!await deleteSelectedKnowledge("evidence", [evidenceId])) return false;
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
  if (evidenceTool !== "text") return false;
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || !selection.rangeCount) return false;
  const range = selection.getRangeAt(0);
  const origin = range.commonAncestorContainer.nodeType === Node.TEXT_NODE
    ? range.commonAncestorContainer.parentElement : range.commonAncestorContainer;
  const pdfPage = origin.closest?.(".pdf-page");
  if (pdfPage) {
    if (!pdfPage.contains(range.startContainer) || !pdfPage.contains(range.endContainer)) {
      return false;
    }
    const quote = range.toString().trim();
    if (!quote) return false;
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
    cancelReaderTextSelectionArm();
    sourceReaderStatusEl.textContent = "Text selected. Review the Evidence before saving.";
    return true;
  }
  const segmentText = origin.closest?.(".capture-segment-text");
  if (!segmentText || !segmentText.contains(range.startContainer)
      || !segmentText.contains(range.endContainer)) return false;
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
  cancelReaderTextSelectionArm();
  sourceReaderStatusEl.textContent = "Text selected. Review the Evidence before saving.";
  return true;
};

sourceReaderSegmentsEl.addEventListener("mouseup", () => captureCurrentReaderSelection({
  showEditor: readerTextSelectionArmed,
}));

evidenceTextToolBtn.addEventListener("click", cancelSnapshotTool);
evidenceSnapshotToolBtn.addEventListener("click", () => {
  if (evidenceTool === "snapshot") {
    cancelSnapshotTool();
  } else {
    setEvidenceTool("snapshot");
  }
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
    await savePendingEvidence();
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
      artifactId: "",
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
    if (!activeSourceWorkspace) return;
    setEvidenceTool("text");
    if (captureCurrentReaderSelection({ showEditor: true })) return;
    readerTextSelectionArmed = true;
    evidenceTextToolBtn.classList.add("is-awaiting-selection");
    sourceReaderSegmentsEl.classList.add("is-awaiting-text-selection");
    sourceReaderStatusEl.textContent = "Select text to create Evidence. Press Esc to cancel.";
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
  if (event.key === "Escape" && readerTextSelectionArmed) {
    cancelReaderTextSelectionArm();
    sourceReaderStatusEl.textContent = "Text selection cancelled.";
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
    libraryStatusEl.textContent = `${visibleSources().length} of ${librarySources.length} Sources`;
  } catch (error) {
    libraryStatusEl.textContent = error instanceof TypeError
      ? "Connection to Knowte was interrupted. Restart Knowte, then reload this page."
      : error.message;
  }
};

libraryProposeClaimsBtn.addEventListener("click", async () => {
  if (!selectedEvidenceIds.size) return;
  if (selectedEvidenceIds.size > claimEvidenceLimit) {
    evidenceStatusEl.textContent = `Select at most ${claimEvidenceLimit} Evidence items for one Claim proposal run.`;
    return;
  }
  libraryProposeClaimsBtn.disabled = true;
  libraryProposeClaimsBtn.textContent = "Proposing…";
  setTabActivity("evidence-panel", "processing");
  copySelectedEvidenceToClaimDraft(true);
  evidenceStatusEl.textContent = "The model is developing Claim proposals from selected Evidence…";
  try {
    const artifact = artifacts.find(
      (item) => item.id === collectArtifactSelect.value,
    ) || null;
    const response = await fetch("/api/claim-proposals/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        evidence_ids: [...selectedEvidenceIds], artifact,
        focus: claimProposalFocusInput?.value.trim() || "",
        model_profile_id: claimsModelSelect?.value || "",
      }),
    });
    const data = await response.json().catch(() => ({}));
    updateUsage(data.usage);
    if (!response.ok) throw new Error(data.message || "Could not propose Claims.");
    claimProposalQueueOpen = true;
    claimReviewCategory = "proposals";
    const returned = Array.isArray(data.proposals) ? data.proposals : [];
    const byId = new Map(
      [...returned, ...claimProposals].map((proposal) => [proposal.id, proposal]),
    );
    claimProposals = [...byId.values()];
    latestClaimProposalReport = {
      summary: data.summary || "",
      skipped: Array.isArray(data.skipped) ? data.skipped : [],
      comparisonClaimCount: Number(data.comparison_claim_count || 0),
      comparisonScope: data.comparison_scope || {},
    };
    renderClaimProposals();
    setTabActivity("evidence-panel", "idle");
    setTabActivity("claims-panel", "result");
    claimsStatusEl.textContent = returned.length
      ? `${returned.length} Claim change${returned.length === 1 ? "" : "s"} awaiting review.`
      : `${latestClaimProposalReport.skipped.length} item${latestClaimProposalReport.skipped.length === 1 ? "" : "s"} examined; no durable Claim change proposed.`;
    evidenceStatusEl.textContent = returned.length
      ? `${returned.length} Claim proposal${returned.length === 1 ? "" : "s"} ready in Claims → Awaiting review.`
      : "Review completed; no Claim change proposed. See Claims for details.";
    await fetchClaimProposals().catch(() => {
      claimsStatusEl.textContent += " The background queue refresh failed; the returned proposals remain visible.";
    });
  } catch (error) {
    setTabActivity("evidence-panel", "idle");
    evidenceStatusEl.textContent = error instanceof TypeError
      ? "Connection to Knowte was interrupted before Claims could be proposed. Restart Knowte, then try again."
      : error.message;
  } finally {
    renderEvidenceLibrary();
  }
});

evidenceProposalFocusInput.addEventListener("input", renderLibrary);
sourceDiscoveryModelSelect.addEventListener("change", renderLibrary);

sourceDiscoveryRunBtn.addEventListener("click", async () => {
  if (sourceDiscoveryBusy) return;
  const seeds = selectedLibrarySources();
  if (!seeds.length || seeds.length > 3) {
    libraryStatusEl.textContent = "Select one to three Seed Sources.";
    return;
  }
  if (!sourceDiscoveryModelSelect.value) {
    libraryStatusEl.textContent = "Choose a model for related Source discovery.";
    return;
  }
  sourceDiscoveryBusy = true;
  sourceDiscoveryRunBtn.disabled = true;
  sourceDiscoveryRunBtn.textContent = "Exploring…";
  setTabActivity("sources-panel", "processing");
  const startedAt = Date.now();
  const progress = window.setInterval(() => {
    libraryStatusEl.textContent = `Following the academic graph and verifying candidates…\n${Math.floor((Date.now() - startedAt) / 1000)} s elapsed`;
  }, 1000);
  libraryStatusEl.textContent = "Following the academic graph and verifying candidates…\n0 s elapsed";
  libraryStatusEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  try {
    const response = await fetch("/api/source-discovery", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_ids: seeds.map((source) => source.id),
        focus: sourceDiscoveryFocusInput.value.trim(),
        model_profile_id: sourceDiscoveryModelSelect.value,
      }),
    });
    const data = await response.json().catch(() => ({}));
    updateUsage(data.usage);
    if (!response.ok) throw new Error(data.message || "Could not explore related Sources.");
    sourceDiscoveryResults = data.results || [];
    sourceDiscoveryExcluded = data.excluded_results || [];
    const retrievalFailures = data.retrieval_failures || [];
    sourceDiscoveryEmptyMessage = data.empty_reason === "already_saved"
      ? `All ${data.already_saved_count || 0} retrieved candidates are already in Library.`
      : retrievalFailures.length
        ? "No candidates were returned by the successful paths. Other retrieval paths failed; the result is incomplete."
        : "Semantic Scholar returned no related candidates for these Seeds. This does not prove no related papers exist.";
    selectedDiscoverySourceKeys.clear();
    sourceDiscoveryOpen = true;
    sourceDiscoverySummaryEl.textContent = `${seeds.length} Seed${seeds.length === 1 ? "" : "s"}`
      + ` · ${data.retrieved_count ?? data.candidate_count ?? 0} retrieved`
      + ` · ${data.already_saved_count || 0} already in Library`
      + ` · ${data.assessed_count ?? 0} assessed`
      + ` · ${sourceDiscoveryResults.filter((item) => item.relevance_tier === "strong").length} Strong`
      + ` · ${sourceDiscoveryResults.filter((item) => item.relevance_tier !== "strong").length} Possible`
      + ` · ${sourceDiscoveryExcluded.length} Excluded`;
    const notices = [];
    if (retrievalFailures.length) {
      const labels = { provider_restricted: "reference data withheld by provider", rate_limited: "rate limited",
        paper_not_found: "paper not found", timeout: "request timed out", network_error: "network connection failed",
        invalid_response: "unexpected provider response", http_error: "provider request failed" };
      notices.push(`Incomplete retrieval: ${data.successful_requests}/${data.path_count || data.requests} paths available. `
        + retrievalFailures.map((item) => `${item.lane}: ${labels[item.code] || item.code}`
          + (item.retry_after ? ` (retry in ${item.retry_after}s)` : "")).join("; ") + ".");
    }
    if (data.cache_hits) notices.push(`${data.cache_hits} path(s) reused from the 15-minute retrieval cache; no new retrieval request for those paths.`);
    if ((data.truncated_paths || []).length) notices.push(`More ${data.truncated_paths.join(" / ")} papers exist upstream; Explore samples up to 40 per path per Seed.`);
    if (data.undisplayed_count) notices.push(`${data.undisplayed_count} additional matches are outside the top 20 shown.`);
    if (data.unassessed_count) notices.push(`${data.unassessed_count} candidates not assessed: the 20-match target was reached. This is not an exhaustive review.`);
    if (data.unresolved_seed_count) notices.push(`${data.unresolved_seed_count} Seed(s) could not be resolved.`);
    if ((data.warnings || []).length) {
      notices.push("Some verification batches failed; affected candidates are marked Possible match.");
    } else if (sourceDiscoveryResults.length) {
      notices.push("Strong and Possible matches are ready to review. Excluded candidates remain inspectable.");
    } else if (sourceDiscoveryExcluded.length) {
      notices.push("All assessed candidates were excluded by the model. Expand Excluded to inspect them.");
    }
    sourceDiscoveryStatusEl.textContent = notices.join(" ");
    libraryStatusEl.textContent = "";
    renderLibrary();
  } catch (error) {
    libraryStatusEl.textContent = error instanceof TypeError
      ? "Connection to Knowte was interrupted during related Source discovery."
      : error.message;
  } finally {
    window.clearInterval(progress);
    sourceDiscoveryBusy = false;
    setTabActivity("sources-panel", "idle");
    renderLibrary();
  }
});

sourceDiscoveryCloseBtn.addEventListener("click", () => {
  sourceDiscoveryOpen = false;
  sourceDiscoveryResults = [];
  sourceDiscoveryExcluded = [];
  selectedDiscoverySourceKeys.clear();
  sourceDiscoveryStatusEl.textContent = "";
  renderLibrary();
});

sourceDiscoveryAddBtn.addEventListener("click", async () => {
  const candidates = [...sourceDiscoveryResults, ...sourceDiscoveryExcluded]
    .filter((item) => selectedDiscoverySourceKeys.has(resultKey(item)));
  if (!candidates.length) return;
  sourceDiscoveryAddBtn.disabled = true;
  sourceDiscoveryAddBtn.textContent = "Adding…";
  try {
    const response = await fetch("/api/library/sources/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sources: candidates }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Could not add the selected Sources.");
    sourceDiscoveryResults = sourceDiscoveryResults.filter(
      (item) => !selectedDiscoverySourceKeys.has(resultKey(item)),
    );
    sourceDiscoveryExcluded = sourceDiscoveryExcluded.filter(
      (item) => !selectedDiscoverySourceKeys.has(resultKey(item)),
    );
    selectedDiscoverySourceKeys.clear();
    await fetchLibrary();
    if (!sourceDiscoveryResults.length && !sourceDiscoveryExcluded.length) {
      sourceDiscoveryEmptyMessage = "All displayed candidates have been added to Library.";
    }
    sourceDiscoveryStatusEl.textContent = `${data.sources_created || 0} new Source${data.sources_created === 1 ? "" : "s"} added to the Library. `
      + sourceDiscoveryStatusEl.textContent;
    renderSourceDiscovery();
  } catch (error) {
    sourceDiscoveryStatusEl.textContent = error.message;
  } finally {
    renderSourceDiscovery();
  }
});

proposeEvidenceBtn.addEventListener("click", async () => {
  const focus = evidenceProposalFocusInput.value.trim();
  const sourceIds = librarySources
    .filter((source) => selectedLibrarySourceKeys.has(resultKey(source)))
    .map((source) => source.id);
  if (!focus || !sourceIds.length) return;
  if (sourceIds.length > evidenceSourceLimit) {
    libraryStatusEl.textContent = `Select at most ${evidenceSourceLimit} Sources for one Evidence proposal run.`;
    return;
  }
  proposeEvidenceBtn.disabled = true;
  proposeEvidenceBtn.textContent = "Proposing…";
  setTabActivity("sources-panel", "processing");
  const modelName = evidenceModelSelect?.selectedOptions?.[0]?.textContent
    || "selected model";
  const startedAt = Date.now();
  let progressLabel = `Proposing Evidence with ${modelName}…`;
  const related = evidenceReadScope.value === "related";
  const modelProfileId = evidenceModelSelect?.value || "";
  evidenceReadScope.disabled = evidenceRelatedLimit.disabled = true;
  evidenceRelatedReport.hidden = true;
  const renderProposalProgress = () => {
    const elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    libraryStatusEl.textContent = `${progressLabel}\n${elapsed} s elapsed`;
  };
  renderProposalProgress();
  const elapsedTimer = window.setInterval(renderProposalProgress, 1000);
  try {
    let selection = null;
    if (related) {
      progressLabel = "Discovering related pages and selecting with AI (1 extra call)…";
      renderProposalProgress();
      const response = await fetch("/api/evidence-pages/select", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({source_ids: sourceIds, focus, max_pages: Number(evidenceRelatedLimit.value), model_profile_id: modelProfileId}),
      });
      selection = await response.json();
      updateUsage(selection.usage);
      if (!response.ok) throw new Error(selection.message || "Could not select related pages.");
      const count = selection.pages.length;
      evidenceRelatedReport.hidden = false;
      evidenceRelatedReport.textContent = `${count} pages selected from ${selection.candidate_count} discovered URLs. ${selection.summary || ""}\n`
        + selection.pages.map((page) => `${page.title}\n${page.url}`).join("\n")
        + (selection.warnings?.length ? `\n${selection.warnings.join("\n")}` : "");
      if (!count) {
        libraryStatusEl.textContent = "No relevant pages selected. One selection call completed; no Evidence extraction was requested.";
        return;
      }
      progressLabel = `Reading ${count} selected pages with ${modelName} (${selection.request_mode === "individual" ? count : 1} extraction call${selection.request_mode === "individual" && count > 1 ? "s" : ""}, after 1 selection call)…`;
      renderProposalProgress();
    }
    const response = await fetch("/api/evidence-proposals/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_ids: sourceIds, focus,
        model_profile_id: modelProfileId,
        ...(selection ? {related_pages: selection.pages, related_request_mode: selection.request_mode} : {}),
      }),
    });
    const data = await response.json().catch(() => ({}));
    updateUsage(data.usage);
    if (!response.ok) throw new Error(data.message || "Could not propose Evidence.");
    evidenceProposalQueueOpen = true;
    const returned = Array.isArray(data.proposals) ? data.proposals : [];
    const byId = new Map(
      [...returned, ...evidenceProposals].map((proposal) => [proposal.id, proposal]),
    );
    evidenceProposals = [...byId.values()];
    renderEvidenceProposals();
    setTabActivity("sources-panel", "idle");
    setTabActivity("evidence-panel", "result");
    evidenceStatusEl.textContent = `${returned.length} Evidence proposal${returned.length === 1 ? "" : "s"} awaiting review.`;
    libraryStatusEl.textContent = returned.length
      ? `${returned.length} Evidence proposal${returned.length === 1 ? "" : "s"} ready in Evidence → Awaiting review.`
      : "Review completed; no Evidence proposed for this Focus.";
    if (data.summary) {
      libraryStatusEl.textContent += `\n${data.summary}`;
      evidenceStatusEl.textContent += `\n${data.summary}`;
    }
    if (data.warnings?.length) {
      const warningText = "\n" + data.warnings.join("\n");
      libraryStatusEl.textContent += warningText;
      evidenceStatusEl.textContent += warningText;
    }
    fetchEvidenceProposals().catch(() => {
      evidenceStatusEl.textContent += " The background queue refresh failed; the returned proposals remain visible.";
    });
  } catch (error) {
    setTabActivity("sources-panel", "idle");
    libraryStatusEl.textContent = error instanceof TypeError
      ? "Connection to Knowte was interrupted before Evidence could be proposed."
      : error.message;
  } finally {
    window.clearInterval(elapsedTimer);
    setTabActivity("sources-panel", "idle");
    evidenceReadScope.disabled = evidenceRelatedLimit.disabled = false;
    proposeEvidenceBtn.disabled = false;
    proposeEvidenceBtn.textContent = selectedLibrarySourceKeys.size
      ? `Propose Evidence via LLM · ${selectedLibrarySourceKeys.size}`
      : "Propose Evidence via LLM";
    renderLibrary();
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
  if (!claimProposals.length) return;
  claimProposalQueueOpen = !claimProposalQueueOpen;
  if (claimProposalQueueOpen && !reviewItems("claim").length) {
    claimReviewCategory = claimProposals.some(isEvidenceChangeReview) ? "changed" : "proposals";
  }
  renderClaimProposals();
  if (claimProposalQueueOpen) {
    scrollClaimProposalQueueToStart();
  }
});

claimsAuditToggleBtn.addEventListener("click", () => {
  claimAuditBoardOpen = true;
  claimProposalQueueOpen = false;
  renderClaimProposals();
  renderClaimAudit();
  claimAuditBoardEl.scrollIntoView({ behavior: "smooth", block: "start" });
});

claimAuditCloseBtn.addEventListener("click", () => {
  claimAuditBoardOpen = false;
  renderClaimAudit();
});

claimAuditScopeInput.addEventListener("change", () => {
  activeClaimAudit = ["ready", "running", "paused"].includes(activeClaimAudit?.status)
    ? activeClaimAudit : null;
  claimAuditEstimateEl.textContent = "Preview the scope before starting.";
  claimAuditPreviewKey = "";
  renderClaimAudit();
});
[claimAuditAnyTagsEl, claimAuditAllTagsEl].forEach((control) => {
  control.addEventListener("change", () => {
    claimAuditPreviewKey = "";
    claimAuditEstimateEl.textContent = "Scope changed. Preview it before starting.";
    renderClaimAudit();
  });
});

claimAuditPreviewBtn.addEventListener("click", async () => {
  if (claimAuditScopeInput.value === "tags"
      && !selectedClaimAuditAnyTags.size && !selectedClaimAuditAllTags.size) {
    claimAuditEstimateEl.textContent = "Select at least one Tag for a scoped audit.";
    return;
  }
  claimAuditPreviewBtn.disabled = true;
  claimAuditEstimateEl.textContent = "Building a local candidate estimate…";
  try {
    const response = await fetch("/api/claim-audits/preview", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope: claimAuditScope() }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Could not preview audit.");
    claimAuditPreviewKey = JSON.stringify(claimAuditScope());
    claimAuditEstimateEl.textContent = `${data.claim_count} Claims in scope · ${data.candidate_count} candidate pairs · ${data.estimated_batches} estimated model calls. Candidates use text, tags, shared grounding and relation neighbors; existing links within scope are always checked. Not every possible pair is examined.`;
  } catch (error) {
    claimAuditEstimateEl.textContent = error.message;
  } finally {
    claimAuditPreviewBtn.disabled = false;
  }
});

claimAuditStartBtn.addEventListener("click", async () => {
  if (claimAuditScopeInput.value === "tags"
      && !selectedClaimAuditAnyTags.size && !selectedClaimAuditAllTags.size) {
    claimAuditEstimateEl.textContent = "Select at least one Tag for a scoped audit.";
    return;
  }
  if (!claimAuditModelSelect.value) {
    claimAuditEstimateEl.textContent = "Select a model for this audit.";
    return;
  }
  if (claimAuditPreviewKey !== JSON.stringify(claimAuditScope())) {
    claimAuditEstimateEl.textContent = "Preview this scope before starting the audit.";
    return;
  }
  claimAuditStartBtn.disabled = true;
  try {
    const response = await fetch("/api/claim-audits", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope: claimAuditScope(), model_profile_id: claimAuditModelSelect.value,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || "Could not start audit.");
    activeClaimAudit = data;
    renderClaimAudit();
    advanceClaimAudit();
  } catch (error) {
    claimAuditEstimateEl.textContent = error.message;
  } finally {
    claimAuditStartBtn.disabled = false;
  }
});

claimAuditPauseBtn.addEventListener("click", () => setClaimAuditStatus("pause"));
claimAuditResumeBtn.addEventListener("click", () => setClaimAuditStatus("resume"));
claimAuditCancelBtn.addEventListener("click", async () => {
  if (await confirmAction("Cancel this Claim audit? Completed review proposals will be kept.")) {
    setClaimAuditStatus("cancel");
  }
});

evidenceProposalsToggleBtn.addEventListener("click", () => {
  if (!evidenceProposals.length) return;
  evidenceProposalQueueOpen = !evidenceProposalQueueOpen;
  renderEvidenceProposals();
  if (evidenceProposalQueueOpen) {
    evidenceProposalBoardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
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

viewDetailBackBtn.addEventListener("click", async () => {
  if (!viewDetailEditor.hidden && !await confirmAction("Leave without saving View changes?")) return;
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
  if (!view || !await confirmAction(`Delete View “${view.title}”? Claims and Evidence will not be deleted.`)) return;
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
    artifactStatusEl.textContent = `Created “${data.title}”. Open Project to select Claims and organize its knowledge.`;
  } catch (error) {
    artifactStatusEl.textContent = error.message;
  } finally {
    artifactCreateBtn.disabled = false;
    artifactCreateBtn.textContent = "Create Project";
  }
});

projectImportFileInput.addEventListener("change", async () => {
  const file = projectImportFileInput.files?.[0];
  if (!file) return;
  artifactStatusEl.textContent = "Checking knowledge package…";
  try {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.addEventListener("load", () => resolve(String(reader.result || "")));
      reader.addEventListener("error", () => reject(new Error("Could not read the package.")));
      reader.readAsDataURL(file);
    });
    const encoded = dataUrl.split(",", 2)[1] || "";
    const response = await fetch("/api/project-imports", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, data: encoded }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || "Could not import the package.");
    await fetchArtifacts();
    artifactStatusEl.textContent = `“${body.project.title}” is awaiting review. No imported Claim has entered the Wiki.`;
  } catch (error) {
    artifactStatusEl.textContent = error.message;
  } finally {
    projectImportFileInput.value = "";
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

const collectSelectedResults = async () => {
  const selected = selectedResults();
  if (!selected.length) return;
  contextCollectSelectedBtn.disabled = true;
  contextActionStatusEl.textContent = "Collecting selected Sources…";
  try {
    const response = await fetch("/api/library/sources/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sources: selected, artifact_id: "" }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || "Could not collect the selected Sources.");
    }
    contextActionStatusEl.textContent = `${data.count} Source(s) saved; ${data.sources_created} newly added.`;
    await Promise.all([fetchLibrary(), fetchArtifacts()]);
  } catch (error) {
    contextActionStatusEl.textContent = error.message;
  } finally {
    renderReviewWorkspace();
  }
};

contextCollectSelectedBtn.addEventListener("click", () => {
  collectSelectedResults();
});

const appendMarkdownInline = (parent, value) => {
  const text = String(value || "");
  const tokenPattern = /(\*\*[^*\n]+\*\*|__[^_\n]+__|`[^`\n]+`|\[[^\]\n]+\]\(https?:\/\/[^)\s]+\)|\*[^*\n]+\*|_[^_\n]+_)/g;
  let cursor = 0;
  for (const match of text.matchAll(tokenPattern)) {
    if (match.index > cursor) {
      parent.appendChild(document.createTextNode(text.slice(cursor, match.index)));
    }
    const token = match[0];
    if ((token.startsWith("**") && token.endsWith("**"))
        || (token.startsWith("__") && token.endsWith("__"))) {
      const strong = document.createElement("strong");
      appendMarkdownInline(strong, token.slice(2, -2));
      parent.appendChild(strong);
    } else if (token.startsWith("`") && token.endsWith("`")) {
      const code = document.createElement("code");
      code.textContent = token.slice(1, -1);
      parent.appendChild(code);
    } else if (token.startsWith("[")) {
      const linkMatch = token.match(/^\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)$/);
      if (linkMatch) {
        const link = document.createElement("a");
        link.textContent = linkMatch[1];
        link.href = linkMatch[2];
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        parent.appendChild(link);
      } else {
        parent.appendChild(document.createTextNode(token));
      }
    } else {
      const emphasis = document.createElement("em");
      appendMarkdownInline(emphasis, token.slice(1, -1));
      parent.appendChild(emphasis);
    }
    cursor = match.index + token.length;
  }
  if (cursor < text.length) {
    parent.appendChild(document.createTextNode(text.slice(cursor)));
  }
};

const appendMarkdownParagraph = (parent, lines) => {
  const paragraph = document.createElement("p");
  lines.forEach((line, index) => {
    if (index) paragraph.appendChild(document.createElement("br"));
    appendMarkdownInline(paragraph, line);
  });
  parent.appendChild(paragraph);
};

const renderSafeMarkdown = (value) => {
  const root = document.createElement("div");
  root.className = "context-chat-markdown";
  const lines = String(value || "").replaceAll("\r\n", "\n").split("\n");
  let paragraphLines = [];
  let list = null;
  let listType = "";
  const flushParagraph = () => {
    if (paragraphLines.length) appendMarkdownParagraph(root, paragraphLines);
    paragraphLines = [];
  };
  const closeList = () => { list = null; listType = ""; };
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.trim().startsWith("```")) {
      flushParagraph(); closeList();
      const language = line.trim().slice(3).trim();
      const codeLines = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      if (language) code.dataset.language = language;
      code.textContent = codeLines.join("\n");
      pre.appendChild(code); root.appendChild(pre);
      continue;
    }
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      flushParagraph(); closeList();
      const heading = document.createElement(`h${Math.min(4, headingMatch[1].length + 2)}`);
      appendMarkdownInline(heading, headingMatch[2]);
      root.appendChild(heading);
      continue;
    }
    const quoteMatch = line.match(/^>\s?(.*)$/);
    if (quoteMatch) {
      flushParagraph(); closeList();
      const quoteLines = [quoteMatch[1]];
      while (index + 1 < lines.length && /^>\s?/.test(lines[index + 1])) {
        index += 1;
        quoteLines.push(lines[index].replace(/^>\s?/, ""));
      }
      const quote = document.createElement("blockquote");
      appendMarkdownParagraph(quote, quoteLines);
      root.appendChild(quote);
      continue;
    }
    const unordered = line.match(/^\s*[-+*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      flushParagraph();
      const nextType = ordered ? "ol" : "ul";
      if (!list || listType !== nextType) {
        closeList();
        list = document.createElement(nextType);
        listType = nextType;
        root.appendChild(list);
      }
      const item = document.createElement("li");
      appendMarkdownInline(item, (ordered || unordered)[1]);
      list.appendChild(item);
      continue;
    }
    if (!line.trim()) {
      flushParagraph(); closeList();
      continue;
    }
    closeList();
    paragraphLines.push(line);
  }
  flushParagraph();
  return root;
};

const appendReviewMessage = (
  text,
  role,
  recommendations = [],
  sources = activeReviewSources(),
  proposedSearchActions = [],
) => {
  const message = document.createElement("div");
  message.className = `context-chat-message is-${role}`;
  const body = role === "assistant"
    ? renderSafeMarkdown(text)
    : document.createElement("p");
  if (role !== "assistant") body.textContent = text;
  message.appendChild(body);
  if (recommendations.length && currentReviewContext() === "library") {
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
  if (role === "assistant" && proposedSearchActions.length) {
    proposedSearchActions = proposedSearchActions.map((action) => ({
      ...action, target: "academic",
    }));
    const actionKey = (action) => `academic::${String(action.query || "").trim().toLowerCase().replace(/\s+/g, " ")}`;
    const existingKeys = new Set(
      [...searchStrategyActions, ...searchStrategyWaitingActions].map(actionKey),
    );
    const proposalKeys = new Set();
    const novelActions = proposedSearchActions.filter((action) => {
      const key = actionKey(action);
      if (!String(action.query || "").trim() || existingKeys.has(key) || proposalKeys.has(key)) return false;
      proposalKeys.add(key);
      return true;
    });
    const proposal = document.createElement("div");
    proposal.className = "chat-strategy-proposal";
    const proposalHead = document.createElement("strong");
    proposalHead.textContent = "Proposed candidates";
    proposal.appendChild(proposalHead);
    novelActions.forEach((action) => {
      const row = document.createElement("div");
      row.className = "chat-strategy-proposal-row";
      const meta = document.createElement("span");
      meta.textContent = "ACADEMIC";
      const content = document.createElement("div");
      const query = document.createElement("strong");
      query.textContent = action.query;
      const purpose = document.createElement("small");
      purpose.textContent = action.purpose || "No purpose supplied.";
      content.append(query, purpose);
      row.append(meta, content);
      proposal.appendChild(row);
    });
    if (!novelActions.length) {
      const note = document.createElement("small");
      note.textContent = "No candidates differ from the current strategy.";
      proposal.appendChild(note);
    }
    message.appendChild(proposal);
    const apply = document.createElement("button");
    apply.type = "button";
    apply.className = "chat-apply-strategy";
    apply.disabled = novelActions.length === 0;
    apply.textContent = novelActions.length
      ? `Add candidates · ${novelActions.length}`
      : "Already in strategy";
    apply.addEventListener("click", () => {
      const available = SEARCH_STRATEGY_CANDIDATE_LIMIT
        - searchStrategyActions.length - searchStrategyWaitingActions.length;
      const additions = novelActions.slice(0, Math.max(0, available));
      searchStrategyWaitingActions.push(...additions.map((item) => ({ ...item })));
      searchStrategyEl.hidden = false;
      renderSearchStrategy();
      searchStrategyEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
      apply.disabled = true;
      apply.textContent = additions.length
        ? `${additions.length} added to waiting list`
        : "Candidate limit reached";
    });
    message.appendChild(apply);
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
      message.search_actions || [],
    );
  });
};

contextChatInput.addEventListener("input", () => {
  chatInputDrafts[activeReviewContextKey] = contextChatInput.value;
  chatInputHistoryCursors[activeReviewContextKey] =
    (chatInputHistories[activeReviewContextKey] || []).length;
});

contextChatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    if (!contextChatSendBtn.disabled) contextChatForm.requestSubmit();
    return;
  }
  if (!["ArrowUp", "ArrowDown"].includes(event.key)
      || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
  if (contextChatInput.value.includes("\n")) return;
  const history = chatInputHistories[activeReviewContextKey] || [];
  if (!history.length) return;
  const cursorPosition = contextChatInput.selectionStart ?? 0;
  const beforeCursor = contextChatInput.value.slice(0, cursorPosition);
  const afterCursor = contextChatInput.value.slice(cursorPosition);
  const atHistoryEdge = event.key === "ArrowUp"
    ? !beforeCursor.includes("\n")
    : !afterCursor.includes("\n");
  if (!atHistoryEdge) return;
  event.preventDefault();
  let historyCursor = chatInputHistoryCursors[activeReviewContextKey];
  if (!Number.isInteger(historyCursor)) historyCursor = history.length;
  if (event.key === "ArrowUp") {
    if (historyCursor === history.length) {
      chatInputDrafts[activeReviewContextKey] = contextChatInput.value;
    }
    historyCursor = Math.max(0, historyCursor - 1);
    contextChatInput.value = history[historyCursor];
  } else {
    historyCursor = Math.min(history.length, historyCursor + 1);
    contextChatInput.value = historyCursor === history.length
      ? (chatInputDrafts[activeReviewContextKey] || "")
      : history[historyCursor];
  }
  chatInputHistoryCursors[activeReviewContextKey] = historyCursor;
  contextChatInput.setSelectionRange(
    contextChatInput.value.length, contextChatInput.value.length,
  );
});

contextChatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = contextChatInput.value.trim();
  if (!question) return;
  const contextKey = activeReviewContextKey;
  const inputHistory = chatInputHistories[contextKey] ||= [];
  if (inputHistory[inputHistory.length - 1] !== question) inputHistory.push(question);
  chatInputHistoryCursors[contextKey] = inputHistory.length;
  chatInputDrafts[contextKey] = "";
  const selected = [...chatContextSources.values()];
  const evidence = [...chatContextEvidence.values()];
  const selectedClaimContext = currentReviewContext() === "claims"
    ? selectedClaims()
    : currentReviewContext() === "views"
      ? [...new Set([
          ...(activeWikiPage()?.claim_ids || []),
          ...incomingViewClaimIds,
        ])].map((id) => wikiClaimById(id) || claims.find((claim) => claim.id === id)).filter(Boolean)
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
        model_profile_id: contextModelSelect.value,
        context: currentReviewContext(),
        sources: selected,
        evidence,
        claims: selectedClaimContext,
        wiki_context: currentReviewContext() === "views" ? {
          mode: wikiMode,
          page: activeWikiPage() ? {
            title: activeWikiPage().title,
            summary: activeWikiPage().summary,
            claim_ids: activeWikiPage().claim_ids,
          } : null,
          unorganized_claim_ids: wikiState.unorganized_claim_ids || [],
          stale_claim_ids: wikiState.stale_claim_ids || [],
        } : null,
        artifact,
        search_strategy: currentReviewContext() === "search" ? {
          intent: input.value.trim(),
          actions: searchStrategyActions.slice(0, SEARCH_STRATEGY_TOP_LIMIT),
        } : null,
        conversation: recentConversation,
      }),
    });
    const data = await response.json().catch(() => ({}));
    updateUsage(data.usage);
    if (!response.ok) {
      throw new Error(data.message || "The review copilot is unavailable.");
    }
    const answer = (data.answer || "The model returned no written assessment.")
      + (data.structured_output_degraded
        ? "\n\nStructured suggestions were unavailable, but the model's text response was preserved."
        : "");
    appendReviewMessage(
      answer,
      "assistant",
      data.recommendations || [],
      selected,
      data.search_actions || [],
    );
    conversation.push({
      role: "assistant",
      content: answer,
      recommendations: data.recommendations || [],
      sources: selected,
      evidence,
      search_actions: data.search_actions || [],
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
    search_actions: searchStrategyActions.slice(0, SEARCH_STRATEGY_TOP_LIMIT),
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
    mode.textContent = plan.mode === "intelligent" ? "Search · AI Review on" : "Search · AI Review off";
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
  searchStrategyActions = Array.isArray(plan.search_actions)
    ? plan.search_actions.slice(0, SEARCH_STRATEGY_TOP_LIMIT).map((item) => ({ ...item }))
    : [];
  searchStrategyWaitingActions = [];
  searchStrategyIntent = normalizedSearchIntent();
  searchStrategyStaleAcknowledged = false;
  setSearchMode(plan.mode === "intelligent" ? "smart" : "keyword");
  renderSearchStrategy();
  searchStrategyEl.hidden = searchMode === "import"
    || !(searchStrategyActions.length || searchStrategyWaitingActions.length);
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
    const name = await promptText("Plan name", plan.name);
    if (name === null) return;
    const query = await promptText("Search intent or keywords", plan.query);
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
  if (action === "delete" && await confirmAction(`Delete “${plan.name}”?`)) {
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
    const hadResult = link.classList.contains("has-result");
    setTabActivity(target, "idle");
    showPanel(target);
    if (hadResult) {
      window.requestAnimationFrame(() => {
        if (target === "evidence-panel") {
          evidenceProposalBoardEl.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        if (target === "claims-panel") scrollClaimProposalQueueToStart();
      });
    }
    if (target === "plans-panel") fetchPlans();
    if (target === "sources-panel") fetchLibrary();
    if (target === "evidence-panel") fetchEvidenceLibrary();
    if (target === "claims-panel") {
      Promise.all([
        fetchClaims(), fetchClaimProposals(), fetchEvidenceLibrary(), fetchClaimAudits(),
      ]);
    }
    if (target === "views-panel") Promise.all([fetchWiki(), fetchClaims()]);
    if (target === "create-panel") fetchArtifacts();
  });
});

wikiModeWikiBtn.addEventListener("click", () => {
  wikiMode = "wiki";
  wikiProposalReviewEl.hidden = true;
  wikiImportReviewEl.hidden = true;
  renderWiki();
});

wikiModeGraphBtn.addEventListener("click", () => {
  wikiMode = "graph";
  wikiProposalReviewEl.hidden = true;
  wikiImportReviewEl.hidden = true;
  renderWiki();
});

wikiOrganizeBtn.addEventListener("click", generateWikiProposal);
wikiEditStructureBtn.addEventListener("click", editWikiStructure);
wikiResetStructureBtn.addEventListener("click", resetWikiStructure);
wikiProposalsToggleBtn.addEventListener("click", () => {
  wikiImportReviewEl.hidden = true;
  wikiProposalReviewEl.hidden = false;
  renderWiki();
});
wikiProposalCloseBtn.addEventListener("click", () => {
  wikiProposalReviewEl.hidden = true;
  renderWiki();
});
wikiExportBtn.addEventListener("click", () => exportKnowledge(
  "wiki", [], wikiStatusEl, wikiExportBtn,
));
wikiImportCloseBtn.addEventListener("click", () => {
  wikiImportReviewEl.hidden = true; renderWiki();
});
wikiImportsToggleBtn.addEventListener("click", () => {
  wikiProposalReviewEl.hidden = true; wikiImportReviewEl.hidden = false; renderWiki();
});
wikiImportFileInput.addEventListener("change", async () => {
  const file = wikiImportFileInput.files?.[0];
  if (!file) return;
  wikiStatusEl.textContent = "Checking Wiki package…";
  try {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.addEventListener("load", () => resolve(String(reader.result || "")));
      reader.addEventListener("error", () => reject(new Error("Could not read the package.")));
      reader.readAsDataURL(file);
    });
    const response = await fetch("/api/wiki/imports", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, data: dataUrl.split(",", 2)[1] || "" }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.message || "Could not import the Wiki package.");
    wikiImportReviewEl.hidden = false; wikiProposalReviewEl.hidden = true;
    await fetchWiki(); wikiStatusEl.textContent = "Wiki package is awaiting one complete review.";
  } catch (error) {
    wikiStatusEl.textContent = error.message;
  } finally {
    wikiImportFileInput.value = "";
  }
});
wikiReadingCloseBtn.addEventListener("click", () => {
  wikiReadingComposerEl.hidden = true;
  wikiReadingEl.hidden = true;
});
wikiReadingRunBtn.addEventListener("click", generateWikiReading);

[
  emailInput,
  s2KeyInput,
  searxngInput,
  searxngProxyInput,
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
  aiSearchTimeoutInput,
  aiStageTimeoutInput,
  ai_evidence_source_limitInput,
  ai_claim_evidence_limitInput,
  aiClaimComparisonLimitInput,
  aiWikiClaimLimitInput,
  ai_copilot_context_limitInput,
  evidenceRequestModeInput,
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
      body: JSON.stringify({ theme: mode }),
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
fetchArtifacts();
fetchClaims();
fetchClaimProposals();
fetchClaimAudits();
fetchEvidenceProposals();
fetchWiki().catch((error) => { wikiStatusEl.textContent = error.message; });
fetchLibrary();
fetchCompanionInbox();
window.setInterval(fetchCompanionInbox, 5000);
renderSelectedAreas();
renderPresetState();
initTheme();
setFiltersCollapsed(false);
renderPaginationControls();
