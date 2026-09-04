"""Assemble the Module 2 final report from its canonical section files.

The report has no prose of its own: :func:`assemble_report` concatenates the section files
listed in ``docs/report/manifest.md`` (see :func:`manifest_sections`), in order, into one
Markdown document. A section file that has not been generated yet (e.g.
``results/calibration_report.md`` before calibration is run) is replaced by a short
*pending* note rather than any fabricated content.

``scripts/build_report.py`` writes the Markdown and, if ``pandoc`` is available, renders it
to PDF.
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

REPORT_TITLE = (
    "CSc 8830 Module 2 — Smartphone Camera Calibration and "
    "Real-World 2D Object Dimension Estimation"
)

_SECTION_ORDER_RE = re.compile(r"##\s*Section order.*?```(?:\w+)?\n(.*?)\n```", re.S)


def manifest_sections(manifest_path: str | Path) -> list[str]:
    """Return the ordered list of repo-relative section paths from the manifest.

    The manifest must contain a ``## Section order`` heading followed by a fenced code block
    with one repo-relative path per line (blank lines and ``#`` comments are ignored). Each
    path must appear **exactly once** — a repeated path would make :func:`assemble_report`
    emit the same section twice, so it is rejected here.

    Raises:
        ValueError: if the fenced list is missing, empty, or contains a duplicate path.
    """
    text = Path(manifest_path).read_text(encoding="utf-8")
    match = _SECTION_ORDER_RE.search(text)
    if match is None:
        raise ValueError(
            f"{manifest_path}: no '## Section order' fenced list found"
        )
    paths = [
        line.strip()
        for line in match.group(1).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not paths:
        raise ValueError(f"{manifest_path}: the 'Section order' list is empty")

    seen: set[str] = set()
    duplicates: list[str] = []
    for path in paths:
        if path in seen:
            duplicates.append(path)
        seen.add(path)
    if duplicates:
        raise ValueError(
            f"{manifest_path}: duplicate section path(s) in the 'Section order' list: "
            f"{', '.join(sorted(set(duplicates)))}. Each section must appear exactly once."
        )
    return paths


def _pending_note(rel: str) -> str:
    name = rel.rsplit("/", 1)[-1]
    return (
        f"# {name} — pending\n\n"
        f"> **Pending.** `{rel}` has not been generated yet. Run the corresponding script "
        f"(see the project README) on real data to produce this section. "
        f"No placeholder values are shown."
    )


def assemble_report(
    manifest_path: str | Path,
    repo_root: str | Path,
    *,
    today: str | None = None,
) -> str:
    """Concatenate the manifest's section files into one Markdown document.

    Args:
        manifest_path: path to ``docs/report/manifest.md``.
        repo_root: repository root; section paths in the manifest are resolved against it.
        today: ISO date string for the generated-on line (defaults to the current date).

    Returns:
        The assembled Markdown. Missing section files become a *pending* note; no section's
        text is emitted more than once.
    """
    root = Path(repo_root)
    stamp = today or _dt.date.today().isoformat()
    parts = [f"% {REPORT_TITLE}", f"% Generated {stamp}", ""]

    for rel in manifest_sections(manifest_path):
        target = root / rel
        parts.append(f"<!-- section: {rel} -->")
        if target.is_file():
            parts.append(target.read_text(encoding="utf-8").rstrip())
        else:
            parts.append(_pending_note(rel))
        parts.append("")
        parts.append("* * *")
        parts.append("")

    while parts and parts[-1] in ("", "* * *"):
        parts.pop()
    return "\n".join(parts) + "\n"
