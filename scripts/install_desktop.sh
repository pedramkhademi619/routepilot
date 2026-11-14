#!/usr/bin/env bash
# ==============================================================================
# RoutePilot Desktop Installation & Synchronization Script
# Installs application launchers, icons, polkit helpers, and desktop shortcuts.
# ==============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/routepilot"
HICOLOR_DIR="${HOME}/.local/share/icons/hicolor"
DESKTOP_DIR="${HOME}/Desktop"

echo "==> Installing RoutePilot in desktop environment from ${PROJECT_DIR}..."

# 1. Ensure directories exist
mkdir -p "${BIN_DIR}" "${APP_DIR}" "${ICON_DIR}" "${DESKTOP_DIR}"
mkdir -p "${HICOLOR_DIR}/scalable/apps" "${HICOLOR_DIR}/128x128/apps"

# 2. Sync editable python package
echo "==> Synchronizing Python virtual environment..."
cd "${PROJECT_DIR}"
uv pip install -e . --quiet

# 3. Copy application icon
if [[ -f "${PROJECT_DIR}/src/routepilot/resources/icon.png" ]]; then
    cp "${PROJECT_DIR}/src/routepilot/resources/icon.png" "${ICON_DIR}/icon.png"
    cp "${PROJECT_DIR}/src/routepilot/resources/icon.png" "${HICOLOR_DIR}/128x128/apps/routepilot.png"
elif [[ -f "${ICON_DIR}/icon.png" ]]; then
    cp "${ICON_DIR}/icon.png" "${HICOLOR_DIR}/128x128/apps/routepilot.png" 2>/dev/null || true
fi

# 4. Install / Update CLI and GUI wrappers in ~/.local/bin
echo "==> Updating executables in ${BIN_DIR}..."
cat << 'EOF' > "${BIN_DIR}/routepilot-gui"
#!/usr/bin/env bash
set -e
PROJECT_DIR="/home/pedram/Projects/routepilot"
exec "$PROJECT_DIR/.venv/bin/python3" -m routepilot.ui.app "$@"
EOF
chmod +x "${BIN_DIR}/routepilot-gui"

cat << 'EOF' > "${BIN_DIR}/routepilot"
#!/usr/bin/env bash
set -e
PROJECT_DIR="/home/pedram/Projects/routepilot"
exec "$PROJECT_DIR/.venv/bin/python3" -m routepilot.cli.main "$@"
EOF
chmod +x "${BIN_DIR}/routepilot"

cat << 'EOF' > "${BIN_DIR}/routepilot-recover"
#!/usr/bin/env bash
set -e
PROJECT_DIR="/home/pedram/Projects/routepilot"
exec "$PROJECT_DIR/.venv/bin/python3" -m routepilot.cli.recover "$@"
EOF
chmod +x "${BIN_DIR}/routepilot-recover"

cat << 'EOF' > "${BIN_DIR}/routepilot-apply"
#!/usr/bin/env bash
set -e
PROJECT_DIR="/home/pedram/Projects/routepilot"
exec pkexec env PYTHONPATH="$PROJECT_DIR/src" "$PROJECT_DIR/.venv/bin/python3" -m routepilot.cli.apply "$@"
EOF
chmod +x "${BIN_DIR}/routepilot-apply"

# 5. Create Desktop Entry in Applications Menu & Desktop
echo "==> Creating Desktop Entries..."
DESKTOP_CONTENT="[Desktop Entry]
Name=RoutePilot
GenericName=Network Traffic Router
GenericName[fa]=مسیریابی هوشمند ترافیک و بای‌پس VPN
Comment=Selective VPN Bypass & Policy Routing Utility
Comment[fa]=ابزار دور زدن انتخابی VPN و هدایت ترافیک در لینوکس
Exec=${BIN_DIR}/routepilot-gui %u
Icon=${ICON_DIR}/icon.png
Terminal=false
Type=Application
Categories=Network;Settings;System;Utility;
Keywords=network;vpn;bypass;split-tunnel;routing;nftables;
StartupNotify=true
StartupWMClass=RoutePilot
Actions=EmergencyReset;

[Desktop Action EmergencyReset]
Name=Emergency Reset Networking
Name[fa]=بازنشانی اضطراری شبکه
Exec=${BIN_DIR}/routepilot-recover
"

echo "${DESKTOP_CONTENT}" > "${APP_DIR}/routepilot.desktop"
chmod +x "${APP_DIR}/routepilot.desktop"

echo "${DESKTOP_CONTENT}" > "${DESKTOP_DIR}/routepilot.desktop"
chmod +x "${DESKTOP_DIR}/routepilot.desktop"

# Mark trusted in KDE Plasma / GNOME
gio set "${DESKTOP_DIR}/routepilot.desktop" metadata::trusted true 2>/dev/null || true

# 6. Update system desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APP_DIR}" 2>/dev/null || true
fi

echo "✅ RoutePilot successfully installed and updated on Desktop and System Applications!"
