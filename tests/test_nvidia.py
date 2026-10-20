from __future__ import annotations

import os
import sys
import pytest
from fastapi.testclient import TestClient

from app.main import app

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or str(json_data)

    def json(self):
        return self._json_data

    def iter_lines(self):
        yield b'data: {"choices": [{"delta": {"content": "Image shows tunnel face."}}]}'
        yield b'data: [DONE]'


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def nvidia_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-testkey123")
    yield


@pytest.fixture
def nvidia_off(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVAPI_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    yield


class TestNvidiaModule:
    def test_is_configured_false(self, nvidia_off):
        import app.assistant_nvidia as m
        assert not m.is_configured()

    def test_is_configured_true(self, nvidia_env):
        import app.assistant_nvidia as m
        assert m.is_configured()

    def test_respond_nvidia_text(self, nvidia_env, monkeypatch):
        import app.assistant_nvidia as m

        def fake_post(*args, **kwargs):
            return FakeResponse(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Tunnel system operational.",
                            }
                        }
                    ]
                },
            )

        monkeypatch.setattr("requests.post", fake_post)
        res = m.respond_nvidia([{"role": "user", "text": "hello"}], db=None)
        assert res is not None
        assert res["reply"] == "Tunnel system operational."

    def test_respond_nvidia_tool_calling(self, nvidia_env, monkeypatch):
        import app.assistant_nvidia as m

        def fake_post(*args, **kwargs):
            return FakeResponse(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "navigate",
                                            "arguments": '{"window": "win-twin"}',
                                        }
                                    }
                                ],
                            }
                        }
                    ]
                },
            )

        monkeypatch.setattr("requests.post", fake_post)
        res = m.respond_nvidia([{"role": "user", "text": "open cyber twin"}], db=None)
        assert res is not None
        assert any(a["type"] == "navigate" and a["window"] == "win-twin" for a in res["actions"])

    def test_analyze_vision_nvidia_non_stream(self, nvidia_env, monkeypatch):
        import app.assistant_nvidia as m

        def fake_post(*args, **kwargs):
            return FakeResponse(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "content": "A high-resolution image of a TBM cutterhead."
                            }
                        }
                    ]
                },
            )

        monkeypatch.setattr("requests.post", fake_post)
        res = m.analyze_vision_nvidia("What is in this image?", "https://example.com/test.jpg")
        assert res["model"] == "moonshotai/kimi-k3"
        assert "TBM cutterhead" in res["text"]

    def test_analyze_vision_nvidia_stream(self, nvidia_env, monkeypatch):
        import app.assistant_nvidia as m

        def fake_post(*args, **kwargs):
            return FakeResponse(200, {}, text="stream")

        monkeypatch.setattr("requests.post", fake_post)
        res = m.analyze_vision_nvidia("What is in this image?", "https://example.com/test.jpg", stream=True)
        assert res["streamed"] is True
        assert "Image shows tunnel face." in res["text"]


class TestNvidiaApiEndpoints:
    def test_nvidia_chat_unconfigured(self, client, nvidia_off):
        res = client.post("/api/assistant/nvidia/chat", json={"message": "hi"})
        assert res.status_code == 503

    def test_nvidia_vision_unconfigured(self, client, nvidia_off):
        res = client.post("/api/assistant/nvidia/vision", json={"prompt": "test"})
        assert res.status_code == 503

    def test_nvidia_chat_success(self, client, nvidia_env, monkeypatch):
        import app.api.assistant_routes as routes

        monkeypatch.setattr(routes, "respond_nvidia", lambda *a, **kw: {"reply": "NVIDIA NIM response", "actions": []})
        res = client.post("/api/assistant/nvidia/chat", json={"message": "hi"})
        assert res.status_code == 200
        assert res.json()["reply"] == "NVIDIA NIM response"

    def test_nvidia_vision_success(self, client, nvidia_env, monkeypatch):
        import app.api.assistant_routes as routes

        monkeypatch.setattr(
            routes,
            "analyze_vision_nvidia",
            lambda *a, **kw: {"model": "moonshotai/kimi-k3", "text": "Cutterhead disc wear detected."},
        )
        res = client.post(
            "/api/assistant/nvidia/vision",
            json={
                "prompt": "What is in this image?",
                "image_url": "https://assets.ngc.nvidia.com/products/api-catalog/phi-3-5-vision/example1b.jpg",
                "model": "moonshotai/kimi-k3",
            },
        )
        assert res.status_code == 200
        assert "Cutterhead" in res.json()["text"]
