# Frontend Integration

## Purpose

Provide a browser interface for the existing application echo mode,
development MCP tool commands, and the separate query-gateway workflow.

## Technology

Plain HTML, CSS, and JavaScript.
No frontend build step.
Static assets are packaged in the FastAPI application image.
The chat UI is served from `application/static/`; its CSS tokens and styles,
JavaScript modules, and bilingual example prompts are local static assets.

## Chat interface preferences and suggestions

The interface supports German and English. `application/static/suggestions.json`
contains separate example-question lists for both languages; the selected
language controls the empty-state chips and prefix completion. Tab accepts the
visible completion, and Escape dismisses it. A matching partial suggestion is
shown as subdued ghost text; once the typed text diverges from the suggestion,
it is displayed normally. Choosing an example chip fills the chat input but
does not submit it.

Language and visual preferences are stored in versioned browser local storage.
Chat messages are not saved there. Theme options are dark, light, and system;
system follows the browser's current color-scheme preference.

## Routes

GET /
GET /static/style.css
GET /static/app.js

Existing API routes used:

GET /health/live
GET /api/mcp/status
POST /api/chat
POST /api/query

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

Individual MCP tools can be selected from the Connections drawer. Selecting a
tool fills a `/tool <server>__<tool> {}` command into the chat input; the user
can edit the JSON arguments before sending it. The drawer also retains the
known schema, constraints, and examples tool shortcuts when MCP discovery is
unavailable. Tool commands require `ENABLE_DEBUG_TOOLS=true` on the server.

Unknown response formats:
Display an error rather than assuming an analysis succeeded.

## Connection architecture

Browser -> FastAPI -> MCP servers (context requests)
                   -> Query gateway (explicit SQL proposals only)

The browser receives no PostgreSQL credentials or gateway API key.
It does not connect directly to MCP servers or PostgreSQL. SQL proposals are
sent to the application `/api/query` route, which delegates to the gateway.
Ordinary chat messages are not SQL proposals and are only echoed unless they
are explicit `/tool` commands.

## Deployment

UI and API share the same origin:

http://127.0.0.1:8080/

No CORS configuration is required for this arrangement.

## Browser storage

Messages are not stored in localStorage. Language, theme, display name, and
other UI preferences are stored under `aktin.frontend.settings.v1`.
Clearing the display does not delete backend logs.

## Security and limitations

Dynamic content is rendered with textContent.
Development tool commands remain development-only.
No LLM integration is added here.
Chat does not execute database queries. The separate query proposal view uses
the existing application-to-gateway workflow.
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
