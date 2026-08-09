"""Agent tools registry — Anthropic tool schemas + async invokers.

Each tool exports:
  - `TOOL_SCHEMA`  : dict passed to Anthropic Messages `tools=[...]`
  - `run(input_)`  : async callable returning a JSON-serialisable result

The registry lets `agent.loop` dispatch by tool name.

Note: `ingest_doc` is intentionally NOT exposed to the agent — document ingest
is an operator action via `POST /documents/ingest` (UI upload) or
`python -m multirag.rag.pipeline ./docs` / `make ingest`. This keeps the corpus curated.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from multirag.agent.tools import (
    compile_composite as _composite,
)
from multirag.agent.tools import (
    compile_metric as _compile,
)
from multirag.agent.tools import (
    forget as _forget,
)
from multirag.agent.tools import (
    list_catalog as _catalog,
)
from multirag.agent.tools import (
    list_metrics as _metrics,
)
from multirag.agent.tools import (
    query_postgres as _sql,
)
from multirag.agent.tools import (
    recall as _recall,
)
from multirag.agent.tools import (
    remember as _remember,
)
from multirag.agent.tools import (
    search_docs as _search,
)

ToolRunner = Callable[[dict[str, Any]], Awaitable[Any]]

TOOL_SCHEMAS: list[dict[str, Any]] = [
    _compile.TOOL_SCHEMA,
    _composite.TOOL_SCHEMA,
    _catalog.TOOL_SCHEMA,
    _metrics.TOOL_SCHEMA,
    _search.TOOL_SCHEMA,
    _sql.TOOL_SCHEMA,
    _remember.TOOL_SCHEMA,
    _recall.TOOL_SCHEMA,
    _forget.TOOL_SCHEMA,
]

TOOL_RUNNERS: dict[str, ToolRunner] = {
    _compile.NAME: _compile.run,
    _composite.NAME: _composite.run,
    _catalog.NAME: _catalog.run,
    _metrics.NAME: _metrics.run,
    _search.NAME: _search.run,
    _sql.NAME: _sql.run,
    _remember.NAME: _remember.run,
    _recall.NAME: _recall.run,
    _forget.NAME: _forget.run,
}
