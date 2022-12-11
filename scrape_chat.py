"""
Simple client for fetching latest activity in a chat room
"""

from datetime import datetime
from time import sleep
import platform
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup


class TranscriptException(Exception):
    """
    Base class for transcript errors
    """
    ...


class TranscriptFrozenDeletedException(TranscriptException):
    """
    Exception thrown when a room is frozen or deleted
    """
    ...


class Transcript:
    """
    Simple wrapper for fetching the transcript of a room.
    """
    UA = "SloshyBot/0.1 (+%s) Python/%s Requests/%s" % (
        "https://github.com/tripleee/sloshy",
        platform.python_version(),
        requests.__version__)

    def _get_requests_soup(self, url: str) -> BeautifulSoup:
        """
        Simple wrapper to set the User-Agent: correctly and fetch a page,
        then return the BeautifulSoup parse of the result.
        """
        result = requests.get(url, headers={'User-Agent': self.UA})
        result.raise_for_status()
        return BeautifulSoup(result.text, 'html.parser')

    def fetch(
            self, server: str, room: int,
            fallback_sleep: int = 1
    ) -> tuple:  # TODO: better typing?
        """
        Generator to retrieve increasingly old room transcripts from server
        and extract the .text component as a BeautifulSoup object, and the
        URL it was fetched from.

        Optionally sleep before fetching an older page; the fallback_sleep
        integer argument controls this.
        """
        url = "https://%s/transcript/%i" % (server, room)
        while True:
            logging.info('Fetching %s', url)
            soup = self._get_requests_soup(url)
            yield soup, url

            trans = soup.body.find("div", {"id": "transcript"})
            assert trans is not None
            # assert trans.text.strip() == "no messages today"
            main = soup.body.find("div", {"id": "main"})
            prev = main.find("a", {"rel": "prev"})
            if not prev:
                break
            url = 'https://%s%s' % (server, prev['href'])
            logging.info('No messages, falling back to %s', url)
            sleep(fallback_sleep)

    def messages(self, server: str, room: int) -> dict:
        """
        Generator to retrieve increasingly older messages from the room's
        transcript.

        Yield a dict with a representation of the extracted message.

        {'server': server, 'room': room, 'url': url, 'when': datetime,
         'user': {'name': str, 'id': int}, 'msg': str, 'link': str}

        The 'msg' member is the actual message; the 'link' is its permalink.
        The 'server' and 'room' members are simply copied from the input.
        The 'url' is the address of the transcript page we fetched and scraped.
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

    def check_frozen_or_deleted(self, server: str, room: int) -> bool:
        """
        Raise an exception if the room's info page says it's frozen or deleted
        """
        # https://chat.stackexchange.com/rooms/info/140197/hnq-operations-research?tab=feeds
        # https://chat.stackexchange.com/rooms/info/111121/modeling-questions-related-to-chemistry?tab=feeds

        url = "https://%s/rooms/info/%i/?tab=feeds" % (server, room)
        soup = self._get_requests_soup(url)

        if 'Currently no feeds are being posted into this room.' in soup.text:
            return False
        for candidate in ('Because this room is deleted, no feeds are'
                          ' being posted into this room.',
                          'Because this room is frozen, no feeds are'
                          ' being posted into this room.'):
            if candidate in soup.text:
                raise TranscriptFrozenDeletedException(candidate)
        return False

    def usercount(
            self,
            room: int,
            server: str,
            userlimit: int=1,
            messagelimit: int=1,
            skip_system_messages: bool=True
    ):
        """
        Fetch latest messages from room on server. Stop when the unique
        user count reaches the limit, though always return at least as
        many messages as specified by messagelimit, if available.
        Optionally, skip system messages (where the user id < 0).

        Return the sequence of messages as a list of dicts, newest first,
        each as described in the `messages` method's docstring.
        """
        assert isinstance(room, int)
        room = int(room)

        self.check_frozen_or_deleted(server, room)

        messages = []
        users = set()
        for message in self.messages(server, room):
            userid = message['user']['id']
            if userid < 0 and skip_system_messages:
                continue
            messages.append(message)
            if userid not in users:
                users.add(userid)
            if len(users) >= userlimit and len(messages) >= messagelimit:
                return messages
            print(f"# {len(messages)} messages, {len(users)} users")

    def latest(self, room: int, server: str) -> dict:
        """
        Fetch latest message from room on server. Return a dict like
        the one produced by the `messages` method.

        Skip any negative user id:s, as those are feed messages which do
        not count as actual activity.
        """
        return self.usercount(room, server, userlimit=1, messagelimit=1)[0]

    def search(
            self, server: str, room: int, user: int, phrase: str
    ) -> Optional[str]:
        """
        Search room on server for posts by user containing phrase.
        Return the URL where the newest post was found, or None if it wasn't.
        """
        logging.info(
            'Searching for %s by user %i in room %s:%i',
            phrase, user, server, room)
        url = 'https://%s/search?q=%s&user=%i&room=%i' % (
            server, requests.utils.quote(phrase, safe=''), user, room)
        found = self._get_requests_soup(url)
        content = found.body.find("div", {"id": "content"})
        if '\n0 messages found' in content.text:
            return None
        messages = content.find("div", {"class": "messages"})
        return 'https://%s%s' % (server, messages.find("a")['href'])


def main():
    fetcher = Transcript()
    for room in (6, 291, 109494, 228186):  # python, rebol, friendly bin, git
        info = fetcher.latest(room, "chat.stackoverflow.com")
        print(info)
    for room in (109983, 117114):
        info = fetcher.latest(room, "chat.stackexchange.com")
        print(info)
    """
    # Really slow, will scroll all the way back to 2016
    for room in (111347,): # SObotics
    """
    for room in (233626,):
        for message in fetcher.messages("chat.stackoverflow.com", room):
            print(message)


if __name__ == '__main__':
    main()
