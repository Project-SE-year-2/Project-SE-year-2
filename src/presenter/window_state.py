"""
window_state.py
---------------
Holds the current view state for a single period's ranking window.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from src.presenter.ranking_query_engine import RankingQueryEngine, ROW_COLUMNS

DEFAULT_PAGE_SIZE = 100


@dataclass
class WindowState:
    """View state for one exam-period ranking window."""

    period_id: str
    engine: RankingQueryEngine
    sort_cols: list = field(default_factory=lambda: ["min_days_required"])
    page_size: int = DEFAULT_PAGE_SIZE

    rows: list = field(default_factory=list, init=False)
    offset: int = field(default=0, init=False)
    total: int = field(default=0, init=False)
    pending: bool = field(default=False, init=False)

    def load(self) -> None:
        """Reset to page 1, fetch, clear pending."""
        self.offset = 0
        self._fetch()
        self.pending = False

    def refresh(self) -> None:
        """Re-fetch current page, clear pending."""
        self._fetch()
        self.pending = False

    def next_page(self) -> bool:
        """Advance one page. Returns False if already on the last page."""
        new_offset = self.offset + self.page_size
        if new_offset >= self.total:
            return False
        self.offset = new_offset
        self._fetch()
        return True

    def prev_page(self) -> bool:
        """Go back one page. Returns False if already on page 1."""
        if self.offset == 0:
            return False
        self.offset = max(0, self.offset - self.page_size)
        self._fetch()
        return True

    @property
    def current_page(self) -> int:
        return self.offset // self.page_size + 1

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        return (self.total + self.page_size - 1) // self.page_size

    def set_sort(self, sort_cols: list) -> None:
        """Change ranking priority and re-fetch from page 1 (no regeneration).

        Validates the new sort_cols before modifying any state, so a ValueError
        leaves the object in its previous valid state.
        """
        # Validate first — do not touch state until we know the input is good.
        self.engine._build_order_clause(sort_cols)
        previous = self.sort_cols
        self.sort_cols = sort_cols
        self.offset = 0
        try:
            self._fetch()
        except Exception:
            # Restore previous state if the fetch itself fails unexpectedly.
            self.sort_cols = previous
            raise
        self.pending = False

    def set_pending(self) -> None:
        """Mark that new scores arrived — UI should show a Refresh banner."""
        self.pending = True

    def _fetch(self) -> None:
        self.total = self.engine.count(self.period_id)
        tuples = self.engine.fetch_window(
            self.period_id, self.sort_cols,
            limit=self.page_size, offset=self.offset,
        )
        self.rows = [dict(zip(ROW_COLUMNS, row)) for row in tuples]
