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
from routepilot.ui.viewmodels.overview_viewmodel import OverviewViewModel


class OverviewView(QWidget):
    """Overview dashboard view."""

    def __init__(self, viewmodel: OverviewViewModel, on_navigate_rules: Callable[[], None]) -> None:
        super().__init__()
        self.viewmodel = viewmodel
        self.on_navigate_rules = on_navigate_rules
        self.i18n = TranslationManager.instance()

        self._setup_ui()
        self.viewmodel.data_changed.connect(self._render_data)
        self.retranslate_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Title header
        title_box = QVBoxLayout()
        self.title = QLabel("Overview")
        self.title.setObjectName("titleLabel")
        self.subtitle = QLabel(
            "Live Linux connection discovery, active VPN egress, and routing policy status."
        )
        self.subtitle.setObjectName("subtitleLabel")
        title_box.addWidget(self.title)
        title_box.addWidget(self.subtitle)
        layout.addLayout(title_box)

        # Cards layout
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        # Card 1: Connection & VPN Status
        self.conn_card = QFrame()
        self.conn_card.setObjectName("card")
        conn_layout = QVBoxLayout(self.conn_card)
        self.conn_title = QLabel("Network & VPN Egress")
        self.conn_title.setObjectName("cardTitle")
        conn_layout.addWidget(self.conn_title)

        self.status_label = QLabel("Scanning network...")
        self.status_label.setWordWrap(True)
        conn_layout.addWidget(self.status_label)

        self.badges_layout = QHBoxLayout()
        conn_layout.addLayout(self.badges_layout)
        conn_layout.addStretch()
        cards_row.addWidget(self.conn_card, 1)

        # Card 2: Routing Policy Rules
        self.rules_card = QFrame()
        self.rules_card.setObjectName("card")
        rules_layout = QVBoxLayout(self.rules_card)
        self.rules_title = QLabel("Traffic Rules")
        self.rules_title.setObjectName("cardTitle")
        rules_layout.addWidget(self.rules_title)

        self.rules_summary_label = QLabel("0 active rules")
        rules_layout.addWidget(self.rules_summary_label)

        btn_row = QHBoxLayout()
        self.manage_rules_btn = QPushButton("Manage Rules")
        self.manage_rules_btn.setObjectName("secondaryButton")
        self.manage_rules_btn.clicked.connect(self.on_navigate_rules)
        btn_row.addWidget(self.manage_rules_btn)
        btn_row.addStretch()
        rules_layout.addLayout(btn_row)
        rules_layout.addStretch()
        cards_row.addWidget(self.rules_card, 1)

        layout.addLayout(cards_row)

        # Honest Technical Reality Banner
        reality_card = QFrame()
        reality_card.setObjectName("card")
        reality_layout = QVBoxLayout(reality_card)
        self.reality_title = QLabel("Observed Network Reality vs Intended Policy")
        self.reality_title.setObjectName("cardTitle")
        reality_layout.addWidget(self.reality_title)

        self.reality_desc = QLabel(
            "• Direct internet bypass routes traffic out physical non-VPN interfaces via Linux kernel policy routing (RPDB).\n"
            "• Sockets established before a rule was applied remain bound to their original interface until reopened.\n"
            "• Domain routing uses resolved IP sets: shared CDN/Anycast edge IPs (e.g. Cloudflare) affect other domains on that edge.\n"
            "• Applications with internal DNS-over-HTTPS (DoH) may bypass local resolver configuration."
        )
        self.reality_desc.setWordWrap(True)
        self.reality_desc.setStyleSheet("color: #A0AEC0; line-height: 1.5;")
        reality_layout.addWidget(self.reality_desc)

        layout.addWidget(reality_card)
        layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def retranslate_ui(self) -> None:
        """Dynamically retranslates texts in OverviewView."""
        t = self.i18n.t
        self.title.setText(t("overview.title"))
        self.subtitle.setText(t("overview.subtitle"))
        self.conn_title.setText(t("overview.card_egress"))
        self.rules_title.setText(t("overview.card_rules"))
        self.manage_rules_btn.setText(t("overview.manage_rules"))
        self.reality_title.setText(t("overview.reality_title"))
        self.reality_desc.setText(t("overview.reality_desc"))
        self._render_data()

    def _render_data(self) -> None:
        is_fa = self.i18n.current_language == "fa"
        self.status_label.setText(self.viewmodel.status_summary)

        # Clear old badges
        while self.badges_layout.count():
            item = self.badges_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        direct = self.viewmodel.direct_connection
        if direct:
            prefix = "مستقیم" if is_fa else "Direct"
            direct_badge = QLabel(f"{prefix}: {direct.id} ({direct.interface})")
            direct_badge.setObjectName("badgeDirect")
            self.badges_layout.addWidget(direct_badge)

        for vpn in self.viewmodel.active_vpns:
            prefix = "وی‌پی‌ان" if is_fa else "VPN"
            vpn_badge = QLabel(f"{prefix}: {vpn.id} ({vpn.interface})")
            vpn_badge.setObjectName("badgeVpn")
            self.badges_layout.addWidget(vpn_badge)

        self.badges_layout.addStretch()

        active = self.viewmodel.active_rules_count
        total = self.viewmodel.total_rules_count
        if is_fa:
            self.rules_summary_label.setText(
                f"{active} قانون فعال اعمال‌شده (از مجموع {total} قانون)."
            )
        else:
            self.rules_summary_label.setText(
                f"{active} active rules enforced (out of {total} configured)."
            )
