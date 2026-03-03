const { Plugin, ItemView, requestUrl, Notice, setIcon, PluginSettingTab, Setting } = require("obsidian");

const VIEW_TYPE = "second-brain-sidebar";

// --- Settings Tab ---
class SecondBrainSettingTab extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Second Brain Settings" });

    new Setting(containerEl)
    .setName("Backend URL")
    .setDesc("The base URL for your Python backend (e.g., http://localhost:8000)")
    .addText((text) =>
    text
    .setPlaceholder("http://localhost:8000")
    .setValue(this.plugin.settings.baseUrl)
    .onChange(async (value) => {
      this.plugin.settings.baseUrl = value.replace(/\/$/, ""); // Remove trailing slash
      await this.plugin.saveSettings();
    })
    );
  }
}

class SecondBrainView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin; // Reference to plugin to access settings
    this.currentMode = "chat";
    this.params = JSON.parse(localStorage.getItem("sb-params")) || {
      chat: { model: "llama3.2:1b", temp: 0.1, top_k: 3 },
      search: { top_k: 5 },
      similar: { k: 3 },
    };
  }

  getViewType() { return VIEW_TYPE; }
  getDisplayText() { return "Second Brain AI"; }
  getIcon() { return "brain-circuit"; }

  async onOpen() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("sb-sidebar-container");

    // --- Header ---
    const header = container.createEl("div", { cls: "sb-header" });
    header.createEl("h3", { text: "AI Assistant" });
    const headerBtns = header.createEl("div", { cls: "sb-header-btns" });

    const syncBtn = headerBtns.createEl("button", { text: "Sync", cls: "sb-sync-btn" });
    syncBtn.onclick = () => this.handleSync(syncBtn);

    const closeBtn = headerBtns.createEl("button", { cls: "sb-close-btn" });
    setIcon(closeBtn, "x");
    closeBtn.onclick = () => this.leaf.detach();

    // --- Mode Tabs ---
    const toggleContainer = container.createEl("div", { cls: "sb-toggle-container" });
    ["chat", "search", "similar"].forEach((mode) => {
      const tab = toggleContainer.createEl("div", {
        text: mode.charAt(0).toUpperCase() + mode.slice(1),
                                           cls: `sb-tab ${this.currentMode === mode ? "active" : ""}`,
      });
      tab.onclick = () => {
        this.currentMode = mode;
        container.querySelectorAll(".sb-tab").forEach((t) => t.removeClass("active"));
        tab.addClass("active");
        this.renderParams();
        if (mode === "similar") {
          this.inputWrapper.addClass("sb-hidden");
          this.handleSimilarSearch();
        } else {
          this.inputWrapper.removeClass("sb-hidden");
        }
      };
    });

    this.chatWindow = container.createEl("div", { cls: "sb-chat-window" });
    this.paramsPanel = container.createEl("div", { cls: "sb-params-panel sb-hidden" });
    this.renderParams();

    // --- Input Area ---
    this.inputWrapper = container.createEl("div", { cls: "sb-input-wrapper" });
    this.inputField = this.inputWrapper.createEl("textarea", {
      placeholder: "Type and press Enter...",
      cls: "sb-input-box",
    });

    this.inputField.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.handleSubmit();
      }
    });

    const actionRow = this.inputWrapper.createEl("div", { cls: "sb-action-row" });
    const configBtn = actionRow.createEl("button", { cls: "sb-icon-btn sb-knob-trigger" });
    setIcon(configBtn, "more-horizontal");
    configBtn.onclick = () => this.paramsPanel.classList.toggle("sb-hidden");

    const sendBtn = actionRow.createEl("button", { text: "Send", cls: "sb-send-btn mod-cta" });
    sendBtn.onclick = () => this.handleSubmit();
  }

  renderParams() {
    this.paramsPanel.empty();
    this.paramsPanel.createEl("h4", { text: "API Settings", style: "margin:0 0 10px 0; font-size:14px;" });
    const mode = this.currentMode;
    const currentData = this.params[mode];

    Object.keys(currentData).forEach((key) => {
      const row = this.paramsPanel.createEl("div", { cls: "sb-param-row" });
      row.createEl("span", { text: key.replace("_", " ").toUpperCase() + ":" });
      const input = row.createEl("input", {
        attr: {
          type: typeof currentData[key] === "number" ? "number" : "text",
          value: currentData[key],
          step: key === "temp" ? "0.1" : "1",
        },
      });
      input.onchange = (e) => {
        this.params[mode][key] = input.type === "number" ? parseFloat(e.target.value) : e.target.value;
        localStorage.setItem("sb-params", JSON.stringify(this.params));
        new Notice(`Saved ${key}: ${e.target.value}`);
      };
    });
  }

  async handleSubmit() {
    const query = this.inputField.value.trim();
    if (!query) return;

    this.appendMessage("user", query);
    this.inputField.value = "";
    const loadingMsg = this.appendMessage("ai", "Thinking...");
    const p = this.params[this.currentMode];
    const baseUrl = this.plugin.settings.baseUrl;

    try {
      const isChat = this.currentMode === "chat";
      const endpoint = isChat ? "/chat" : "/search/hybrid";
      const body = isChat ? { query, ...p, num_ctx: 2048 } : { query, top_k: p.top_k };

      const res = await requestUrl({
        url: `${baseUrl}${endpoint}`,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      loadingMsg.remove();
      if (isChat) {
        this.appendMessage("ai", res.json.response, res.json.context);
      } else {
        this.renderSearchResults(res.json);
      }
    } catch (err) {
      loadingMsg.setText("Error: Backend offline or unreachable.");
    }
  }

  async handleSimilarSearch() {
    const activeFile = this.app.workspace.getActiveFile();
    if (!activeFile) return;

    const loading = this.chatWindow.createEl("div", { text: "Finding similar notes...", cls: "sb-loading" });
    this.chatWindow.scrollTo(0, this.chatWindow.scrollHeight);

    try {
      const res = await requestUrl({
        url: `${this.plugin.settings.baseUrl}/auto-link`,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: await this.app.vault.read(activeFile),
                             k: this.params.similar.k,
        }),
      });
      loading.remove();
      this.renderSimilarLinks(res.json.links, activeFile.basename);
    } catch (e) {
      loading.setText("Failed to fetch connections.");
    }
  }

  appendMessage(role, text, context = []) {
    const msgWrap = this.chatWindow.createEl("div", { cls: `sb-msg-wrap sb-${role}` });
    msgWrap.createEl("div", { text: text, cls: "sb-msg-text" });

    if (role === "ai" && context?.length > 0) {
      const sourceContainer = msgWrap.createEl("div", { cls: "sb-rag-sources" });
      sourceContainer.createEl("div", { text: "Sources used:", cls: "sb-rag-label" });
      const list = sourceContainer.createEl("ul", { cls: "sb-rag-list" });
      const uniquePaths = [...new Set(context.map((i) => i.path))];
      uniquePaths.forEach((path) => {
        const li = list.createEl("li");
        const link = li.createEl("a", { text: `[[${path}]]`, cls: "sb-source-link-list" });
        link.onclick = () => app.workspace.openLinkText(path, "/", true);
      });
    }
    this.chatWindow.scrollTo(0, this.chatWindow.scrollHeight);
    return msgWrap;
  }

  renderSearchResults(results) {
    const wrap = this.chatWindow.createEl("div", { cls: "sb-msg-wrap sb-ai" });
    wrap.createEl("div", { text: "Hybrid Search Results", cls: "sb-result-header" });

    results.forEach((res) => {
      const item = wrap.createEl("div", { cls: "sb-search-result-item" });
      const link = item.createEl("a", { text: `[[${res.path}]]`, cls: "sb-source-link-bold" });
      link.onclick = () => app.workspace.openLinkText(res.path, "/", true);

      const contentMatch = res.text.match(/CONTENT:\s*([\s\S]*)/i);
      const content = contentMatch ? contentMatch[1].trim() : res.text.substring(0, 150);
      item.createEl("div", { text: content, cls: "sb-result-content" });
    });
    this.chatWindow.scrollTo(0, this.chatWindow.scrollHeight);
  }

  renderSimilarLinks(links, sourceNote) {
    const wrap = this.chatWindow.createEl("div", { cls: "sb-msg-wrap sb-ai" });
    wrap.createEl("div", { text: `Notes similar to "${sourceNote}":`, cls: "sb-result-header" });

    if (!links || links.length === 0) {
      wrap.createEl("div", { text: "No matches found.", style: "font-style:italic;" });
    } else {
      links.forEach((l) => {
        const clean = l.replace(/[\[\]]/g, "");
        const item = wrap.createEl("div", { style: "margin-bottom: 6px;" });
        const a = item.createEl("a", { text: `🔗 ${clean}`, cls: "sb-source-link-list" });
        a.onclick = () => app.workspace.openLinkText(clean, "/", true);
      });
    }
    this.chatWindow.scrollTo(0, this.chatWindow.scrollHeight);
  }

  async handleSync(btn) {
    btn.innerText = "Syncing...";
    try {
      await requestUrl({ url: `${this.plugin.settings.baseUrl}/sync`, method: "POST" });
      const check = setInterval(async () => {
        const res = await requestUrl({
          url: `${this.plugin.settings.baseUrl}/sync/status`,
          method: "GET",
        });
        if (!res.json.running) {
          clearInterval(check);
          btn.innerText = "Sync";
          new Notice("Sync complete!");
        }
      }, 2000);
    } catch (e) {
      btn.innerText = "Sync";
      new Notice("Sync failed.");
    }
  }
}

const DEFAULT_SETTINGS = {
  baseUrl: "http://localhost:8000"
};

module.exports = class SecondBrainPlugin extends Plugin {
  async onload() {
    await this.loadSettings();

    this.addSettingTab(new SecondBrainSettingTab(this.app, this));

    this.registerView(VIEW_TYPE, (leaf) => new SecondBrainView(leaf, this));

    this.addRibbonIcon("brain-circuit", "Open Second Brain", () =>
    this.activateView()
    );
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  async activateView() {
    const { workspace } = this.app;
    let leaf = workspace.getLeavesOfType(VIEW_TYPE)[0] || workspace.getRightLeaf(false);
    await leaf.setViewState({ type: VIEW_TYPE, active: true });
    workspace.revealLeaf(leaf);
  }
};
