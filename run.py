"""
Main function for Sloshy the Thawman

Runs periodically from a lambda in AWS

Wake up, check if there are any rooms have no recent activity,
post a brief message in those to keep them from freezing
"""

from sloshy import Sloshy


if __name__ == '__main__':
    assert 'SLOSHY_EMAIL' in os.environ
    assert 'SLOSHY_PASSWORD' in os.environ
    Sloshy("sloshy.yaml").scan_rooms("nightly run")
