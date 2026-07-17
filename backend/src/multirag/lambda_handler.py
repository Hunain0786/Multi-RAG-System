"""AWS Lambda entrypoint for API Gateway / Function URL via Mangum.

This wraps the existing FastAPI app so the exact same routes and tool-use loop
can run behind Lambda.
"""

from __future__ import annotations

from mangum import Mangum

from multirag.main import app

# `lifespan="auto"` preserves FastAPI startup/shutdown semantics when possible.
# That means our DB pool open/close and Pinecone ensure_index logic in
# `multirag.main.lifespan` still run correctly in Lambda's execution environment.
handler = Mangum(app, lifespan="auto")

