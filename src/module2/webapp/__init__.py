"""Streamlit UI for Module 2.

This is the only ``module2`` sub-package that imports Streamlit. It exposes page components
through the :func:`module2.webapp.pages.get_pages` provider so they run in the standalone
submission app (``app.py``) and can later mount unchanged into a course-level
Module 2 -> Module N dashboard. See ``docs/architecture.md``.
"""
from __future__ import annotations
