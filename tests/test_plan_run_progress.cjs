const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('knowte/web/app.js', 'utf8');
const context = vm.createContext({});
vm.runInContext(source.slice(source.indexOf('const planRunProgress ='), source.indexOf('const showPlanRuns =')) + '\nthis.progress = planRunProgress;', context);
assert.equal(context.progress({status: 'completed'}), null);
assert.match(context.progress({status: 'queued'}), /Queued/);
assert.match(context.progress({status: 'running', actions: [{status: 'running', action_name: 'RL', report: {progress: 'Fetching · arxiv'}}]}), /Action 1\/1 · RL · Fetching · arxiv/);
for (const [stage, label] of Object.entries({evidence: 'Proposing Evidence', claims: 'Proposing Claims', relations: 'Finding Relations', wiki: 'Organizing Projected Wiki'})) {
  const text = context.progress({status: 'running', knowledge_jobs: [{stage, status: 'completed'}, {stage, status: 'running'}]});
  assert.ok(text.includes(label));
  assert.ok(text.includes('1 batches finished'));
}
assert.match(context.progress({status: 'running', ingestion: {}}), /Preparing next knowledge stage/);
console.log('PASS Run progress covers queued, acquisition, all knowledge stages and completion');
