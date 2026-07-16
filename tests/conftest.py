"""Shared pytest configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Prevent registry-startup validation from crashing tests if the env is bare.
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/dummy")
os.environ.setdefault("PINECONE_API_KEY", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy")
