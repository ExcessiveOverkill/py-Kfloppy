import sys
from pathlib import Path


if __name__ == "__main__":
    try:
        from .cli import main
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from kfloppy.cli import main

    raise SystemExit(main())
