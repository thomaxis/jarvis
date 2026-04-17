"""User input endpoint. Receives text, runs through brain, returns context."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["input"])


class InputRequest(BaseModel):
    device_id: str
    text: str
    chat: bool = True  # If True, call LLM and return response. If False, return raw context.


class ResponseAck(BaseModel):
    device_id: str
    response_text: str
    facts: list[dict] | None = None
    topic: str | None = None


@router.post("/input")
async def process_input(req: InputRequest, request: Request) -> dict:
    brain = request.app.state.brain
    if not brain:
        raise HTTPException(status_code=503, detail="Brain not ready")

    if req.chat:
        llm_result = await brain.chat(req.device_id, req.text)
        return {"status": "ok", "response": llm_result.get("response", ""), "data": llm_result}
    else:
        context = await brain.process_input(req.device_id, req.text)
        return {"status": "ok", "context": context}


@router.post("/response")
async def process_response(req: ResponseAck, request: Request) -> dict:
    brain = request.app.state.brain
    if not brain:
        raise HTTPException(status_code=503, detail="Brain not ready")

    await brain.process_response(
        device_id=req.device_id,
        response_text=req.response_text,
        facts=req.facts,
        topic=req.topic,
    )
    return {"status": "ok"}
