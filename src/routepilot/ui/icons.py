"""Monochrome line icons rendered from inline SVG so they follow the active theme."""

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_PATHS = {
    "overview": '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/>'
    '<rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "rules": '<path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/>',
    "connections": '<path d="M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 19.5h.01"/>',
    "diagnostics": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "settings": '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/>'
    '<circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "apply": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4"/>',
    "delete": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.34-5.66L20 8M20 3v5h-5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
}


class Icons:
    """Builds QIcons for the named glyphs in a given color."""

    @classmethod
    def get(cls, name: str, color: str, checked_color: str | None = None) -> QIcon:
        """Icon in ``color``; checkable buttons show ``checked_color`` while checked."""
        icon = QIcon(cls._pixmap(name, color))
        if checked_color:
            icon.addPixmap(cls._pixmap(name, checked_color), QIcon.Mode.Normal, QIcon.State.On)
        return icon

    @staticmethod
    def _pixmap(name: str, color: str, size: int = 48) -> QPixmap:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f"{_PATHS[name]}</svg>"
        )
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        return pixmap
