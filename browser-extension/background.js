const ext = globalThis.browser || chrome;

const storageGet = async (keys) => ext.storage.local.get(keys);

const bytesToDataUrl = (bytes, mimeType = "image/png") => {
  let binary = "";
  const values = new Uint8Array(bytes);
  for (let index = 0; index < values.length; index += 0x8000) {
    binary += String.fromCharCode(...values.subarray(index, index + 0x8000));
  }
  return `data:${mimeType};base64,${btoa(binary)}`;
};

const cropScreenshot = async (dataUrl, rect, scale) => {
  const bitmap = await createImageBitmap(await (await fetch(dataUrl)).blob());
  const ratio = Number(scale || 1);
  const x = Math.max(0, Math.round(rect.x * ratio));
  const y = Math.max(0, Math.round(rect.y * ratio));
  const width = Math.min(bitmap.width - x, Math.max(1, Math.round(rect.width * ratio)));
  const height = Math.min(bitmap.height - y, Math.max(1, Math.round(rect.height * ratio)));
  const canvas = new OffscreenCanvas(width, height);
  canvas.getContext("2d").drawImage(bitmap, x, y, width, height, 0, 0, width, height);
  return bytesToDataUrl(await (await canvas.convertToBlob({ type: "image/png" })).arrayBuffer());
};

const companionRequest = async (path, options = {}) => {
  const saved = await storageGet(["serverUrl", "token"]);
  const serverUrl = (saved.serverUrl || "http://127.0.0.1:7880").replace(/\/$/, "");
  if (!saved.token) throw new Error("Pair the extension with Knowte first.");
  const response = await fetch(`${serverUrl}${path}`, {
    headers: {
      "Authorization": `Bearer ${saved.token}`,
      ...(options.body ? { "Content-Type": "application/json" } : {})
    },
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "Knowte rejected the capture.");
  return data;
};

const postCapture = (payload, options) => companionRequest("/api/companion/commit", {
  method: "POST", body: JSON.stringify({ ...payload, options })
});

const getCompanionOptions = () => companionRequest("/api/companion/options");

const prepareCaptureFromTab = async (mode) => {
  const [tab] = await ext.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !/^https?:/.test(tab.url || "")) {
    throw new Error("Open a normal HTTP or HTTPS page first.");
  }
  const saved = await storageGet(["serverUrl"]);
  const knowteUrl = saved.serverUrl || "http://127.0.0.1:7880";
  try {
    if (new URL(tab.url).origin === new URL(knowteUrl).origin) {
      await ext.scripting.executeScript({
        target: { tabId: tab.id },
        func: (captureMode) => window.dispatchEvent(new CustomEvent(
          "knowte:capture-shortcut", { detail: { mode: captureMode } }
        )),
        args: [mode]
      });
      return { prepared: true, internal: true };
    }
  } catch (_) {}
  await ext.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
  const payload = await ext.tabs.sendMessage(tab.id, { type: "KNOWTE_CAPTURE", mode });
  if (payload?.__knowte_internal) {
    await ext.scripting.executeScript({
      target: { tabId: tab.id },
      func: (captureMode) => window.dispatchEvent(new CustomEvent(
        "knowte:capture-shortcut", { detail: { mode: captureMode } }
      )),
      args: [mode]
    });
    return { prepared: true, internal: true };
  }
  if (payload?.__error) throw new Error(payload.__error);
  if (mode === "snapshot") {
    const screenshot = await ext.tabs.captureVisibleTab(tab.windowId, { format: "png" });
    payload.image_data = await cropScreenshot(
      screenshot, payload.anchor.region, payload.anchor.device_pixel_ratio
    );
  }
  const options = await getCompanionOptions();
  await ext.tabs.sendMessage(tab.id, {
    type: "KNOWTE_SHOW_COMPOSER", payload, options
  });
  return { prepared: true };
};

ext.runtime.onMessage.addListener((message) => {
  if (message?.type !== "KNOWTE_RUN_CAPTURE") return undefined;
  return prepareCaptureFromTab(message.mode).then(
    (item) => ({ ok: true, item }),
    (error) => ({ ok: false, message: error.message })
  );
});

ext.runtime.onMessage.addListener((message, sender) => {
  if (message?.type !== "KNOWTE_COMPOSE_CAPTURE") return undefined;
  return (async () => {
    if (!sender.tab?.id) throw new Error("Could not identify the current page.");
    const options = await getCompanionOptions();
    await ext.tabs.sendMessage(sender.tab.id, {
      type: "KNOWTE_SHOW_COMPOSER", payload: message.payload, options
    });
    return { ok: true };
  })().catch((error) => ({ ok: false, message: error.message }));
});

ext.runtime.onMessage.addListener((message) => {
  if (message?.type !== "KNOWTE_COMMIT_CAPTURE") return undefined;
  return postCapture(message.payload, message.options).then(
    (result) => ({ ok: true, result }),
    (error) => ({ ok: false, message: error.message })
  );
});

ext.commands.onCommand.addListener((command) => {
  if (command === "capture-text") prepareCaptureFromTab("text").catch(() => {});
  if (command === "capture-region") prepareCaptureFromTab("snapshot").catch(() => {});
});
