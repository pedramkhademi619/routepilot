"""Overview View displaying active connection status, VPN state, and policy summary."""

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from routepilot.ui.viewmodels.overview_viewmodel import OverviewViewModel


class OverviewView(QWidget):
    """Overview dashboard view."""

    def __init__(self, viewmodel: OverviewViewModel, on_navigate_rules: callable) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self.on_navigate_rules = on_navigate_rules

        self._setup_ui()
        self.viewmodel.data_changed.connect(self._render_data)
        self._render_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Title header
        title_box = QVBoxLayout()
        title = QLabel("Overview")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "Live Linux connection discovery, active VPN egress, and routing policy status."
        )
        subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Cards layout
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        # Card 1: Connection & VPN Status
        self.conn_card = QFrame()
        self.conn_card.setObjectName("card")
        conn_layout = QVBoxLayout(self.conn_card)
        conn_title = QLabel("Network & VPN Egress")
        conn_title.setObjectName("cardTitle")
        conn_layout.addWidget(conn_title)

        self.status_label = QLabel("Scanning network...")
        self.status_label.setWordWrap(True)
        conn_layout.addWidget(self.status_label)

        self.badges_layout = QHBoxLayout()
        conn_layout.addLayout(self.badges_layout)
        conn_layout.addStretch()
        cards_row.addWidget(self.conn_card)

        # Card 2: Routing Policy Rules
        self.rules_card = QFrame()
        self.rules_card.setObjectName("card")
        rules_layout = QVBoxLayout(self.rules_card)
        rules_title = QLabel("Traffic Rules")
        rules_title.setObjectName("cardTitle")
        rules_layout.addWidget(rules_title)

        self.rules_summary_label = QLabel("0 active rules")
        rules_layout.addWidget(self.rules_summary_label)

        btn_row = QHBoxLayout()
        manage_rules_btn = QPushButton("Manage Rules")
        manage_rules_btn.setObjectName("secondaryButton")
        manage_rules_btn.clicked.connect(self.on_navigate_rules)
        btn_row.addWidget(manage_rules_btn)
        btn_row.addStretch()
        rules_layout.addLayout(btn_row)
        rules_layout.addStretch()
        cards_row.addWidget(self.rules_card)

        layout.addLayout(cards_row)

        # Honest Technical Reality Banner
        reality_card = QFrame()
        reality_card.setObjectName("card")
        reality_layout = QVBoxLayout(reality_card)
        reality_title = QLabel("Observed Network Reality vs Intended Policy")
        reality_title.setObjectName("cardTitle")
        reality_layout.addWidget(reality_title)

        reality_desc = QLabel(
            "• Direct internet bypass routes traffic out physical non-VPN interfaces via Linux kernel policy routing (RPDB).\n"
            "• Sockets established before a rule was applied remain bound to their original interface until reopened.\n"
            "• Domain routing uses resolved IP sets: shared CDN/Anycast edge IPs (e.g. Cloudflare) affect other domains on that edge.\n"
            "• Applications with internal DNS-over-HTTPS (DoH) may bypass local resolver configuration."
        )
        reality_desc.setWordWrap(True)
        reality_desc.setStyleSheet("color: #A0AEC0; line-height: 1.5;")
        reality_layout.addWidget(reality_desc)

        layout.addWidget(reality_card)
        layout.addStretch()

    def _render_data(self) -> None:
        self.status_label.setText(self.viewmodel.status_summary)

        # Clear old badges
        while self.badges_layout.count():
            item = self.badges_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        direct = self.viewmodel.direct_connection
        if direct:
            direct_badge = QLabel(f"Direct: {direct.id} ({direct.interface})")
            direct_badge.setObjectName("badgeDirect")
            self.badges_layout.addWidget(direct_badge)

        for vpn in self.viewmodel.active_vpns:
            vpn_badge = QLabel(f"VPN: {vpn.id} ({vpn.interface})")
            vpn_badge.setObjectName("badgeVpn")
            self.badges_layout.addWidget(vpn_badge)

        self.badges_layout.addStretch()

        active = self.viewmodel.active_rules_count
        total = self.viewmodel.total_rules_count
        self.rules_summary_label.setText(
            f"{active} active rules enforced (out of {total} configured)."
        )
