"""`forget` agent tool — soft-delete a stored memory by id."""

from __future__ import annotations

from typing import Any

from multirag.memory import store, vector

NAME = "forget"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Soft-delete a stored memory by its id. Use when the user explicitly "
        "says 'forget X' or 'remove that preference'. Call `recall` first to "
        "find the id — never guess ids. The Postgres row stays for audit but "
        "future recall/injection ignores it and its vector is dropped."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
        },
        "required": ["id"],
    },
}


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    fact_id = str(input_["id"])
    row = await store.get_fact(fact_id)
    if row is None:
        return {"id": fact_id, "deleted": False, "reason": "not found"}
    if row.deleted_at is not None:
        return {"id": fact_id, "deleted": False, "reason": "already deleted"}

    deleted = await store.soft_delete_fact(fact_id)
    if deleted:
        await vector.delete_fact_vectors([fact_id])
    return {"id": fact_id, "deleted": deleted}
