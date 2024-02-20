"""
Main function for Sloshy the Thawman

Runs periodically from a lambda in AWS

Wake up, check if there are any rooms have no recent activity,
post a brief message in those to keep them from freezing
"""

import os

from sloshy import Sloshy


if __name__ == '__main__':
    import sys

    assert 'SLOSHY_EMAIL' in os.environ
    assert 'SLOSHY_PASSWORD' in os.environ
    sloshy = Sloshy("sloshy.yaml")
    sloshy.test_rooms()
    sloshy.perform_scan("nightly run" if len(sys.argv) == 1 else sys.argv[1])
