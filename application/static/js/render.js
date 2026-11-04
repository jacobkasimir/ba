import { t } from "./i18n.js";

const codeMessages = [
  "TABLE_NOT_ALLOWED", "IDENTIFIER_COLUMN", "STAR_NOT_ALLOWED", "FUNCTION_NOT_ALLOWED",
  "MISSING_COUNT_COLUMN", "UNKNOWN_COLUMN", "NOT_SELECT", "NOT_SINGLE_STATEMENT",
  "FORBIDDEN_OPERATION", "PARSE_ERROR", "RUNTIME_ERROR",
];

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function actionButton(label, handler, className = "small-action") {
  const button = element("button", className, label);
  button.type = "button";
  button.addEventListener("click", handler);
  return button;
}

function formatValue(value, language) {
  if (value === null) return t(language, "nullValue");
  if (typeof value === "number" && Number.isFinite(value)) return new Intl.NumberFormat(language).format(value);
  if (typeof value === "boolean") return String(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
}

function appendHighlightedSql(pre, sql) {
  const pattern = /(--[^\n]*|'(?:''|[^'])*'|"(?:""|[^"])*"|\b(?:SELECT|FROM|WHERE|GROUP|BY|ORDER|HAVING|LIMIT|COUNT|DISTINCT|AS|AND|OR|NOT|NULL|IS|IN|JOIN|ON|CASE|WHEN|THEN|ELSE|END|ASC|DESC)\b)/gi;
  let cursor = 0;
  for (const match of sql.matchAll(pattern)) {
    if (match.index > cursor) pre.append(document.createTextNode(sql.slice(cursor, match.index)));
    const token = match[0];
    const className = token.startsWith("--") ? "sql-comment" : (token.startsWith("'") || token.startsWith('"') ? "sql-string" : "sql-keyword");
    pre.append(element("span", className, token));
    cursor = match.index + token.length;
  }
  if (cursor < sql.length) pre.append(document.createTextNode(sql.slice(cursor)));
}

function renderTable(columns, rows, language) {
  if (!Array.isArray(columns) || !Array.isArray(rows)) return null;
  const wrap = element("div", "result-wrap");
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", t(language, "resultTable"));
  wrap.tabIndex = 0;
  const table = element("table", "result-table");
  const head = element("thead");
  const headRow = element("tr");
  const names = columns.map((column, index) => typeof column === "string" ? column : (column?.name ?? column?.label ?? String(index + 1)));
  for (const name of names) headRow.append(element("th", "", name));
  head.append(headRow);
  const body = element("tbody");
  for (const row of rows) {
    const tr = element("tr");
    names.forEach((name, index) => {
      const value = Array.isArray(row) ? row[index] : row?.[name];
      const numeric = typeof value === "number";
      tr.append(element("td", numeric ? "numeric" : "", formatValue(value, language)));
    });
    body.append(tr);
  }
  table.append(head, body);
  wrap.append(table);
  return wrap;
}

function renderErrorCodes(codes, language) {
  if (!Array.isArray(codes) || !codes.length) return null;
  const holder = element("div", "error-explanations");
  const allowed = new Set(codeMessages);
  for (const raw of codes) {
    const code = typeof raw === "string" ? raw : raw?.code;
    if (!code) continue;
    const p = element("p", "friendly-error", t(language, `error_${code}`) === `error_${code}` ? t(language, "blocked") : t(language, `error_${code}`));
    const rawCode = element("code", "error-code", code);
    p.append(document.createTextNode(" "), rawCode);
    holder.append(p);
    if (!allowed.has(code)) rawCode.classList.add("unknown-error-code");
  }
  return holder;
}

function renderDetails(payload, language, settings) {
  const fields = [
    ["attempts", "attempts"], ["error_codes", "errorCodes"],
    ["suppressed_rows", "suppressedRows"], ["min_cell_count", "minCellCount"],
  ].filter(([key]) => Object.prototype.hasOwnProperty.call(payload, key));
  if (!fields.length) return null;
  const details = element("details", "details-section");
  details.open = Boolean(settings.showDetails);
  details.append(element("summary", "", t(language, "details")));
  const dl = element("dl", "detail-grid");
  for (const [key, label] of fields) {
    dl.append(element("dt", "", t(language, label)));
    const value = Array.isArray(payload[key]) ? payload[key].join(", ") : formatValue(payload[key], language);
    dl.append(element("dd", "", value));
  }
  details.append(dl);
  return details;
}

function renderSql(sql, language, settings, onCopy) {
  if (typeof sql !== "string" || !sql.trim()) return null;
  const details = element("details", "sql-details");
  details.open = Boolean(settings.showSql);
  const summary = element("summary", "", t(language, "sql"));
  details.append(summary);
  const toolbar = element("div", "sql-toolbar");
  toolbar.append(actionButton(t(language, "copySql"), () => onCopy(sql), "small-action copy-sql"));
  details.append(toolbar);
  const pre = element("pre", "sql-code");
  pre.setAttribute("aria-label", t(language, "sql"));
  appendHighlightedSql(pre, sql);
  details.append(pre);
  return details;
}

