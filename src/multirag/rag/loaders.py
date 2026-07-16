"""File loaders — turn a path on disk into plain text."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTS = {".txt", ".md", ".pdf"}


def load_file(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"file not found: {p}")
    ext = p.suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise ValueError(f"unsupported extension '{ext}' — supported: {sorted(SUPPORTED_EXTS)}")

    if ext == ".pdf":
        return _load_pdf(p)
    return p.read_text(encoding="utf-8", errors="replace")


def _load_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("pypdf is required to load PDFs — pip install pypdf") from e

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 — pdf pages sometimes throw on extraction
            continue
    return "\n\n".join(pages).strip()
