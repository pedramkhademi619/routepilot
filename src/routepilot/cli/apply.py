"""``routepilot-apply``: shortcut for ``routepilot apply`` (kept for existing launchers)."""

import sys

from routepilot.cli.main import RoutePilotCli


def main() -> None:
    sys.exit(RoutePilotCli().run([*sys.argv[1:], "apply"]))


if __name__ == "__main__":
    main()
