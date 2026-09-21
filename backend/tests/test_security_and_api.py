import asyncio
from uuid import uuid4
import pytest
from app.api.middleware import BodyLimitMiddleware
from app.config import get_settings
from app.storage.files import atomic_bytes, safe_path, sanitize_filename, verify
from app.utils.errors import AppError

def test_safe_paths_and_filename():
    assert sanitize_filename("../../records.csv") == "records.csv"
    assert sanitize_filename("C:\\private\\records.csv") == "records.csv"
    with pytest.raises(AppError):
        safe_path("data/datasets", "../../etc/passwd", ".csv")
    with pytest.raises(AppError):
        safe_path("../../", str(uuid4()), ".csv")

def test_integrity_detects_modified_bytes():
    path = safe_path("data/datasets", str(uuid4()), ".csv")
    digest = atomic_bytes(path, b"fixture")
    verify(path, digest)
    path.write_bytes(b"changed")
    with pytest.raises(AppError, match="integrity"):
        verify(path, digest)

def test_health_and_private_origin(client):
    assert client.get("/api/health").status_code == 200
    blocked = client.get("/api/datasets", headers={"Origin": "https://untrusted.invalid"})
    assert blocked.status_code == 403

def test_bearer_token_is_enforced_when_configured(client, monkeypatch):
    # Runtime-generated test credential; no credential is embedded in source.
    import secrets
    token = secrets.token_urlsafe(32)
    monkeypatch.setattr(get_settings(), "api_token", token)
    assert client.get("/api/datasets").status_code == 401
    assert client.get("/api/datasets", headers={"Authorization": f"Bearer {token}"}).status_code == 200

def test_unknown_ids_and_validation_are_sanitized(client):
    response = client.get(f"/api/datasets/{uuid4()}")
    assert response.status_code == 404
    response = client.post("/api/training/jobs", json={"dataset_id": "private-record-marker"})
    assert response.status_code == 422
    assert "private-record-marker" not in response.text

def test_public_model_upload_route_does_not_exist(client):
    response = client.post("/api/models/upload", files={"file": ("model.dill", b"not-code", "application/octet-stream")})
    assert response.status_code in (404, 405, 422)

def test_original_records_not_exposed_in_dataset_summary(client, registered):
    result = client.get(f"/api/datasets/{registered.id}")
    assert result.status_code == 200
    assert "rows" not in result.json()
    assert "records" not in result.json()

def test_body_size_limit_is_enforced(client):
    response = client.post("/api/datasets/upload", content=b"", headers={"Content-Length": str(1024 * 1024 * 500)})
    assert response.status_code == 413

def test_body_limit_non_http_passthrough():
    app_called = False
    async def dummy_app(scope, receive, send):
        nonlocal app_called
        app_called = True

    middleware = BodyLimitMiddleware(dummy_app, max_bytes=100)
    scope = {"type": "websocket"}
    asyncio.run(middleware(scope, None, None))
    assert app_called is True

def test_body_limit_invalid_and_negative_content_length():
    async def mock_receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    for invalid_val in [b"invalid", b"-5", b"105"]:
        sent_messages = []
        async def mock_send(message):
            sent_messages.append(message)

        app_called = False
        async def dummy_app(scope, receive, send):
            nonlocal app_called
            app_called = True

        middleware = BodyLimitMiddleware(dummy_app, max_bytes=100)
        scope = {"type": "http", "headers": [(b"content-length", invalid_val)]}
        asyncio.run(middleware(scope, mock_receive, mock_send))

        assert app_called is False
        assert len(sent_messages) > 0
        assert sent_messages[0]["type"] == "http.response.start"
        assert sent_messages[0]["status"] == 413

