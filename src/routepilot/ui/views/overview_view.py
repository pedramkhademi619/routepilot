"""Overview dashboard view."""

from collections.abc import Callable

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.ui.viewmodels.overview_viewmodel import OverviewViewModel
from routepilot.ui.views.base_page import BasePage
from routepilot.ui.widgets.card import Card
from routepilot.ui.widgets.flow_layout import FlowLayout
from routepilot.ui.widgets.responsive_row import ResponsiveRow


class OverviewView(BasePage):
    """Connectivity status, rule counters and the technical caveats users should know."""

    def __init__(self, viewmodel: OverviewViewModel, on_navigate_rules: Callable[[], None]) -> None:
        super().__init__()
        self.viewmodel = viewmodel

        self.status_card = Card()
        self.status_label = QLabel()
        self.status_label.setObjectName("heroLabel")
        self.status_label.setWordWrap(True)
        self.status_card.body.addWidget(self.status_label)
        badges_host = QWidget()
        self.badges = FlowLayout(badges_host)
        self.status_card.body.addWidget(badges_host)
        self.content.addWidget(self.status_card)

        self.stats_row = ResponsiveRow(breakpoint=640)
        self.rules_stat, self.rules_value, self.rules_caption = self._stat_tile()
        self.vpn_stat, self.vpn_value, self.vpn_caption = self._stat_tile()
        self.direct_stat, self.direct_value, self.direct_caption = self._stat_tile()
        for tile in (self.rules_stat, self.vpn_stat, self.direct_stat):
            self.stats_row.add(tile)
        self.content.addWidget(self.stats_row)

        self.manage_rules_btn = QPushButton()
        self.manage_rules_btn.setObjectName("secondaryButton")
        self.manage_rules_btn.clicked.connect(on_navigate_rules)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.manage_rules_btn)
        btn_row.addStretch()
        self.rules_stat.body.addLayout(btn_row)

        self.notes_card = Card()
        self.notes_label = QLabel()
        self.notes_label.setObjectName("mutedLabel")
        self.notes_label.setWordWrap(True)
        self.notes_card.body.addWidget(self.notes_label)
        self.content.addWidget(self.notes_card)
        self.content.addStretch()

        self.viewmodel.data_changed.connect(self._render_data)

    def retranslate_ui(self) -> None:
        t = self.i18n.t
        self.header.set_text(t("overview.title"), t("overview.subtitle"))
        self.rules_caption.setText(t("overview.stat_rules"))
        self.vpn_caption.setText(t("overview.stat_vpns"))
        self.direct_caption.setText(t("overview.stat_direct"))
        self.manage_rules_btn.setText(t("overview.manage_rules"))
        self.notes_card.set_title(t("overview.notes_title"))
        self.notes_label.setText(t("overview.notes_body"))
        self._render_data()

    def _stat_tile(self) -> tuple[Card, QLabel, QLabel]:
        tile = Card()
        caption = QLabel()
        caption.setObjectName("statLabel")
        value = QLabel()
        value.setObjectName("statValue")
        value.setWordWrap(True)
        tile.body.addWidget(caption)
        tile.body.addWidget(value)
        tile.body.addStretch()
        return tile, value, caption

    def _render_data(self) -> None:
        t = self.i18n.t
        direct, vpns = self.viewmodel.direct_connection, self.viewmodel.active_vpns
        self.status_label.setText(
            t(
                self.viewmodel.state_key,
                iface=direct.interface if direct else "",
                name=direct.id if direct else "",
            )
        )

        self.badges.clear()
        if direct:
            self._badge(t("overview.badge_direct", conn=self._conn(direct)), "badgeDirect")
        for vpn in vpns:
            self._badge(t("overview.badge_vpn", conn=self._conn(vpn)), "badgeVpn")

        active, total = self.viewmodel.rule_counts()
        self.rules_value.setText(t("overview.stat_rules_value", active=active, total=total))
        self.vpn_value.setText(str(len(vpns)))
        self.direct_value.setText(direct.interface if direct else t("common.none"))

    def _conn(self, conn: NetworkConnection) -> str:
        return self.i18n.ltr(f"{conn.id} ({conn.interface})")

    def _badge(self, text: str, object_name: str) -> None:
        badge = QLabel(text)
        badge.setObjectName(object_name)
        self.badges.addWidget(badge)
