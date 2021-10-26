"""__init.py__"""
import sys

MIN_PYTHON_VERSION = (3, 8)

if sys.version_info < MIN_PYTHON_VERSION:
    version_str = '.'.join(map(str, MIN_PYTHON_VERSION))
    raise EnvironmentError("Python version needs to be at least " + version_str)
