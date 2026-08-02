(() => {
  if (globalThis.__knowteCompanionLoaded) return;
  globalThis.__knowteCompanionLoaded = true;
  const ext = globalThis.browser || chrome;

  const visible = (element) => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden"
      && rect.width > 0 && rect.height > 0;
  };

  const pageSource = () => ({
    title: document.title || location.hostname,
    url: location.href,
    canonical_url: document.querySelector('link[rel="canonical"]')?.href || location.href,
    authors: document.querySelector('meta[name="author"]')?.content || "",
    abstract: document.querySelector('meta[name="description"]')?.content || "",
    source: location.hostname,
    result_type: "web"
  });

  const pageBlocks = () => {
    const root = document.querySelector("article") || document.querySelector("main") || document.body;
    const selectors = "h1,h2,h3,h4,h5,h6,p,li,blockquote,pre,td,th,figcaption";
    return [...root.querySelectorAll(selectors)].filter(visible).map((element) => {
      const tag = element.tagName.toLowerCase();
      const type = /^h[1-6]$/.test(tag) ? "heading"
        : tag === "li" ? "list_item"
          : tag === "blockquote" ? "quote"
            : tag === "pre" ? "code"
              : tag === "td" ? "table_cell"
                : tag === "th" ? "table_header"
                  : tag === "figcaption" ? "caption" : "paragraph";
      return {
        type,
        text: (element.innerText || element.textContent || "").trim(),
        metadata: /^h[1-6]$/.test(tag) ? { level: Number(tag[1]) } : {}
      };
    }).filter((block) => block.text).slice(0, 1000);
  };

  const selectionPayload = () => {
    const selection = getSelection();
    if (!selection || selection.isCollapsed || !selection.rangeCount) {
      throw new Error("Select some text on the page first.");
    }
    const quote = selection.toString().trim();
    const container = selection.getRangeAt(0).commonAncestorContainer;
    const element = container.nodeType === Node.TEXT_NODE ? container.parentElement : container;
    const context = (element?.innerText || element?.textContent || quote).trim();
    const offset = context.indexOf(quote);
    const rect = selection.getRangeAt(0).getBoundingClientRect();
    return {
      quote,
      prefix: offset >= 0 ? context.slice(Math.max(0, offset - 300), offset) : "",
      suffix: offset >= 0 ? context.slice(offset + quote.length, offset + quote.length + 300) : "",
      anchor: {
        exact: quote, page_url: location.href,
        popup: { x: rect.left, y: rect.bottom, width: rect.width, height: rect.height }
      }
    };
  };

  const showComposer = (payload, options) => {
    document.querySelector("#knowte-companion-composer")?.remove();
    const host = document.createElement("div");
    host.id = "knowte-companion-composer";
    host.dataset.knowteTheme = ["light", "dark"].includes(options.theme)
      ? options.theme : "auto";
    const anchor = payload.anchor?.popup || payload.anchor?.region || {
      x: innerWidth / 2 - 170, y: innerHeight / 2 - 120, width: 0, height: 0
    };
    const left = Math.max(12, Math.min(innerWidth - 356, anchor.x));
    const top = Math.max(12, Math.min(innerHeight - 390, anchor.y + 8));
    host.style.cssText = `all:initial;position:fixed;left:${left}px;top:${top}px;z-index:2147483647`;
    const root = host.attachShadow({ mode: "closed" });
    root.innerHTML = `
      <style>
        :host{color-scheme:light dark;--bg:#0b1425;--field:#111e33;--text:#eef4ff;--muted:#91a0b8;--line:#2a3a52;--accent:#54e0c1;font:13px system-ui,sans-serif}
        .card{box-sizing:border-box;width:344px;padding:14px;border:1px solid var(--line);border-radius:15px;background:color-mix(in srgb,var(--bg) 96%,transparent);color:var(--text);box-shadow:0 20px 65px rgba(0,0,0,.38);backdrop-filter:blur(18px)}
        header{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:start;gap:10px;margin-bottom:10px}strong{display:-webkit-box;min-width:0;overflow:hidden;overflow-wrap:anywhere;font-size:13px;line-height:1.35;-webkit-box-orient:vertical;-webkit-line-clamp:2}.kind{flex:none;color:var(--accent);font-size:10px;font-weight:750;letter-spacing:.07em;text-transform:uppercase;white-space:nowrap}
        .quote{display:-webkit-box;max-height:54px;margin:0 0 10px;overflow:hidden;color:var(--muted);font-size:11px;line-height:1.45;-webkit-box-orient:vertical;-webkit-line-clamp:3}
        label{display:grid;gap:4px;margin-top:8px;color:var(--muted);font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
        select,input,textarea,button{box-sizing:border-box;width:100%;border:1px solid var(--line);border-radius:8px;padding:8px;color:var(--text);background:var(--field);font:12px system-ui,sans-serif}textarea{min-height:54px;resize:vertical}.actions{display:grid;grid-template-columns:auto 1fr;gap:7px;margin-top:10px}button{min-height:32px;padding:5px 9px;cursor:pointer;font-size:11px;font-weight:700}.discard{width:auto;background:transparent;color:var(--muted)}.save{border-color:rgba(84,224,193,.58);background:linear-gradient(120deg,#54e0c1,#7d70ff);color:#071320}.status{min-height:15px;margin:7px 0 0;color:var(--muted);font-size:10px}
        :host([data-knowte-theme="light"]){color-scheme:light;--bg:#f8fbff;--field:#fff;--text:#172642;--muted:#65748b;--line:#ced9e7;--accent:#16846e}
        :host([data-knowte-theme="light"]) .card{box-shadow:0 18px 55px rgba(30,55,90,.2)}
        @media(prefers-color-scheme:light){:host([data-knowte-theme="auto"]){--bg:#f8fbff;--field:#fff;--text:#172642;--muted:#65748b;--line:#ced9e7;--accent:#16846e}:host([data-knowte-theme="auto"]) .card{box-shadow:0 18px 55px rgba(30,55,90,.2)}}
      </style>
      <div class="card">
        <header><strong></strong><span class="kind"></span></header>
        <p class="quote"></p>
        <label>Destination<select></select></label>
        <label>Tags<input placeholder="Comma-separated"></label>
        <label>Annotation<textarea placeholder="Optional note, question, or warning"></textarea></label>
        <div class="actions"><button class="discard">Discard</button><button class="save">Save</button></div>
        <p class="status"></p>
      </div>`;
    root.querySelector("strong").textContent = payload.source.title || "Web Source";
    root.querySelector(".kind").textContent = payload.kind === "text"
      ? "Text Evidence" : payload.kind === "snapshot" ? "Snapshot Evidence" : "Source";
    const quote = root.querySelector(".quote");
    quote.textContent = payload.quote || (payload.kind === "source"
      ? "Save this page to the Library without creating Evidence." : "Selected region");
    const destination = root.querySelector("select");
    destination.append(new Option("Library only", ""));
    (options.artifacts || []).forEach((artifact) => destination.append(
      new Option(`Library + ${artifact.title}`, artifact.id)
    ));
    root.querySelector(".discard").addEventListener("click", () => host.remove());
    root.querySelector(".save").addEventListener("click", async () => {
      const save = root.querySelector(".save");
      const status = root.querySelector(".status");
      save.disabled = true;
      status.textContent = "Saving…";
      const tags = root.querySelector("input").value.split(",")
        .map((tag) => tag.trim()).filter(Boolean);
      const result = await ext.runtime.sendMessage({
        type: "KNOWTE_COMMIT_CAPTURE", payload,
        options: {
          artifact_id: destination.value, tags,
          annotation: root.querySelector("textarea").value.trim()
        }
      });
      if (result?.ok) {
        status.textContent = "Saved to Knowte.";
        setTimeout(() => host.remove(), 850);
      } else {
        status.textContent = result?.message || "Could not save.";
        save.disabled = false;
      }
    });
    document.documentElement.appendChild(host);
  };

  const selectRegion = () => new Promise((resolve, reject) => {
    const overlay = document.createElement("div");
    overlay.style.cssText = "position:fixed;inset:0;z-index:2147483647;cursor:crosshair;background:rgba(5,10,20,.18)";
    const box = document.createElement("div");
    box.style.cssText = "position:fixed;border:2px solid #54e0c1;background:rgba(84,224,193,.12);pointer-events:none";
    overlay.appendChild(box);
    document.documentElement.appendChild(overlay);
    let start = null;
    const cleanup = () => overlay.remove();
    overlay.addEventListener("mousedown", (event) => {
      start = { x: event.clientX, y: event.clientY };
    });
    overlay.addEventListener("mousemove", (event) => {
      if (!start) return;
      const x = Math.min(start.x, event.clientX);
      const y = Math.min(start.y, event.clientY);
      Object.assign(box.style, {
        left: `${x}px`, top: `${y}px`, width: `${Math.abs(event.clientX - start.x)}px`,
        height: `${Math.abs(event.clientY - start.y)}px`
      });
    });
    overlay.addEventListener("mouseup", (event) => {
      if (!start) return;
      const region = {
        x: Math.min(start.x, event.clientX), y: Math.min(start.y, event.clientY),
        width: Math.abs(event.clientX - start.x), height: Math.abs(event.clientY - start.y)
      };
      cleanup();
      if (region.width < 8 || region.height < 8) reject(new Error("Selected region is too small."));
      else resolve(region);
    });
    overlay.addEventListener("contextmenu", (event) => {
      event.preventDefault(); cleanup(); reject(new Error("Region capture cancelled."));
    });
    addEventListener("keydown", function cancel(event) {
      if (event.key === "Escape" && overlay.isConnected) {
        cleanup(); removeEventListener("keydown", cancel); reject(new Error("Region capture cancelled."));
      }
    });
  });

  ext.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type !== "KNOWTE_CAPTURE") return undefined;
    (async () => {
      const payload = { kind: message.mode, source: pageSource(), blocks: pageBlocks() };
      if (message.mode === "text") Object.assign(payload, selectionPayload());
      if (message.mode === "snapshot") {
        payload.anchor = {
          page_url: location.href,
          region: await selectRegion(),
          device_pixel_ratio: devicePixelRatio
        };
      }
      return payload;
    })().then(sendResponse, (error) => sendResponse({ __error: error.message }));
    return true;
  });

  ext.runtime.onMessage.addListener((message) => {
    if (message?.type !== "KNOWTE_SHOW_COMPOSER") return undefined;
    showComposer(message.payload, message.options || {});
    return Promise.resolve({ shown: true });
  });
})();
