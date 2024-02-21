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
    if len(sys.argv) == 1:
        greeting = "nightly run"
        location = "Github Actions"
        verbose = False
    elif sys.argv[1] == "--circle-ci":
        greeting = "circleci run"
        location = "CircleCI"
        verbose = True
    sloshy = Sloshy("sloshy.yaml", verbose=verbose)
    sloshy.config['nodename'] = f"{sloshy.nodename()} ({location})"
    sloshy.test_rooms()
    sloshy.perform_scan(greeting)
