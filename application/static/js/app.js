import { t, applyTranslations } from "./i18n.js";
import { loadSettings, saveSettings, resetSettings, applyVisualSettings } from "./settings.js";
import { getHealth, getConnections, sendChat, askAssistant, submitQuery, ApiError } from "./api.js";
import { renderMessage } from "./render.js";

const colorScheme = matchMedia("(prefers-color-scheme: dark)");
const motionPreference = matchMedia("(prefers-reduced-motion: reduce)");
const assistantErrorCodes = new Set([
  "explicit_query_action_required", "assistant_not_configured", "assistant_busy",
  "assistant_timeout", "context_unavailable", "llm_provider_error",
  "llm_timeout", "llm_unavailable", "invalid_llm_response",
  "invalid_gateway_response", "gateway_busy", "gateway_timeout",
  "gateway_unavailable", "gateway_authentication_failed", "gateway_error",
]);

export function startApp() {
  let settings = loadSettings();
  let messages = [];
  let suggestions = [];
  let suggestionSets = { de: [], en: [] };
  let suggestionDismissed = false;
  let controller = null;
  let isSending = false;
  let isRefreshing = false;
  let drawerReturnFocus = null;
  let activeTab = "connections";
  let connectionData = null;
  let assistantConfigured = false;
  let backendUnavailable = false;
  let queryStatusKey = "";
  let queryOutputKey = "";
  let queryOutputRaw = "";
  let connectionStatusKey = "";
  let requestStatusKey = "";

  const $ = (id) => document.getElementById(id);
  const html = document.documentElement;
  const chatScroll = $("chat-scroll");
  const composer = $("message-form");
  const input = $("message-input");
  const assistantMode = $("assistant-mode");
  const assistantModeButtons = document.querySelectorAll("[data-mode-option]");
  const sendButton = $("send-button");
  const loadingRow = $("loading-row");
  const requestStatus = $("request-status");
  const connectionList = $("connection-list");
  const connectionStatus = $("connection-status");
  const drawer = $("drawer");
  const menuButton = $("menu-button");
  const drawerBackdrop = $("drawer-backdrop");
  const suggestionChips = $("suggestion-chips");
  const backendBanner = $("backend-banner");
  const jumpLatest = $("jump-latest");
  const queryForm = $("query-form");

  function nearBottom() {
    return chatScroll.scrollHeight - chatScroll.scrollTop - chatScroll.clientHeight < 140;
  }

  function scrollToLatest(force = false) {
    if (force || nearBottom()) {
      chatScroll.scrollTop = chatScroll.scrollHeight;
      jumpLatest.hidden = true;
    } else {
      jumpLatest.hidden = false;
    }
  }

  function renderChat() {
    const wasNearBottom = nearBottom();
    const container = $("messages");
    container.replaceChildren();
    const isEmpty = messages.length === 0;
    $("welcome").hidden = !isEmpty;
    for (const message of messages) {
      const node = renderMessage(message, {
        language: settings.language,
        settings,
        onAction: (action, data) => handleMessageAction(action, data, message),
      });
      container.append(node);
    }
    requestAnimationFrame(() => scrollToLatest(wasNearBottom));
  }

  function renderWelcome() {
    $("welcome-name").textContent = settings.displayName.trim() || t(settings.language, "defaultName");
    suggestionChips.setAttribute("aria-label", t(settings.language, "exampleQuestions"));
    suggestionChips.replaceChildren();
    for (const question of currentSuggestions().slice(0, 4)) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "suggestion-chip";
      chip.textContent = question;
      chip.title = t(settings.language, "useExamples");
      chip.addEventListener("click", () => fillComposer(question));
      suggestionChips.append(chip);
    }
  }

  function currentSuggestions() {
    return suggestionSets[settings.language]?.length ? suggestionSets[settings.language] : suggestions;
  }

  function syncSettingsControls() {
    $("language-select").value = settings.language;
    $("theme-select").value = settings.theme;
    $("setting-font-size").value = settings.fontSize;
    $("setting-density").value = settings.density;
    $("setting-motion").value = settings.reduceMotion;
    $("setting-autocomplete").checked = settings.autocomplete;
    $("setting-show-sql").checked = settings.showSql;
    $("setting-show-details").checked = settings.showDetails;
    $("setting-name").value = settings.displayName;
    document.querySelectorAll("[data-language]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.language === settings.language));
    });
  }

  function syncModeNotice() {
    const notice = $("demo-notice");
    const warning = $("assistant-warning");
    if (notice) {
      notice.textContent = t(
        settings.language,
        assistantMode.value === "assistant" ? "assistant.modeNotice" : "demoNotice",
      );
    }
    if (warning) {
      warning.hidden = assistantConfigured;
      warning.textContent = t(settings.language, "assistant.disabledNotice");
    }
  }

  function setAssistantConfigured(configured) {
    assistantConfigured = configured === true;
    const assistantButton = [...assistantModeButtons].find(
      (button) => button.dataset.modeOption === "assistant",
    );
    if (assistantButton) assistantButton.disabled = !assistantConfigured;
    if (!assistantConfigured && assistantMode.value === "assistant") {
      assistantMode.value = "chat";
    }
    assistantModeButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.modeOption === assistantMode.value));
    });
    syncModeNotice();
  }

  function applySettings() {
    applyVisualSettings(settings, colorScheme, motionPreference);
    applyTranslations(settings.language);
    syncModeNotice();
    syncSettingsControls();
    renderWelcome();
    renderChat();
    updateGhost();
    if (requestStatusKey) requestStatus.textContent = t(settings.language, requestStatusKey);
    if (connectionStatusKey) connectionStatus.textContent = t(settings.language, connectionStatusKey);
    if (queryStatusKey) $("query-status").textContent = t(settings.language, queryStatusKey);
    if (queryOutputKey) {
      const output = $("query-result");
      output.replaceChildren();
      const pre = document.createElement("pre");
      pre.textContent = queryOutputKey === "raw" ? queryOutputRaw : t(settings.language, queryOutputKey);
      output.append(pre);
    }
    menuButton.setAttribute("aria-label", t(settings.language, drawer.classList.contains("open") ? "menuClose" : "menuOpen"));
    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.content = settings.theme === "light" || (settings.theme === "system" && !colorScheme.matches) ? "#F3F7F4" : "#060A08";
    if (backendUnavailable) backendBanner.textContent = t(settings.language, "backendDown");
    if (connectionData) renderConnections(connectionData);
  }

  function updateSetting(key, value) {
    settings = { ...settings, [key]: value };
    saveSettings(settings);
    applySettings();
  }

  function updateGhost() {
    const composerElement = composer;
    let preview = $("completion-preview");
    if (!preview) {
      preview = document.createElement("div");
      preview.id = "completion-preview";
      preview.className = "completion-preview";
      preview.setAttribute("aria-hidden", "true");
      composerElement.prepend(preview);
    }
    preview.replaceChildren();
    composerElement.classList.remove("has-ghost");
    const typed = input.value;
    if (!settings.autocomplete || suggestionDismissed || !typed || typed.includes("\n")) return;
    const match = currentSuggestions().find((item) => item.toLocaleLowerCase().startsWith(typed.toLocaleLowerCase()) && item.length > typed.length);
    if (!match) return;
    preview.append(document.createTextNode(typed));
    const rest = document.createElement("span");
    rest.className = "ghost-rest";
    rest.textContent = match.slice(typed.length);
    preview.append(rest);
    composerElement.classList.add("has-ghost");
  }

  function fillComposer(value) {
    input.value = value;
    suggestionDismissed = true;
    updateGhost();
    autoGrow();
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
    if (drawer.classList.contains("open")) closeDrawer(false);
  }

  function autoGrow() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
  }

  function setLoading(value) {
    isSending = value;
    loadingRow.hidden = !value;
    sendButton.disabled = value;
    input.disabled = value;
  }

  function appendMessage(message) {
    messages.push({ id: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`, ...message });
    renderChat();
  }

  function setBackendUnavailable(value) {
    backendUnavailable = value;
    backendBanner.hidden = !value;
    if (value) backendBanner.textContent = t(settings.language, "backendDown");
  }

  async function submitMessage(text = input.value.trim(), { appendUser = true } = {}) {
    if (!text || isSending) return;
    const previous = text;
    if (appendUser) appendMessage({ role: "user", text });
    controller = new AbortController();
    setLoading(true);
    requestStatusKey = "loading";
    requestStatus.textContent = t(settings.language, requestStatusKey);
    const useAssistant = assistantMode.value === "assistant";
    try {
      const response = useAssistant
        ? await askAssistant(text, controller.signal)
        : await sendChat(text, controller.signal);
      setBackendUnavailable(false);
      if (useAssistant) {
        appendMessage({ role: "assistant", kind: "assistant-reply", payload: response });
        input.value = "";
        autoGrow();
        requestStatusKey = "";
        requestStatus.textContent = "";
        return;
      }
      const kind = response.mode === "tool" ? "tool" : (response.mode === "echo" ? "echo" : "analysis");
      appendMessage({ role: "assistant", kind, payload: response });
      input.value = "";
      autoGrow();
      requestStatusKey = "";
      requestStatus.textContent = "";
    } catch (error) {
      if (error.name === "AbortError") {
        requestStatusKey = "cancelled";
        requestStatus.textContent = t(settings.language, "cancelled");
      } else {
        const unreachable = error instanceof ApiError && error.unreachable;
        setBackendUnavailable(unreachable);
        const knownCode = error instanceof ApiError && error.code && assistantErrorCodes.has(error.code);
        const uiKey = useAssistant
          ? (knownCode ? `assistant.error.${error.code}` : (unreachable ? "assistant.error.assistant_unavailable" : "assistant.error.assistant_request_failed"))
          : (unreachable ? "backendDown" : null);
        const textContent = t(settings.language, uiKey || "requestError");
        appendMessage({ role: "error", kind: "error", payload: { reply: textContent }, uiKey, retryText: previous });
        requestStatusKey = unreachable ? "" : "requestError";
        requestStatus.textContent = unreachable ? "" : t(settings.language, requestStatusKey);
      }
    } finally {
      controller = null;
      setLoading(false);
    }
  }

  function downloadCsv(columns, rows) {
    const names = columns.map((column) => typeof column === "string" ? column : (column?.name ?? column?.label ?? ""));
    const escape = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const lines = [names.map(escape).join(","), ...rows.map((row) => names.map((name, index) => escape(Array.isArray(row) ? row[index] : row?.[name])).join(","))];
    const blob = new Blob(["\ufeff", lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "analysis-results.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function handleMessageAction(action, data, message) {
    if (action === "edit") {
      const index = messages.findIndex((item) => item.id === message.id);
      messages = messages.slice(0, Math.max(index, 0));
      input.value = message.text;
      renderChat();
      autoGrow();
      input.focus();
    } else if (action === "retry") {
      messages = messages.filter((item) => item.id !== message.id);
      renderChat();
      await submitMessage(data.text, { appendUser: false });
    } else if (action === "copy") {
      try {
        await navigator.clipboard.writeText(data.text);
        requestStatusKey = "copied";
        requestStatus.textContent = t(settings.language, "copied");
      } catch {
        requestStatusKey = "copyFailed";
        requestStatus.textContent = t(settings.language, "copyFailed");
      }
    } else if (action === "csv") downloadCsv(data.columns, data.rows);
  }

  async function refreshConnections() {
    if (isRefreshing) return;
    isRefreshing = true;
    connectionStatusKey = "checking";
    connectionStatus.textContent = t(settings.language, connectionStatusKey);
    try {
      const [health, services] = await Promise.all([getHealth(), getConnections()]);
      connectionData = { health, services };
      setAssistantConfigured(health.assistant_configured);
      setBackendUnavailable(false);
      renderConnections(connectionData);
      connectionStatusKey = "statusDone";
      connectionStatus.textContent = t(settings.language, connectionStatusKey);
    } catch {
      connectionData = { health: null, services: null };
      setAssistantConfigured(false);
      setBackendUnavailable(true);
      renderConnections(connectionData);
      connectionStatusKey = "statusFailed";
      connectionStatus.textContent = t(settings.language, connectionStatusKey);
    } finally {
      isRefreshing = false;
    }
  }

  function renderConnections(data) {
    connectionList.replaceChildren();
    const appCard = document.createElement("article");
    appCard.className = "connection-item";
    const appHeader = document.createElement("header");
    appHeader.append(document.createElement("strong"));
    appHeader.firstElementChild.textContent = t(settings.language, "appName");
    const appBadge = document.createElement("span");
    const appAvailable = data.health?.status === "running";
    appBadge.className = `connection-badge ${appAvailable ? "available" : "unavailable"}`;
    appBadge.textContent = t(settings.language, appAvailable ? "appRunning" : "appUnavailable");
    appHeader.append(appBadge);
    appCard.append(appHeader);
    if (appAvailable) {
      const detail = document.createElement("small");
      detail.textContent = `${t(settings.language, "mode")}: ${data.health.mode || "unknown"}`;
      appCard.append(detail);
    }
    connectionList.append(appCard);

    const servers = Array.isArray(data.services?.servers) ? data.services.servers : [];
    renderToolShortcuts(servers);
    for (const server of servers) {
      const card = document.createElement("article");
      card.className = "connection-item";
      const header = document.createElement("header");
      const name = document.createElement("strong");
      name.textContent = server.server || "MCP";
      const badge = document.createElement("span");
      const available = server.status === "available";
      badge.className = `connection-badge ${available ? "available" : "unavailable"}`;
      badge.textContent = t(settings.language, available ? "available" : "unavailable");
      header.append(name, badge);
      card.append(header);
      const tools = document.createElement("small");
      tools.textContent = `${t(settings.language, "tools")}: ${Array.isArray(server.tools) && server.tools.length ? server.tools.join(", ") : t(settings.language, "noTools")}`;
      card.append(tools);
      connectionList.append(card);
    }
  }

  function renderToolShortcuts(servers) {
    const list = $("tool-shortcut-list");
    list.replaceChildren();
    const known = new Set();
    for (const server of servers) {
      for (const tool of Array.isArray(server.tools) ? server.tools : []) {
        if (typeof tool !== "string" || !tool.trim() || known.has(tool)) continue;
        known.add(tool);
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.command = `/tool ${tool} {}`;
        button.textContent = tool;
        button.addEventListener("click", () => fillComposer(button.dataset.command));
        list.append(button);
      }
    }
    // Keep the familiar tools available even when status discovery cannot reach an MCP server.
    for (const tool of ["schema__get_schema", "constraints__get_query_policy", "examples__get_examples"]) {
      if (known.has(tool)) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.command = `/tool ${tool} {}`;
      button.textContent = tool;
      button.addEventListener("click", () => fillComposer(button.dataset.command));
      list.append(button);
    }
  }

  function selectTab(name) {
    const tab = document.querySelector(`[data-tab="${name}"]`);
    if (!tab) return;
    activeTab = name;
    document.querySelectorAll("[data-tab]").forEach((button) => {
      const selected = button === tab;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    });
    document.querySelectorAll(".drawer-panel").forEach((panel) => { panel.hidden = panel.id !== `panel-${name}`; });
    if (name === "connections") refreshConnections();
  }

  function openDrawer(tab = activeTab) {
    drawerReturnFocus = document.activeElement;
    drawer.inert = false;
    drawer.setAttribute("aria-hidden", "false");
    drawer.classList.add("open");
    drawerBackdrop.hidden = false;
    menuButton.setAttribute("aria-expanded", "true");
    menuButton.setAttribute("aria-label", t(settings.language, "menuClose"));
    selectTab(tab);
    requestAnimationFrame(() => document.querySelector(`[data-tab="${activeTab}"]`)?.focus());
  }

  function closeDrawer(restoreFocus = true) {
    const wasOpen = drawer.classList.contains("open");
    drawer.classList.remove("open");
    drawer.inert = true;
    drawer.setAttribute("aria-hidden", "true");
    drawerBackdrop.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", t(settings.language, "menuOpen"));
    if (wasOpen && restoreFocus) drawerReturnFocus?.focus?.();
  }

  function handleDrawerKeys(event) {
    if (event.key === "Escape") { closeDrawer(); return; }
    if (event.key !== "Tab") return;
    const focusable = [...drawer.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')].filter((node) => !node.closest("[hidden]"));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  async function handleQuery(event) {
    event.preventDefault();
    const sql = $("query-sql").value;
    const status = $("query-status");
    const output = $("query-result");
    if (!sql.trim()) { queryStatusKey = "enterSql"; status.textContent = t(settings.language, queryStatusKey); return; }
    $("query-submit").disabled = true;
    queryStatusKey = "querySending";
    status.textContent = t(settings.language, queryStatusKey);
    output.replaceChildren();
    queryOutputKey = "";
    queryOutputRaw = "";
    try {
      const result = await submitQuery(sql);
      queryStatusKey = result.status === "suppressed" ? "querySuppressed" : "queryApproved";
      status.textContent = t(settings.language, queryStatusKey);
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(result, null, 2);
      output.append(pre);
    } catch (error) {
      queryStatusKey = error.code === "query_rejected" ? "queryRejected" : "queryFailed";
      status.textContent = t(settings.language, queryStatusKey);
      const pre = document.createElement("pre");
      const unreachable = error instanceof ApiError && error.unreachable;
      queryOutputKey = unreachable ? "gatewayUnavailable" : "raw";
      queryOutputRaw = error.message || t(settings.language, "gatewayUnavailable");
      pre.textContent = unreachable ? t(settings.language, "gatewayUnavailable") : queryOutputRaw;
      if (unreachable) setBackendUnavailable(true);
      output.append(pre);
    } finally {
      $("query-submit").disabled = false;
    }
  }

  function handleGlobalKeys(event) {
    const key = event.key.toLowerCase();
    if ((event.metaKey || event.ctrlKey) && key === "k") {
      event.preventDefault();
      closeDrawer();
      input.focus();
    } else if ((event.metaKey || event.ctrlKey) && event.shiftKey && key === "o") {
      event.preventDefault();
      startNewChat();
    } else if (event.key === "?" && !event.metaKey && !event.ctrlKey && !event.altKey && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
      openDrawer("about");
    }
  }

  function startNewChat() {
    messages = [];
    input.value = "";
    autoGrow();
    requestStatusKey = "sessionCleared";
    requestStatus.textContent = t(settings.language, requestStatusKey);
    setBackendUnavailable(false);
    renderChat();
    closeDrawer();
    input.focus();
  }

  async function loadSuggestions() {
    try {
      const response = await fetch("/static/suggestions.json", { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) return;
      const body = await response.json();
      if (Array.isArray(body)) {
        suggestions = body.filter((value) => typeof value === "string").slice(0, 12);
        suggestionSets = { de: suggestions, en: suggestions };
      } else if (body && typeof body === "object") {
        suggestionSets = {
          de: Array.isArray(body.de) ? body.de.filter((value) => typeof value === "string").slice(0, 12) : [],
          en: Array.isArray(body.en) ? body.en.filter((value) => typeof value === "string").slice(0, 12) : [],
        };
        suggestions = suggestionSets.de;
      }
      renderWelcome();
    } catch { /* Suggestions are optional; there are no external requests. */ }
  }

  applySettings();
  drawer.inert = true;
  $("language-select").addEventListener("change", (event) => updateSetting("language", event.target.value));
  document.querySelectorAll("[data-language]").forEach((button) => button.addEventListener("click", () => updateSetting("language", button.dataset.language)));
  $("theme-select").addEventListener("change", (event) => updateSetting("theme", event.target.value));
  $("theme-quick-toggle").addEventListener("click", () => updateSetting("theme", html.dataset.theme === "dark" ? "light" : "dark"));
  assistantModeButtons.forEach((button) => button.addEventListener("click", () => {
    if (button.dataset.modeOption === "assistant" && !assistantConfigured) return;
    assistantMode.value = button.dataset.modeOption;
    assistantModeButtons.forEach((option) => {
      option.setAttribute("aria-pressed", String(option === button));
    });
    syncModeNotice();
  }));
  $("setting-font-size").addEventListener("change", (event) => updateSetting("fontSize", event.target.value));
  $("setting-density").addEventListener("change", (event) => updateSetting("density", event.target.value));
  $("setting-motion").addEventListener("change", (event) => updateSetting("reduceMotion", event.target.value));
  $("setting-autocomplete").addEventListener("change", (event) => updateSetting("autocomplete", event.target.checked));
  $("setting-show-sql").addEventListener("change", (event) => updateSetting("showSql", event.target.checked));
  $("setting-show-details").addEventListener("change", (event) => updateSetting("showDetails", event.target.checked));
  $("setting-name").addEventListener("input", (event) => {
    settings = { ...settings, displayName: event.target.value.slice(0, 40) };
    saveSettings(settings);
    renderWelcome();
  });
  $("reset-settings").addEventListener("click", () => {
    settings = resetSettings();
    applySettings();
    requestStatus.textContent = t(settings.language, "resetDone");
  });
  $("clear-button").addEventListener("click", startNewChat);

  $("menu-button").addEventListener("click", () => drawer.classList.contains("open") ? closeDrawer() : openDrawer());
  $("close-drawer").addEventListener("click", closeDrawer);
  drawerBackdrop.addEventListener("click", closeDrawer);
  drawer.addEventListener("keydown", handleDrawerKeys);
  document.querySelectorAll("[data-tab]").forEach((tab) => {
    tab.addEventListener("click", () => selectTab(tab.dataset.tab));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const tabs = [...document.querySelectorAll("[data-tab]")];
      const current = tabs.indexOf(tab);
      const next = (current + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
      tabs[next].focus();
      selectTab(tabs[next].dataset.tab);
    });
  });
  $("refresh-status").addEventListener("click", refreshConnections);
  $("query-form").addEventListener("submit", handleQuery);
  $("cancel-request").addEventListener("click", () => controller?.abort());
  $("jump-latest").addEventListener("click", () => scrollToLatest(true));

  composer.addEventListener("submit", (event) => { event.preventDefault(); suggestionDismissed = false; submitMessage(); });
  input.addEventListener("input", () => { suggestionDismissed = false; autoGrow(); updateGhost(); });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Tab" && composer.classList.contains("has-ghost")) {
      event.preventDefault();
      const match = currentSuggestions().find((item) => item.toLocaleLowerCase().startsWith(input.value.toLocaleLowerCase()) && item.length > input.value.length);
      if (match) fillComposer(match);
    } else if (event.key === "Escape" && composer.classList.contains("has-ghost")) {
      suggestionDismissed = true;
      updateGhost();
    } else if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (!isSending) composer.requestSubmit();
    }
  });
  document.querySelectorAll("[data-command]").forEach((button) => button.addEventListener("click", () => {
    fillComposer(button.dataset.command);
  }));
  chatScroll.addEventListener("scroll", () => {
    if (nearBottom()) jumpLatest.hidden = true;
  }, { passive: true });
  document.addEventListener("keydown", handleGlobalKeys);

  colorScheme.addEventListener?.("change", () => {
    if (settings.theme === "system") applySettings();
  });
  motionPreference.addEventListener?.("change", () => {
    if (settings.reduceMotion === "auto") applySettings();
  });

  void loadSuggestions();
  void refreshConnections();
}
