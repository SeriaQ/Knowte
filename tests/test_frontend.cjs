// Run with: node tests/test_frontend.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const code = fs.readFileSync(`${__dirname}/../knowte/web/app.js`, "utf8");
const wikiLayoutCss = fs.readFileSync(`${__dirname}/../knowte/web/styles.css`, "utf8");
for (const selector of ["wiki-claim-statement", "wiki-patch-claim-statement"]) {
  const rule = wikiLayoutCss.match(new RegExp(`\\.${selector} \\{([^}]+)\\}`))[1];
  assert.match(rule, /border-radius:\s*0;/);
  assert.match(rule, /overflow:\s*visible;/);
  assert.match(rule, /overflow-wrap:\s*anywhere;/);
}
const fragment = (start, end) => {
  const first = code.indexOf(start);
  const last = code.indexOf(end, first);
  assert.ok(first >= 0 && last > first, `Missing fragment: ${start}`);
  return code.slice(first, last);
};
const element = (tag) => ({
  tag, children: [], dataset: {}, style: { setProperty() {} },
  replaceChildren(...items) { this.children = items; },
  append(...items) { this.children.push(...items); },
  appendChild(item) { this.children.push(item); },
  addEventListener(name, callback) { this[name] = callback; },
});
const document = { createElement: element, createTextNode: (text) => ({textContent: text}) };

const imported = { input: { value: 'PPO "clipping"\nimplementation' } };
vm.createContext(imported);
vm.runInContext(fragment("const importPrompt =", "const updateImportPrompt =") + "this.prompt = importPrompt;", imported);
const prompt = imported.prompt();
const jsonLines = prompt.split("\n").filter((line) => line.startsWith('{"knowte_import_version"')).map(JSON.parse);
assert.equal(jsonLines[0].request, imported.input.value);
assert.equal(jsonLines[1].sources.length, 3);
assert.equal(new Set(jsonLines[1].sources.map((source) => source.source_type)).size, 3);
assert.ok(!prompt.split("\n")[0].includes("Knowte"));
for (const [count, expected] of [[undefined, "Unknown"], [null, "Unknown"], [0, "0"], [42, "42"]]) {
  const context = { document, paper: { citation_count: count } };
  vm.createContext(context);
  vm.runInContext(fragment('    const meta = document.createElement("p");', "    if (paper.import_status)") + "this.label = meta.textContent;", context);
  assert.ok(context.label.endsWith(`Citations: ${expected}`));
}
console.log("PASS citation counts and multi-type import prompt JSON");

const modelSelect = () => ({value: "old", options: [],
  replaceChildren(...options) { this.options = options; },
  appendChild(option) { this.options.push(option); },
});
const modelControls = {
  Option: function(text, value) { this.text = text; this.value = value; },
  aiRoleAssignments: Object.fromEntries(["intelligent_search", "source_discovery", "evidence", "claims", "wiki", "article"].map((role) => [role, "new"])),
  aiModelProfiles: [{id: "old", capabilities: ["chat"]}, {id: "new", capabilities: ["chat"]}],
};
for (const name of ["searchModelSelect", "sourceDiscoveryModelSelect", "evidenceModelSelect", "claimsModelSelect", "claimAuditModelSelect", "wikiModelSelect", "articleModelSelect"]) modelControls[name] = modelSelect();
vm.createContext(modelControls);
vm.runInContext(fragment("const renderActionModelSelectors =", "const renderAIProfiles =") + "this.renderModels = renderActionModelSelectors;", modelControls);
modelControls.renderModels();
assert.equal(modelControls.evidenceModelSelect.value, "old");
modelControls.renderModels(true);
for (const value of Object.values(modelControls)) {
  if (value?.options) assert.equal(value.value, "new");
}
console.log("PASS saved role assignments replace existing action model selections");

const selection = {
  currentReviewContext: () => "evidence",
  libraryEvidence: [{ id: "a" }, { id: "b" }],
  selectedEvidenceIds: new Set(["a", "b"]),
  activeSourceWorkspace: { evidence: [{ id: "a" }] },
};
vm.createContext(selection);
vm.runInContext(fragment("const selectedEvidence =", "const updateSelectAllState =")
  + "this.getSelected = selectedEvidence;", selection);
assert.equal(selection.getSelected().length, 2);
selection.currentReviewContext = () => "library";
assert.equal(selection.getSelected().length, 1);
selection.currentReviewContext = () => "artifact";
assert.equal(selection.getSelected().length, 0);

const wiki = { document, selectedClaimIds: new Set(), showPanel(target) { this.target = target; } };
vm.createContext(wiki);
vm.runInContext(fragment("const renderWikiSummary =", "const renderProjectClaimScope =")
  + "this.renderPages = renderProjectWikiPages; this.renderSummary = renderWikiSummary;", wiki);
const preview = element("div");
wiki.renderPages(preview, [{ key: "p", title: "Training", summary: "Three steps", claim_ids: ["c"] }],
  [{ id: "c", statement: "PPO optimizes the reward" }], ["Missing implementation details"]);
assert.equal(preview.children.length, 2);
assert.equal(preview.children[0].children[0].textContent, "Training");
const claimButton = preview.children[0].children[2].children[0];
assert.equal(claimButton.textContent, "PPO optimizes the reward");
claimButton.click();
assert.ok(wiki.selectedClaimIds.has("c"));
assert.equal(preview.children[1].children[0].textContent, "Knowledge gaps");
const linkedSummary = element("p");
let destination;
wiki.renderSummary(linkedSummary, "See [[claim:c|PPO]] and [[claim:missing|unavailable]].", [{key:"home",title:"Training",claim_ids:["c"]}], (page,id) => { destination = [page.key,id]; });
const links = linkedSummary.children.filter(node => node.tag === "button");
assert.equal(links.length, 1);
assert.equal(links[0].textContent, "PPO");
links[0].click();
assert.deepEqual(destination, ["home", "c"]);

