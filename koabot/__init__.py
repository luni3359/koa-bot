"""__init.py__"""
import sys

MIN_PYTHON_VERSION = (3, 5, 3)

if sys.version_info < MIN_PYTHON_VERSION:
    sys.exit(1)
