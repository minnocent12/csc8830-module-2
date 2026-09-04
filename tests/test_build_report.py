"""Tests for report assembly (`module2.report`) and the `scripts/build_report.py` CLI."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from module2.report import assemble_report, manifest_sections

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str, mod_name: str):
    """Import a file under `scripts/` as a module (they are not on the package path)."""
    path = REPO_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_build_report():
    return _load_script("build_report.py", "_build_report_cli")


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


def test_manifest_with_duplicate_section_path_raises(tmp_path: Path) -> None:
    mf = _write_manifest(tmp_path, ["docs/a.md", "results/b.md", "docs/a.md"])
    with pytest.raises(ValueError, match="duplicate section path"):
        manifest_sections(mf)
    # assemble_report goes through manifest_sections, so it rejects the manifest too
    with pytest.raises(ValueError, match="duplicate section path"):
        assemble_report(mf, tmp_path)


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
    # Pandoc %-title block: title / empty author / date on three consecutive lines, so the
    # date is not misread as the author.
    head = md.splitlines()[:3]
    assert head[0].startswith("% CSc 8830 Module 2")
    assert head[1] == "%"
    assert head[2] == "% Generated 2026-01-01"


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


def test_cli_without_pandoc_exits_zero_and_keeps_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = _load_build_report()
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)  # pandoc absent
    out_md = tmp_path / "report.md"
    rc = cli.main(["--out-md", str(out_md), "--out-pdf", str(tmp_path / "report.pdf")])
    assert rc == 0
    assert out_md.is_file()
    assert "pandoc not found" in capsys.readouterr().out


def test_cli_with_pandoc_but_no_pdf_engine_exits_zero_with_recovery_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = _load_build_report()
    # pandoc present, every PDF engine absent
    monkeypatch.setattr(
        cli.shutil, "which", lambda name: "/usr/bin/pandoc" if name == "pandoc" else None
    )

    def _fail_run(*_args: object, **_kwargs: object) -> None:  # must not be reached
        raise AssertionError("pandoc should not be invoked without a PDF engine")

    monkeypatch.setattr(cli.subprocess, "run", _fail_run)
    out_md = tmp_path / "report.md"
    out_pdf = tmp_path / "report.pdf"
    rc = cli.main(["--out-md", str(out_md), "--out-pdf", str(out_pdf)])
    assert rc == 0
    assert out_md.is_file()
    out = capsys.readouterr().out
    assert "no LaTeX/PDF engine" in out
    assert f"pandoc {out_md} -o {out_pdf}" in out  # exact command to run later


def test_cli_no_pdf_flag_skips_rendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli = _load_build_report()

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("no PDF work expected with --no-pdf")

    monkeypatch.setattr(cli.subprocess, "run", _boom)
    out_md = tmp_path / "report.md"
    rc = cli.main(["--no-pdf", "--out-md", str(out_md), "--out-pdf", str(tmp_path / "r.pdf")])
    assert rc == 0
    assert out_md.is_file()


def test_cli_invokes_pandoc_with_the_detected_pdf_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """C: pandoc + an engine available -> pandoc is run with --pdf-engine=<that engine>."""
    cli = _load_build_report()
    # pandoc present; xelatex is the ONLY PDF engine on PATH (not pandoc's default)
    monkeypatch.setattr(
        cli.shutil,
        "which",
        lambda name: f"/opt/bin/{name}" if name in ("pandoc", "xelatex") else None,
    )
    recorded: dict[str, list[str]] = {}
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **_k: recorded.setdefault("cmd", list(cmd)))

    out_md, out_pdf = tmp_path / "r.md", tmp_path / "r.pdf"
    rc = cli.main(["--out-md", str(out_md), "--out-pdf", str(out_pdf)])

    assert rc == 0
    cmd = recorded["cmd"]
    assert cmd[0] == "/opt/bin/pandoc"  # resolved path used for execution
    assert "--pdf-engine=xelatex" in cmd  # non-default engine named explicitly
    assert f"--resource-path={cli._RESOURCE_PATH}" in cmd
    assert str(out_pdf) in cmd
    assert "wrote" in capsys.readouterr().out.lower()


def test_cli_surfaces_pandoc_conversion_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """D: pandoc + engine available but conversion fails -> non-zero, Markdown kept, retry shown."""
    cli = _load_build_report()
    monkeypatch.setattr(
        cli.shutil,
        "which",
        lambda name: f"/opt/bin/{name}" if name in ("pandoc", "pdflatex") else None,
    )

    def _boom(cmd: list[str], **_k: object) -> None:
        raise cli.subprocess.CalledProcessError(returncode=3, cmd=cmd)

    monkeypatch.setattr(cli.subprocess, "run", _boom)

    out_md, out_pdf = tmp_path / "r.md", tmp_path / "r.pdf"
    rc = cli.main(["--out-md", str(out_md), "--out-pdf", str(out_pdf)])

    assert rc == 3  # failure is not hidden
    assert out_md.is_file()  # Markdown left intact
    out = capsys.readouterr().out
    assert "pandoc failed (3)" in out
    assert "Retry with" in out
    assert "--pdf-engine=pdflatex" in out


def test_validation_figure_link_resolves_via_pandoc_resource_path(tmp_path: Path) -> None:
    """A figures/<name>.png link in validation_summary.md resolves under docs/report/ once
    the section is concatenated into the report and pandoc gets --resource-path."""
    cli = _load_build_report()
    av = _load_script("analyze_validation.py", "_analyze_validation_cli")

    # 1. the link analyze_validation writes is relative to docs/report/
    real_png = REPO_ROOT / "docs" / "report" / "figures" / "validation_error_hist.png"
    caption, link = av._figure_links([real_png])[0]
    assert link == "figures/validation_error_hist.png"

    # 2. build_report puts <repo>/docs/report on pandoc's resource path
    assert str(REPO_ROOT / "docs" / "report") in cli._RESOURCE_PATH.split(cli.os.pathsep)

    # 3. so pandoc resolves the link to the real plot location
    assert (REPO_ROOT / "docs" / "report" / link) == real_png

    # 4. assembly keeps the link verbatim (no path rewriting)
    (tmp_path / "results").mkdir()
    (tmp_path / "docs" / "report").mkdir(parents=True)
    (tmp_path / "results" / "vs.md").write_text(
        f"# Validation\n\nUNIQUE_VS\n\n![{caption}]({link})\n"
    )
    md = assemble_report(_write_manifest(tmp_path, ["results/vs.md"]), tmp_path)
    assert f"![{caption}]({link})" in md
