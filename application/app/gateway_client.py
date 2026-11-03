import asyncio
import json
import math

import httpx


MAX_RESPONSE_BYTES = 64 * 1024


class GatewayError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def build_gateway_payload(sql: str) -> dict:
    """
    Integration adapter.

    Verify this against gateway/app/schemas.py.
    Add any other required gateway fields here.
    """
    return {"sql": sql}


class GatewayClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 12.0,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url or not api_key:
            raise ValueError("Gateway URL and API key are required")

        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("Gateway timeout must be positive and finite")

        url = httpx.URL(base_url)
        if url.scheme not in {"http", "https"} or not url.host:
            raise ValueError("Gateway URL must be an absolute HTTP(S) URL")

        if url.username or url.password or url.query or url.fragment:
            raise ValueError(
                "Gateway URL must not contain credentials, query, or fragment"
            )

        self._timeout_seconds = timeout_seconds
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={
                "X-Gateway-Key": api_key,
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(
                timeout_seconds,
                connect=min(2.0, timeout_seconds),
                pool=min(2.0, timeout_seconds),
            ),
            limits=httpx.Limits(
                max_connections=3,
                max_keepalive_connections=3,
            ),
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def submit(self, sql: str) -> dict:
        try:
            # Bounds the entire request, including receiving the response.
            async with asyncio.timeout(self._timeout_seconds):
                async with self._client.stream(
                    "POST",
                    "query",
                    json=build_gateway_payload(sql),
                ) as response:
                    self._check_status(response.status_code)

                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise GatewayError(
                                502,
                                "invalid_gateway_response",
                                "The gateway response exceeded the size limit.",
                            )
                        body.extend(chunk)

            try:
                result = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                raise GatewayError(
                    502,
                    "invalid_gateway_response",
                    "The gateway returned invalid JSON.",
                ) from None

            if not isinstance(result, dict):
                raise GatewayError(
                    502,
                    "invalid_gateway_response",
                    "The gateway returned an unexpected response format.",
                )

            return result

        except httpx.PoolTimeout:
            raise GatewayError(
                503,
                "gateway_busy",
                "The query service is busy. Try again later.",
            ) from None

        except (httpx.TimeoutException, TimeoutError):
            raise GatewayError(
                504,
                "gateway_timeout",
                "The gateway did not respond within the time limit.",
            ) from None

        except httpx.RequestError:
            raise GatewayError(
                502,
                "gateway_unavailable",
                "The query gateway could not be reached.",
            ) from None

    @staticmethod
    def _check_status(status_code: int) -> None:
        if 200 <= status_code < 300:
            return

        # Verify these rejection codes against gateway/app/main.py.
        if status_code in {400, 422}:
            raise GatewayError(
                422,
                "query_rejected",
                "The gateway rejected the query proposal.",
            )

        if status_code in {401, 403}:
            raise GatewayError(
                502,
                "gateway_authentication_failed",
                "Application-to-gateway authentication failed.",
            )

        if status_code == 429:
            raise GatewayError(
                503,
                "gateway_busy",
                "The query service is busy. Try again later.",
            )

        raise GatewayError(
            502,
            "gateway_error",
            "The gateway could not complete the request.",
        )