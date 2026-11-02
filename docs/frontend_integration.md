# Frontend Integration

## Purpose

Provide a browser interface for the existing application echo mode
and development MCP tool commands.

## Technology

Plain HTML, CSS, and JavaScript.
No frontend build step.
Static assets are packaged in the FastAPI application image.

## Routes

GET /
GET /static/style.css
GET /static/app.js

Existing API routes used:

GET /health/live
GET /api/mcp/status
POST /api/chat

## Request contract

POST /api/chat

{
  "message": "Hello"
}

No session_id is sent by this implementation.

## Response handling

mode=echo:
Display echoed text and state that no model or database query was used.

mode=tool:
Display context metadata and state that no SQL was executed.

Unknown response formats:
Display an error rather than assuming an analysis succeeded.

## Connection architecture

Browser -> FastAPI -> MCP servers

The browser receives no PostgreSQL credentials or gateway API key.
It does not connect directly to MCP servers or PostgreSQL.

## Deployment

UI and API share the same origin:

http://127.0.0.1:8080/

No CORS configuration is required for this arrangement.

## Browser storage

Messages are not stored in localStorage.
Clearing the display does not delete backend logs.

## Security and limitations

Dynamic content is rendered with textContent.
Development tool commands remain development-only.
No LLM integration is added here.
No database-query execution is added here.
No analysis result or safety guarantee is inferred from MCP availability.

## Verification

- [ ] HTML, CSS, and JavaScript routes return 200.
- [ ] Application unit tests pass.
- [ ] Echo mode works through the browser.
- [ ] Each MCP tool works through the browser.
- [ ] Invalid commands produce clear errors.
- [ ] One failed server does not break working tools.
- [ ] Restarted server becomes available again.
- [ ] HTML-looking text is displayed literally.