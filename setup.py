import sys

# Pre-installation check: Ensure that weewx is already installed.
try:
    import weewx
except ImportError:
    sys.exit(
        "Installation aborted: 'weewx' must be installed before installing weewx-conditions-api. "
        "Please install weewx first."
    )

from setuptools import setup

setup()
