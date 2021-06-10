"""
Simple client for fetching latest activity in a chat room
"""

from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup


def room_transcript(room: int, server: str):
    """
    Fetch transcript of messages from room on server
    """
    assert isinstance(room, int)
    room = int(room)
    url = "https://%s/transcript/%i" % (server, room)
    response = requests.get(url)
    return url, response.text


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
    url, transcript = room_transcript(room, server)
    soup = BeautifulSoup(transcript, 'html.parser')

    title = soup.title.string
    assert ' - ' in title
    datestr = title.rsplit(' - ', 1)[-1]
    date = datetime.strptime(datestr, '%Y-%m-%d')

    final = soup.body.find_all("div", {"class": "monologue"})[-1]

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
    for room in (6, 291, 109494):  # python, rebol, friendly bin
        info = latest(room, "chat.stackoverflow.com")
        print(info)


if __name__ == '__main__':
    main()
