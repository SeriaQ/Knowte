const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync('knowte/web/app.js', 'utf8');
const node = () => ({children: [], events: {}, append(...items) {this.children.push(...items);}, replaceChildren() {this.children = [];}, setAttribute() {}, addEventListener(type, fn) {this.events[type] = fn;}});
const panel = node();
let writes = [];
const context = {document: {querySelector: () => panel, createElement: node},
  selectedPlanActionIds: new Set(['a', 'b']), selectedDestinationPlanId: 'p', plansView: 'actions', choosePlanForActions() { writes.push('choose'); },
  savedActions: [{id:'a', name:'Search'}, {id:'b', name:'Channel'}],
  savedPlans: [{id:'p', name:'Daily', actions:[{action_id:'a'}]}],
  fetchAutomationCatalog: async () => true, plansStatusEl: node(), renderReviewWorkspace() {}, renderPlans() {},
  writeAutomation: async (payload) => {writes.push(payload);},
};
vm.createContext(context);
vm.runInContext(code.slice(code.indexOf('function renderPlanActionSelection('), code.indexOf('const editChannel =')), context);
(async () => {
  context.renderPlanActionSelection('plans');
  assert.equal(panel.hidden, false);
  const add = panel.children.find(item => item.textContent === 'Add to Plan…');
  assert.equal(add.disabled, false);
  await add.events.click();
  assert.equal(writes[0], 'choose');
  context.renderPlanActionSelection('search');
  assert.equal(panel.hidden, true);
  assert.equal(context.selectedPlanActionIds.size, 2);
  context.renderPlanActionSelection('plans');
  panel.children.find((item) => item.textContent === 'Clear').events.click();
  assert.equal(context.selectedPlanActionIds.size, 0);
  context.plansView = 'plans'; context.renderPlanActionSelection('plans');
  assert.ok(panel.children[0].textContent.includes('Daily'));
  console.log('PASS Action selection uses an explicit destination dialog and supports clearing');
})().catch((error) => { console.error(error); process.exitCode=1; });
