const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('knowte/web/app.js', 'utf8');
const controls = ['status', 'setup', 'start', 'stop', 'reboot', 'remove'].map(operation => ({dataset: {rsshub: operation}}));
const elements = Object.fromEntries(['rsshub-status', 'rsshub-state', 'rsshub-status-detail'].map(id => ['#' + id, {dataset: {}, textContent: ''}]));
const context = vm.createContext({document: {querySelectorAll: () => controls, querySelector: id => elements[id]}});
vm.runInContext(source.slice(source.indexOf('const renderRsshubStatus ='), source.indexOf('document.querySelector("#rsshub-edit-env").addEventListener')), context);
function check(data, enabled) {
  vm.runInContext(`renderRsshubStatus(${JSON.stringify(data)})`, context);
  assert.deepEqual(controls.filter(button => !button.disabled).map(button => button.dataset.rsshub).sort(), enabled.sort());
  for (const button of controls.filter(button => button.disabled)) assert.ok(button.title);
}
check({}, ['status']);
check({state: 'not installed'}, ['status', 'setup']);
check({state: 'running'}, ['status', 'stop', 'reboot', 'remove']);
check({state: 'exited'}, ['status', 'start', 'reboot', 'remove']);
check({state: 'created'}, ['status', 'start', 'reboot', 'remove']);
check({state: 'running', running: true, message: 'Working'}, []);
check({error: true}, ['status']);
assert.equal(elements['#rsshub-status'].dataset.state, 'error');
console.log('PASS RSSHub controls follow service state and recover after errors');
