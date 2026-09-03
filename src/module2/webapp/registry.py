"""Provider-agnostic page collection.

:func:`collect_pages` is a pure function (no Streamlit import) so it can be unit-tested and
reused by any host: the Module 2 standalone app passes one provider; a future course
dashboard would pass one provider per module.
"""
from __future__ import annotations

from typing import Callable, Iterable, Sequence

from module2.webapp._page import PageSpec

#: A provider is a zero-argument callable returning the pages it contributes.
PageProvider = Callable[[], Iterable[PageSpec]]


def collect_pages(providers: Sequence[PageProvider]) -> list[PageSpec]:
    """Merge pages from ``providers`` into a stable, de-duplicated, ordered list.

    Pages are sorted by ``(module_label, order, page_label)``. If a later provider yields a
    page with the same ``(module_label, page_label)`` as an earlier one, the later page wins.

    Args:
        providers: callables that each return an iterable of :class:`PageSpec`.

    Returns:
        The merged list of pages.

    Raises:
        TypeError: if a provider yields something other than a :class:`PageSpec`.
    """
    merged: dict[tuple[str, str], PageSpec] = {}
    for provider in providers:
        for page in provider():
            if not isinstance(page, PageSpec):
                raise TypeError(
                    f"provider {provider!r} yielded {type(page)!r}, expected PageSpec"
                )
            merged[(page.module_label, page.page_label)] = page
    return sorted(merged.values(), key=lambda p: (p.module_label, p.order, p.page_label))
