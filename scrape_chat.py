"""
Simple client for fetching latest activity in a chat room
"""

from datetime import datetime, timedelta
from time import sleep
import platform
import logging

import requests
from bs4 import BeautifulSoup


class Transcript:
    """
    Simple wrapper for fetching the transcript of a room.
    """
    UA = "SloshyBot/0.1 (+%s) Python/%s Requests/%s" % (
        "https://github.com/tripleee/sloshy",
        platform.python_version(),
        requests.__version__)

    def fetch(self, url: str, fallback_sleep: int = 1) -> BeautifulSoup:
        """
        Retrieve URL and return the .text component as a BeautifulSoup object.
        Send the User-Agent: header of this client.

        If the current transcript is empty, optionally sleep before fetching
        an older page; the fallback_sleep integer argument controls this.
        """
        while True:
            logging.info('Fetching %s', url)
            transcript = requests.get(
                url, headers={'User-Agent': __class__.UA}).text
            soup = BeautifulSoup(transcript, 'html.parser')
            if soup.body.find_all("div", {"class": "monologue"}):
                break
            else:
                trans = soup.body.find("div", {"id": "transcript"})
                assert trans is not None
                assert trans.text.strip() == "no messages today"
                main = soup.body.find("div", {"id": "main"})
                url = 'https://%s%s' % (
                    server, main.find("a", {"rel": "prev"})['href'])
                logging.info('No messages, falling back to %s', url)
                sleep(fallback_sleep)
        return soup

    def latest(self, room: int, server: str) -> dict:
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
        soup = self.fetch(url)

        title = soup.title.string
        assert ' - ' in title
        datestr = title.rsplit(' - ', 1)[-1]
        date = datetime.strptime(datestr, '%Y-%m-%d')

        # TODO maybe return this from fetch() too?
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
    fetcher = Transcript()
    for room in (6, 291, 109494, 228186):  # python, rebol, friendly bin, git
        info = fetcher.latest(room, "chat.stackoverflow.com")
        print(info)


if __name__ == '__main__':
    main()
