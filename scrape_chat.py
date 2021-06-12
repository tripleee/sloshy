"""
Simple client for fetching latest activity in a chat room
"""

from datetime import datetime, timedelta
from time import sleep
import logging

import requests
from bs4 import BeautifulSoup


def latest(room: int, server: str):
    """
    Fetch latest message from room on server. Return a dict of
    {'server': server, 'room': room, 'url': url, 'when': datetime,
     'user': {'name': str, 'id': int}, 'msg': str, 'link': str}
    The 'msg' member is the actual message; the 'link' is its permalink.
    The 'server' and 'room' members are simply copied from the input.
    The 'url' is the address of the transcript page we fetched and scraped.
    """
    assert isinstance(room, int)
    room = int(room)
    url = "https://%s/transcript/%i" % (server, room)

    while True:
        logging.info('Fetching %s', url)
        print('fetching %s' % url)
        transcript = requests.get(url).text
        soup = BeautifulSoup(transcript, 'html.parser')
        mono = soup.body.find_all("div", {"class": "monologue"})
        if mono:
            final = mono[-1]
            break
        else:
            trans = soup.body.find("div", {"id": "transcript"})
            assert trans is not None
            assert trans.text.strip() == "no messages today"
            main = soup.body.find("div", {"id": "main"})
            url = 'https://%s%s' % (
                server, main.find("a", {"rel": "prev"})['href'])
            logging.info('No messages, falling back to %s', url)
            print('falling back to', url)
            sleep(1)

    title = soup.title.string
    assert ' - ' in title
    datestr = title.rsplit(' - ', 1)[-1]
    date = datetime.strptime(datestr, '%Y-%m-%d')

    when = final.find("div", {"class": "timestamp"})
    if when:
        time = datetime.strptime(when.text, "%I:%M %p").time()
    else:
        time = datetime(1970, 1, 1).time()

    user = final.find("div", {"class": "username"}).a['href'].split('/')
    result = {
        'server': server,
        'room': room,
        'url': url,
        'when': datetime.combine(date, time),
        'user': {
            'name': user[-1],
            'id': int(user[-2])
            },
        'msg': final.find("div", {"class": "content"}).text.strip(),
        'link': '//%s%s' % (
            server, final.find("div", {"class": "message"}).a['href'])
    }
    return result


def main():
    for room in (6, 291, 109494, 228186):  # python, rebol, friendly bin, git
        info = latest(room, "chat.stackoverflow.com")
        print(info)


if __name__ == '__main__':
    main()
