const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const code = fs.readFileSync("knowte/web/app.js", "utf8");
const start = code.indexOf("const fetchClaimProposals =");
const end = code.indexOf("const scrollClaimProposalQueueToStart", start);
const context = {
  claimProposals: [{id: "child", payload: {_draftEdited: true, statement: "My edit", basis: "inference",
    evidence: [{evidence_id: "proposal:old"}], blocked_reason: "Old pending guard"}}],
  fetch: async () => ({ok: true, json: async () => ({proposals: [{id: "child", derivation: {status: "stale"},
    payload: {statement: "Original", basis: "reported", evidence: [{evidence_id: "accepted"}], blocked_reason: "New stale guard"}}]})}),
  renderClaimProposals() {},
};
vm.createContext(context);
vm.runInContext(code.slice(start, end) + "this.refresh = fetchClaimProposals;", context);
(async () => {
  await context.refresh();
  const item = context.claimProposals[0];
  assert.equal(item.payload.statement, "My edit");
  assert.equal(item.payload.basis, "inference");
  assert.equal(item.payload.blocked_reason, "New stale guard");
  assert.equal(item.payload.evidence[0].evidence_id, "accepted");
  assert.equal(item.derivation.status, "stale");
  assert.match(code, /if \(payload.blocked_reason\) \{ accept.disabled = true; keepDisputed.disabled = true; \}/);
  console.log("PASS edited drafts preserve current dependency IDs and review guards");
})().catch(error => { console.error(error); process.exitCode = 1; });
