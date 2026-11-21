#!/usr/bin/env bash
# ==============================================================================
# RoutePilot per-user installer (no root needed to install).
#
#   ./scripts/install_desktop.sh              install or update from this checkout
#   ./scripts/install_desktop.sh --uninstall  remove launchers, icon and venv links
#
# Creates .venv in the checkout, links the commands into ~/.local/bin and registers
# the desktop entry + icon. Applying routes later asks for authorization via polkit.
# ==============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
BIN_DIR="${HOME}/.local/bin"
DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
APP_DIR="${DATA_HOME}/applications"
ICON_DIR="${DATA_HOME}/icons/hicolor/scalable/apps"
COMMANDS=(routepilot routepilot-gui routepilot-apply routepilot-recover)
DESKTOP_FILE="routepilot.desktop"

desktop_dir() {
    if command -v xdg-user-dir >/dev/null 2>&1; then
        xdg-user-dir DESKTOP
    else
        echo "${HOME}/Desktop"
    fi
}

uninstall() {
    echo "==> Removing RoutePilot launchers..."
    for cmd in "${COMMANDS[@]}"; do
        rm -f "${BIN_DIR}/${cmd}"
    done
    rm -f "${APP_DIR}/${DESKTOP_FILE}" "${ICON_DIR}/routepilot.svg" "$(desktop_dir)/${DESKTOP_FILE}"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "${APP_DIR}" || true
    echo "Done. Your rules in ~/.config/routepilot were kept; run 'routepilot reset' first if"
    echo "you want to remove routes that are still applied."
}

check_requirements() {
    local missing=()
    command -v python3 >/dev/null 2>&1 || missing+=("python3 (>= 3.11)")
    command -v nft >/dev/null 2>&1 || missing+=("nftables")
    command -v pkexec >/dev/null 2>&1 || missing+=("polkit (pkexec)")
    if ((${#missing[@]})); then
        echo "Missing system packages: ${missing[*]}" >&2
        echo "Debian/Ubuntu: sudo apt install python3 python3-venv nftables policykit-1" >&2
        exit 1
    fi
    if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
        echo "RoutePilot needs Python 3.11 or newer (found $(python3 --version))." >&2
        exit 1
    fi
    command -v resolvectl >/dev/null 2>&1 ||
        echo "Note: systemd-resolved not found; domain rules will work but split DNS is disabled."
}

install() {
    check_requirements
    echo "==> Installing RoutePilot from ${PROJECT_DIR}"

    if command -v uv >/dev/null 2>&1; then
        [[ -d "${VENV_DIR}" ]] || uv venv --quiet "${VENV_DIR}"
        uv pip install --quiet --python "${VENV_DIR}/bin/python" -e "${PROJECT_DIR}"
    else
        [[ -d "${VENV_DIR}" ]] || python3 -m venv "${VENV_DIR}"
        "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
        "${VENV_DIR}/bin/pip" install --quiet -e "${PROJECT_DIR}"
    fi

    mkdir -p "${BIN_DIR}" "${APP_DIR}" "${ICON_DIR}"
    for cmd in "${COMMANDS[@]}"; do
        ln -sf "${VENV_DIR}/bin/${cmd}" "${BIN_DIR}/${cmd}"
    done

    cp "${PROJECT_DIR}/src/routepilot/ui/resources/routepilot.svg" "${ICON_DIR}/routepilot.svg"
    sed -e "s|^Exec=routepilot-gui|Exec=${BIN_DIR}/routepilot-gui|" \
        -e "s|^Exec=routepilot-recover|Exec=${BIN_DIR}/routepilot-recover|" \
        "${PROJECT_DIR}/packaging/desktop/${DESKTOP_FILE}" >"${APP_DIR}/${DESKTOP_FILE}"

    local desktop
    desktop="$(desktop_dir)"
    if [[ -d "${desktop}" ]]; then
        cp "${APP_DIR}/${DESKTOP_FILE}" "${desktop}/${DESKTOP_FILE}"
        chmod +x "${desktop}/${DESKTOP_FILE}"
        gio set "${desktop}/${DESKTOP_FILE}" metadata::trusted true 2>/dev/null || true
    fi
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "${APP_DIR}" || true

    echo "RoutePilot installed. Start it from your application menu or run: routepilot-gui"
    [[ ":${PATH}:" == *":${BIN_DIR}:"* ]] ||
        echo "Note: ${BIN_DIR} is not on your PATH; add it to use the 'routepilot' command."
}

case "${1:-}" in
    --uninstall) uninstall ;;
    "") install ;;
    *)
        echo "Usage: $0 [--uninstall]" >&2
        exit 2
        ;;
esac
