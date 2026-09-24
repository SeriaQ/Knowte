const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const node = tag => ({tag, children: [], events: {}, disabled: false,
  append(...items) {this.children.push(...items);},
  appendChild(item) {this.children.push(item);},
  addEventListener(name, handler) {this.events[name] = handler;},
  classList: {toggle() {}},
});
const context = {
  document: {createElement: node, createTextNode: text => ({text}), getElementById: () => node("button")},
  createControlIcon: name => ({icon: name}),
  updateSelectAllState: (input, selected, total) => {input.checked = total > 0 && selected === total; input.indeterminate = selected > 0 && selected < total;},
  confirmAction: async () => true,
  evidenceProposals: [{id:"a",payload:{tags:["RL"]}}, {id:"b",payload:{tags:["NLP"]}}],
  claimProposals: [], claims: [],
  matchesTagFilter: (item, any, all) => (!any.size || item.tags.some(tag => any.has(tag.name))) && [...all].every(name => item.tags.some(tag => tag.name === name)),
};
const app = fs.readFileSync("knowte/web/app.js", "utf8");
const wikiDecisionCode = app.slice(app.indexOf("const sendWikiPatchDecision ="), app.indexOf("const renderWikiProposals ="));
vm.runInNewContext(app.slice(app.indexOf("const reviewSelections ="), app.indexOf("const setupEntityReview ="))
  + "\nthis.api = {createReviewBatchBar, reviewState, visibleReviewItems};", context);
