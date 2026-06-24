#!/usr/bin/env python3
"""Entry point — delegates entirely to :mod:`allotrope_gen.cli`."""

import sys

from allotrope_gen.cli import main

if __name__ == "__main__":
    sys.exit(main())