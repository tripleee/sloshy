#!/usr/bin/env python3

import platform
import re
from sys import argv, exit, stderr

import requests

from sloshy import Sloshy


def resolve_room(room_url: str) -> (str, int):
    """
    Given a room profile URL, parse out and return the chat server and room ID.
    """
    assert room_url.startswith('https://')
    assert '/rooms/' in room_url
    parts = room_url[8:].split('/rooms/')
    return parts[0], int(parts[1].split('/')[0])


def get(url: str) -> requests.Response:
    """
    Wrapper to pass a custom user agent
    """
    UA = "SloshyBot/0.1 (+%s) Python/%s Requests/%s" % (
        "https://github.com/tripleee/sloshy",
        platform.python_version(),
        requests.__version__)
    return requests.get(url, headers={'User-Agent': UA})


def resolve_user(user_url: str) -> (int, str):
    """
    Given a user profile URL, chase the network profile and parse it
    to return the user ID and display name.
    """
    assert user_url.startswith('https://')
    assert '/users/' in user_url

    profile = get(user_url)
    title = profile.text.split('<title>')[1].split('</title>')[0]
    assert title.startswith('User ')
    title = title[5:]
    display_name = title.rsplit(' - ', 1)[0]

    if not user_url.startswith('https://stackexchange.com/'):
        network_url_candidates = re.findall(
            r'''https://stackexchange.com/users/\d+(?:/[^<>'"\s]+)?''',
            profile.text)
        network_url = list(filter(
            lambda x: '?' not in x, network_url_candidates))
        assert len(network_url) == 1
        user_url = network_url[0]

    parts = user_url[8:].split('/users/')
    user_id = int(parts[1].split('/')[0])

    return user_id, display_name


def update_yaml_config(sloshy: Sloshy, newroom: dict):
    sloshy.config['servers'][chatserver]['rooms'].append(newroom)
    sloshy.write_conf()


def test_config(sloshy: Sloshy, chatserver: str, newroom: dict):
    # Minimize the config for room test
    del_servers = []
    for server in sloshy.config['servers']:
        if server != chatserver:
            del_servers.append(server)
    for server in del_servers:
        del sloshy.config['servers'][server]

    sloshy.config['servers'][chatserver]['rooms'] = [newroom]

    homeroom = {
        'contact': 'tripleee (468289)',
        'id': 233626,
        'name': 'Sloshy the Thawman',
        'role': 'home'
    }
    if chatserver != 'chat.stackoverflow.com':
        sloshy.config['servers']['chat.stackoverflow.com']['rooms'] = []
    sloshy.config['servers']['chat.stackoverflow.com']['rooms'].append(newroom)

    sloshy.test_rooms()

    
me = argv[0].split('/')[-1]

if len(argv) not in (4, 5):
    print(
        f'Usage: {me} room-url "room description" user-url ["user name"]',
        file=stderr)
    exit(1)

chatserver, room_id = resolve_room(argv[1])
user_id, user_name = resolve_user(argv[3])
if len(argv) == 5 and argv[4]:
    user_name = argv[4]

newroom = {
    'contact': f'{user_name} ({user_id})',
    'id': room_id,
    'name': argv[2]
}

sloshy = Sloshy(conffile='sloshy.yaml')
assert room_id not in [
    x['id'] for x in sloshy.config['servers'][chatserver]['rooms']]

update_yaml_config(sloshy, newroom)
test_config(sloshy, chatserver, newroom)
