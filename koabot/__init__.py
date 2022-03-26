import sys

MIN_PYTHON_VERSION = (3, 10)

if sys.version_info < MIN_PYTHON_VERSION:
    VERSION_STR = '.'.join(map(str, MIN_PYTHON_VERSION))
    raise EnvironmentError("Python version needs to be at least " + VERSION_STR)
