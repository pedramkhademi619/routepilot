"""Background, periodic network discovery so the UI thread never blocks on D-Bus."""

import asyncio
import logging

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal

from routepilot.application.services.discovery_service import DiscoveryService

logger = logging.getLogger(__name__)


class _RefreshTask(QRunnable):
    def __init__(self, refresher: "DiscoveryRefresher") -> None:
        super().__init__()
        self._refresher = refresher

    def run(self) -> None:
        ok = True
        try:
            # Listeners are notified from this worker; Qt queues their signals to the GUI.
            asyncio.run(self._refresher.service.refresh())
        except Exception:
            logger.exception("Network discovery failed")
            ok = False
        self._refresher.done.emit(ok)


class DiscoveryRefresher(QObject):
    """Refreshes ``DiscoveryService`` on a timer and on demand, one scan at a time."""

    INTERVAL_MS = 15_000

    refreshing = pyqtSignal(bool)
    done = pyqtSignal(bool)

    def __init__(self, service: DiscoveryService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self._running = False
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._timer = QTimer(self)
        self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self.refresh_now)
        self.done.connect(self._on_done)

    def start(self) -> None:
        self.refresh_now()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._pool.waitForDone(5_000)

    def refresh_now(self) -> None:
        if self._running:
            return
        self._running = True
        self.refreshing.emit(True)
        self._pool.start(_RefreshTask(self))

    def _on_done(self, _ok: bool) -> None:
        self._running = False
        self.refreshing.emit(False)
