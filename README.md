# Sloshy the Thawman

This is a simple Stack Overflow / Stack Exchange chat bot
which keeps an eye on a selected list of rooms,
and makes sure they are not frozen.

The threshold is currently set to 12 days since the previous message,
to leave some leeway for possible accidents
(the freeze happens after 14 days of inactivity).

There is no interactive interface to the bot;
create a pull request if you would like to add a room
to Sloshy's watch list.
The YAML configuration file should hopefully be
reasonably self-explanatory
(save perhaps for the "home" role, which selects a room
for Sloshy to report his activities into;
please don't touch that).

In brief, if your chatroom's URL is
https://chat.stackexchange.com/rooms/12345/my-room,
you would have
```
rooms:
 - chat.stackexchange.com:
   - name: "my room's name"
     id: 12345
```
in the configuration file.
(This is showing the complete YAML structure;
the `rooms` top-level key obviously already exists,
and it is likely that `chat.stackexchange.com`
will be added if it is not already there by the time you read this.
Perhaps notice that there are two chat servers
with very similar names,
where one contains "overflow" and the other contains "exchange".)

The `name` key is not important,
it just determines what Sloshy displays
in its status message
when it visits the room.
Only the server name and the `id` matters
for actually identifying the room.


## Deploy

There is a simple Github Action which runs nightly.


## Bot Profiles

* [Main profile](https://stackoverflow.com/users/16115299/sloshy)
* [Chat profile](https://chat.stackoverflow.com/users/16115299/sloshy)


## Author

tripleee
