const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const code = fs.readFileSync("knowte/web/app.js", "utf8");
const html = fs.readFileSync("knowte/web/index.html", "utf8");
const fragment = (start, end) => code.slice(code.indexOf(start), code.indexOf(end, code.indexOf(start)));
const reconcileEditingAction = code.match(/editingSearchAction = savedActions\.find\(\(action\) => action\.id === editingSearchAction\?\.id\) \|\| null;/)[0];
const editingContext = vm.createContext({editingSearchAction: {id: "deleted"}, savedActions: [{id: "remaining"}]});
vm.runInContext(reconcileEditingAction, editingContext);
assert.equal(editingContext.editingSearchAction, null, "Deleted Actions must save as new, not update");
editingContext.editingSearchAction = {id: "remaining", version: 1};
editingContext.savedActions = [{id: "remaining", version: 2}];
vm.runInContext(reconcileEditingAction, editingContext);
assert.equal(editingContext.editingSearchAction.version, 2, "Editing uses the refreshed catalog version");
assert.ok(html.indexOf('data-search-mode="search"') < html.indexOf('data-search-mode="subscribe"'));
assert.ok(html.indexOf('data-search-mode="subscribe"') < html.indexOf('data-search-mode="import"'));
assert.match(html, /id="save-plan">Save Action</);
assert.match(html, /data-target="search-panel">Discover</);
assert.ok(!html.includes('id="subscription-add"'));
assert.match(html, /id="subscription-form"/);
assert.match(html, /id="subscription-save"[^>]*>Save Channel</);
assert.match(html, /class="save-plan-btn stage-save-action" id="copy-import-prompt"/);

const node = (tag) => ({tag, children: [], dataset: {}, events: {},
  classList: {add() {}},
  setAttribute() {},
  append(...items) {this.children.push(...items);}, appendChild(item) {this.children.push(item);},
  addEventListener(name, handler) {this.events[name] = handler;},
});
const context = {
  document: {createElement: node, querySelectorAll: () => [], querySelector: id => filters[id] || node("section")},
  planDetailTab: "overview", planActionPickerOpen: false, openPlanDetail() {},
  plansListEl: node("div"), plansView: "plans",
  selectedPlanActionIds: new Set(), renderReviewWorkspace() {},
  selectedDestinationPlanId: "",
  automationCheckbox(parent, text, checked) { const input = node("input"); input.checked = checked; parent.append(input); return input; },
  savedActions: [{id: "a", name: "Action", version: 1, config: {query: "RL", sources: ["arxiv"]}, used_by: [{id: "p", name: "Daily"}]}],
  savedPlans: [{id: "p", name: "Daily", enabled: true, actions: [{action_id: "a"}]}],
};
const filters = {'#action-library-search': {value: ''}, '#action-library-kind': {value: ''}};
vm.createContext(context);
vm.runInContext(fragment("const sourceDisplayName =", "const fetchPlans =") + "this.render = renderPlans;", context);
context.render();
const text = (item) => [item.textContent || "", ...item.children.map(text)].join(" ");
assert.match(text(context.plansListEl), /Daily.*Manual.*1 Actions.*Run Now.*Delete/);
assert.ok(!text(context.plansListEl).includes("⋯"));
assert.ok(text(context.plansListEl).includes("Run Now"));
assert.ok(!text(context.plansListEl).includes("Open Plan"));
context.selectedDestinationPlanId = 'p'; context.plansListEl.children = []; context.render();
assert.match(text(context.plansListEl), /Overview.*Runs.*Actions · 1.*Add Actions/);
assert.match(text(context.plansListEl), /Remove/);
context.selectedDestinationPlanId = '';
context.plansView = "actions"; context.plansListEl.children = []; context.render();
assert.match(text(context.plansListEl), /Used by 1 Plans: Daily/);
assert.match(text(context.plansListEl), /Test Run/);
context.savedActions.push({id: "channel-c", kind: "subscribe", name: "My Channel", version: 1, config: {subscription_ids: ["c"]}, used_by: []});
context.plansListEl.children = []; context.render();
assert.match(text(context.plansListEl), /My Channel/);
assert.match(text(context.plansListEl), /Test Fetch/);
filters['#action-library-search'].value = 'channel'; context.plansListEl.children = []; context.render();
assert.match(text(context.plansListEl), /My Channel/);
assert.ok(!text(context.plansListEl).includes('Test Run'));
filters['#action-library-search'].value = ''; filters['#action-library-kind'].value = 'subscribe'; context.plansListEl.children = []; context.render();
assert.ok(!text(context.plansListEl).includes('Test Run'));
filters['#action-library-kind'].value = ''; context.plansListEl.children = []; context.render();
assert.ok(!text(context.plansListEl).includes("Add to Plan…"), "Add to Plan belongs only in the side panel");
const selection = () => context.plansListEl.children.find(item => item.className === 'action-library-selection').children[0];
assert.equal(selection().checked, false);
selection().checked = true; selection().events.change();
assert.equal(context.selectedPlanActionIds.size, 2);
context.plansListEl.children = []; context.render();
assert.equal(selection().checked, true);
context.selectedPlanActionIds.delete('a'); context.plansListEl.children = []; context.render();
assert.equal(selection().indeterminate, true);
selection().checked = false; selection().events.change();
assert.equal(context.selectedPlanActionIds.size, 0);
context.savedActions = []; context.plansListEl.children = []; context.render();
assert.equal(selection().disabled, true);

