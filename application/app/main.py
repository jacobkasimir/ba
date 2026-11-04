import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .event_log import EventLog
from .mcp_client import MCPManager, MCPUnavailable, UnknownTool

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .gateway_client import GatewayClient
from .query_api import router as query_router

from .assistant_api import router as assistant_router
from .assistant_bindings import (
    CONTEXT_TOOLS,
    call_context_tool,
)
from .assistant_context import ContextLoader
from .assistant_service import AssistantService
from .llm_client import LLMClient

class ChatRequest(BaseModel):
    """A bounded development chat message."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=4000,
        strict=True,
    )


def parse_tool_command(message: str) -> tuple[str, dict]:
    """Parse: /tool server__tool {json}

    This parser does not perform fuzzy intent recognition.
    """

    parts = message.strip().split(maxsplit=2)

    if len(parts) != 3 or parts[0] != "/tool":
        raise ValueError(
            "Use: /tool server__tool {}"
        )

    tool_name = parts[1]

    try:
        arguments = json.loads(parts[2])
    except json.JSONDecodeError:
        raise ValueError(
            "Tool arguments must be valid JSON"
        ) from None

    if not isinstance(arguments, dict):
        raise ValueError(
            "Tool arguments must be a JSON object"
        )

    return tool_name, arguments


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_path = Path(
        os.environ.get(
            "MCP_CONFIG_PATH",
            "/app/config/mcp_servers.json",
        )
    )

    log_path = Path(
        os.environ.get(
            "APP_LOG_PATH",
            "/app/logs/app.log.jsonl",
        )
    )

    # Invalid local configuration fails startup.
    # Unavailable remote services do not fail startup: connections are lazy.
    app.state.mcp = MCPManager(config_path)
    app.state.events = EventLog(log_path)

    app.state.debug_tools = (
        os.environ.get("ENABLE_DEBUG_TOOLS", "false").lower()
        == "true"
    )

    gateway_url = os.getenv("APP_GATEWAY_URL")
    gateway_key = os.getenv("APP_GATEWAY_KEY")

    if bool(gateway_url) != bool(gateway_key):
        raise ValueError(
            "APP_GATEWAY_URL and APP_GATEWAY_KEY must be configured together"
        )

    gateway = (
        GatewayClient(
            base_url=gateway_url,
            api_key=gateway_key,
            timeout_seconds=float(os.getenv("APP_GATEWAY_TIMEOUT", "12")),
        )
        if gateway_url and gateway_key
        else None
    )
    app.state.gateway = gateway

    llm = None
    app.state.assistant = None

    try:
        enabled = (
            os.getenv("LLM_ENABLED", "false").lower() == "true"
        )

        if enabled:
            if app.state.gateway is None:
                raise ValueError(
                    "LLM integration requires gateway configuration"
                )

            names = (
                "LLM_BASE_URL",
                "LLM_API_KEY",
                "LLM_MODEL",
            )
            settings = {
                name: os.getenv(name, "")
                for name in names
            }

            missing = [
                name
                for name, value in settings.items()
                if not value
            ]

            if missing:
                raise ValueError(
                    "Missing LLM settings: " + ", ".join(missing)
                )

            async def call_mcp(server, tool, arguments):
                return await call_context_tool(
                    app.state.mcp,
                    server,
                    tool,
                    arguments,
                )

            context_loader = ContextLoader(
                call_tool=call_mcp,
                tools=CONTEXT_TOOLS,
            )

            llm = LLMClient(
                base_url=settings["LLM_BASE_URL"],
                api_key=settings["LLM_API_KEY"],
                model=settings["LLM_MODEL"],
            )

            app.state.assistant = AssistantService(
                context_loader=context_loader,
                llm=llm,
                gateway=app.state.gateway,
            )

        yield
    finally:
        if llm is not None:
            await llm.aclose()

        if gateway is not None:
            await gateway.aclose()


app = FastAPI(
    title="AKTIN Prototype Application",
    lifespan=lifespan,
)

app.include_router(query_router)
app.include_router(assistant_router)

STATIC_DIRECTORY = Path(__file__).resolve().parent.parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIRECTORY)), name="static")

@app.get("/", include_in_schema=False)
def frontend():
    """Serve the browser UI from the same origin as the API."""

    return FileResponse(
        STATIC_DIRECTORY / "index.html",
        media_type="text/html",

        # Helpful during development so HTML updates are revalidated.
        headers={"Cache-Control": "no-cache"},
    )

@app.get("/health/live")
def live():
    """Check whether the application process is running."""
    return {"status": "running", "mode": "echo"}


@app.get("/api/mcp/status")
async def mcp_status(request: Request):
    """Check each configured MCP server independently."""

    statuses = await request.app.state.mcp.inspect_all()

    for item in statuses:
        request.app.state.events.write(
            "mcp_status",
            server=item["server"],
            status=item["status"],
        )

    return {"servers": statuses}


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request):
    """Development chat endpoint.

    Ordinary input is echoed.
    /tool invokes only configured context tools.
    No LLM and no SQL execution are involved.
    """

    message = body.message.strip()
    request_id = str(uuid4())

    if not message:
        raise HTTPException(
            status_code=422,
            detail="Message must not be empty",
        )

    if not message.startswith("/tool"):
        request.app.state.events.write(
            "echo",
            request_id=request_id,
            character_count=len(message),
        )

        return {
            "request_id": request_id,
            "mode": "echo",
            "message": message,
        }

    if not request.app.state.debug_tools:
        raise HTTPException(
            status_code=403,
            detail="Development tool commands are disabled",
        )

    try:
        tool_name, arguments = parse_tool_command(message)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from None

    # Do not log the submitted JSON arguments or full message.
    request.app.state.events.write(
        "tool_call",
        request_id=request_id,
        tool=tool_name,
    )

    try:
        result = await request.app.state.mcp.call_tool(
            tool_name,
            arguments,
        )

    except UnknownTool:
        request.app.state.events.write(
            "tool_error",
            request_id=request_id,
            tool=tool_name,
            reason="unknown_tool",
        )

        raise HTTPException(
            status_code=404,
            detail="Unknown or disallowed tool",
        ) from None

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from None

    except MCPUnavailable:
        request.app.state.events.write(
            "tool_error",
            request_id=request_id,
            tool=tool_name,
            reason="mcp_unavailable",
        )

        raise HTTPException(
            status_code=503,
            detail="The requested context tool is unavailable",
        ) from None

    request.app.state.events.write(
        "tool_result",
        request_id=request_id,
        tool=tool_name,
        context_version=result.get("context_version"),
    )

    return {
        "request_id": request_id,
        "mode": "tool",
        "tool": tool_name,
        "result": result,
    }
