"use strict";

// All API URLs are relative to the page's own origin.
// If the page is loaded from http://127.0.0.1:8080/,
// requests also go to http://127.0.0.1:8080/.
const CHAT_URL = "/api/chat";
const MCP_STATUS_URL = "/api/mcp/status";
const HEALTH_URL = "/health/live";

// This is a browser-side waiting limit, not a database timeout.
// Backend MCP operations have their own shorter timeout.
const REQUEST_TIMEOUT_MS = 30000;

const form = document.getElementById("message-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const clearButton = document.getElementById("clear-button");
const refreshButton = document.getElementById("refresh-status");

const messages = document.getElementById("messages");
const requestStatus = document.getElementById("request-status");
const applicationStatus = document.getElementById("application-status");
const serverStatuses = document.getElementById("server-statuses");
const statusMessage = document.getElementById("status-message");

let sending = false;
let refreshing = false;


/**
 * Turn an API error into a readable message.
 *
 * FastAPI may return "detail" as a string or as an array of
 * validation errors. Never insert it as HTML.
 */
function describeError(body, httpStatus) {
  if (typeof body?.detail === "string") {
    return body.detail;
  }

  if (Array.isArray(body?.detail)) {
    return body.detail
      .map((entry) => {
        const location = Array.isArray(entry.loc)
          ? entry.loc.join(".")
          : "request";

        return `${location}: ${entry.msg ?? "Invalid value"}`;
      })
      .join("; ");
  }

  return `Request failed with HTTP ${httpStatus}`;
}


/**
 * Send an HTTP request and read a JSON response.
 *
 * An AbortController prevents the browser from waiting indefinitely.
 * Aborting the browser request does not guarantee that every backend
 * operation has stopped; backend timeouts are still necessary.
 */
async function requestJSON(url, options = {}) {
  const controller = new AbortController();

  const timeout = setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS
  );

  try {
    const headers = new Headers(options.headers ?? {});
    headers.set("Accept", "application/json");

    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
      cache: "no-store",
    });

    let body;

    try {
      body = await response.json();
    } catch {
      throw new Error(
        `Expected JSON from ${url}, received HTTP ${response.status}`
      );
    }

    if (!response.ok) {
      throw new Error(describeError(body, response.status));
    }

    return body;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(
        "The request timed out. Check application and MCP service status."
      );
    }

    if (error instanceof TypeError) {
      throw new Error(
        "The application could not be reached. Check that it is running."
      );
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}


/**
 * Append a message using safe DOM operations.
 *
 * We deliberately use textContent rather than innerHTML.
 */
function appendMessage(kind, title, text) {
  document.getElementById("empty-message")?.remove();

  const article = document.createElement("article");
  article.className = `message ${kind}`;

  const heading = document.createElement("strong");
  heading.className = "message-title";
  heading.textContent = title;

  const paragraph = document.createElement("p");
  paragraph.className = "message-text";
  paragraph.textContent = text;

  article.append(heading, paragraph);
  messages.append(article);

  messages.scrollTop = messages.scrollHeight;

  return article;
}


/**
 * Render the existing backend response contract.
 *
 * Echo responses and MCP context results are not database analyses.
 */
function renderResponse(response) {
  let article;

  if (response.mode === "echo") {
    article = appendMessage(
      "assistant",
      "Echo response",
      typeof response.message === "string"
        ? response.message
        : "The server returned no echo text."
    );

    const note = document.createElement("p");
    note.className = "message-meta";
    note.textContent = "No LLM or database query was used.";
    article.append(note);

  } else if (response.mode === "tool") {
    article = appendMessage(
      "assistant",
      `MCP context: ${response.tool ?? "unknown tool"}`,
      "Context metadata was retrieved. No SQL was executed."
    );

    const output = document.createElement("pre");

    // JSON.stringify produces text; textContent displays it literally.
    output.textContent = JSON.stringify(
      response.result ?? null,
      null,
      2
    );

    article.append(output);

  } else {
    // Do not guess that an unfamiliar response represents success.
    throw new Error(
      "The backend returned an unsupported response format."
    );
  }

  if (response.request_id) {
    const identifier = document.createElement("p");
    identifier.className = "message-meta";
    identifier.textContent = `Request ID: ${response.request_id}`;
    article.append(identifier);
  }

  messages.scrollTop = messages.scrollHeight;
}


/**
 * Disable submission while a request is active.
 * This avoids accidental duplicate requests.
 */
