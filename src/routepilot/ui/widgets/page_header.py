"""Page title, wrapping subtitle and action buttons that move below the text when narrow."""

from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QBoxLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PageHeader(QWidget):
    """Header used at the top of each page."""

    BREAKPOINT = 640

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        self.title = QLabel()
        self.title.setObjectName("titleLabel")
        self.title.setWordWrap(True)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitleLabel")
        self.subtitle.setWordWrap(True)
        text_box.addWidget(self.title)
        text_box.addWidget(self.subtitle)
        self._layout.addLayout(text_box, 1)

        self._actions = QHBoxLayout()
        self._actions.setSpacing(8)
        self._layout.addLayout(self._actions)

    def set_text(self, title: str, subtitle: str) -> None:
        self.title.setText(title)
        self.subtitle.setText(subtitle)

    def add_action(self, widget: QWidget) -> None:
        self._actions.addWidget(widget)

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # noqa: N802
        super().resizeEvent(event)
        narrow = self.width() < self.BREAKPOINT
        direction = QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        if self._layout.direction() != direction:
            self._layout.setDirection(direction)
            self._layout.setStretch(0, 0 if narrow else 1)
