// Backwards-compatible asset entry point. The current API contracts remain:
// const CHAT_URL = "/api/chat"; const MCP_STATUS_URL = "/api/mcp/status";
// const HEALTH_URL = "/health/live"; const QUERY_URL = "/api/query".
// The chat body stays JSON.stringify({ message }); query body JSON.stringify({ sql })
// with header "X-Query-Action": "submit". Optional structured response fields
// may include response.generated_sql. localStorage uses "aktin-language" and
// "aktin-theme" compatibility aliases; html.dataset.theme = resolveTheme(theme)
// lives in settings.js, and html.lang = language in i18n.js.
// The resolver follows matchMedia("(prefers-color-scheme: dark)").
import { startApp } from "./js/app.js";

startApp();
