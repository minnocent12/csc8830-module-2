"""Phase 0: the page-provider contract is provider-agnostic and reusable by a dashboard.

Uses a TEST-ONLY fake provider — no placeholder module is shipped in the package.
"""
from __future__ import annotations

import pytest

from module2.webapp._page import PageSpec
from module2.webapp.pages import get_pages
from module2.webapp.registry import collect_pages


def _fake_module_provider() -> list[PageSpec]:
    """Stand in for a second module a future course dashboard might mount."""
    return [
        PageSpec("Module X", "Overview", 10, lambda: None),
        PageSpec("Module X", "Details", 20, lambda: None),
    ]


def test_single_provider_returns_module2_pages_in_order() -> None:
    pages = collect_pages([get_pages])
    assert [p.page_label for p in pages] == [
        "Calibration",
        "Dimension Estimation",
        "Validation Analysis",
        "Theory",
    ]
    assert {p.module_label for p in pages} == {"Module 2"}


def test_multiple_providers_merge_grouped_and_ordered() -> None:
    pages = collect_pages([get_pages, _fake_module_provider])
    assert [(p.module_label, p.page_label) for p in pages] == [
        ("Module 2", "Calibration"),
        ("Module 2", "Dimension Estimation"),
        ("Module 2", "Validation Analysis"),
        ("Module 2", "Theory"),
        ("Module X", "Overview"),
        ("Module X", "Details"),
    ]


def test_later_provider_overrides_same_key() -> None:
    original = collect_pages([get_pages])
    marker = object()

    def _override() -> list[PageSpec]:
        return [PageSpec("Module 2", "Theory", 40, lambda: marker)]

    pages = collect_pages([get_pages, _override])
    assert len(pages) == len(original)
    theory = next(p for p in pages if p.page_label == "Theory")
    assert theory.render() is marker


def test_non_pagespec_is_rejected() -> None:
    with pytest.raises(TypeError):
        collect_pages([lambda: ["not a page"]])
