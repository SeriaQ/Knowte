const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const katex = require("../knowte/web/vendor/katex/katex.min.js");
const rendered = [];
const node = () => ({children: [], classList: {add() {}}, replaceChildren() {this.children = [];}, append(...items) {this.children.push(...items);}});
const context = {
  window: {katex: {render(formula, element, options) {
    rendered.push({formula, options});
    element.math = katex.renderToString(formula, options);
  }}},
  document: {createElement: node, createTextNode: text => ({text})},
};
vm.runInNewContext(fs.readFileSync("knowte/web/evidence-math.js", "utf8"), context);
const target = node();
const quote = String.raw`Policy \pi\_{\theta}(a|s), \(V(s)=\mathbb{E}[r]\), and \[\sum_{t=0}^{\infty}r_t\].`;
context.window.renderEvidenceText(target, quote);
assert.equal(rendered.length, 3);
assert.equal(rendered[0].formula, String.raw`\pi_{\theta}(a|s)`);
assert.equal(rendered[2].options.displayMode, true);
assert.equal(rendered[0].options.trust, false);
assert.ok(quote.includes(String.raw`\pi\_{\theta}`));
assert.ok(target.children.some(item => item.math?.includes("<msub>")));
context.window.renderEvidenceText(target, String.raw`Broken \(\unknowncommand{x}\)`);
assert.ok(target.children.some(item => item.textContent === String.raw`\(\unknowncommand{x}\)`));
context.window.renderEvidenceText(target, "<img src=x onerror=alert(1)>");
assert.equal(target.children[0].text, "<img src=x onerror=alert(1)>");
rendered.length = 0;
context.window.renderEvidenceText(target, String.raw`V^{π}, Q^{\pi}(s,a), a_t, r_{t+1}, x^2, π_θ, V(s)^{\pi}, x_{i_{t+1}}, \pi\_\theta`);
assert.equal(rendered.length, 9);
assert.equal(rendered[0].formula, "V^{π}");
assert.ok(target.children.some(item => item.math?.includes("<msup>")));
assert.ok(target.children.some(item => item.math?.includes("<msub>")));
rendered.length = 0;
context.window.renderEvidenceText(target, "user_id config_path x_axis `V^{π}` https://example.org/a_t");
assert.equal(rendered.length, 0);
rendered.length = 0;
context.window.renderEvidenceText(target, String.raw`Q^\*(s,a), Q^{\*}(s,a), V^*, Q\^\*(s,a), \(Q^\*(s,a)\)`);
assert.equal(rendered.length, 5);
assert.equal(rendered[0].formula, "Q^*(s,a)");
assert.equal(rendered[1].formula, "Q^{*}(s,a)");
assert.ok(target.children.filter(item => item.math?.includes("<msup>")).length === 5);
console.log("Evidence math rendering checks passed");
const app = fs.readFileSync("knowte/web/app.js", "utf8");
assert.ok(app.includes("renderEvidenceText(statement, claim.statement)"));
assert.ok(app.includes("renderEvidenceText(statementPreview, statement.value)"));
assert.ok(app.includes("renderEvidenceText(detail, sourceItem"));
assert.ok(app.includes("card.append(statementPreview, statementEditor, fields)"));
console.log("Claim display and review use formula rendering with a separate text editor");
