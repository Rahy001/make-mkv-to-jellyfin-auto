#!/usr/bin/env python3
"""JellyRip — lanceur. Usage : python jellyrip.py [--gui | --scan | --mode mp4 ...]"""

from jellyrip.__main__ import cli_main

if __name__ == "__main__":
    raise SystemExit(cli_main())
