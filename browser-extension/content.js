(() => {
  if (globalThis.__knowteCompanionLoaded) return;
  globalThis.__knowteCompanionLoaded = true;
  const ext = globalThis.browser || chrome;

  const isKnowteApp = () => document.documentElement.hasAttribute("data-knowte-app");
  let selectionBubble = null;
  let selectionArm = null;

  const clearBrowserSelection = () => getSelection()?.removeAllRanges();

  const removeSelectionBubble = () => {
    selectionBubble?.remove();
    selectionBubble = null;
  };

  const removeSelectionArm = () => {
    selectionArm?.remove();
    selectionArm = null;
  };

  const parsedBackground = (value) => {
    const match = String(value || "").match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)/i);
    if (!match) return null;
    const alpha = match[4] === undefined ? 1 : Number(match[4]);
    if (!Number.isFinite(alpha) || alpha < 0.18) return null;
    return match.slice(1, 4).map(Number);
  };

  const backgroundTheme = (anchor, fallback = "auto") => {
    const region = anchor || {};
    const x = Math.max(0, Math.min(innerWidth - 1,
      Number(region.x || 0) + Number(region.width || 0) / 2));
    const y = Math.max(0, Math.min(innerHeight - 1,
      Number(region.y || 0) + Math.max(1, Number(region.height || 0) / 2)));
    let element = document.elementFromPoint(x, y);
    while (element) {
      const rgb = parsedBackground(getComputedStyle(element).backgroundColor);
      if (rgb) {
        const linear = rgb.map((channel) => {
          const value = channel / 255;
          return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
        });
        const luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
        return luminance > 0.36 ? "light" : "dark";
      }
      element = element.parentElement;
    }
    if (["light", "dark"].includes(fallback)) return fallback;
    return globalThis.matchMedia?.("(prefers-color-scheme: light)")?.matches ? "light" : "dark";
  };

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

  const editableSelection = (selection) => {
    const node = selection?.anchorNode;
    const element = node?.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    return Boolean(element?.closest?.("input,textarea,[contenteditable=true],[role=textbox]"));
  };

  const showSelectionArm = () => {
    removeSelectionArm();
    const host = document.createElement("div");
    host.id = "knowte-companion-selection-arm";
    host.style.cssText = "all:initial;position:fixed;left:50%;top:18px;transform:translateX(-50%);z-index:2147483647;pointer-events:none";
    const root = host.attachShadow({ mode: "closed" });
    root.innerHTML = `
      <style>:host{font:12px system-ui,sans-serif}.hint{display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid rgba(84,224,193,.55);border-radius:999px;background:rgba(9,20,37,.94);color:#eef4ff;box-shadow:0 10px 34px rgba(0,0,0,.3);backdrop-filter:blur(14px)}.dot{width:7px;height:7px;border-radius:50%;background:#54e0c1;box-shadow:0 0 0 4px rgba(84,224,193,.13)}small{color:#9eacc0}</style>
      <div class="hint"><span class="dot"></span><span>Select text</span><small>Esc to cancel</small></div>`;
    document.documentElement.appendChild(host);
    selectionArm = host;
  };

  const waitForTextSelection = () => new Promise((resolve, reject) => {
    showSelectionArm();
    const cleanup = () => {
      removeSelectionArm();
      document.removeEventListener("mouseup", selected, true);
      document.removeEventListener("keydown", cancelled, true);
    };
    const selected = () => {
      setTimeout(() => {
        const selection = getSelection();
        if (!selection || selection.isCollapsed || editableSelection(selection)) return;
        try {
          const payload = selectionPayload();
          cleanup();
          removeSelectionBubble();
          resolve(payload);
        } catch (_) {}
      }, 0);
    };
    const cancelled = (event) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      cleanup();
      reject(new Error("Text selection cancelled."));
    };
    document.addEventListener("mouseup", selected, true);
    document.addEventListener("keydown", cancelled, true);
  });

  const beginPreparedCapture = async (payload) => {
    removeSelectionBubble();
    const result = await ext.runtime.sendMessage({
      type: "KNOWTE_COMPOSE_CAPTURE", payload: { ...payload, blocks: pageBlocks() }
    });
    if (!result?.ok) throw new Error(result?.message || "Could not open Knowte capture.");
  };

  const beginRegionCapture = async () => {
    removeSelectionBubble();
    clearBrowserSelection();
    const result = await ext.runtime.sendMessage({ type: "KNOWTE_RUN_CAPTURE", mode: "snapshot" });
    if (!result?.ok) throw new Error(result?.message || "Could not start region capture.");
  };

  const showSelectionBubble = (payload) => {
    removeSelectionBubble();
    const anchor = payload.anchor.popup;
    const host = document.createElement("div");
    host.id = "knowte-companion-selection-bubble";
    host.dataset.knowteTheme = backgroundTheme({
      ...anchor, y: anchor.y - Number(anchor.height || 0),
    });
    const left = Math.max(10, Math.min(innerWidth - 154, anchor.x + anchor.width / 2 - 77));
    const top = Math.max(10, Math.min(innerHeight - 48, anchor.y + 7));
    host.style.cssText = `all:initial;position:fixed;left:${left}px;top:${top}px;z-index:2147483647`;
    const root = host.attachShadow({ mode: "closed" });
    const logoUrl = ext.runtime.getURL("knowte_icon.png");
    root.innerHTML = `
      <style>
        :host{--bubble-bg:rgba(9,20,37,.95);--bubble-text:#eef4ff;--bubble-line:rgba(145,160,184,.3);--bubble-border:rgba(84,224,193,.55);--bubble-hover:rgba(84,224,193,.15);font:12px system-ui,sans-serif}.bar{display:flex;align-items:center;overflow:hidden;border:1px solid var(--bubble-border);border-radius:10px;background:var(--bubble-bg);box-shadow:0 10px 34px rgba(0,0,0,.32);backdrop-filter:blur(14px)}.brand{display:flex;align-items:center;gap:6px;height:34px;padding:0 9px;color:var(--bubble-text);font-size:11px;font-weight:700}.brand img{width:16px;height:16px;object-fit:contain;filter:brightness(0) invert(1);opacity:.82}button{display:flex;align-items:center;gap:3px;height:34px;margin:0;padding:0 9px;border:0;border-left:1px solid var(--bubble-line);background:transparent;color:var(--bubble-text);cursor:pointer;font:700 11px system-ui,sans-serif}button:hover{background:var(--bubble-hover)}svg{width:14px;height:14px;fill:none;stroke:#54e0c1;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.plus{color:#54e0c1;font-size:14px}:host([data-knowte-theme="light"]){--bubble-bg:rgba(248,251,255,.96);--bubble-text:#172642;--bubble-line:rgba(30,55,95,.18);--bubble-border:rgba(31,142,120,.48);--bubble-hover:rgba(84,224,193,.19)}:host([data-knowte-theme="light"]) .bar{box-shadow:0 10px 30px rgba(30,55,90,.2)}:host([data-knowte-theme="light"]) .brand img{filter:none;opacity:.78}
      </style>
      <div class="bar">
        <div class="brand"><img src="${logoUrl}" alt=""><span>Knowte</span></div>
        <button class="text" type="button" title="Save selected text"><span class="plus">+</span><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3h10M8 3v10M5.5 13h5"/></svg></button>
        <button class="region" type="button" title="Capture a region"><span class="plus">+</span><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 2H2v4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg></button>
      </div>`;
    root.querySelector(".text").addEventListener("mousedown", (event) => event.preventDefault());
    root.querySelector(".text").addEventListener("click", () => beginPreparedCapture(payload).catch(() => {}));
    root.querySelector(".region").addEventListener("click", () => beginRegionCapture().catch(() => {}));
    document.documentElement.appendChild(host);
    selectionBubble = host;
  };

  const showComposer = (payload, options) => {
    document.querySelector("#knowte-companion-composer")?.remove();
    const host = document.createElement("div");
    host.id = "knowte-companion-composer";
    const anchor = payload.anchor?.popup || payload.anchor?.region || {
      x: innerWidth / 2 - 170, y: innerHeight / 2 - 120, width: 0, height: 0
    };
    host.dataset.knowteTheme = backgroundTheme(
      payload.anchor?.popup
        ? { ...anchor, y: anchor.y - Number(anchor.height || 0) }
        : anchor,
      options.theme,
    );
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
    if (isKnowteApp()) {
      sendResponse({ __knowte_internal: true });
      return false;
    }
    (async () => {
      const payload = { kind: message.mode, source: pageSource(), blocks: pageBlocks() };
      if (message.mode === "text") {
        try {
          Object.assign(payload, selectionPayload());
        } catch (_) {
          Object.assign(payload, await waitForTextSelection());
        }
      }
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
    if (isKnowteApp()) {
      document.querySelector("#knowte-companion-composer")?.remove();
      return Promise.resolve({ shown: false, internal: true });
    }
    showComposer(message.payload, message.options || {});
    return Promise.resolve({ shown: true });
  });

  document.addEventListener("mouseup", (event) => {
    if (isKnowteApp() || selectionArm || event.button !== 0) return;
    setTimeout(() => {
      const selection = getSelection();
      if (!selection || selection.isCollapsed || editableSelection(selection)) {
        removeSelectionBubble();
        return;
      }
      try {
        showSelectionBubble({ kind: "text", source: pageSource(), ...selectionPayload() });
      } catch (_) {
        removeSelectionBubble();
      }
    }, 0);
  }, true);

  document.addEventListener("mousedown", (event) => {
    if (selectionBubble && event.target !== selectionBubble) removeSelectionBubble();
  }, true);
})();
