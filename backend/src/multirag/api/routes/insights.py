"""GET /insights — data-analyst risk + insight feed for the Live Updates page."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from multirag.insights import compute_insights
from multirag.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="", tags=["insights"])


@router.get("/insights")
async def list_insights() -> dict[str, Any]:
    """Run all insight checks against the semantic layer and return the feed."""
    try:
        items = await compute_insights()
    except Exception as e:  # noqa: BLE001
        log.exception("insights.compute.failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    counts = {
        "high": sum(1 for i in items if i["severity"] == "high"),
        "med": sum(1 for i in items if i["severity"] == "med"),
        "low": sum(1 for i in items if i["severity"] == "low"),
        "info": sum(1 for i in items if i["severity"] == "info"),
        "good": sum(1 for i in items if i["severity"] == "good"),
        "unknown": sum(1 for i in items if i["severity"] == "unknown"),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "items": items,
    }
