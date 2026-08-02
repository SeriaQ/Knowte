const ext = globalThis.browser || chrome;
const serverInput = document.querySelector("#server-url");
const pairingInput = document.querySelector("#pairing-key");
const status = document.querySelector("#status");
document.querySelector("#extension-version").textContent = ext.runtime.getManifest().version;

const saved = await ext.storage.local.get(["serverUrl", "token", "theme"]);
if (["light", "dark"].includes(saved.theme)) {
  document.documentElement.dataset.theme = saved.theme;
}
serverInput.value = saved.serverUrl || serverInput.value;
status.textContent = saved.token ? "Paired with local Knowte." : "Generate a pairing key in Knowte Config.";

if (saved.token) {
  try {
    const response = await fetch(`${serverInput.value.replace(/\/$/, "")}/api/companion/options`, {
      headers: { "Authorization": `Bearer ${saved.token}` },
    });
    const options = await response.json();
    if (response.ok && ["light", "dark"].includes(options.theme)) {
      document.documentElement.dataset.theme = options.theme;
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
  status.textContent = "Pairing…";
  try {
    const response = await fetch(`${serverUrl}/api/companion/pair`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, nonce })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Pairing failed.");
    const theme = ["light", "dark"].includes(data.theme) ? data.theme : "auto";
    await ext.storage.local.set({ serverUrl, token: data.token, theme });
    if (theme !== "auto") document.documentElement.dataset.theme = theme;
    if (data.version) document.querySelector("#extension-version").textContent = data.version;
    status.textContent = "Paired with local Knowte.";
  } catch (error) { status.textContent = error.message; }
});

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", async () => {
    status.textContent = button.dataset.mode === "snapshot"
      ? "Drag a region on the page. Right-click or press Esc to cancel." : "Opening the page editor…";
    const result = await ext.runtime.sendMessage({
      type: "KNOWTE_RUN_CAPTURE", mode: button.dataset.mode
    });
    status.textContent = result?.ok ? "Complete the floating editor on the page." : (result?.message || "Capture failed.");
  });
});

document.querySelector("#open-knowte").addEventListener("click", async () => {
  await ext.tabs.create({ url: serverInput.value.trim().replace(/\/$/, "") });
});
