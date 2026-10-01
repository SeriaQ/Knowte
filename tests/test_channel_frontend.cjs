const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const code = fs.readFileSync("knowte/web/app.js", "utf8");
const html = fs.readFileSync("knowte/web/index.html", "utf8");
const fragment = (start, end) => code.slice(code.indexOf(start), code.indexOf(end, code.indexOf(start)));
const fields = new Map();
const element = () => ({value: "", checked: false, disabled: false, hidden: false, dataset: {}, children: [],
  replaceChildren() {this.children = [];}, append(...items) {this.children.push(...items);}, addEventListener() {},
  querySelectorAll() { return this.children.flatMap((label) => label.children || []).filter((input) => input.type === "checkbox" && input.checked); },
  querySelector() { return this.children.flatMap((label) => label.children || []).find((input) => input.type === "text"); },
});
const field = (id) => {if (!fields.has(id)) fields.set(id, element()); return fields.get(id);};
const context = {document: {getElementById: field, querySelector: (id) => field(id.slice(1)), createElement: element, createTextNode: (text) => text}};
vm.createContext(context);
vm.runInContext(fragment("const connectorSecretKeys =", "const serializeProfileState =") + "this.load = loadConnectorSettings; this.payload = connectorSettingsPayload;", context);
context.load({github_token_configured: true, rsshub_base_url: "http://localhost:1200"});
assert.ok(!("werss_mode" in context.payload()));
assert.equal(field("github-token").value, "");
assert.match(field("github-token").placeholder, /Saved/);
field("github-token").value = "new-secret";
field("clear-github-token").checked = true;
assert.equal(context.payload().github_token, "new-secret");
assert.equal(context.payload().clear_github_token, true);
context.load({github_token_configured: true});
assert.equal(field("github-token").value, "");
assert.equal(field("clear-github-token").checked, false);
context.load({rsshub_env_file: "/private/rsshub.env"});
assert.equal(context.payload().rsshub_env_file, undefined);
assert.ok(!html.includes('id="rsshub-env-file"'));
assert.ok(html.includes('data-rsshub="reboot"'));

field("subscription-connector").value = "github";
vm.runInContext(fragment("let detectedChannels =", 'document.querySelector("#subscription-choice").addEventListener')
  + "this.reset = resetChannelDetection; this.renderChoice = renderChannelChoice; this.choose = (items) => {detectedChannels = items;};", context);
