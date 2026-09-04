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

# pandoc joins --resource-path entries with the platform separator (':' POSIX, ';' Windows)
_RESOURCE_PATH = os.pathsep.join(
    [str(REPO_ROOT), str(REPO_ROOT / "docs" / "report")]
)


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
    if pandoc is None:
        print(
            "pandoc not found — Markdown only. Install pandoc + a LaTeX engine, then run:\n"
            f"  pandoc {args.out_md} -o {args.out_pdf} --resource-path={_RESOURCE_PATH}"
        )
        return 0

    cmd = [
        pandoc,
        str(args.out_md),
        "-o",
        str(args.out_pdf),
        f"--resource-path={_RESOURCE_PATH}",
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"pandoc failed ({exc.returncode}); the Markdown is at {args.out_md}")
        return exc.returncode
    print(f"wrote {args.out_pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
