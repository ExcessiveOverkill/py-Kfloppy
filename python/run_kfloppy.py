#!/usr/bin/env python
"""Convenience runner for pyKfloppy when not installed as a package."""

import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kfloppy.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
