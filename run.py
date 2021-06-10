"""
Main function for Sloshy the Thawman

Runs periodically from a lambda in AWS

Wake up, check if there are any rooms have no recent activity,
post a brief message in those to keep them from freezing
"""

from sloshy import Sloshy


def main():
    Sloshy("sloshy.yaml").scan_rooms()


if __name__ == '__main__':
    main()
