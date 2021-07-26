"""
Simple client for fetching latest activity in a chat room
"""

from datetime import datetime
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

    def fetch(
            self, server: str, room: int,
            fallback_sleep: int = 1
    ) -> tuple:  # TODO: better typing?
        """
        Generator to retrieve increasingly old room transcripts from server
        and extract the .text component as a BeautifulSoup object, and the
        URL it was fetched from.

        On each fetch, send the User-Agent: header of this client.

        Optionally sleep before fetching an older page; the fallback_sleep
        integer argument controls this.
        """
        url = "https://%s/transcript/%i" % (server, room)
        while True:
            logging.info('Fetching %s', url)
            transcript = requests.get(
                url, headers={'User-Agent': __class__.UA}).text
            soup = BeautifulSoup(transcript, 'html.parser')

            yield soup, url

            trans = soup.body.find("div", {"id": "transcript"})
            assert trans is not None
            # assert trans.text.strip() == "no messages today"
            main = soup.body.find("div", {"id": "main"})
            url = 'https://%s%s' % (
                server, main.find("a", {"rel": "prev"})['href'])
            logging.info('No messages, falling back to %s', url)
            sleep(fallback_sleep)

    def messages(self, server: str, room: int) -> dict:
        """
        Generator to retrieve increasingly old messages from the room's
        transcript.

        Yield a dict with a representation of the extracted message.
        """
        for soup, url in self.fetch(server, room):
            title = soup.title.string
            assert ' - ' in title
            # Title sometimes contains ' (page 1 of 2)' after date
            title = title.split(' (page ')[0]
            datestr = title.rsplit(' - ', 1)[-1]
            date = datetime.strptime(datestr, '%Y-%m-%d')

            monologue = soup.body.find_all("div", {"class": "monologue"})
            for message in reversed(monologue):
                when = message.find("div", {"class": "timestamp"})
                if when:
                    time = datetime.strptime(when.text, "%I:%M %p").time()
                else:
                    time = datetime(1970, 1, 1).time()

                userdiv = message.find("div", {"class": "username"})
                try:
                    # <div class="username">
                    # <a href="/users/3735529/smokedetector"
                    #    title="SmokeDetector">SmokeDetector</a></div>
                    user = userdiv.a['href'].split('/')
                    username = user[-1]
                    userid = int(user[-2])
                except TypeError:
                    # <div class="username">user12716323</div>
                    username = userdiv.text
                    if username.startswith('user'):
                        try:
                            userid = int(username[4:])
                        except ValueError:
                            userid = 0

                yield {
                    'server': server,
                    'room': room,
                    'url': url,
                    'when': datetime.combine(date, time),
                    'user': {
                        'name': username,
                        'id': userid
                        },
                    'msg': message.find(
                        "div", {"class": "content"}).text.strip(),
                    'link': url
                }

    def latest(self, room: int, server: str) -> dict:
        """
        Fetch latest message from room on server. Return a dict of
        {'server': server, 'room': room, 'url': url, 'when': datetime,
         'user': {'name': str, 'id': int}, 'msg': str, 'link': str}
        The 'msg' member is the actual message; the 'link' is its permalink.
        The 'server' and 'room' members are simply copied from the input.
        The 'url' is the address of the transcript page we fetched and scraped.

        Skip any negative user id:s, as those are feed messages which do
        not count as actual activity.
        """
        assert isinstance(room, int)
        room = int(room)

        for message in self.messages(server, room):
            if message['user']['id'] < 0:
                continue
            return message


def main():
    fetcher = Transcript()
    for room in (6, 291, 109494, 228186):  # python, rebol, friendly bin, git
        info = fetcher.latest(room, "chat.stackoverflow.com")
        print(info)
    for room in (109983, 117114):
        info = fetcher.latest(room, "chat.stackexchange.com")
        print(info)


if __name__ == '__main__':
    main()
