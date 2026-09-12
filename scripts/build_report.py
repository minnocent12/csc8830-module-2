"""CLI: assemble the Module 2 report from its canonical sections (Markdown + optional PDF
and DOCX).

Run from the repository root (or the ``Assignments/`` workspace root with ``Module_2/``
prefixes)::

    python scripts/build_report.py

Writes ``results/module2_report.md`` always. If ``pandoc`` is installed it also renders
``results/module2_report.docx`` — pandoc's docx writer turns the report's LaTeX math
(``$...$`` / ``$$...$$``) directly into native OOXML/Word equation objects, so this path
needs **no** separate LaTeX engine. If ``pandoc`` **and** a LaTeX/PDF engine are both
installed it additionally renders ``results/module2_report.pdf``. Whichever step is
skipped prints the exact command to run later once the missing tool is installed. Section
files that do not exist yet (e.g. ``results/calibration_report.md`` before calibration)
appear as a *pending* note — never fabricated content.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SRC = REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from module2.report import assemble_report  # noqa: E402

# pandoc joins --resource-path entries with the platform separator (':' POSIX, ';' Windows).
# docs/report is on the path so the figures/<name>.png links in validation_summary.md
# resolve to docs/report/figures/<name>.png when the PDF is built.
_RESOURCE_PATH = os.pathsep.join(
    [str(REPO_ROOT), str(REPO_ROOT / "docs" / "report")]
)

# PDF back-ends pandoc can drive, most-common first. pandoc defaults to `pdflatex`, so if a
# non-default engine is the only one installed it must be named explicitly with
# `--pdf-engine=`; this script always does that for whichever engine it actually finds.
_PDF_ENGINES = (
    "pdflatex", "xelatex", "lualatex", "tectonic", "latexmk", "context",
    "wkhtmltopdf", "weasyprint", "prince", "pdfroff", "typst",
)


def _select_pdf_engine() -> str | None:
    """The first pandoc PDF engine found on PATH (see ``_PDF_ENGINES``), or ``None``."""
    for engine in _PDF_ENGINES:
        if shutil.which(engine):
            return engine
    return None


def _pandoc_command(out_md: Path, out_pdf: Path, engine: str | None) -> list[str]:
    """The pandoc argv used both to render and (joined) as the printed retry command."""
    cmd = [
        "pandoc",
        str(out_md),
        "-o",
        str(out_pdf),
        f"--resource-path={_RESOURCE_PATH}",
    ]
    if engine is not None:
        cmd.append(f"--pdf-engine={engine}")
    return cmd


def _render_pdf(out_md: Path, out_pdf: Path, pandoc: str | None) -> int:
    """Render the PDF via pandoc + a detected LaTeX/PDF engine.

    Returns 0 both on success and on a graceful skip (pandoc or an engine missing — the
    exact retry command is printed instead); a pandoc subprocess failure returns pandoc's
    exit code so the caller can stop and surface it.
    """
    engine = _select_pdf_engine()
    later_cmd = " ".join(_pandoc_command(out_md, out_pdf, engine))

    if pandoc is None:
        print(
            "pandoc not found — Markdown only. Install pandoc + a LaTeX engine, then run:\n"
            f"  {later_cmd}"
        )
        return 0
    if engine is None:
        print(
            "pandoc found, but no LaTeX/PDF engine is on PATH — PDF skipped. Install a "
            "LaTeX engine supported by pandoc (e.g. TeX Live or MiKTeX), then run:\n"
            f"  {later_cmd}"
        )
        return 0

    cmd = _pandoc_command(out_md, out_pdf, engine)
    cmd[0] = pandoc  # use the resolved pandoc path for execution
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"pandoc failed ({exc.returncode}) building the PDF; the Markdown is at "
            f"{out_md}. Retry with:\n  {later_cmd}"
        )
        return exc.returncode
    print(f"wrote {out_pdf}")
    return 0


def _render_docx(out_md: Path, out_docx: Path, pandoc: str | None) -> int:
    """Render the .docx via pandoc alone.

    Unlike the PDF path, this needs **no** LaTeX/PDF engine: pandoc's native docx writer
    turns the report's LaTeX math (the default markdown reader's ``tex_math_dollars``
    extension) directly into OOXML ``<m:oMath>`` Word equation objects. It therefore does
    not call ``_select_pdf_engine()`` at all, and re-uses ``_pandoc_command`` with
    ``engine=None`` (no ``--pdf-engine`` flag) since the resulting argv is identical to
    what a docx conversion needs.
    """
    cmd = _pandoc_command(out_md, out_docx, engine=None)
    later_cmd = " ".join(cmd)

    if pandoc is None:
        print(f"pandoc not found — .docx skipped. Install pandoc, then run:\n  {later_cmd}")
        return 0

    cmd[0] = pandoc
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"pandoc failed ({exc.returncode}) building the .docx; the Markdown is at "
            f"{out_md}. Retry with:\n  {later_cmd}"
        )
        return exc.returncode
    print(f"wrote {out_docx}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble the Module 2 report from its canonical section files."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "docs" / "report" / "manifest.md",
    )
    parser.add_argument(
        "--out-md", type=Path, default=REPO_ROOT / "results" / "module2_report.md"
    )
    parser.add_argument(
        "--out-pdf", type=Path, default=REPO_ROOT / "results" / "module2_report.pdf"
    )
    parser.add_argument(
        "--out-docx", type=Path, default=REPO_ROOT / "results" / "module2_report.docx"
    )
    parser.add_argument("--no-pdf", action="store_true", help="skip PDF rendering")
    parser.add_argument("--no-docx", action="store_true", help="skip .docx rendering")
    args = parser.parse_args(argv)

    markdown = assemble_report(args.manifest, REPO_ROOT)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown, encoding="utf-8")
    print(f"wrote {args.out_md}  ({len(markdown.splitlines())} lines)")

    pandoc = shutil.which("pandoc")

    if not args.no_pdf:
        rc = _render_pdf(args.out_md, args.out_pdf, pandoc)
        if rc != 0:
            return rc

    if not args.no_docx:
        rc = _render_docx(args.out_md, args.out_docx, pandoc)
        if rc != 0:
            return rc

    return 0


if __name__ == "__main__":
    sys.exit(main())