const areas = {actionAreaOverride: null, activePresets: new Set(), PRESETS: {AI: ["ai.ml", "ai.rl"]},
  renderPresetState() {}, renderSelectedAreas() {}};
vm.createContext(areas);
vm.runInContext(fragment("const getEffectiveAreas =", "const renderSelectedAreas =")
  + fragment("const restorePlanAreas =", "const loadPlanIntoSearch =")
  + "this.restore = restorePlanAreas; this.areas = getEffectiveAreas;", areas);
areas.restore(["ai.rl"]);
assert.deepEqual([...areas.areas()], ["ai.rl"]);
areas.restore(["ai.ml", "ai.rl"]);
assert.deepEqual([...areas.areas()], ["ai.ml", "ai.rl"]);
areas.restore([]); assert.equal(areas.areas().size, 0);

assert.match(fragment('if (action === "run")', 'if (action === "edit")'), /form.requestSubmit/);
assert.doesNotMatch(fragment('if (action === "run")', 'if (action === "edit")'), /last_run_at|method: "PUT"/);
console.log("PASS Discover ordering, Plan/Action cards, legacy area restoration and checkpoint-free Test Run");

assert.match(code, /target === "evidence-panel"\) Promise.all\(\[fetchEvidenceLibrary\(\), fetchEvidenceProposals\(\)\]\)/);
assert.doesNotMatch(html, /Projected Wiki is not connected yet/);
const endpoints = {claimProposals: [{id: "pending", payload: {statement: "Pending policy Claim"}}],
  claims: [{id: "accepted", statement: "Accepted reward Claim"}]};
vm.createContext(endpoints);
vm.runInContext(fragment("const endpointLabel =", "const subject = document.createElement")
  + "this.label = endpointLabel;", endpoints);
assert.equal(endpoints.label("proposal:pending"), "Pending policy Claim");
assert.equal(endpoints.label("accepted"), "Accepted reward Claim");
assert.equal(endpoints.label("missing"), "Unavailable Claim");
const mergePreview = {targetLabel: node("small"), target: node("div"), document: {createElement: node},
  payload: {target_claim_id: "a", source_claim_id: "b"},
  claims: [{id: "a", statement: "Keep policy definition"}, {id: "b", statement: "Merge duplicate definition"}],
  renderEvidenceText: (element, value) => {element.textContent = value;}};
vm.createContext(mergePreview);
vm.runInContext(fragment('targetLabel.textContent = "Keep and consolidate into";',
  '    if (payload.blocked_reason &&').replace(/\s*}\s*$/, ''), mergePreview);
assert.match(text(mergePreview.target), /Keep policy definition.*Merge duplicate definition/);
assert.match(code, /run.processing\?\.knowledge_only \? "Knowledge recomputation only/);

(async () => {
  const refreshed = [], activities = [];
  const poll = {
    plansStatusEl: {}, savedPlans: [{id: "p", last_run: {id: "run", status: "running"}}],
    savedActions: [], evidenceProposals: [{}], claimProposals: [{}],
    planRunPollTimer: 1, planRunHistoryId: null,
    window: {clearInterval() {}},
    fetch: async () => ({ok: true, json: async () => ({plans: [{id: "p", last_run: {id: "run", status: "completed"}}]})}),
    setTabActivity: (...args) => activities.push(args.join(":")),
    renderPlans() {}, renderReviewWorkspace() {},
  };
  for (const name of ["fetchEvidenceProposals", "fetchClaimProposals", "fetchLibrary", "fetchClaims", "fetchWiki"])
    poll[name] = async () => {
      refreshed.push(name);
      if (name === "fetchEvidenceProposals") poll.evidenceProposals = [{id: "new-evidence"}];
      if (name === "fetchClaimProposals") poll.claimProposals = [{id: "new-claim"}];
    };
  vm.createContext(poll);
  vm.runInContext(fragment("const fetchPlans =", "const saveCurrentPlan =") + "this.refresh = fetchPlans;", poll);
  await poll.refresh();
  assert.equal(refreshed.length, 5);
  assert.ok(activities.includes("evidence-panel:result"));
  assert.ok(activities.includes("claims-panel:result"));
  await poll.refresh();
  assert.equal(refreshed.length, 5, "Completed runs must not repeatedly refresh knowledge");
  activities.length = 0;
  poll.savedPlans[0].last_run.status = "running";
  await poll.refresh();
  assert.equal(refreshed.length, 10);
  assert.ok(!activities.includes("evidence-panel:result"), "Old Evidence is not new output from a source-only Run");
  assert.ok(!activities.includes("claims-panel:result"), "Old Claims are not new output from a source-only Run");
  poll.savedPlans[0].last_run = null;
  await poll.refresh();
  assert.equal(refreshed.length, 15, "A first Run completing before its first poll must also refresh knowledge");
  console.log("PASS automation completion refreshes review queues once");
})().catch(error => {console.error(error); process.exitCode = 1;});
