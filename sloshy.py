#!/usr/bin/env python3

"""
Sloshy the Thawman - main class
"""

from datetime import datetime, timedelta
from os import environ
import random
from time import sleep
import platform
import logging

import yaml
from chatexchange.client import Client as ChExClient, ChatActionError
from requests.exceptions import RequestException

from scrape_chat import Transcript, TranscriptFrozenDeletedException, RepScrape


DEFAULT_MAX_AGE = {'days': 12}
AGGRESSIVE_MAX_MSG_THRESHOLD = 15
DEFAULT_AGGRESSIVE_MAX_AGE = {'days': 5}


class SchemaError(Exception):
    pass


class LocalClientRequestQueue:
    "Quick hack to support logout() method"
    def empty(self):
        return True


class LocalClient:
    """
    Simple mock ChatExchange.client with no actual networking functionality
    """
    def __init__(self, host='stackexchange.com', email=None, password=None):
        self.host = host
        self.email = email
        self.password = password

        self.room = None

        self._request_queue = LocalClientRequestQueue()

    def login(self, email=None, password=None):
        logging.info('local - not logging in to %s', self.host)

    def get_room(self, id: int):
        logging.info('local - not fetching %s/rooms/%s', self.host, id)
        self.room = id
        return self

    def join(self):
        assert self.room is not None
        logging.info('local - not joining %s/rooms/%i', self.host, self.room)

    def send_message(self, message: str):
        assert self.room is not None
        logging.info(
            'local - %s/rooms/%i: not sending message', self.host, self.room)
        if message:
            print(message)
        else:
            print('(Not printing any message, just checking ability to join)')

    def logout(self):
        logging.info('local - %s/rooms/%i: logging out', self.host, self.room)


class Chatclients:
    """
    Singleton to keep track of chat servers, with one client for each.
    """
    def __init__(self, local=False):
        """
        Create a dispatcher for the servers we know about.
        With local=True, create a LocalClient instead of a real
        chatexchange one.
        """
        self.servers = dict()
        self.email = None
        self.password = None
        self.local = local
        self.rep_check = None

    def authnz(self, email: str, password: str):
        self.email = email
        self.password = password

    def get_client_for_server(self, server: str) -> ChExClient:
        assert self.email is not None
        assert self.password is not None

        if server not in self.servers:
            assert server.startswith('chat.')
            site = server[5:]
            if self.local:
                client = LocalClient(site)
            else:
                self.rep_check = self.perform_rep_check()
                client = ChExClient(site)
            client.login(self.email, self.password)
            self.servers[server] = client
        return self.servers[server]

    def perform_rep_check(self) -> None:
        """
        Fetch Sloshy's network profile page's accounts tab
        and check that relevant accounts have enough reputation
        points to participate in chat (requires 30 rep).
        """
        if self.rep_check is not None:
            return None
        self.rep_check = RepScrape(21818820)

    def logout(self):
        """
        Log out from all the chat clients.
        """
        for server, client in self.servers.items():
            logging.info("Logging out from %s", server)
            client.logout()
            queue = client._request_queue
            while not queue.empty():
                logging.info(
                    "Waiting for %s queue to drain (%i items in queue)",
                    server, queue.qsize())
                sleep(15)
        self.servers = dict()


class Room:
    """
    Chat room with server, id, and a name for human-readable messages.
    Also, include Sloshy's chat id for this server, and a handle to a
    Chatclients object which instantiates clients as necessary.
    """
    def __init__(
            self,
            server: str,
            id: int,
            name: str,
            sloshy_id: int,
            clients: Chatclients
    ):
        self.server = server
        self.id = id
        self.name = name
        self.log_id = 'https://%s/rooms/%i' % (server, id)
        self.escaped_name = name.replace('[', r'\[').replace(']', r'\]')
        self.linked_name = '[%s](%s)' % (self.escaped_name, self.log_id)
        self.sloshy_id = sloshy_id
        self.clients = clients

        self.homeroom = False
        self.ccroom = False

        self._chatroom = None

    def set_as_home_room(self):
        self.homeroom = True

    def is_home_room(self) -> bool:
        return self.homeroom

    def set_as_cc_room(self):
        self.ccroom = True

    def is_cc_room(self):
        return self.ccroom

    def transcript_url(self) -> str:
        return 'https://%s/transcript/%i' % (self.server, self.id)

    def send_message(self, message: str) -> None:
        if self._chatroom is None:
            chat = self.clients.get_client_for_server(self.server)
            room = chat.get_room(self.id)
            room.join()
            self._chatroom = room
        else:
            room = self._chatroom
        if message:
            room.send_message(message)

    def get_sloshy_id(self) -> int:
        return self.sloshy_id


