const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('knowte/web/app.js', 'utf8');
let handler;
const opened = [];
const context = {plansListEl: {addEventListener: (_, fn) => {handler = fn;}}, plansView: 'plans',
  savedPlans: [{id: 'p'}], openPlanDetail: id => opened.push(id)};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('plansListEl.addEventListener("click"'), source.indexOf('\nnavLinks.forEach', source.indexOf('plansListEl.addEventListener("click"'))), context);
const card = {dataset: {planId: 'p'}, classList: {contains: value => value === 'plan-list-row'}};
const event = (button, interactive = false) => ({target: {closest: selector => selector === '[data-plan-id]' ? card : selector === 'button[data-plan-action]' ? button : interactive ? {} : null}});
(async () => {
  await handler(event(null));
  await handler(event({dataset: {planAction: 'select-plan'}}));
  await handler(event(null, true));
  assert.deepEqual(opened, ['p', 'p']);
  console.log('PASS Plan name and row open details; other interactive controls do not');
})().catch(error => {console.error(error); process.exitCode = 1;});
