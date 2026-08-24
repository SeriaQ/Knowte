const ext = globalThis.browser || chrome;
const serverInput = document.querySelector("#server-url");
const pairingInput = document.querySelector("#pairing-key");
const status = document.querySelector("#status");
document.querySelector("#extension-version").textContent = ext.runtime.getManifest().version;

const setStatus = (message, kind = "") => {
  status.textContent = message;
  status.classList.remove("is-success", "is-error", "is-pending");
  if (kind) status.classList.add(`is-${kind}`);
};

const applyTheme = (theme) => {
  if (["light", "dark"].includes(theme)) {
    document.documentElement.dataset.theme = theme;
  } else {
    delete document.documentElement.dataset.theme;
  }
};

const saved = await ext.storage.local.get(["serverUrl", "token", "theme"]);
applyTheme(saved.theme);
serverInput.value = saved.serverUrl || serverInput.value;
setStatus(
  saved.token ? "Paired with local Knowte." : "Generate a pairing key in Knowte Config.",
  saved.token ? "success" : "",
);

const markPairingChanged = () => {
  const hasKey = Boolean(pairingInput.value.trim());
  setStatus(
    hasKey
      ? (saved.token
        ? "New pairing key entered. Select Pair to replace the current connection."
        : "Pairing key entered. Select Pair to connect.")
      : (saved.token
        ? "Connection settings changed. Select Pair with a new key to reconnect."
        : "Generate a pairing key in Knowte Config."),
  );
};

pairingInput.addEventListener("input", markPairingChanged);
serverInput.addEventListener("input", markPairingChanged);

if (saved.token) {
  try {
    const response = await fetch(`${serverInput.value.replace(/\/$/, "")}/api/companion/options`, {
      headers: { "Authorization": `Bearer ${saved.token}` },
    });
    const options = await response.json();
    if (response.ok && ["auto", "light", "dark"].includes(options.theme)) {
      applyTheme(options.theme);
      await ext.storage.local.set({ theme: options.theme });
    }
    if (response.ok && options.version) {
      document.querySelector("#extension-version").textContent = options.version;
    }
  } catch (_) {}
}

document.querySelector("#pair").addEventListener("click", async () => {
  const [code, nonce] = pairingInput.value.trim().split(".", 2);
  const serverUrl = serverInput.value.trim().replace(/\/$/, "");
  setStatus("Pairing…", "pending");
  try {
    const response = await fetch(`${serverUrl}/api/companion/pair`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, nonce })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Pairing failed.");
    const theme = ["light", "dark"].includes(data.theme) ? data.theme : "auto";
    await ext.storage.local.set({ serverUrl, token: data.token, theme });
    applyTheme(theme);
    if (data.version) document.querySelector("#extension-version").textContent = data.version;
    setStatus("✓ Paired with local Knowte.", "success");
  } catch (error) { setStatus(error.message, "error"); }
});

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", async () => {
    setStatus(button.dataset.mode === "snapshot"
      ? "Drag a region on the page. Right-click or press Esc to cancel." : "Opening the page editor…");
    const result = await ext.runtime.sendMessage({
      type: "KNOWTE_RUN_CAPTURE", mode: button.dataset.mode
    });
    setStatus(
      result?.ok ? "Complete the floating editor on the page." : (result?.message || "Capture failed."),
      result?.ok ? "" : "error",
    );
  });
});

document.querySelector("#open-knowte").addEventListener("click", async () => {
  await ext.tabs.create({ url: serverInput.value.trim().replace(/\/$/, "") });
});
