"""``routepilot-recover``: shortcut for ``routepilot reset`` (emergency state purge)."""

import sys

from routepilot.cli.main import RoutePilotCli


def main() -> None:
    sys.exit(RoutePilotCli().run([*sys.argv[1:], "reset"]))


if __name__ == "__main__":
    main()