const articles = { document, detail: { documents: [{ title: "Reading", content: { title: "Reading" } }] },
  documents: element("div"), artifact: { id: "project" }, card: element("article"),
  wikiReadingEl: element("div"), renderWikiReading(reading) { articles.opened = reading; } };
vm.createContext(articles);
vm.runInContext(fragment("      (detail.documents || []).forEach", "      renderProjectClaimScope(card"), articles);
assert.equal(articles.documents.children[0].textContent, "Reading");
articles.documents.children[0].click();
assert.equal(articles.opened.title, "Reading");
console.log("PASS Evidence selection, Project Wiki preview, saved Article list");

const tagFilters = {};
vm.createContext(tagFilters);
vm.runInContext(fragment("const matchesTagFilter =", "const visibleEvidence =") + "this.matches = matchesTagFilter;", tagFilters);
assert.equal(tagFilters.matches({tags:[{name:"RL"}]}, new Set(["__has_related__"]), new Set(["RL"]), 2), true);
assert.equal(tagFilters.matches({tags:[{name:"RL"}]}, new Set(["__no_related__"]), new Set(["RL"]), 2), false);
assert.equal(tagFilters.matches({tags:[]}, new Set(["__no_related__"]), new Set(), 0), true);
assert.ok(!/window\.(confirm|prompt|alert)\(/.test(code));
console.log("PASS relation filters and application dialog migration");

const search = {};
vm.createContext(search);
vm.runInContext(fragment("const mergeSearchQueryResults =", "const runSearch =")
  + "this.merge = mergeSearchQueryResults;", search);
const pages = [
  { results: [{ url: "https://paper/a", source: "arxiv" }, { url: "https://paper/b", source: "arxiv" }], usage: { n: 1 } },
  { results: [{ url: "https://paper/a/", source: "openalex" }, { url: "https://paper/c", source: "openalex" }], usage: { n: 2 } },
];
const combined = search.merge(pages, "intent", 2);
assert.equal(combined.count, 2);
assert.equal(combined.can_find_more, true);
assert.equal(combined.usage.n, 2);
assert.equal(search.merge(pages, "intent", 4).count, 3);
assert.equal(search.merge(pages, "intent", 4).can_find_more, false);

const control = (mode) => ({ hidden: false, dataset: { searchMode: mode }, classList: { toggle() {} }, setAttribute() {} });
const modes = {
  searchMode: "keyword", searchAIReview: false, searchAIReviewInput: {},
  searchModeButtons: [control("search"), control("import")],
  searchStrategyActions: [{ query: "attention" }], searchStrategyWaitingActions: [],
  document: { querySelector: () => control() },
  clearDisplayedSearchResults() {}, updateImportPrompt() {},
};
for (const name of ["searchStrategyEl", "searchImportEl", "filtersEl", "discussSearchBtn", "searchModelControl", "form", "searchSubmitBtn", "savePlanBtn", "input", "searchModeHint", "intelligentProgressEl", "statusEl"]) modes[name] = control();
vm.createContext(modes);
vm.runInContext(fragment("const setSearchMode =", "const renderDefaultSearchMode =") + "this.setMode = setSearchMode;", modes);
modes.setMode("smart"); // Legacy Intelligent Plan.
assert.equal(modes.searchAIReviewInput.checked, true);
modes.setMode("keyword"); // Legacy Keyword Plan.
assert.equal(modes.searchAIReviewInput.checked, false);
assert.equal(modes.discussSearchBtn.hidden, false);
assert.equal(modes.searchStrategyEl.hidden, false);
modes.setMode("import");
assert.equal(modes.searchStrategyEl.hidden, true);
modes.setMode("search");
assert.equal(modes.searchStrategyActions.length, 1);
assert.equal(modes.searchMode, "keyword");
console.log("PASS legacy search mapping, independent Discuss, multi-query deduplication");

(async () => {
  const calls = [];
  const raw = {
    URLSearchParams, AbortController, lastQuery: "original intent",
    lastSearchQueries: ["first query", "second query"], lastAreas: "ai.ml",
    lastBackends: ["arxiv"], lastYearFrom: "2015", lastYearTo: "",
    activeLimit: 20, activeWebPages: 1, searchController: null,
    statusEl: { scrollIntoView() {} }, resultsEl: {},
    setSearching() {}, updateUsage() {}, renderResults() {}, setFiltersCollapsed() {},
    fetch: async (url) => {
      calls.push(url);
      return { ok: true, json: async () => ({ results: [{ url: "https://paper/a", source: "arxiv" }], count: 1, usage: {}, warnings: [] }) };
    },
  };
  vm.createContext(raw);
  vm.runInContext(fragment("const mergeSearchQueryResults =", "const normalizeSearchYears =") + "this.run = runSearch;", raw);
  await raw.run();
  assert.equal(calls.length, 2);
  calls.forEach((url, index) => {
    assert.ok(url.startsWith("/api/search?"));
    const params = new URLSearchParams(url.split("?")[1]);
    assert.equal(params.get("q"), raw.lastSearchQueries[index]);
    assert.equal(params.get("year_from"), "2015");
  });
  assert.equal(raw.fullResults.length, 1);
  assert.match(raw.statusEl.textContent, /Searched 2 active queries/);
  console.log("PASS AI Review off executes Discuss queries through the non-AI endpoint");
})().catch((error) => { console.error(error); process.exitCode = 1; });
