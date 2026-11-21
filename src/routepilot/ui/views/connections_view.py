"""Connections view: one card per discovered network link or VPN."""

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from routepilot.domain.models.connection_kind import ConnectionKind
from routepilot.domain.models.network_connection import NetworkConnection
from routepilot.ui.viewmodels.connections_viewmodel import ConnectionsViewModel
from routepilot.ui.views.base_page import BasePage
from routepilot.ui.widgets.card import Card


class ConnectionsView(BasePage):
    """Renders cards for all discovered network and VPN connections."""

    def __init__(self, viewmodel: ConnectionsViewModel, on_refresh: Callable[[], None]) -> None:
        super().__init__()
        self.viewmodel = viewmodel

        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.clicked.connect(on_refresh)
        self.header.add_action(self.refresh_btn)

        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)
        self.content.addWidget(self.cards_host)
        self.content.addStretch()

        self.viewmodel.connections_updated.connect(self._render_connections)

    def retranslate_ui(self) -> None:
        t = self.i18n.t
        self.header.set_text(t("connections.title"), t("connections.subtitle"))
        self.refresh_btn.setText(t("common.refresh"))
        self._render_connections()

    def set_refreshing(self, running: bool) -> None:
        self.refresh_btn.setEnabled(not running)

    def _render_connections(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.deleteLater()

        conns = self.viewmodel.connections
        if not conns:
            empty = QLabel(self.i18n.t("connections.empty"))
            empty.setObjectName("mutedLabel")
            empty.setWordWrap(True)
            self.cards_layout.addWidget(empty)
            return
        for conn in sorted(conns, key=lambda c: (not c.is_vpn, not c.is_eligible_direct, c.id)):
            self.cards_layout.addWidget(self._card(conn))

    def _card(self, conn: NetworkConnection) -> Card:
        t = self.i18n.t
        card = Card()
        top = QHBoxLayout()
        name = QLabel(conn.id)
        name.setObjectName("cardTitle")
        name.setWordWrap(True)
        top.addWidget(name, 1)
        kind = t(f"kind.{conn.kind.value}")
        if conn.is_vpn and conn.kind == ConnectionKind.VPN_GENERIC:
            badge = QLabel(kind)
            badge.setObjectName("badgeVpn")
        elif conn.is_vpn:
            badge = QLabel(t("connections.badge_vpn", kind=kind))
            badge.setObjectName("badgeVpn")
        elif conn.is_eligible_direct:
            badge = QLabel(t("connections.badge_direct"))
            badge.setObjectName("badgeDirect")
        else:
            badge = QLabel(kind)
            badge.setObjectName("badgeOffline")
        top.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        card.body.addLayout(top)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(6)
        addresses = [*(conn.ip4_config.addresses if conn.ip4_config else [])]
        addresses += conn.ip6_config.addresses if conn.ip6_config else []
        gateways = [g for g in (conn.gateway_for(4), conn.gateway_for(6)) if g]
        rows = (
            ("connections.field_interface", conn.interface),
            ("connections.field_addresses", ", ".join(addresses) or t("common.none")),
            ("connections.field_gateway", ", ".join(gateways) or t("common.none")),
            ("connections.field_metric", str(conn.metric)),
            (
                "connections.field_default",
                t("connections.default_yes" if conn.is_default else "connections.default_no"),
            ),
            ("connections.field_uuid", conn.uuid),
        )
        for key, value in rows:
            label = QLabel(t(key))
            label.setObjectName("fieldLabel")
            field = QLabel(value)
            field.setWordWrap(True)
            field.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(label, field)
        card.body.addLayout(form)
        return card
