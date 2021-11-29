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

from scrape_chat import Transcript


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
        print(message)

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
                client = ChExClient(site)
            client.login(self.email, self.password)
            self.servers[server] = client
        return self.servers[server]

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
    Also, handle to a Chatclients object which instantiates clients
    as necessary.
    """
    def __init__(self, server: str, id: int, name: str, clients: Chatclients):
        self.server = server
        self.id = id
        self.name = name
        self.clients = clients

        self.homeroom = False

        self._chatroom = None

    def set_as_home_room(self):
        self.homeroom = True

    def is_home_room(self) -> bool:
        return self.homeroom

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
        room.send_message(message)


class Sloshy:
    def __init__(self, conffile=None, local=False):
        """
        Create a Sloshy instance by parsing the supplied YAML file.

        With local=True, don't connect to chat rooms.
        """
        self.conffile = conffile
        self.local = local

        self.rooms = []
        self.homeroom = None
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

    def nodename(self):
        """
        Produce a string which identifies where Sloshy is running,
        for the startup message in the monitoring room.

        If the configuration file contains a node name, use that;
        otherwise, return platform.node()
        """
        if 'nodename' not in self.config:
            self.config['nodename'] = platform.node()
        return self.config['nodename']

    def generate_chat_message(self):
        """
        Output a random witty, witty unfreeze message
        """
        return random.choice((
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

    def notice(self, room: Room):
        """
        Drop a thawing notice in room
        """
        self.send_chat_message(room, self.generate_chat_message())

    def scan_rooms(self, startup_message=None):
        """
        Main entry point for scanning: Visit room transcripts,
        check if they are in danger of being frozen; if so, join
        and post a message.

        The startup_message is included in the notification in the
        monitoring room when Sloshy starts up.
        If it is missing or None, it defaults to "manual run".
        """
        if not startup_message:
            startup_message = "manual run"

        now = datetime.now()

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
            maxage = timedelta(days=12)

        fetcher = Transcript()
        homeroom = self.homeroom
        self.send_chat_message(
            homeroom, '[Sloshy](%s) startup: %s on %s' % (
                'https://github.com/tripleee/sloshy',
                startup_message,
                self.nodename()))
        for room in self.rooms:
            if room.is_home_room() and 'scan_homeroom' not in self.config:
                continue
            room_latest = fetcher.latest(room.id, room.server)
            if room_latest:
                when = room_latest['when']
                age = now-when
                # Trim microseconds
                age = age - timedelta(microseconds=age.microseconds)
                msg = '[%s](%s): latest activity %s (%s hours ago)' % (
                    room.name, room_latest['url'], when, age)
            else:
                msg = '[%s](%s): no non-feed, non-admin activity ever' % (
                        room.name, room.transcript_url())
                age = maxage + 1
            self.send_chat_message(homeroom, msg)
            logging.info(msg)
            if age > maxage:
                try:
                    self.notice(room)
                    self.send_chat_message(
                        homeroom, '%s: Age threshold exceeded;'
                        ' sending a thawing notice' % room.name)
                except ChatActionError as err:
                    self.send_chat_message(
                        homeroom, '%s: Age threshold exceeded,'
                        ' but failed to thaw: %s' % err)

    def perform_scan(self, startup_message=None):
        """
        Entry point for a single scan: Perform scan_rooms, then logout().
        """
        self.scan_rooms(startup_message)
        self.chatclients.logout()


def main():
    from sys import argv
    logging.basicConfig(level=logging.INFO)
    Sloshy(argv[1] if len(argv) > 1 else "test.yaml").perform_scan(
        argv[2] if len(argv) > 2 else None)


if __name__ == '__main__':
    main()
