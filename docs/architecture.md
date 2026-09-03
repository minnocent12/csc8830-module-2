# Module 2 — web application architecture

## Goals

- Module 2 is **independently submittable**: a bare clone of this repository installs and
  runs its own Streamlit submission app with **no unpublished local-only dependency**.
- The same page components mount **unchanged** into a future course-level
  Module 2 → Module N dashboard.
- Core computer-vision / math logic is **completely independent of Streamlit**.

## Pieces

| File | Role | Imports Streamlit? |
| ---- | ---- | ------------------ |
| `src/module2/webapp/_page.py` | `PageSpec` dataclass — the page contract | no |
| `src/module2/webapp/registry.py` | `collect_pages(providers)` — pure merge / order / dedupe | no |
| `src/module2/webapp/shell.py` | `render_app(pages)` — sidebar + dispatch | yes |
| `src/module2/webapp/ui.py` | small shared UI helpers | yes |
| `src/module2/webapp/pages.py` | the four Module 2 pages + `get_pages()` provider | yes |
| `app.py` (repo root) | thin standalone entry: `render_app(collect_pages([get_pages]))` | via shell |
| `src/module2/*` (non-webapp) | calibration, geometry, estimation, metrics, validation, units, io | **never** |

## The provider contract

A *provider* is a zero-argument callable returning an iterable of `PageSpec`
(`get_pages` is Module 2's). `collect_pages` takes a list of providers, so:

- **Standalone (now):** `collect_pages([module2.webapp.pages.get_pages])`.
- **Course dashboard (deferred):**
  `collect_pages([module2_get_pages, module3_get_pages, ...])`, rendered by the same
  `render_app`, grouped by `PageSpec.module_label`.

## Deferred

The course dashboard implementation, any shared library it might live in, and any
`module2 → shared-lib` dependency wiring are deferred until the multi-repo topology and
packaging story are settled. No `importlib.metadata` entry points are used; a future
dashboard imports each module's `get_pages` explicitly. Whatever is chosen must not add an
unpublished local-only dependency to this repository.
