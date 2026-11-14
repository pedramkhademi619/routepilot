# ADR 0002: PyQt6 QtWidgets for Desktop UI

## Status
Accepted

## Context
RoutePilot targets the Linux desktop environment (GNOME, KDE Plasma, XFCE). The UI must provide accessible controls, high-DPI scaling, dark/light theme compliance, system tray integration, and future Persian Right-to-Left (RTL) support. We compared `PyQt6.QtWidgets` against `PyQt6.QtQuick` (QML).

## Decision
Use **PyQt6 QtWidgets** as the desktop UI framework.

## Rationale
1. **Accessibility (a11y):** QtWidgets seamlessly integrates with AT-SPI2 on Linux desktops (`QAccessible`), providing full screen reader support (Orca). Qt Quick accessibility on Linux requires significant manual bridging.
2. **Desktop Integration:** QtWidgets automatically adapts to KDE Breeze, GNOME Adwaita, and system color schemes without requiring fragile distro QML style packages.
3. **Complex Data Displays:** RoutePilot's rule lists, connection monitors, and diagnostic journals require high-performance tabular models (`QTableView`, `QTreeView`, `QHeaderView`), which are native in QtWidgets.
4. **RTL Support:** Full built-in layout mirroring support for Persian RTL (`setLayoutDirection(Qt.LayoutDirection.RightToLeft)`).

## Consequences
- UI is built with standard Python classes, layouts, and custom widgets.
- Licensed under GPL-3.0-or-later to comply with Riverbank Computing's PyQt6 GPL license.
