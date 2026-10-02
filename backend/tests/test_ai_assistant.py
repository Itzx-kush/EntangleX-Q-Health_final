import pytest

from app.api import ai
from app.api.schemas import ChatMessage, ChatRequest


def test_chat_request_bounds_and_roles():
    request = ChatRequest(
        message="What is the VQC workflow?",
        conversation=[
            ChatMessage(role="user", content="Explain the model."),
            ChatMessage(role="model", content="It uses a variational quantum circuit."),
        ],
    )
    messages = ai._normalize_history(request)
    assert messages[0]["role"] == "system"
    assert messages[-2]["role"] == "assistant"
    assert messages[-1] == {"role": "user", "content": "What is the VQC workflow?"}


def test_chat_request_rejects_oversized_message():
    with pytest.raises(ValueError):
        ChatRequest(message="x" * 2001)


def test_ai_endpoint_reports_unconfigured(monkeypatch, client):
    class Settings:
        groq_api_key = ""

    monkeypatch.setattr(ai, "get_settings", lambda: Settings())
    response = client.post(
        "/api/ai/chat",
        json={"message": "What is EntangleX Q-Health?", "conversation": []},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"
