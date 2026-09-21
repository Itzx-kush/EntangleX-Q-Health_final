from starlette.responses import JSONResponse

class BodyLimitMiddleware:
    """Bound the complete ASGI body before multipart or JSON parsing.

    This also bounds chunked requests without Content-Length. Payloads are never logged.
    """
    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        try:
            advertised = int(headers.get(b"content-length", b"0"))
        except ValueError:
            advertised = self.max_bytes + 1
        async def too_large():
            response = JSONResponse({"error": {"code": "request_too_large", "message": "Request body exceeds the configured size limit."}}, status_code=413)
            await response(scope, receive, send)
        if advertised > self.max_bytes or advertised < 0:
            await too_large()
            return
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                await too_large()
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body, delivered = b"".join(chunks), False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()
        await self.app(scope, replay, send)
