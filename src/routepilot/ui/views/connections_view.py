"""Connections View showing discovered Linux network interfaces and VPNs."""

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from routepilot.ui.viewmodels.connections_viewmodel import ConnectionsViewModel


class ConnectionsView(QWidget):
    """View rendering detailed cards for all discovered network and VPN connections."""

    def __init__(self, viewmodel: ConnectionsViewModel, on_refresh: callable) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self.on_refresh = on_refresh

        self._setup_ui()
        self.viewmodel.connections_updated.connect(self._render_connections)
        self._render_connections()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Network & VPN Connections")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "Discovered Linux interfaces, NetworkManager active connections, and routing metrics."
        )
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)

        header_row.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.clicked.connect(self.on_refresh)
        header_row.addWidget(refresh_btn)

        layout.addLayout(header_row)

        # Scroll area for connection cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll)

    def _render_connections(self) -> None:
        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        conns = self.viewmodel.connections
        if not conns:
            empty_lbl = QLabel("No active network connections detected.")
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
                badge = QLabel(f"VPN ({conn.kind.value.upper()})")
                badge.setObjectName("badgeVpn")
            elif conn.is_eligible_direct:
                badge = QLabel("Direct Egress (Physical)")
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
                else "No IPv4"
            )
            gw_str = (
                conn.ip4_config.gateway if conn.ip4_config and conn.ip4_config.gateway else "None"
            )
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
