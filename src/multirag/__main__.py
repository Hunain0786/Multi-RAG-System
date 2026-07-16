"""Entry point: `python -m multirag`.

Sets the Windows selector event loop policy BEFORE creating any loop, which is
required for psycopg's async pool. `uvicorn.run()` overrides this policy
internally, so we instead run `uvicorn.Server` under an explicit `asyncio.run`
that respects the policy we set. On macOS/Linux the policy line is a no-op.
"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn  # noqa: E402  — must import after the policy line above

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


async def _serve(reload: bool) -> None:
    config = uvicorn.Config(
        "multirag.main:app",
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        reload=reload,
        loop="asyncio",
        log_config=None,
    )
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    reload = "--reload" in sys.argv
    asyncio.run(_serve(reload=reload))


if __name__ == "__main__":
    main()
