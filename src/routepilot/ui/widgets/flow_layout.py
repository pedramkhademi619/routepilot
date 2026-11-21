"""Layout that places items left-to-right (or right-to-left) and wraps them onto new lines."""

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QLayoutItem, QWidget


class FlowLayout(QLayout):
    """Wrapping layout for badges and button groups that must never force horizontal scroll."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 8) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

    def addItem(self, item: QLayoutItem | None) -> None:  # noqa: N802 (Qt API)
        if item is not None:
            self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, apply=True)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def clear(self) -> None:
        """Removes and deletes every widget in the layout."""
        while self._items:
            item = self._items.pop()
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _do_layout(self, rect: QRect, apply: bool) -> int:
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        parent = self.parentWidget()
        rtl = parent is not None and parent.layoutDirection() == Qt.LayoutDirection.RightToLeft
        spacing = self.spacing()
        x, y, line_height = area.x(), area.y(), 0

        for item in self._items:
            widget = item.widget()
            if widget is not None and widget.isHidden():
                continue
            hint = item.sizeHint().boundedTo(QSize(area.width(), 16777215))
            if x + hint.width() > area.right() + 1 and line_height > 0:
                x, y, line_height = area.x(), y + line_height + spacing, 0
            if apply:
                left = area.right() - (x - area.x()) - hint.width() + 1 if rtl else x
                item.setGeometry(QRect(QPoint(left, y), hint))
            x += hint.width() + spacing
            line_height = max(line_height, hint.height())

        return int(y + line_height - rect.y() + margins.bottom())
