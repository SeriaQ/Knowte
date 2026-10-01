const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const app = fs.readFileSync("knowte/web/app.js", "utf8");
for (const id of ["wiki-call-estimate", "wiki-call-detail"])
  assert.ok(app.includes(`document.getElementById("${id}").hidden = wikiState.view === "projected"`));
const button = () => ({disabled: false, classList: {toggle() {}}, setAttribute() {}});
const context = {
  wikiState: {view: "projected", claims: [{id: "proposal:one", lifecycle: "active"}], pages: []},
  wikiProposals: [], wikiProposalRunning: false, reviewState: () => ({busy: false}),
  wikiOrganizeBtn: button(), wikiEditStructureBtn: button(), wikiResetStructureBtn: button(),
};
const start = app.indexOf("const renderWikiIncoming =");
vm.runInNewContext(app.slice(start, app.indexOf("const renderWikiPage =", start)) + "renderWikiIncoming();", context);
for (const key of ["wikiOrganizeBtn", "wikiEditStructureBtn", "wikiResetStructureBtn"]) {
  assert.equal(context[key].disabled, true, `${key} must not mutate reviewed pages from projection`);
}
const calls = [];
const state = {any: new Set(["filtered"]), all: new Set(["filtered"])};
const navigation = {
  claimProposals: [{id: "one", payload: {operation: "create_claim"}}],
  fetchClaimProposals: async () => calls.push("refresh"),
  reviewState: () => state,
  showPanel: id => calls.push(id), renderClaimProposals() {}, scrollClaimProposalQueueToStart() {},
  document: {getElementById: id => ({scrollIntoView: () => calls.push(id)})},
  wikiStatusEl: {}, claimProposalQueueOpen: false, claimReviewCategory: "changed",
};
const openStart = app.indexOf("const openClaimFromWiki =");
vm.runInNewContext(app.slice(openStart, app.indexOf("const wikiPageDepth =", openStart)) + "this.open = openClaimFromWiki;", navigation);
(async () => {
  await navigation.open("proposal:one");
  assert.deepEqual(calls, ["refresh", "claims-panel", "claim-proposal-one"]);
  assert.equal(navigation.claimReviewCategory, "proposals");
  assert.equal(navigation.claimProposalQueueOpen, true);
  assert.equal(state.any.size + state.all.size, 0);
  navigation.claimProposals[0].payload.operation = "review_evidence_change";
  await navigation.open("proposal:one");
  assert.equal(navigation.claimReviewCategory, "changed");
  const busy = {busy: false};
  const reviewContext = {reviewState: () => busy, wikiRefreshVersion: 0,
    renderWiki() {}, wikiStatusEl: {}, wikiKnowledgeView: "projected", wikiKnowledgeViewSelect: {value: "projected"},
    fetchWiki: async () => {}, wikiProposalReviewEl: {hidden: true}, wikiImportReviewEl: {hidden: true}, activeWikiProposalId: "",
    fetchWikiLocal: async (url, options) => {
      assert.equal(url, "/api/wiki/projection/review");
      assert.equal(JSON.parse(options.body).projection_id, "projection");
      return {ok: true, json: async () => ({proposal: {id: "draft"}})};
    }};
  const reviewStart = app.indexOf("const reviewProjectedWiki =");
  vm.runInNewContext(app.slice(reviewStart, app.indexOf("const editWikiStructure =", reviewStart)) + "this.review = reviewProjectedWiki;", reviewContext);
  await reviewContext.review("projection");
  assert.equal(reviewContext.activeWikiProposalId, "draft");
  assert.equal(reviewContext.wikiProposalReviewEl.hidden, false);
  assert.equal(reviewContext.wikiKnowledgeView, "reviewed");
  assert.equal(busy.busy, false);
  reviewContext.fetchWikiLocal = async () => ({ok: false, json: async () => ({message: "Review Claims first"})});
  await reviewContext.review("projection");
  assert.equal(reviewContext.wikiStatusEl.textContent, "Review Claims first");
  assert.equal(busy.busy, false);
  console.log("PASS projected Wiki mutation guards and pending Claim review navigation");
})().catch(error => {console.error(error); process.exitCode = 1;});
