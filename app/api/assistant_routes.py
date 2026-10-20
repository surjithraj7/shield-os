from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.assistant import respond
from app.assistant_gemini import (
    answer_question,
    generate_image,
    generate_questions,
    is_configured as gemini_configured,
    respond_gemini,
)
from app.assistant_gpt import is_configured as gpt_configured
from app.assistant_gpt import respond_gpt
from app.assistant_nvidia import (
    analyze_vision_nvidia,
    is_configured as nvidia_configured,
    respond_nvidia,
)
from app.db import get_db

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class ChatRequest(BaseModel):
    message: str = ""
    history: list[dict] = []


class NvidiaVisionRequest(BaseModel):
    prompt: str = "What is in this image?"
    image_url: str = "https://assets.ngc.nvidia.com/products/api-catalog/phi-3-5-vision/example1b.jpg"
    model: str = "moonshotai/kimi-k3"
    max_tokens: int = 16384
    stream: bool = False
    temperature: float = 1.0
    reasoning_effort: str = "max"
    seed: int = 0


class GeminiImageRequest(BaseModel):
    prompt: str
    number_of_images: int = Field(default=1, ge=1, le=4)
    aspect_ratio: str = Field(default="1:1", pattern="^(1:1|3:4|4:3|9:16|16:9)$")


class GeminiQuestionsRequest(BaseModel):
    prompt: str
    image_base64: str | None = None


class GeminiQARequest(BaseModel):
    prompt: str
    image_base64: str | None = None


def _require_gemini() -> None:
    if not gemini_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini is not configured. Set GEMINI_API_KEY in the .env file.",
        )


def _require_nvidia() -> None:
    if not nvidia_configured():
        raise HTTPException(
            status_code=503,
            detail="NVIDIA API is not configured. Set NVIDIA_API_KEY in the .env file.",
        )


@router.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    if nvidia_configured():
        try:
            result = respond_nvidia([*req.history, {"role": "user", "text": req.message}], db)
            if result is not None:
                return result
        except Exception:
            pass
    if gpt_configured():
        try:
            result = respond_gpt([*req.history, {"role": "user", "text": req.message}], db)
            if result is not None:
                return result
        except Exception:
            pass
    if gemini_configured():
        try:
            result = respond_gemini([*req.history, {"role": "user", "text": req.message}], db)
            if result is not None:
                return result
        except Exception:
            pass
    return respond(req.message, db)


@router.post("/nvidia/chat")
def nvidia_chat(req: ChatRequest, db: Session = Depends(get_db)):
    _require_nvidia()
    result = respond_nvidia([*req.history, {"role": "user", "text": req.message}], db)
    if result is None:
        raise HTTPException(status_code=502, detail="NVIDIA NIM request failed.")
    return result


@router.post("/nvidia/vision")
def nvidia_vision(req: NvidiaVisionRequest):
    _require_nvidia()
    try:
        res = analyze_vision_nvidia(
            prompt=req.prompt,
            image_url=req.image_url,
            model=req.model,
            max_tokens=req.max_tokens,
            stream=req.stream,
            temperature=req.temperature,
            reasoning_effort=req.reasoning_effort,
            seed=req.seed,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NVIDIA Vision request failed: {exc}") from exc


@router.post("/gemini/chat")
def gemini_chat(req: ChatRequest, db: Session = Depends(get_db)):
    if not gemini_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini is not configured. Set GEMINI_API_KEY in the .env file.",
        )
    result = respond_gemini([*req.history, {"role": "user", "text": req.message}], db)
    if result is None:
        raise HTTPException(status_code=502, detail="Gemini request failed.")
    return result


@router.post("/gemini/image")
def gemini_image(req: GeminiImageRequest):
    try:
        images = generate_image(
            prompt=req.prompt,
            number_of_images=req.number_of_images,
            aspect_ratio=req.aspect_ratio,
        )
    except Exception as exc:  # noqa: BLE001 - surface SDK errors to the client
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}") from exc
    return {"model": "imagen-3.0-generate-002", "count": len(images), "images": images}


@router.post("/gemini/questions")
def gemini_questions(req: GeminiQuestionsRequest):
    _require_gemini()
    try:
        data = generate_questions(prompt=req.prompt, image_base64=req.image_base64)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Question generation failed: {exc}") from exc
    return {"model": "gemini-2.5-flash", "questions": data}


@router.post("/gemini/qa")
def gemini_qa(req: GeminiQARequest):
    _require_gemini()
    try:
        text = answer_question(prompt=req.prompt, image_base64=req.image_base64)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Question answering failed: {exc}") from exc
    return {"model": "gemini-2.5-flash", "answer": text}