function normalizePayload(payload) {
  return payload && typeof payload === "object" ? payload : { reply: String(payload ?? "") };
}

export function renderMessage(message, { language, settings, onAction }) {
  const row = element("article", `message-row ${message.role}`);
  row.dataset.messageId = message.id;
  const avatar = element("div", "message-avatar", message.role === "user" ? t(language, "user") : "A");
  avatar.setAttribute("aria-hidden", "true");
  const body = element("div", "message-body");

  if (message.role === "user") {
    body.append(element("div", "user-bubble", message.text));
    body.append(element("div", "message-actions", ""));
    const actions = body.lastElementChild;
    actions.append(actionButton(t(language, "edit"), () => onAction("edit", message)));
    row.append(body, avatar);
    return row;
  }

  if (message.kind === "assistant-reply") {
    return renderAssistantReply(message.payload, language);
  }

  const payload = normalizePayload(message.payload || {});
  const isFailure = message.role === "error" || payload.ok === false;
  const card = element("div", isFailure ? "error-card" : "assistant-card");
  const header = element("div", "assistant-header");
  let kind = message.role === "error" || message.kind === "error"
    ? t(language, "requestError")
    : (message.kind === "tool" ? t(language, "context") : (message.kind === "echo" ? t(language, "demo") : t(language, "analysis")));
  header.append(element("span", "assistant-kind", kind));
  card.append(header);

  const answer = message.uiKey ? t(language, message.uiKey) : (payload.answer ?? payload.reply ?? payload.message);
  if (isFailure) card.append(element("p", "friendly-error", typeof answer === "string" ? answer : t(language, "blocked")));
  else if (typeof answer === "string" && answer.length) card.append(element("p", "message-content", answer));
  else if (message.kind === "tool" && payload.result !== undefined) {
    const output = element("details", "details-section");
    output.append(element("summary", "", t(language, "context")));
    const pre = element("pre", "sql-code", JSON.stringify(payload.result, null, 2));
    output.append(pre);
    card.append(output);
  } else card.append(element("p", "message-content", t(language, "emptyAnswer")));

  const codes = renderErrorCodes(payload.error_codes, language);
  if (codes) card.append(codes);

  const table = renderTable(payload.columns, payload.rows, language);
  if (table) card.append(table);

  const sql = renderSql(payload.sql, language, settings, (value) => onAction("copy", { text: value }));
  if (sql) card.append(sql);
  const details = renderDetails(payload, language, settings);
  if (details) card.append(details);

  const actions = element("div", "message-actions");
  if (typeof answer === "string" && answer) actions.append(actionButton(t(language, "copyAnswer"), () => onAction("copy", { text: answer })));
  if (typeof payload.sql === "string" && payload.sql) actions.append(actionButton(t(language, "copySql"), () => onAction("copy", { text: payload.sql })));
  if (Array.isArray(payload.columns) && Array.isArray(payload.rows)) actions.append(actionButton(t(language, "downloadCsv"), () => onAction("csv", { columns: payload.columns, rows: payload.rows })));
  if (isFailure && message.retryText) actions.append(actionButton(t(language, "retry"), () => onAction("retry", { text: message.retryText }), "small-action primary-button"));
  if (actions.childElementCount) card.append(actions);
  body.append(card);
  row.append(avatar, body);
  return row;
}

function renderAssistantReply(reply, language) {
  const row = element("article", "message-row assistant");
  const avatar = element("div", "message-avatar", "A");
  avatar.setAttribute("aria-hidden", "true");
  const body = element("div", "message-body");
  const card = element("div", "assistant-card");
  card.append(element("div", "assistant-header", t(language, "assistant")));

  const statusKey = `assistant.status.${reply?.status}`;
  const knownStatus = ["completed", "suppressed", "unsupported", "rejected"].includes(reply?.status);
  const status = element("p", "message-content", t(language, knownStatus ? statusKey : "assistant.error.invalidResult"));
  card.append(status);

  if (reply?.proposed_sql !== null && typeof reply?.proposed_sql === "string") {
    const details = element("details", "sql-details");
    details.append(element("summary", "", t(language, "sql")));
    details.append(element("pre", "sql-code", reply.proposed_sql));
    card.append(details);
  }

  if (reply?.status === "completed") {
    if (!Number.isSafeInteger(reply.count) || reply.count < 0) {
      status.textContent = t(language, "assistant.error.invalidResult");
    } else {
      card.append(element("p", "message-content assistant-count", String(reply.count)));
    }
  } else if (reply?.status === "suppressed") {
    card.append(element("p", "message-content", t(language, "assistant.result.suppressed")));
  }

  body.append(card);
  row.append(avatar, body);
  return row;
}
