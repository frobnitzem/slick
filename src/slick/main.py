import argparse
import logging
import sys

from slick import __version__

__author__ = "David M. Rogers"
__copyright__ = "David M. Rogers"
__license__ = "MIT"

_logger = logging.getLogger(__name__)

from .repo import load_package

def slick(pkg):
    """Print info. about a package.

    Args:
      pkg (string): package name

    Returns:
      info (string): package metadata description
    """
    pkg = load_package("local", pkg)

    info = '\n'.join(map(repr,
       pkg,
       pkg.variants
    ))
    return info

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )

def main(argv):
    """CLI wrapper for slick.

    Instead of returning a value from :func:`slick`, it prints the result to the
    ``stdout`` in a nicely formatted message.
    """
    assert len(argv) > 1, f"Usage: {argv[0]} <package dir>"

    setup_logging(logging.INFO) # DEBUG
    _logger.debug("Starting slick.")
    ans = slick(argv[1])
    _logger.info("Completed slick.")
    print(ans)

def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv)


if __name__ == "__main__":
    run()
