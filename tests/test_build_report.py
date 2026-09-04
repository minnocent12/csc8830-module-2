"""Tests for report assembly (`module2.report`)."""
from __future__ import annotations

from pathlib import Path

import pytest

from module2.report import assemble_report, manifest_sections

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_manifest(tmp_path: Path, rels: list[str]) -> Path:
    body = "\n".join(rels)
    path = tmp_path / "manifest.md"
    path.write_text(f"# manifest\n\n## Section order\n\n```text\n{body}\n```\n")
    return path


def test_manifest_sections_parses_the_fenced_list(tmp_path: Path) -> None:
    mf = _write_manifest(tmp_path, ["docs/a.md", "results/b.md", "docs/c.md"])
    assert manifest_sections(mf) == ["docs/a.md", "results/b.md", "docs/c.md"]


def test_manifest_without_section_order_raises(tmp_path: Path) -> None:
    (tmp_path / "m.md").write_text("# manifest\n\njust prose\n")
    with pytest.raises(ValueError, match="Section order"):
        manifest_sections(tmp_path / "m.md")


def test_assemble_concatenates_sections_in_order_without_duplication(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "docs" / "a.md").write_text("# Alpha\n\nUNIQUE_ALPHA body.\n")
    (tmp_path / "results" / "b.md").write_text("# Bravo\n\nUNIQUE_BRAVO body.\n")
    (tmp_path / "docs" / "c.md").write_text("# Charlie\n\nUNIQUE_CHARLIE body.\n")
    mf = _write_manifest(tmp_path, ["docs/a.md", "results/b.md", "docs/c.md"])

    md = assemble_report(mf, tmp_path, today="2026-01-01")

    assert md.index("UNIQUE_ALPHA") < md.index("UNIQUE_BRAVO") < md.index("UNIQUE_CHARLIE")
    for marker in ("UNIQUE_ALPHA", "UNIQUE_BRAVO", "UNIQUE_CHARLIE"):
        assert md.count(marker) == 1  # each section's text appears exactly once
    assert md.startswith("% CSc 8830 Module 2")
    assert "% Generated 2026-01-01" in md


def test_missing_section_becomes_pending_note_not_an_error(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("# Alpha\n\nUNIQUE_ALPHA.\n")
    mf = _write_manifest(tmp_path, ["docs/a.md", "results/not_generated_yet.md"])

    md = assemble_report(mf, tmp_path)

    assert "UNIQUE_ALPHA" in md
    assert "results/not_generated_yet.md" in md
    assert "Pending" in md
    assert "No placeholder values are shown" in md


def test_assemble_against_the_real_repo_manifest() -> None:
    # smoke test: the real manifest parses and assembles without error, and the always-
    # present authored (tracked) sections are included in full. Whether the experiment
    # outputs are present depends on workspace state, so it is not asserted here
    # (test_missing_section_becomes_pending_note_not_an_error covers the pending path).
    md = assemble_report(REPO_ROOT / "docs" / "report" / "manifest.md", REPO_ROOT)
    assert md.startswith("% CSc 8830 Module 2")
    assert "Two-camera projection" in md
    assert "Dimension-estimation assumptions" in md
    assert "<!-- section: docs/theory_two_camera_projection.md -->" in md
