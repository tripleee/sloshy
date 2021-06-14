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
import chatexchange.client

from scrape_chat import Transcript


class LocalClient:
    """
    Simple mock ChatExchange.client with no actual networking functionality
    """
    def __init__(self, host='stackexchange.com', email=None, password=None):
        self.host = host
        self.email = email
        self.password = password

        self.room = None

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

    def get_client_for_server(self, server: str) -> chatexchange.client.Client:
        assert self.email is not None
        assert self.password is not None

        if server not in self.servers:
            assert server.startswith('chat.')
            site = server[5:]
            if self.local:
                client = LocalClient(site)
            else:
                client = chatexchange.client.Client(site)
            client.login(self.email, self.password)
            self.servers[server] = client
        return self.servers[server]


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

        clients = Chatclients(local=self.local)
        self.chatclients = clients

        for item in self.config['rooms']:
            for server, rooms in item.items():
                for idx in range(len(item[server])):
                    room = item[server][idx]
                    assert 'id' in room
                    assert 'name' in room
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

    def scan_rooms(self, startup_message="manual run"):
        """
        Main entry point for scanning: Visit room transcripts,
        check if they are in danger of being frozen; if so, join
        and post a message.

        The startup_message is included in the notification in the
        monitoring room when Sloshy starts up.
        """
        now = datetime.now()
        # Freeze schedule is 14 days; thaw a little before that,
        # just to be on the safe side.
        maxage = timedelta(days=12)

        fetcher = Transcript()
        homeroom = self.homeroom
        self.send_chat_message(
            homeroom, '[Sloshy](%s) %s on %s' % (
                'https://github.com/tripleee/sloshy',
                startup_message,
                self.nodename()))
        for room in self.rooms:
            if room.is_home_room():
                continue
            room_latest = fetcher.latest(room.id, room.server)
            when = room_latest['when']
            age = now-when
            msg = '[%s](%s): latest activity %s (%s ago)' % (
                room.name, room_latest['url'], when, age)
            self.send_chat_message(homeroom, msg)
            logging.info(msg)
            if age > maxage:
                self.notice(room)
                self.send_chat_message(
                    homeroom,
                    '%s: Age threshold exceeded; sending a thawing notice' % (
                        room.name))


def main():
    logging.basicConfig(level=logging.INFO)
    Sloshy("test.yaml", local=True).scan_rooms()


if __name__ == '__main__':
    main()
