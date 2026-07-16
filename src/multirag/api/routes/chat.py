"""POST /chat — SSE stream of the tool_use loop."""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from multirag.agent.loop import run_agent
from multirag.logging import get_logger
from multirag.schemas.chat import ChatRequest

log = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(req: ChatRequest) -> EventSourceResponse:
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    if req.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="last message must be role='user'")

    messages = [m.model_dump() for m in req.messages]

    async def event_stream() -> AsyncIterator[dict]:
        try:
            async for event in run_agent(messages):
                yield {"event": event["type"], "data": json.dumps(event, default=str)}
        except Exception as e:  # noqa: BLE001
            log.exception("chat.error", error=str(e))
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_stream())