const {createReviewBatchBar, reviewState, visibleReviewItems} = context.api;
const findButton = (bar, text) => bar.children.find(item => item.tag === "button" && item.children.some(child => child.text === text));
(async () => {
  const state = reviewState("evidence");
  state.any.add("RL");
  assert.deepEqual(Array.from(visibleReviewItems("evidence"), item => item.id), ["a"]);
  state.selected.add("a"); state.selected.add("b");
  const status = node("p");
  const filtered = createReviewBatchBar("evidence", visibleReviewItems("evidence"), async () => {}, async () => {}, status);
  assert.deepEqual([...state.selected], ["a"], "hidden selections must not be accepted accidentally");
  assert.equal(findButton(filtered.bar, "Accept selected").disabled, false);

  let refreshes = 0;
  const calls = [];
  const batch = createReviewBatchBar("partial", [{id:"a"},{id:"b"}], async (item, accepted) => {
    calls.push([item.id, accepted]); if (item.id === "b") throw new Error("test failure");
  }, async fetchData => {assert.equal(fetchData, true); refreshes++;}, status);
  batch.state.selected.add("a"); batch.state.selected.add("b"); batch.update();
  await findButton(batch.bar, "Accept selected").events.click();
  assert.deepEqual(calls, [["a",true],["b",true]]);
  assert.deepEqual([...batch.state.selected], ["b"]);
  assert.equal(batch.state.busy, false);
  assert.equal(refreshes, 1);
  assert.match(status.textContent, /1 accepted.*1 failed/);

  const relationOrder = [];
  const relationBatch = createReviewBatchBar("claim", [
    {id:"relation", payload:{operation:"create_relation"}},
    {id:"claim-a", payload:{operation:"create_claim"}},
    {id:"claim-b", payload:{operation:"create_claim"}},
  ], async item => relationOrder.push(item.id), async () => {}, status);
  ["relation", "claim-a", "claim-b"].forEach(id => relationBatch.state.selected.add(id));
  relationBatch.update();
  await findButton(relationBatch.bar, "Accept selected").events.click();
  assert.deepEqual(relationOrder, ["claim-a", "claim-b", "relation"], "accept endpoint drafts before relations, regardless of display order");

  let applied = 0;
  const wiki = createReviewBatchBar("wiki-test", [{id:"a"},{id:"b"}], async () => {applied++;}, async () => {}, status, {singleAccept:true});
  wiki.state.selected.add("a"); wiki.state.selected.add("b"); wiki.update();
  assert.equal(findButton(wiki.bar, "Accept selected").disabled, true);
  await findButton(wiki.bar, "Accept selected").events.click();
  assert.equal(applied, 0);
  await findButton(wiki.bar, "Discard selected").events.click();
  assert.equal(applied, 2);
  const decisions = [];
  const dispute = createReviewBatchBar("claim-dispute-test", [
    {id:"new",payload:{operation:"create_claim"}},
    {id:"changed",payload:{operation:"review_evidence_change"}},
    {id:"links",payload:{operation:"link_evidence"}},
  ], async (item, decision) => {decisions.push([item.id, decision]);}, async () => {}, status,
  {canDispute: item => ["create_claim", "review_evidence_change"].includes(item.payload.operation)});
  const disputeButton = findButton(dispute.bar, "Keep selected disputed");
  assert.equal(disputeButton.disabled, true);
  dispute.state.selected.add("new"); dispute.state.selected.add("links"); dispute.update();
  assert.equal(disputeButton.disabled, true);
  await disputeButton.events.click();
  assert.equal(decisions.length, 0);
  dispute.state.selected.delete("links"); dispute.state.selected.add("changed"); dispute.update();
  assert.equal(disputeButton.disabled, false);
  await disputeButton.events.click();
  assert.deepEqual(decisions, [["new", "disputed"], ["changed", "disputed"]]);
  assert.match(status.textContent, /2 kept disputed/);
  assert.equal(dispute.state.selected.size, 0);
  assert.equal(findButton(filtered.bar, "Keep selected disputed"), undefined);
  const wikiContext = {
    wikiProposals: [{id:"a"}, {id:"b"}],
    activeWikiProposalPageKeys: new Map([["a", "page"]]),
    wikiStatusEl: {}, wikiProposalListEl: {append() {}},
    wikiRefreshVersion:0, activeWikiProposalId:"a", reviewState:()=>({selected:new Set()}), currentReviewContext:()=>"search",
    fetch: async url => {if (url.endsWith("/b")) throw new Error("Deletion failed"); return {ok:true,json:async()=>({})};},
    createReviewBatchBar: (key, items, decide, refresh) => {wikiContext.decide = decide; wikiContext.refresh = refresh; return {bar:{}};},
    renderWiki: () => {wikiContext.renderedIds = wikiContext.wikiProposals.map(item => item.id);},
    fetchWiki: async () => {throw new Error("Refresh failed");},
  };
  const wikiStart = app.indexOf('  const batch = createReviewBatchBar("wiki",');
  wikiContext.fetchWikiLocal = (...args) => wikiContext.fetch(...args);
  vm.runInNewContext(wikiDecisionCode + app.slice(wikiStart, app.indexOf("  wikiProposals.forEach", wikiStart)), wikiContext);
  await wikiContext.decide({id:"a"}, false);
  await assert.rejects(wikiContext.decide({id:"b"}, false), /Deletion failed/);
  assert.deepEqual(Array.from(wikiContext.wikiProposals, item => item.id), ["b"]);
  assert.equal(wikiContext.activeWikiProposalPageKeys.has("a"), false);
  await wikiContext.refresh(true);
  assert.deepEqual(wikiContext.renderedIds, ["b"], "confirmed deletions are rendered even if refresh fails");
  const emptyWiki = {wikiProposals: [], activeWikiProposalId:"old", wikiProposalReviewEl:{hidden:false}};
  const renderStart = app.indexOf("const renderWiki = () => {") + "const renderWiki = () => {".length;
  const guardEnd = app.indexOf("\n  }", renderStart) + 4;
  vm.runInNewContext(app.slice(renderStart, guardEnd), emptyWiki);
  assert.equal(emptyWiki.wikiProposalReviewEl.hidden, true);
  assert.equal(emptyWiki.activeWikiProposalId, "");
  const renderDispatchStart = app.indexOf("  if (!wikiMainEl.hidden) {", app.indexOf("const renderWiki ="));
  const renderDispatch = app.slice(renderDispatchStart, app.indexOf("\n};", renderDispatchStart));
  for (const visible of ["main", "patch", "graph", "import"]) {
    const rendered = [];
    vm.runInNewContext(renderDispatch, {
      wikiMainEl:{hidden:visible !== "main"}, wikiGraphEl:{hidden:visible !== "graph"},
      wikiProposalReviewEl:{hidden:visible !== "patch"}, wikiImportReviewEl:{hidden:visible !== "import"},
      renderWikiTree:()=>rendered.push("tree"), renderWikiPage:()=>rendered.push("page"),
      renderWikiGraph:()=>rendered.push("graph"), renderWikiProposals:()=>rendered.push("patch"),
      renderWikiImports:()=>rendered.push("import"),
    });
    assert.deepEqual(rendered, visible === "main" ? ["tree", "page"] : [visible]);
  }
  const appliedWiki = {pages:[], claims:[]};
  const applyContext = {
    wikiRefreshVersion:0, reviewState:()=>({selected:new Set()}),
    wikiStatusEl:{}, wikiState:{}, wikiProposals:[{id:"apply"}],
    activeWikiProposalPageKeys:new Map(), activeWikiProposalId:"apply",
    wikiProposalReviewEl:{hidden:false}, renderWiki:()=>{}, currentReviewContext:()=>"search",
    fetch:async()=>({ok:true,json:async()=>appliedWiki}),
    fetchWiki:async()=>{throw new Error("Redundant reload");},
  };
  const applyStart = app.indexOf("const acceptWikiProposal =");
  applyContext.fetchWikiLocal = (...args) => applyContext.fetch(...args);
  vm.runInNewContext(wikiDecisionCode + app.slice(applyStart, app.indexOf("const discardWikiProposal =", applyStart)) + "\nthis.apply = acceptWikiProposal;", applyContext);
  await applyContext.apply("apply");
  assert.equal(applyContext.wikiState, appliedWiki);
  assert.equal(applyContext.wikiProposals.length, 0);
  assert.equal(applyContext.wikiProposalReviewEl.hidden, true);
  const originalWiki = {pages:[{id:"home", title:"Existing Wiki"}], claims:[]};
  const sequence = {
    wikiRefreshVersion:0,
    wikiProposals:[], wikiState:originalWiki, activeWikiProposalId:"",
    wikiEditStructureBtn:{disabled:false}, wikiStatusEl:{}, wikiImportReviewEl:{hidden:true},
    wikiProposalReviewEl:{hidden:true}, activeWikiProposalPageKeys:new Map(),
    renderWiki:()=>{}, currentReviewContext:()=>"search", reviewState:()=>({selected:new Set()}),
    fetchWiki:async()=>{throw new Error("Must not reload the whole Wiki");},
    fetch:async(url, options)=> options.method === "POST"
      ? {ok:true,json:async()=>({proposal:{id:"draft",payload:{pages:[]}}})}
      : {ok:true,json:async()=>({})},
  };
  const editStart = app.indexOf("const editWikiStructure =");
  sequence.fetchWikiLocal = (...args) => sequence.fetch(...args);
  const discardEnd = app.indexOf("const editWikiReading =", editStart);
  vm.runInNewContext(wikiDecisionCode + app.slice(editStart, discardEnd) + "\nthis.edit = editWikiStructure; this.discard = discardWikiProposal;", sequence);
  await sequence.edit();
  assert.equal(sequence.wikiProposals.length, 1);
  assert.equal(sequence.wikiProposalReviewEl.hidden, false);
  await sequence.discard("draft");
  assert.equal(sequence.wikiProposals.length, 0);
  assert.equal(sequence.wikiProposalReviewEl.hidden, true);
  assert.equal(sequence.wikiState, originalWiki);
  assert.equal(sequence.wikiStatusEl.textContent, "Wiki Patch discarded.");
  sequence.wikiProposals = [{id:"keep"}];
  sequence.fetch = async()=>{throw new Error("Connection lost");};
  await sequence.discard("keep");
  assert.equal(sequence.wikiProposals.length, 1);
  assert.equal(sequence.wikiStatusEl.textContent, "Connection lost");
  const persistStart = app.indexOf("const persistWikiProposal =");
  const saveContext = {wikiRefreshVersion:0, wikiStatusEl:{}, wikiProposals:[{id:"draft",_dirty:true}],
    fetch:async()=>{throw new Error("Save offline");}, renderWikiProposals:()=>{}};
  saveContext.fetchWikiLocal = (...args) => saveContext.fetch(...args);
  vm.runInNewContext(app.slice(persistStart, app.indexOf("const sendWikiPatchDecision =", persistStart)) + "\nthis.save = persistWikiProposal;", saveContext);
  assert.equal(await saveContext.save(saveContext.wikiProposals[0]), false);
  assert.equal(saveContext.wikiProposals[0]._dirty, true);
  assert.equal(saveContext.wikiStatusEl.textContent, "Save offline");
  const refreshStart = app.indexOf("let wikiRefreshVersion = 0;");
  const refreshContext = {wikiProposals:[{id:"draft",_dirty:true,payload:{title:"local edit"}}],
    wikiStatusEl:node("small"), document:{createElement:node},
    wikiState:{},wikiImports:[], reviewState:()=>({busy:false}),renderWiki:()=>{},currentReviewContext:()=>"search",
    fetch:async url=>({ok:true,json:async()=>url.endsWith('/proposals') ? {proposals:[{id:"draft",payload:{title:"server"}}]} : url.endsWith('/imports') ? {imports:[]} : {pages:[]}})};
  refreshContext.fetchWikiLocal = (...args) => refreshContext.fetch(...args);
  vm.runInNewContext(app.slice(refreshStart, app.indexOf("const generateWikiProposal =", refreshStart)) + "\nthis.refresh = fetchWiki; this.invalidate = () => {wikiRefreshVersion++;};", refreshContext);
  await refreshContext.refresh();
  assert.equal(refreshContext.wikiProposals[0].payload.title, "local edit");
  const savedState = refreshContext.wikiState;
  const pendingRefresh = refreshContext.refresh();
  refreshContext.invalidate();
  await pendingRefresh;
  assert.equal(refreshContext.wikiState, savedState, "late fetch must not overwrite a newer mutation");
  let releaseImports;
  const loadedWiki = {pages:[{id:"loaded"}]};
  refreshContext.fetch = async url => {
    if (url.endsWith("/imports")) await new Promise(resolve => {releaseImports = resolve;});
    return {ok:true,json:async()=>url === "/api/wiki" ? loadedWiki : {proposals:[]}};
  };
  const partialLoad = refreshContext.refresh();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(refreshContext.wikiState, loadedWiki, "slow imports must not block Wiki content");
  releaseImports(); await partialLoad;
  refreshContext.fetch = async url => {
    if (url.endsWith("/proposals")) throw new Error("Offline");
    return {ok:true,json:async()=>url === "/api/wiki" ? loadedWiki : {imports:[]}};
  };
  await refreshContext.refresh();
  assert.equal(refreshContext.wikiState, loadedWiki);
  assert.match(refreshContext.wikiStatusEl.textContent, /\/api\/wiki\/proposals: Offline/);
  assert.equal(refreshContext.wikiStatusEl.children.at(-1).textContent, "Reload Wiki");
  const localRequestContext = {AbortController, clearTimeout, setTimeout: callback => setTimeout(callback, 5),
    fetch:async (url, {signal}) => ({ok:true,json:()=>new Promise((resolve,reject) => {
      signal.addEventListener("abort", () => reject(new Error("Aborted")));
    })})};
  vm.runInNewContext(app.slice(app.indexOf("const fetchWikiLocal ="), persistStart) + "\nthis.request = fetchWikiLocal;", localRequestContext);
  await assert.rejects(localRequestContext.request("/api/wiki"), /timed out/);
  const actionStart = app.indexOf("    const runAction = async (action, progress) =>", app.indexOf("const renderWikiProposals ="));
  const actionEnd = app.indexOf("    discard.addEventListener", actionStart);
  const button = {disabled:false};
  const draft = {id:"feedback"};
  const actionContext = {batch:{state:{busy:false},update(){}}, actionStatus:{}, wikiStatusEl:{},
    wikiProposalListEl:{querySelectorAll:()=>[button]}, wikiProposals:[draft], proposal:draft,
    wikiProposalReviewEl:{hidden:false}, renderWikiProposals(){}};
  vm.runInNewContext(app.slice(actionStart, actionEnd) + "\nthis.run = runAction;", actionContext);
  await actionContext.run(async()=>{
    assert.equal(actionContext.actionStatus.textContent, "Applying…");
    assert.equal(button.disabled, true);
    throw new Error("A Page title is required");
  }, "Applying…");
  assert.equal(draft._actionStatus, "A Page title is required", "error stays beside actions after rerender");
  assert.equal(button.disabled, false);
  assert.equal(actionContext.batch.state.busy, false);
  console.log("Review batch checks passed");
})().catch(error => {console.error(error); process.exitCode = 1;});
