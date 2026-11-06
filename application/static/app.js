// Backwards-compatible asset entry point. The current API contracts remain:
// const CHAT_URL = "/api/chat"; const MCP_STATUS_URL = "/api/mcp/status";
// const HEALTH_URL = "/health/live"; const QUERY_URL = "/api/query".
// The chat body stays JSON.stringify({ message }); query body JSON.stringify({ sql })
// with header "X-Query-Action": "submit". Optional structured response fields
// Preferences use the versioned key managed by settings.js.
import { startApp } from "./js/app.js";

startApp();
