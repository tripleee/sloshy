"""
Simple async client for fetching latest activity in a chat room
"""

from datetime import datetime, timedelta
import asyncio

import aiohttp
from bs4 import BeautifulSoup


async def room_transcript(room: int, server: str):
    """
    Fetch transcript of messages from room on server
    """
    assert isinstance(room, int)
    room = int(room)
    url = "https://%s/transcript/%i" % (server, room)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def latest(room: int, server: str):
    """
    Fetch latest message from room on server. Return a dict of
    {'server': server, 'room': room, 'when': datetime,
     'user': {'name': str, 'id': int}, 'msg': str, 'link': str}
    The 'msg' member is the actual message; the 'link' is its permalink.
    The 'server' and 'room' members are simply copied from the input.
    """
    assert isinstance(room, int)
    room = int(room)
    transcript = await room_transcript(room, server)
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
    
async def main():
    for room in (6, 291, 109494):  # python, rebol, friendly bin
        info = await latest(room, "chat.stackoverflow.com")
        print(info)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