def test_body_limit_exact_boundary_content_length():
    max_bytes = 100
    body_data = b"x" * max_bytes

    async def mock_receive():
        return {"type": "http.request", "body": body_data, "more_body": False}

    received_body = None
    async def dummy_app(scope, receive, send):
        nonlocal received_body
        msg = await receive()
        received_body = msg["body"]

    middleware = BodyLimitMiddleware(dummy_app, max_bytes=max_bytes)
    scope = {"type": "http", "headers": [(b"content-length", str(max_bytes).encode())]}
    asyncio.run(middleware(scope, mock_receive, None))
    assert received_body == body_data

    sent_messages = []
    async def mock_send(message):
        sent_messages.append(message)

    app_called = False
    async def dummy_app_fail(scope, receive, send):
        nonlocal app_called
        app_called = True

    scope_over = {"type": "http", "headers": [(b"content-length", str(max_bytes + 1).encode())]}
    asyncio.run(middleware(scope_over, mock_receive, mock_send))
    assert app_called is False
    assert sent_messages[0]["status"] == 413

def test_body_limit_chunked_boundary_and_exceeded():
    max_bytes = 100
    chunks_a = [
        {"type": "http.request", "body": b"a" * 50, "more_body": True},
        {"type": "http.request", "body": b"b" * 50, "more_body": False},
    ]
    idx_a = 0
    async def mock_receive_a():
        nonlocal idx_a
        msg = chunks_a[idx_a]
        idx_a += 1
        return msg

    received_body = None
    async def dummy_app_a(scope, receive, send):
        nonlocal received_body
        msg = await receive()
        received_body = msg["body"]

    middleware = BodyLimitMiddleware(dummy_app_a, max_bytes=max_bytes)
    scope = {"type": "http", "headers": []}
    asyncio.run(middleware(scope, mock_receive_a, None))
    assert received_body == b"a" * 50 + b"b" * 50

    chunks_b = [
        {"type": "http.request", "body": b"a" * 60, "more_body": True},
        {"type": "http.request", "body": b"b" * 51, "more_body": False},
    ]
    idx_b = 0
    async def mock_receive_b():
        nonlocal idx_b
        msg = chunks_b[idx_b]
        idx_b += 1
        return msg

    sent_messages = []
    async def mock_send(message):
        sent_messages.append(message)

    app_called = False
    async def dummy_app_b(scope, receive, send):
        nonlocal app_called
        app_called = True

    middleware_b = BodyLimitMiddleware(dummy_app_b, max_bytes=max_bytes)
    asyncio.run(middleware_b(scope, mock_receive_b, mock_send))
    assert app_called is False
    assert sent_messages[0]["status"] == 413

def test_body_limit_missing_body_key_and_disconnect():
    chunks = [
        {"type": "http.request", "more_body": False}
    ]
    async def mock_receive_missing():
        return chunks[0]

    received_body = None
    async def dummy_app(scope, receive, send):
        nonlocal received_body
        msg = await receive()
        received_body = msg["body"]

    middleware = BodyLimitMiddleware(dummy_app, max_bytes=100)
    scope = {"type": "http", "headers": []}
    asyncio.run(middleware(scope, mock_receive_missing, None))
    assert received_body == b""

    async def mock_receive_disconnect():
        return {"type": "http.disconnect"}

    app_called = False
    async def dummy_app_dc(scope, receive, send):
        nonlocal app_called
        app_called = True

    sent_messages = []
    async def mock_send(message):
        sent_messages.append(message)

    middleware_dc = BodyLimitMiddleware(dummy_app_dc, max_bytes=100)
    asyncio.run(middleware_dc(scope, mock_receive_disconnect, mock_send))
    assert app_called is False
    assert len(sent_messages) == 0

def test_body_limit_replay_behavior():
    chunk_msg = {"type": "http.request", "body": b"hello", "more_body": False}
    first_read = True
    async def mock_receive_sequence():
        nonlocal first_read
        if first_read:
            first_read = False
            return chunk_msg
        return {"type": "http.disconnect"}

    first_msg = None
    second_msg = None
    async def dummy_app(scope, receive, send):
        nonlocal first_msg, second_msg
        first_msg = await receive()
        second_msg = await receive()

    middleware = BodyLimitMiddleware(dummy_app, max_bytes=100)
    scope = {"type": "http", "headers": []}
    asyncio.run(middleware(scope, mock_receive_sequence, None))

    assert first_msg == {"type": "http.request", "body": b"hello", "more_body": False}
    assert second_msg == {"type": "http.disconnect"}