class Sloshy:
    def __init__(
            self,
            conffile=None,
            local=False,
            verbose=False,
            nodename=None,
            location_extra=None
    ):
        """
        Create a Sloshy instance by parsing the supplied YAML file.

        With local=True, don't connect to chat rooms.

        With verbose=True, emit room status messages on standard output.

        With nodename, specify a node name to display in the greeting,
        overriding whatever the configuration file says. (The default is
        the output from nodename().)

        With location_extra, specify additional location information in
        the greeting. This is intended to allow you to indicate a platform,
        like for example Github Actions or CircleCI, where the nodename
        alone is rather uninformative. (The default is None.)
        """
        self.conffile = conffile
        self.local = local
        self.verbose = verbose

        self.rooms = []
        self.homeroom = None
        self.ccrooms = []

        self.chatclients = None
        self.email = ''
        self.password = ''

        if conffile:
            self.load_conf(conffile)
        if 'SLOSHY_EMAIL' in environ:
            self.email = environ.get('SLOSHY_EMAIL')
        if 'SLOSHY_PASSWORD' in environ:
            self.password = environ.get('SLOSHY_PASSWORD')
        self.chatclients.authnz(self.email, self.password)

        if nodename is not None:
            self.config['nodename'] = nodename

        if location_extra is not None:
            self.config['location_extra'] = location_extra
            
    def load_conf(self, conffile=None):
        """
        Load YAML config from self.conffile, or the given file if specified
        """
        if conffile is None:
            assert self.conffile is not None
            conffile = self.conffile

        with open(conffile, 'r') as filehandle:
            config = yaml.safe_load(filehandle)

        warning = None

        if 'schema' not in config:
            warning = 'Config file does not contain key "schema". ' \
                ' Run with --migrate?'

        if config['schema'] != 20230827:
            warning = 'Config file uses old schema %i; run with --migrate?' % (
                config['schema'])

        if warning is not None:
            logging.error(warning)
            raise SchemaError(warning)

        assert 'servers' in config

        self.config = config
        self.rooms = []
        self.homeroom = None
        self.ccrooms = []

        if not self.local and 'local' in config:
            self.local = bool(config['local'])

        clients = Chatclients(local=self.local)
        self.chatclients = clients

        for server in self.config['servers']:
            if server in self.chatclients.servers:
                logging.warning(
                    'Skipping duplicate server %s in %s', server, conffile)
                continue

            assert 'sloshy_id' in self.config['servers'][server]
            sloshy_id = self.config['servers'][server]['sloshy_id']

            assert 'rooms' in self.config['servers'][server]
            seen = set()
            for room in self.config['servers'][server]['rooms']:
                assert 'id' in room
                assert 'name' in room
                if room['id'] in seen:
                    logging.warning(
                        'Skipping duplicate room %s:%s (%s) in %s',
                        server, room['id'], room['name'], conffile)
                    continue
                seen.add(room['id'])
                roomobj = Room(
                    server, room['id'], room['name'], sloshy_id, clients)
                self.rooms.append(roomobj)
                if 'role' in room:
                    if room['role'] == 'home':
                        assert self.homeroom is None
                        self.homeroom = roomobj
                        roomobj.set_as_home_room()
                    elif room['role'] == 'cc':
                        roomobj.set_as_cc_room()
                        self.ccrooms.append(roomobj)
        assert self.homeroom is not None

        if 'auth' in config:
            self.email = config['auth']['email']
            self.password = config['auth']['password']
            # Gripe a bit, we don't want users to embed authnz in the file
            logging.warning('Chat username and password read from config')

    def write_conf(self, config=None):
        """
        Write Sloshy's configuration, or the specified configuration,
        to self.conffile as YAML.
        """
        if config is None:
            config = self.config

        with open(self.conffile, 'w', encoding='utf-8') as newconf:
            yaml.dump(config, newconf)

    def migrate(self):
        """
        Rewrite older-format configuration file using new YAML schema.

        The meat is in the migrated_config method which reads the old
        config and returns the new format.
        """
        self.write_conf(self.migrated_config())

    def migrated_config(self):
        """
        No-op in the base class.  Subclasses should inherit and provide
        a migration path to the new base class.
        """
        warning = 'Already at the newest version of the schema %s' % (
            self.config['schema'])
        logging.error(warning)
        raise SchemaError(warning)
        # return self.config

    def nodename(self):
        """
        Produce a string which identifies where Sloshy is running,
        for the startup message in the monitoring room.

        If the configuration file contains a node name, use that;
        otherwise, return platform.node()
        """
        if 'nodename' not in self.config:
            self.config['nodename'] = platform.node()
        base_nodename = self.config['nodename']
        if 'location_extra' in self.config:
            return '%s (%s)' % (base_nodename, self.config['location_extra'])
        return base_nodename

    def generate_chat_message(self):
        """
        Output a random witty, witty unfreeze message.

        Starting with PR#23 (December 2021), include a tag to make these
        easier to search for.
        """
        return '[tag:unfreeze] ' + random.choice((
            'thaw',
            'sprinkling antifreeze',
            '!freeze',
            '♫ the heat never bothered me anyway🎶',
            'Kilr^WSloshy the Thawman was here!'))

    def send_chat_message(self, room: Room, message: str):
        """
        Send chat message.  If not self.local, sleep after sending.
        """
        assert self.chatclients is not None
        room.send_message(message)
        if not self.local:
            sleep(3)

    def startup_notice(self, room: Room, message: str):
        """
        Send a startup message to the specified room.
        The startup message has a link to the Github repo and
        includes the output from self.nodename().
        """
        self.send_chat_message(
            room, '[Sloshy](%s) startup: %s on %s' % (
                'https://github.com/tripleee/sloshy',
                message,
                self.nodename()))

    def notice(self, room: Room):
        """
        Drop a thawing notice in room
        """
        self.send_chat_message(room, self.generate_chat_message())

    def log_notice(self, message: str, log_emit=logging.info, cc: bool = False):
        """
        Emit a log message to the home room, and as a warning.
        With cc=True, also emit to cc room(s).
        """
        log_emit(message)
        self.send_chat_message(self.homeroom, message)
        if self.verbose:
            print(str(datetime.utcnow()), message)
        if cc:
            for ccroom in self.ccrooms:
                self.send_chat_message(ccroom, message)

    log_warn = lambda self, x, cc=False: self.log_notice(
            x, log_emit=logging.warning, cc=True)
    log_error = lambda self, x, cc=False: self.log_notice(
            x, log_emit=logging.error, cc=True)

    def test_rooms(self, announce=None):
        """
        Test write access in all the rooms in the configuration.

        If announce is missing / None, simply try to enter each room
        in turn, but don't post any message.

        Otherwise, check if Sloshy has already has posted a message to
        each room in turn; if we have, regard it as tested. If not,
        attempt to write the announcement message to the room in question.
        """
        fetcher = Transcript()
        counter = {'server': set(), 'id': set(), 'fail': set()}
        self.startup_notice(self.homeroom, announce or "room test")
        for room in self.rooms:
            sloshy_id = room.get_sloshy_id()
            if announce is None:
                logging.info('Joining %s', room.linked_name)
                try:
                    room.send_message("")  # just join, don't send anything
                except KeyError as exception:
                    # the immediate problem from a closed room is
                    # ...
                    #  File "./sloshy.py", line 156, in send_message
                    #    room.join()
                    #  File ".../chatexchange/rooms.py", line 50, in join
                    #   return self._client._join_room(self.id)
                    #  File ".../chatexchange/client.py", line 340, in _join_room
                    #   self._br.join_room(room_id)
                    #  File ".../chatexchange/browser.py", line 265, in join_room
                    #   eventtime = response.json()['time']
                    # KeyError: 'time'
                    self.log_error(
                        '** Error: could not join %s' % room.linked_name)
                    self.log_error(repr(exception))
                    counter['fail'].add(room.log_id)
                counter['server'].add(room.server)
                counter['id'].add(room.log_id)
                continue
            found = None
            for phrase in (
                    'tagged/unfreeze',
                    # Fall back to static search for keywords in legacy notices
                    'thaw', 'antifreeze', 'freeze', 'heat', 'thawman'):
                try:
                    found = fetcher.search(
                        room.server, room.id, sloshy_id, phrase)
                except RequestException as exception:
                    self.log_error(
                        '** Error: could not fetch transcript for %s'
                        % room.linked_name)
                    self.log_error(repr(exception))
                    counter['fail'].add(room.log_id)
                    break
                if found:
                    logging.info('Found: %s', found)
                    break
                # Sleeps established experimentally
                # The site starts emitting 409 errors if we go too fast
                # but it's not really clear what it regards as too fast
                logging.info('Sleeping between searches ...')
                sleep(3)
            logging.info('Sleeping between searches ...')
            sleep(3)
            if not found:
                try:
                    self.send_chat_message(room, '[tag:unfreeze] %s' % announce)
                except KeyError as exception:
                    self.log_error(
                        '** Error: could not announce presence in %s'
                        % room.linked_name)
                    self.log_error(repr(exception))
                    counter['fail'].add(room.log_id)
                    continue
                self.log_notice(
                    'announced presence in %s' % room.linked_name, cc=True)
        if announce is None:
            self.log_notice(
                'scanned %i rooms on %i servers' % (
                    len(counter['id']), len(counter['server'])))
        if len(counter['fail']) > 0:
            raise ValueError('failed to process rooms %s' % counter['fail'])

    def scan_rooms(self, startup_message=None):
        """
        Main entry point for scanning: Visit room transcripts,
        check if they are in danger of being frozen; if so, join
        and post a message.

        The startup_message is included in the notification in the
        monitoring room when Sloshy starts up.
        If it is empty, missing, or None, it defaults to "manual run".
        """
        if not startup_message:
            startup_message = "manual run"

        now = datetime.now()
        failures = set()

        # Default freeze schedule is 14 days; thaw a little before that,
        # just to be on the safe side.
        if 'threshold' in self.config:
            if isinstance(self.config['threshold'], str):
                maxage = timedelta(*tuple(
                    int(x.strip())
                    for x in self.config['threshold'].split(",")))
            else:
                maxage = timedelta(self.config['threshold'])
        else:
            maxage = timedelta(**DEFAULT_MAX_AGE)

        max_aggressive_age = timedelta(**DEFAULT_AGGRESSIVE_MAX_AGE)

        fetcher = Transcript()
        homeroom = self.homeroom
        self.startup_notice(homeroom, startup_message)
        for room in self.rooms:
            if room.is_home_room() and 'scan_homeroom' not in self.config:
                continue
            try:
                room_latest = fetcher.latest(room.id, room.server)
            except (TranscriptFrozenDeletedException, RequestException
                    ) as exception:
                self.log_error(
                    '** Error: could not fetch transcript for %s'
                    % room.linked_name)
                self.log_error(repr(exception))
                failures.add(room.log_id)
                continue
            if room_latest:
                when = room_latest['when']
                age = now-when
                # Trim microseconds
                age = age - timedelta(microseconds=age.microseconds)
                msg = '[%s](%s): latest activity %s (%s hours ago)' % (
                    room.escaped_name, room_latest['url'], when, age)
            else:
                msg = '[%s](%s): no non-feed, non-admin activity ever' % (
                        room.escaped_name, room.transcript_url())
                age = maxage + timedelta(days=1)
            self.log_notice(msg)
            quiet = False
            if age <= maxage and age > max_aggressive_age:
                activity = fetcher.usercount(
                    room.id, room.server, userlimit=2,
                    messagelimit=AGGRESSIVE_MAX_MSG_THRESHOLD)
                quiet = not activity
            if age > maxage or (quiet and age > max_aggressive_age):
                try:
                    self.notice(room)
                    self.log_notice(
                        'Age threshold exceeded; sending a%s thawing notice '
                        'to %s' % ('' if age>maxage else 'n expedited',
                        room.linked_name), cc=True)
                except ChatActionError as err:
                    self.log_error(
                        '%s: Age threshold exceeded, but failed to thaw: %s'
                        % (room.linked_name, err))
                    failures.add(room.id)

        if failures:
            raise ValueError('Failed to process %i rooms: %s' % (
                len(failures), failures))

    def perform_scan(self, startup_message=None):
        """
        Entry point for a full scan: Perform room scan, then logout().

        If startup_message is given, provide this as the identifying message
        for Sloshy.
        """
        try:
            self.scan_rooms(startup_message)
        except Exception as exception:
            raise
        finally:
            self.chatclients.logout()


