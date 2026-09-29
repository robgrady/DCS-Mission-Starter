#!/usr/bin/env python3
"""v1.100.0 name. Every corridor chart is built by build_corridor_charts.py."""
import runpy
import sys
import pathlib

runpy.run_path(str(pathlib.Path(__file__).with_name("build_corridor_charts.py")), run_name="__main__")