context.reset();
assert.equal(field("subscription-save").disabled, true);
context.choose([{kind: "github", name: "GitHub", event_types: ["ReleaseEvent"]}]);
field("subscription-choice").value = "0";
context.renderChoice();
assert.equal(field("subscription-name").value, "GitHub");
assert.equal(field("subscription-scope").children.length, 7);
assert.equal(field("subscription-scope").children.filter((label) => label.children[0].checked).length, 1);
context.choose([{kind: "github_repo", name: "pytest", scopes: []}]);
context.renderChoice();
assert.equal(field("subscription-save").disabled, true);
assert.equal(field("subscription-preview").disabled, true);
assert.equal(field("subscription-scope").querySelector().disabled, true);
context.choose([{kind: "github_repo", name: "pytest", scopes: ["commits"]}]);
context.renderChoice();
assert.equal(field("subscription-save").disabled, false);
assert.equal(field("subscription-scope").querySelector().disabled, false);
field("subscription-connector").value = "others"; context.reset();
assert.equal(field("subscription-save").disabled, true);
assert.equal(field("subscription-preview-list").hidden, true);
assert.ok(html.includes('data-rsshub="setup"'));
assert.ok(html.includes('id="subscription-preview"'));
for (const id of ["subscription-address", "rsshub-base-url"]) {
  assert.ok(!html.match(new RegExp(`<input[^>]*id="${id}"[^>]*>`))[0].includes("placeholder="));
}
assert.ok(!code.includes('querySelector("#subscription-address").placeholder'));
assert.match(fs.readFileSync("knowte/web/styles.css", "utf8"), /\.config-section \.automation-phase-note\s*\{\s*font-size: \.75rem;/);
for (const id of ["github-token"]) {
  assert.match(html, new RegExp(`type="password" id="${id}"`));
}
assert.ok(!html.includes('id="werss-mode"'));
assert.ok(!html.includes('id="werss-token"'));
assert.ok(!code.includes('querySelector("#werss-mode")'));
assert.match(html, /<section class="connector-details" id="rsshub-settings">/);
assert.ok(!html.includes('id="subscription-detect"'));
assert.ok(!code.includes('querySelector("#subscription-detect")'));
assert.ok(!html.includes('data-werss='));
assert.ok(!html.includes('id="rsshub-twitter-auth-token"'));
assert.match(html, /id="subscription-connector"><option value="github">GitHub<\/option><option value="hackernews">Hacker News<\/option><option value="others">Others/);
for (const title of ["RSSHub", "GitHub", "Hacker News"]) {
  assert.ok(html.includes(`<h3 class="connector-heading">${title}</h3>`));
}
assert.match(html, /connector-address-row[^]*?rsshub-base-url[^]*?rsshub-use-local[^]*?<\/div>/);
for (const service of ["rsshub"]) {
  assert.match(html, new RegExp(`data-${service}="stop" class="[^"]*is-audit`));
  assert.match(html, new RegExp(`data-${service}="remove" class="[^"]*is-destructive`));
}
console.log("PASS Channel scope, detection reset, config credential lifecycle and optional Docker controls");

(async () => {
  let timer;
  context.URL = URL;
  context.setTimeout = (fn) => {timer = fn; return 1;};
  context.clearTimeout = () => {timer = null;};
  context.Option = function (text, value) {this.text = text; this.value = value;};
  field("subscription-choice").add = function (option) {this.children.push(option); this.value = "0";};
  const pending = [];
  context.subscriptionRequest = (payload) => new Promise((resolve) => pending.push({payload, resolve}));
  vm.runInContext(fragment("const detectChannel =", 'document.querySelector("#subscription-preview").addEventListener')
    + "this.schedule = scheduleChannelDetection;", context);
  field("subscription-connector").value = "hackernews";
  field("subscription-hn-mode").value = "keyword";
  field("subscription-address").value = "reinforcement learning";
  context.schedule();
  assert.equal(pending.length, 0, "Wait for input pause");
  timer();
  assert.equal(pending[0].payload.category, "hackernews");
  assert.equal(pending[0].payload.hn_mode, "keyword");
  field("subscription-address").value = "robotics";
  context.schedule(); timer();
  pending[0].resolve({choices: [{kind: "hn_keyword", name: "Old"}], message: ""});
  await new Promise(setImmediate);
  assert.equal(field("subscription-save").disabled, true, "Stale response cannot enable saving");
  pending[1].resolve({choices: [{kind: "hn_keyword", name: "Robotics"}], message: "HN Search"});
  await new Promise(setImmediate);
  assert.equal(field("subscription-name").value, "Robotics");
  assert.equal(field("subscription-save").disabled, false);
  field("subscription-address").value = "bad url";
  field("subscription-connector").value = "others";
  context.schedule(); timer();
  assert.match(field("subscription-status").textContent, /complete/);
  assert.equal(pending.length, 2);
  vm.runInContext("this.inputUI = updateChannelInput; this.preview = renderChannelPreview;", context);
  field("subscription-connector").value = "hackernews";
  field("subscription-hn-mode").value = "user";
  context.inputUI();
  assert.equal(field("subscription-hn-mode-field").hidden, false);
  assert.match(field("subscription-address-label").textContent, /Username/);
  context.preview([{title: "Reply", url: "https://news.ycombinator.com/item?id=2", channel_item_type: "comment"}], "hn_user");
  assert.equal(field("subscription-preview-list").children[0].textContent, "Posts · 0");
  assert.equal(field("subscription-preview-list").children[2].textContent, "Comments · 1");
  field("subscription-connector").value = "github";
  context.inputUI();
  assert.equal(field("subscription-hn-mode-field").hidden, true);
  console.log("PASS automatic detection debounce, category, stale responses and invalid URLs");
})().catch((error) => {console.error(error); process.exitCode = 1;});
