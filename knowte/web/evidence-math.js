/* Display-only formula rendering. The stored quote is never modified. */
(() => {
  function renderEvidenceText(element, value) {
    const text = String(value || "");
    element.replaceChildren();
    element.classList.add("evidence-formatted-text");
    // Recognize bounded nested groups and bare single-variable scripts, not identifiers.
    const group = String.raw`\{(?:[^{}\n]|\{(?:[^{}\n]|\{[^{}\n]*\})*\})*\}`;
    const script = String.raw`\\?[_^](?:${group}|\\[A-Za-z]+|\\?\*|[A-Za-z0-9\u0370-\u03ff])(?![\w\u0370-\u03ff])`;
    const argument = String.raw`\([^()\n]*\)`;
    const pattern = new RegExp(
      String.raw`\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|(?<![\\\d])\$([^$\n]+)\$`
      + String.raw`|\\[A-Za-z]+(?:${script}|${group}|${argument})*`
      + String.raw`|(?<![\w\\\u0370-\u03ff])[A-Za-z\u0370-\u03ff](?:${argument})?(?:${script})+(?:${argument})?`, "g",
    );
    const literals = [...text.matchAll(/```[\s\S]*?```|`[^`\n]*`|https?:\/\/[^\s]+/g)]
      .map(match => [match.index, match.index + match[0].length]);
    let end = 0;
    for (const match of text.matchAll(pattern)) {
      if (literals.some(([start, stop]) => match.index < stop && match.index + match[0].length > start)) continue;
      element.append(document.createTextNode(text.slice(end, match.index)));
      const node = document.createElement("span");
      const formula = match[1] ?? match[2] ?? match[3] ?? match[4] ?? match[0];
      // Repair Markdown escapes only in recognized mathematical scripts, for display.
      const displayFormula = formula
        .replace(/\\([_^])(?=\{|\*|[A-Za-z0-9\u0370-\u03ff]|\\[A-Za-z*])/g, "$1")
        .replace(/([_^]\{?)\\\*/g, "$1*");
      try {
        if (!window.katex) throw new Error("Formula renderer unavailable");
        window.katex.render(displayFormula, node, {
          output: "mathml", displayMode: Boolean(match[1] || match[2]),
          trust: false, throwOnError: true, maxExpand: 300, maxSize: 10,
        });
      } catch (_) {
        node.textContent = match[0];
        node.title = "Formula could not be rendered; original text shown";
      }
      element.append(node);
      end = match.index + match[0].length;
    }
    element.append(document.createTextNode(text.slice(end)));
  }
  window.renderEvidenceText = renderEvidenceText;
})();
