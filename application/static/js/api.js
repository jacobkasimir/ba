export class ApiError extends Error {
  constructor(message, { status = 0, code = null, unreachable = false } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.unreachable = unreachable;
  }
}

async function requestJSON(url, options = {}) {
  let response;
  try {
    response = await fetch(url, { cache: "no-store", ...options, headers: { Accept: "application/json", ...(options.headers || {}) } });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(error.message, { unreachable: true });
  }

  let body;
  try { body = await response.json(); } catch {
    throw new ApiError(`HTTP ${response.status}`, { status: response.status });
  }
  if (!response.ok) {
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : (detail?.message || `HTTP ${response.status}`);
    throw new ApiError(message, { status: response.status, code: detail?.code || null });
  }
  return body;
}

// Keep the deployed API contracts exact: this backend accepts {message}; it
// does not accept session_id. All requests remain same-origin.
export function sendChat(message, signal) {
  return requestJSON("/api/chat", {
    method: "POST", signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}

export async function askAssistant(question, signal) {
  const response = await fetch("/api/assistant", {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      "X-Query-Action": "submit",
    },
    body: JSON.stringify({ question }),
  });

  let body;
  try { body = await response.json(); } catch { body = {}; }

  if (!response.ok) {
    const error = new ApiError("Assistant request failed", {
      status: response.status,
      code: body?.detail?.code ?? "assistant_request_failed",
    });
    throw error;
  }

  return body;
}

export function getHealth(signal) { return requestJSON("/health/live", { signal }); }
export function getConnections(signal) { return requestJSON("/api/mcp/status", { signal }); }

export function submitQuery(sql, signal) {
  return requestJSON("/api/query", {
    method: "POST", signal,
    headers: { "Content-Type": "application/json", "X-Query-Action": "submit" },
    body: JSON.stringify({ sql }),
  });
}
