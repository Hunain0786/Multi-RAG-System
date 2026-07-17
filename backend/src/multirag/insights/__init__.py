"""Live insights + risk-signal engine.

Runs a curated set of checks against the semantic layer and returns a
structured list of `Insight` items for the frontend `Live Updates` page.

All checks are read-only and reuse the same `compile_metric` /
`compile_composite` pipeline the agent uses, so numbers are consistent with
what the chat surface would produce for the same question.
"""

from multirag.insights.engine import Insight, compute_insights

__all__ = ["Insight", "compute_insights"]
