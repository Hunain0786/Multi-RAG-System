"""Agent memory: durable conversations, atomic facts, rolling episode summaries.

Layout:
  store.py      : Postgres CRUD (Conversation / Message / MemoryFact / MemoryEpisode)
  vector.py     : Pinecone thin wrapper (namespace="memory")
  recall.py     : build_context() — top-k facts + last episode summary for a query
  summarize.py  : LLM rolling summariser, invoked explicitly (see config.memory_auto_summarize)
"""