class SloshyLegacyConfig20211215(Sloshy):
    """
    Child class with the original configuration file processing
    and a migration method for updating to the new format.

    This actually now returns the 20230827 schema but the only
    difference is the support for "role: cc" which simply didn't
    exist in the earlier schemas, so we do not write it anywhere
    when migrating.
    """
    def load_conf(self, conffile=None):
        """
        Load YAML config from self.conffile, or the given file if specified
        """
        if conffile is None:
            assert self.conffile is not None
            conffile = self.conffile

        with open(conffile, 'r') as filehandle:
            config = yaml.safe_load(filehandle)
        assert 'rooms' in config

        self.config = config
        self.rooms = []
        self.homeroom = None

        if not self.local and 'local' in config:
            self.local = bool(config['local'])

        clients = Chatclients(local=self.local)
        self.chatclients = clients

        for item in self.config['rooms']:
            for server, rooms in item.items():
                if server in self.chatclients.servers:
                    logging.warning(
                        'Duplicate server %s in %s', server, conffile)
                seen = set()
                for idx in range(len(item[server])):
                    room = item[server][idx]
                    assert 'id' in room
                    assert 'name' in room
                    if room['id'] in seen:
                        logging.warning(
                            'Skipping duplicate room %s:%s (%s) in %s',
                            server, room['id'], room['name'], conffile)
                        continue
                    seen.add(room['id'])
                    roomobj = Room(server, room['id'], room['name'], clients)
                    self.rooms.append(roomobj)
                    if 'role' in room and room['role'] == 'home':
                        assert self.homeroom is None
                        self.homeroom = roomobj
                        roomobj.set_as_home_room()
        assert self.homeroom is not None

        if 'auth' in config:
            self.email = config['auth']['email']
            self.password = config['auth']['password']
            # Gripe a bit, we don't want users to embed authnz in the file
            logging.warning('Chat username and password read from config')

    def migrated_config(self):
        # Stupidly hard-code information which should be in the config
        sloshy_id = {
            'chat.stackoverflow.com': 16115299,
            'chat.stackexchange.com': 514718,
            'chat.meta.stackexchange.com': 1018361
        }
        servers = []
        for serverdict in self.config['rooms']:
            servers.extend(serverdict.keys())

        for server in servers:
            if server in sloshy_id:
                continue
            logging.warning(
                'Server %s not known to migration code - abort', server)
        assert all(x in sloshy_id for x in servers)

        serverconfigs = dict()
        for serverdict in self.config['rooms']:
            for server in serverdict.keys():
                serverconfigs[server] = {
                    'sloshy_id': sloshy_id[server],
                    'rooms': serverdict[server]
                }

        return {'schema': 20230827, 'servers': serverconfigs}


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        '--migrate', action='store_true',
        help='Migrate config from old schema to the current one, then exit.')
    parser.add_argument(
        '--announce',
        help='Announce presence in any rooms where Sloshy has not appeared,'
            ' then exit. Requires announcement string as argument.')
    parser.add_argument(
        '--test-rooms', action='store_true',
        help='Test access to rooms without announcing presence, then exit.')
    parser.add_argument(
        '--local', action='store_true',
        help='Run locally; do not emit chat messages.')
    parser.add_argument(
        '--verbose', action='store_true',
        help='Emit room status messages on standard output.')
    parser.add_argument(
        '--loglevel', default='info',
        help='Logging level: debug, info (default), warning, error')
    parser.add_argument(
        '--nodename',
        help='Specify nodename for Sloshy (overrides config file)')
    parser.add_argument(
        '--location_extra',
        help='Provide additional context for location (like Github/CircleCI)')
    parser.add_argument(
        'conffile', nargs='?', default='',
        help='Configuration file for Sloshy. Default is sloshy.yaml for'
            ' regular run, test.yaml for --test-rooms')
    parser.add_argument(
        'startup_message', nargs='?', default=None,
        help='Message to display in the home room when starting up'
            ' (default: "manual run").')

    args = parser.parse_args()

    logging.basicConfig(level={
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "error": logging.ERROR
        }[args.loglevel])

    if args.migrate:
        SloshyLegacyConfig20211215(args.conffile or "sloshy.yaml").migrate()
        exit(0)

    conffile = args.conffile or "test.yaml"
    me = Sloshy(
        conffile, local=args.local, verbose=args.verbose,
        nodename=args.nodename, location_extra=args.location_extra)
    if args.announce or args.test_rooms:
        if args.local:
            raise ValueError(
                '--local is incompatible with --announce and --test-rooms')
        if args.announce and args.test_rooms:
            raise ValueError(
                '--announce and --test-rooms are mutually exclusive')
        me.test_rooms(args.announce)
    else:
        me.perform_scan(args.startup_message)


if __name__ == '__main__':
    main()
