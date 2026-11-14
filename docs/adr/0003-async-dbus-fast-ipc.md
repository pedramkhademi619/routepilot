# ADR 0003: Asynchronous D-Bus with dbus-fast & Background Concurrency

## Status
Accepted

## Context
NetworkManager and systemd-resolved provide state updates over the Linux D-Bus system bus. Polling D-Bus on a timer introduces latency, wastes CPU, and risks locking the Qt GUI thread. We evaluated D-Bus client libraries (`pydbus`, `dbus-python`, `jeepney`, `dasbus`, `dbus-fast`).

## Decision
Use **dbus-fast** with asynchronous event loop dispatching in a dedicated background worker thread, communicating with the PyQt6 main thread via Qt signals.

## Rationale
1. **Performance & Reliability:** `dbus-fast` is modern, actively maintained, pure-Python/cython, and does not require C-level `libdbus-1-dev` compilation.
2. **Signal-Driven:** Enables true event-driven network monitoring via NetworkManager `PropertiesChanged` signals without polling.
3. **UI Responsiveness:** Isolating D-Bus and Netlink queries to background threads ensures the GUI event loop never stutters, even under high network churn.
