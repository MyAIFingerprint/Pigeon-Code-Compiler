"""pigeon_rename.__main__ — Allow `python -m pigeon_rename` to work."""
from pigeon_rename.cli import main
import sys

sys.exit(main() or 0)
