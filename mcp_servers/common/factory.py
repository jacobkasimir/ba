from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


def create_mcp(
    display_name: str,
    service_name: str,
) -> FastMCP:
    """Create an internal Streamable HTTP MCP server."""

    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,

        # The Host header must match an expected container hostname.
        allowed_hosts=[
            f"{service_name}:8000",
            "localhost:8000",
            "127.0.0.1:8000",
        ],

        # These services are not intended for direct browser access.
        # The server-to-server MCP client sends no Origin header.
        allowed_origins=[],
    )

    return FastMCP(
        display_name,

        # Listen on container interfaces.
        # Docker Compose still controls whether the host can access it.
        host="0.0.0.0",
        port=8000,

        # The tools only read static metadata.
        stateless_http=True,

        # Small ordinary responses are sufficient for this prototype.
        json_response=True,

        transport_security=security,
    )