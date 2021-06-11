"""
Sloshy the Thawman - main class
"""

from datetime import datetime, timedelta
from os import environ
import random
from time import sleep
import logging

import yaml
import chatexchange.client

from scrape_chat import latest


class Sloshy:
    def __init__(self, conffile=None):
        self.conffile = conffile
        self.rooms = dict()
        self.chatclient = dict()
        self.email = ''
        self.password = ''
        self.homeroom = None
        if conffile:
            self.load_conf(conffile)
        if 'SLOSHY_EMAIL' in environ:
            self.email = environ.get('SLOSHY_EMAIL')
        if 'SLOSHY_PASSWORD' in environ:
            self.password = environ.get('SLOSHY_PASSWORD')

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

        self.rooms = config['rooms']

        homeroom = None
        for server, room in self.traverse_rooms():
            assert 'id' in room
            assert 'name' in room
            if 'role' in room and room['role'] == 'home':
                assert homeroom is None
                homeroom = (server, room['id'])
        assert homeroom is not None
        self.homeroom = homeroom

        if 'auth' in config:
            self.email = config['auth']['email']
            self.password = config['auth']['password']
            # Gripe a bit, we don't want users to embed authnz in the file
            logging.warning('Chat username and password read from config')

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

    def traverse_rooms(self):
        """
        Loop over room structure; yield one (server, room) tuple at a time
        """
        for item in self.rooms:
            for server, rooms in item.items():
                for idx in range(len(item[server])):
                    room = item[server][idx]
                    yield server, room

    def chat(self, server, room):
        """
        Establish a chat client connected to room on server
        """
        assert isinstance(room, int)
        if server not in self.chatclient:
            assert server.startswith('chat.')
            site = server[5:]
            client = chatexchange.client.Client(site)
            client.login(self.email, self.password)
            self.chatclient[server] = client
        else:
            client = self.chatclient[server]

        room = client.get_room(room)
        room.join()
        return room

    def notice(self, server, room):
        """
        Drop a thawing notice in room on server
        """
        chat = self.chat(server, room)
        chat.send_message(self.generate_chat_message())
        sleep(3)

    def scan_rooms(self):
        """
        Main entry point for scanning: Visit room transcripts,
        check if they are in danger of being frozen; if so, join
        and post a message.
        """
        chat = self.chat(*self.homeroom)

        now = datetime.now()
        # Freeze schedule is 14 days; thaw a little before that,
        # just to be on the safe side.
        maxage = timedelta(days=12)

        for server, room in self.traverse_rooms():
            if 'role' in room and room['role'] == 'home':
                continue
            room_latest = latest(room['id'], server)
            when = room_latest['when']
            age = now-when
            msg = '%s (%s): %s (%s)' % (
                room['name'], room_latest['url'], when, age)
            chat.send_message(msg)
            logging.info(msg)
            room['latest'] = room_latest
            if age > maxage:
                self.notice(server, room['id'])
                chat.send_message(
                    '%s: Age threshold exceeded; sending a thawing notice' % (
                        room['name']))
                sleep(3)
            sleep(3)
