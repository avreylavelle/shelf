import os
import sys

# Allow running this file directly from the repo.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from legacy.cli.ui_terminal.tui_menu import main_menu

if __name__ == "__main__":
    main_menu()
