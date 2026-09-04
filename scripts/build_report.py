"""CLI: assemble the Module 2 report from its canonical sections (Markdown + optional PDF).

Run from the repository root (or the ``Assignments/`` workspace root with ``Module_2/``
prefixes)::

    python scripts/build_report.py

Writes ``results/module2_report.md`` always. If ``pandoc`` (and a LaTeX engine) is
installed it also renders ``results/module2_report.pdf``; otherwise it prints the exact
pandoc command to run later. Section files that do not exist yet (e.g.
``results/calibration_report.md`` before calibration) appear as a *pending* note — never
fabricated content.
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
        "--no-pdf", action="store_true", help="assemble the Markdown only"
    )
    args = parser.parse_args(argv)

    markdown = assemble_report(args.manifest, REPO_ROOT)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown, encoding="utf-8")
    print(f"wrote {args.out_md}  ({len(markdown.splitlines())} lines)")

    if args.no_pdf:
        return 0

    pandoc = shutil.which("pandoc")
    engine = _select_pdf_engine()
    later_cmd = " ".join(_pandoc_command(args.out_md, args.out_pdf, engine))

    if pandoc is None:
        print(
            "pandoc not found — Markdown only. Install pandoc + a LaTeX engine, then run:\n"
            f"  {later_cmd}"
        )
        return 0
    if engine is None:
        print(
            "pandoc found, but no LaTeX/PDF engine is on PATH — Markdown only. Install a "
            "LaTeX engine supported by pandoc (e.g. TeX Live or MiKTeX), then run:\n"
            f"  {later_cmd}"
        )
        return 0

    cmd = _pandoc_command(args.out_md, args.out_pdf, engine)
    cmd[0] = pandoc  # use the resolved pandoc path for execution
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"pandoc failed ({exc.returncode}); the Markdown is at {args.out_md}. "
            f"Retry with:\n  {later_cmd}"
        )
        return exc.returncode
    print(f"wrote {args.out_pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