function setSending(value) {
  sending = value;

  sendButton.disabled = value;
  clearButton.disabled = value;
  input.disabled = value;

  document.querySelectorAll("[data-command]").forEach((button) => {
    button.disabled = value;
  });

  form.setAttribute("aria-busy", String(value));
  sendButton.textContent = value ? "Sending…" : "Send";
}


/**
 * Submit either ordinary text or a development /tool command.
 */
async function submitMessage(event) {
  event.preventDefault();

  if (sending) {
    return;
  }

  const message = input.value.trim();

  if (!message) {
    input.focus();
    return;
  }

  appendMessage("user", "You", message);

  setSending(true);
  requestStatus.textContent = "Waiting for the application…";

  try {
    const response = await requestJSON(CHAT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },

      // Match the current FastAPI ChatRequest model exactly.
      // Do not add session_id unless the backend explicitly supports it.
      body: JSON.stringify({ message }),
    });

    renderResponse(response);

    input.value = "";
    requestStatus.textContent = "Response received.";

  } catch (error) {
    appendMessage("error", "Request failed", error.message);

    // Keep the input so the user can edit or retry it.
    requestStatus.textContent =
      "No successful result was returned. You can edit and retry.";

  } finally {
    setSending(false);
    input.focus();
  }
}

form.addEventListener("submit", submitMessage);


// Enter submits; Shift+Enter inserts a new line.
// isComposing avoids interrupting input-method composition.
input.addEventListener("keydown", (event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.isComposing
  ) {
    event.preventDefault();

    if (!sending) {
      form.requestSubmit();
    }
  }
});


// Shortcut buttons only fill the input.
// The user presses Send to make the actual request.
document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.command;
    input.focus();
  });
});


clearButton.addEventListener("click", () => {
  messages.replaceChildren();

  const notice = document.createElement("p");
  notice.id = "empty-message";
  notice.className = "muted";
  notice.textContent =
    "Display cleared. This does not delete server-side logs.";

  messages.append(notice);
});


function showUnavailableStatus(message) {
  serverStatuses.replaceChildren();

  const item = document.createElement("li");
  item.className = "server-item";
  item.textContent = message;

  serverStatuses.append(item);
}


/**
 * Render MCP discovery status.
 *
 * "available" means the backend could initialize/discover the MCP
 * server during this check. It does not mean PostgreSQL is available.
 */
function renderServerStatuses(response) {
  if (!Array.isArray(response.servers)) {
    throw new Error("The MCP status response has an unexpected format.");
  }

  serverStatuses.replaceChildren();

  for (const server of response.servers) {
    const item = document.createElement("li");
    item.className = "server-item";

    const heading = document.createElement("div");
    heading.className = "server-heading";

    const name = document.createElement("strong");
    name.textContent = server.server ?? "Unknown server";

    const available = server.status === "available";

    const badge = document.createElement("span");
    badge.className =
      `badge ${available ? "available" : "unavailable"}`;
    badge.textContent = available ? "Available" : "Unavailable";

    heading.append(name, badge);

    const tools = document.createElement("small");
    tools.textContent =
      Array.isArray(server.tools) && server.tools.length
        ? server.tools.join(", ")
        : "No tools available from this check";

    item.append(heading, tools);
    serverStatuses.append(item);
  }
}


/**
 * Refresh application and MCP status.
 *
 * Failures clear previous status so stale green indicators are not
 * left on screen.
 */
async function refreshStatus() {
  if (refreshing) {
    return;
  }

  refreshing = true;
  refreshButton.disabled = true;
  statusMessage.textContent = "Checking services…";

  applicationStatus.className = "badge";
  applicationStatus.textContent = "Checking application";

  try {
    const health = await requestJSON(HEALTH_URL);

    if (health.status !== "running") {
      throw new Error("Unexpected application health response");
    }

    applicationStatus.className = "badge available";
    applicationStatus.textContent =
      `Application running · ${health.mode ?? "unknown"} mode`;

  } catch (error) {
    applicationStatus.className = "badge unavailable";
    applicationStatus.textContent = "Application unavailable";

    showUnavailableStatus("MCP status could not be checked.");
    statusMessage.textContent = error.message;

    refreshButton.disabled = false;
    refreshing = false;
    return;
  }

  try {
    const status = await requestJSON(MCP_STATUS_URL);
    renderServerStatuses(status);
    statusMessage.textContent = "Status check completed.";

  } catch (error) {
    showUnavailableStatus("MCP status could not be checked.");
    statusMessage.textContent = error.message;

  } finally {
    refreshButton.disabled = false;
    refreshing = false;
  }
}

refreshButton.addEventListener("click", refreshStatus);

// Perform one initial check, rather than repeatedly polling all servers.
refreshStatus();