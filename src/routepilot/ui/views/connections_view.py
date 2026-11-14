from collections.abc import Callable

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from routepilot.ui.translation_manager import TranslationManager
from routepilot.ui.viewmodels.connections_viewmodel import ConnectionsViewModel


class ConnectionsView(QWidget):
    """View rendering detailed cards for all discovered network and VPN connections."""

    def __init__(self, viewmodel: ConnectionsViewModel, on_refresh: Callable[[], None]) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self.on_refresh = on_refresh
        self.i18n = TranslationManager.instance()

        self._setup_ui()
        self.viewmodel.connections_updated.connect(self._render_connections)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title = QLabel("Network & VPN Connections")
        self.title.setObjectName("titleLabel")
        self.subtitle = QLabel(
            "Discovered Linux interfaces, NetworkManager active connections, and routing metrics."
        )
        self.subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        header_row.addLayout(title_box)

        header_row.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.clicked.connect(self.on_refresh)
        header_row.addWidget(self.refresh_btn)

        layout.addLayout(header_row)

        # Scroll area for connection cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area)

    def retranslate_ui(self) -> None:
        """Dynamically retranslates texts in ConnectionsView."""
        t = self.i18n.t
        self.title.setText(t("connections.title"))
        self.subtitle.setText(t("connections.subtitle"))
        self.refresh_btn.setText(t("common.refresh"))
        self._render_connections()

    def _render_connections(self) -> None:
        t = self.i18n.t
        is_fa = self.i18n.current_language == "fa"

        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        conns = self.viewmodel.connections
        if not conns:
            empty_lbl = QLabel(t("connections.empty"))
            empty_lbl.setStyleSheet("color: #A0AEC0; padding: 24px;")
            self.cards_layout.addWidget(empty_lbl)
            return

        for conn in conns:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)

            top_row = QHBoxLayout()
            name_lbl = QLabel(conn.id)
            name_lbl.setObjectName("cardTitle")
            top_row.addWidget(name_lbl)

            top_row.addStretch()

            if conn.is_vpn:
                badge_text = (
                    f"وی‌پی‌ان ({conn.kind.value.upper()})"
                    if is_fa
                    else f"VPN ({conn.kind.value.upper()})"
                )
                badge = QLabel(badge_text)
                badge.setObjectName("badgeVpn")
            elif conn.is_eligible_direct:
                badge_text = "خروجی مستقیم (فیزیکی)" if is_fa else "Direct Egress (Physical)"
                badge = QLabel(badge_text)
                badge.setObjectName("badgeDirect")
            else:
                badge = QLabel(conn.kind.value.capitalize())
                badge.setObjectName("badgeOffline")
            top_row.addWidget(badge)

            card_layout.addLayout(top_row)

            # Details
            ip_str = (
                ", ".join(conn.ip4_config.addresses)
                if conn.ip4_config and conn.ip4_config.addresses
                else ("بدون IPv4" if is_fa else "No IPv4")
            )
            gw_str = (
                conn.ip4_config.gateway
                if conn.ip4_config and conn.ip4_config.gateway
                else ("هیچ" if is_fa else "None")
            )
            if is_fa:
                default_str = "بله (گیت‌وی پیش‌فرض)" if conn.is_default else "خیر"
                details = QLabel(
                    f"رابط شبکه: <b>{conn.interface}</b> | اولویت (متریک): <b>{conn.metric}</b> | مسیر پیش‌فرض: <b>{default_str}</b>\n"
                    f"آدرس‌های IP: {ip_str} | گیت‌وی: {gw_str}\n"
                    f"شناسه UUID: <font color='#718096'>{conn.uuid}</font>"
                )
            else:
                default_str = "Yes (Default Gateway)" if conn.is_default else "No"
                details = QLabel(
                    f"Interface: <b>{conn.interface}</b> | Metric: <b>{conn.metric}</b> | Default Route: <b>{default_str}</b>\n"
                    f"IPs: {ip_str} | Gateway: {gw_str}\n"
                    f"UUID: <font color='#718096'>{conn.uuid}</font>"
                )
            details.setTextFormat(details.textFormat().RichText)
            card_layout.addWidget(details)

            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
