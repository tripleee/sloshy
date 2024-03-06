"""
Main function for Sloshy the Thawman

Nightly job run from GithubActions or CircleCI

Wake up, check if there are any rooms have no recent activity,
post a brief message in those to keep them from freezing
"""

import os

from sloshy import Sloshy


if __name__ == '__main__':
    import sys

    assert 'SLOSHY_EMAIL' in os.environ
    assert 'SLOSHY_PASSWORD' in os.environ
    if len(sys.argv) == 1:
        location_extra = "Github Actions"
        verbose = False
    elif sys.argv[1] == "--circle-ci":
        location_extra = "CircleCI"
        verbose = True
    sloshy = Sloshy(
        "sloshy.yaml", verbose=verbose, location_extra=location_extra)
    sloshy.test_rooms()
    sloshy.perform_scan("nightly run")
