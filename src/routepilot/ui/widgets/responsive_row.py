"""Row of widgets that stacks vertically when the available width gets narrow."""

from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QBoxLayout, QWidget


class ResponsiveRow(QWidget):
    """Lays children out horizontally, switching to a vertical stack below ``breakpoint``."""

    def __init__(self, breakpoint: int = 720, spacing: int = 16, parent: QWidget | None = None):
        super().__init__(parent)
        self.breakpoint = breakpoint
        self._layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)

    def add(self, widget: QWidget, stretch: int = 1) -> None:
        self._layout.addWidget(widget, stretch)

    @property
    def is_stacked(self) -> bool:
        return bool(self._layout.direction() == QBoxLayout.Direction.TopToBottom)

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # noqa: N802
        super().resizeEvent(event)
        stacked = self.width() < self.breakpoint
        direction = (
            QBoxLayout.Direction.TopToBottom if stacked else QBoxLayout.Direction.LeftToRight
        )
        if self._layout.direction() != direction:
            self._layout.setDirection(direction)
