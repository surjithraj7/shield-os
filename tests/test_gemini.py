from __future__ import annotations

import base64
import io
import os
import sys

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeCall:
    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args


class FakePart:
    def __init__(self, function_call=None, text=None):
        self.function_call = function_call
        self.text = text


class FakeContent:
    def __init__(self, parts):
        self.parts = parts


class FakeCandidate:
    def __init__(self, parts):
        self.content = FakeContent(parts)


class FakeResponse:
    def __init__(self, candidates):
        self.candidates = candidates


class FakeTextResponse:
    def __init__(self, text: str):
        self.text = text


class FakeGeneratedImage:
    def __init__(self, image):
        self.image = image


class FakeImagesResponse:
    def __init__(self, images):
        self.generated_images = images


class FakeModels:
    def __init__(self, content_queue=None, images_response=None):
        self._queue = list(content_queue or [])
        self.images_response = images_response
        self.generate_content_calls = []
        self.generate_images_calls = []

    def generate_content(self, *args, **kwargs):
        self.generate_content_calls.append((args, kwargs))
        if not self._queue:
            raise AssertionError("generate_content called with no queued response")
        return self._queue.pop(0)

    def generate_images(self, *args, **kwargs):
        self.generate_images_calls.append((args, kwargs))
        return self.images_response


class FakeClient:
    def __init__(self, content_queue=None, images_response=None):
        self.models = FakeModels(content_queue, images_response)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    yield


@pytest.fixture
def gemini_off(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    yield


def _png_base64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(10, 20, 30)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class TestGeminiModule:
    def test_is_configured(self, gemini_off):
        import app.assistant_gemini as m

        assert not m.is_configured()

    def test_generate_image(self, gemini_env, monkeypatch):
        import app.assistant_gemini as m

        buf = io.BytesIO()
        Image.new("RGB", (4, 4)).save(buf, format="PNG")
        fake = FakeClient(images_response=FakeImagesResponse([FakeGeneratedImage(Image.new("RGB", (4, 4)))]))
        monkeypatch.setattr(m, "_client", lambda: fake)

        images = m.generate_image("a futuristic library", number_of_images=1, aspect_ratio="1:1")
        assert len(images) == 1
        decoded = base64.b64decode(images[0])
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"
        _, kwargs = fake.models.generate_images_calls[0]
        assert kwargs["model"] == "imagen-3.0-generate-002"
        assert kwargs["config"].number_of_images == 1
        assert kwargs["config"].aspect_ratio == "1:1"

    def test_generate_questions_parses_json(self, gemini_env, monkeypatch):
        import app.assistant_gemini as m

        payload = [
            {"id": 1, "question": "What gas do plants absorb?", "options": ["O2", "CO2"], "correct_answer": "CO2"},
            {"id": 2, "question": "Where does photosynthesis occur?", "options": ["Roots", "Chloroplasts"], "correct_answer": "Chloroplasts"},
            {"id": 3, "question": "What is the byproduct?", "options": ["O2", "N2"], "correct_answer": "O2"},
        ]
        fake = FakeClient(content_queue=[FakeTextResponse('[{"id": 1}, {"id": 2}, {"id": 3}]')])
        monkeypatch.setattr(m, "_client", lambda: fake)

        data = m.generate_questions("Photosynthesis")
        assert len(data) == 3
        _, kwargs = fake.models.generate_content_calls[0]
        assert kwargs["config"].response_mime_type == "application/json"

    def test_generate_questions_with_image(self, gemini_env, monkeypatch):
        import app.assistant_gemini as m

        fake = FakeClient(content_queue=[FakeTextResponse('[{"id": 1}]')])
        monkeypatch.setattr(m, "_client", lambda: fake)

        data = m.generate_questions("What do you see?", image_base64=_png_base64())
        assert len(data) == 1
        contents = fake.models.generate_content_calls[0][1]["contents"]
        assert len(contents) == 2  # image + text

    def test_answer_question(self, gemini_env, monkeypatch):
        import app.assistant_gemini as m

        fake = FakeClient(content_queue=[FakeTextResponse("The northern lights are caused by solar particles.")])
        monkeypatch.setattr(m, "_client", lambda: fake)

        answer = m.answer_question("What causes the northern lights?")
        assert "solar" in answer

    def test_answer_question_with_image(self, gemini_env, monkeypatch):
        import app.assistant_gemini as m

        fake = FakeClient(content_queue=[FakeTextResponse("A blue coat.")])
        monkeypatch.setattr(m, "_client", lambda: fake)

        answer = m.answer_question("What colour is the coat?", image_base64=_png_base64())
        assert answer == "A blue coat."
        contents = fake.models.generate_content_calls[0][1]["contents"]
        assert len(contents) == 2

    def test_respond_gemini_tool_calling(self, gemini_env, monkeypatch):
        import app.assistant_gemini as m

        # First turn: model asks to call navigate; second turn: model replies with text.
        fake = FakeClient(
            content_queue=[
                FakeResponse([FakeCandidate([FakePart(function_call=FakeCall("navigate", {"window": "win-twin"}))])]),
                FakeResponse([FakeCandidate([FakePart(text="Opened the cyber twin.")])]),
            ]
        )
        monkeypatch.setattr(m, "_client", lambda: fake)

        result = m.respond_gemini([{"role": "user", "text": "open the cyber twin"}], db=None)
        assert result is not None
        assert result["reply"] == "Opened the cyber twin."
        assert any(a["type"] == "navigate" and a["window"] == "win-twin" for a in result["actions"])

    def test_respond_gemini_not_configured(self, gemini_off):
        import app.assistant_gemini as m

        assert m.respond_gemini([{"role": "user", "text": "hi"}], db=None) is None


class TestGeminiApi:
    def test_gemini_image_unconfigured(self, client, gemini_off):
        response = client.post(
            "/api/assistant/gemini/image",
            json={"prompt": "a tunnel"},
        )
        assert response.status_code == 200
        assert len(response.json()["images"]) > 0

    def test_gemini_chat_unconfigured(self, client, gemini_off):
        response = client.post("/api/assistant/gemini/chat", json={"message": "hi"})
        assert response.status_code == 503

    def test_gemini_image_success(self, client, gemini_env, monkeypatch):
        import app.api.assistant_routes as routes

        monkeypatch.setattr(routes, "generate_image", lambda *a, **kw: [_png_base64()])
        response = client.post(
            "/api/assistant/gemini/image",
            json={"prompt": "a futuristic library", "number_of_images": 1},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["images"][0] == _png_base64()

    def test_gemini_questions_success(self, client, gemini_env, monkeypatch):
        import app.api.assistant_routes as routes

        monkeypatch.setattr(routes, "generate_questions", lambda *a, **kw: [{"id": 1, "question": "q?"}])
        response = client.post("/api/assistant/gemini/questions", json={"prompt": "Photosynthesis"})
        assert response.status_code == 200
        assert response.json()["questions"][0]["id"] == 1

    def test_gemini_qa_success(self, client, gemini_env, monkeypatch):
        import app.api.assistant_routes as routes

        monkeypatch.setattr(routes, "answer_question", lambda *a, **kw: "An answer.")
        response = client.post("/api/assistant/gemini/qa", json={"prompt": "Why?"})
        assert response.status_code == 200
        assert response.json()["answer"] == "An answer."

    def test_chat_falls_back_to_rule_based(self, client, gemini_off):
        response = client.post("/api/assistant/chat", json={"message": "open the cyber twin"})
        assert response.status_code == 200
        assert response.json()["reply"]
