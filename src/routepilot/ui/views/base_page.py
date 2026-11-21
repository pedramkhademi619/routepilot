"""Common scaffold for every page: scrollable content area with a responsive header."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.widgets.page_header import PageHeader


class BasePage(QWidget):
    """Scrollable page. Subclasses add widgets to ``content`` and implement retranslate_ui."""

    COMPACT_WIDTH = 620

    def __init__(self, scrollable: bool = True) -> None:
        super().__init__()
        self.setObjectName("page")
        self.i18n = TranslationManager.instance()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setObjectName("page")
        self.content = QVBoxLayout(container)
        self.content.setSpacing(16)
        self.header = PageHeader()
        self.content.addWidget(self.header)

        if scrollable:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(container)
            root.addWidget(scroll)
        else:
            root.addWidget(container)
        self._apply_margins()

    def retranslate_ui(self) -> None:
        raise NotImplementedError

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_margins()

    def _apply_margins(self) -> None:
        margin = 14 if self.width() < self.COMPACT_WIDTH else 28
        self.content.setContentsMargins(margin, margin, margin, margin)
