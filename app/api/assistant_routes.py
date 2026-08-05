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
from app.db import get_db

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class ChatRequest(BaseModel):
    message: str = ""
    history: list[dict] = []


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


@router.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    if gpt_configured():
        result = respond_gpt([*req.history, {"role": "user", "text": req.message}], db)
        if result is not None:
            return result
    if gemini_configured():
        result = respond_gemini([*req.history, {"role": "user", "text": req.message}], db)
        if result is not None:
            return result
    return respond(req.message, db)


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
    _require_gemini()
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
