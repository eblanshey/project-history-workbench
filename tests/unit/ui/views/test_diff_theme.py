"""File responsibility: Unit tests for theme-aware diff color helpers."""

import pytest
from PySide6.QtGui import QColor, QPalette

from freecad.diff_wb.domain.diff.models import DiffState
from freecad.diff_wb.ui.views.diff_theme import background_for_state, foreground_for_background


def _palette(base: QColor, text: QColor, window: QColor) -> QPalette:
    """Build a minimal palette for diff theme tests."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Window, window)
    return palette


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (DiffState.ADDED, QColor(200, 255, 200)),
        (DiffState.DELETED, QColor(255, 200, 200)),
        (DiffState.MODIFIED, QColor(200, 200, 255)),
    ],
)
def test_light_theme_uses_original_bright_backgrounds_with_black_text(state: DiffState, expected: QColor) -> None:
    """Light themes keep original bright highlight colors and black text."""
    palette = _palette(base=QColor(255, 255, 255), text=QColor(0, 0, 0), window=QColor(245, 245, 245))

    background = background_for_state(state, palette)

    assert background == expected
    assert foreground_for_background(expected, palette) == QColor(0, 0, 0)


def test_unchanged_state_uses_normal_theme_background() -> None:
    """UNCHANGED rows have no custom background color."""
    palette = _palette(base=QColor(255, 255, 255), text=QColor(0, 0, 0), window=QColor(245, 245, 245))

    assert background_for_state(DiffState.UNCHANGED, palette) is None


def test_dark_theme_uses_blended_background_instead_of_light_pastel() -> None:
    """Dark themes avoid original pastels because they clash with light text."""
    palette = _palette(base=QColor(30, 30, 30), text=QColor(240, 240, 240), window=QColor(20, 20, 20))

    background = background_for_state(DiffState.ADDED, palette)

    assert background is not None
    assert background != QColor(200, 255, 200)
