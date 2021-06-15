# Sloshy the Thawman


![Build status badge][1]

  [1]: https://github.com/tripleee/sloshy/actions/workflows/test-pushed.yml/badge.svg


This is a simple Stack Overflow / Stack Exchange chat bot
which keeps an eye on a selected list of rooms,
and makes sure they are not frozen.

The threshold is currently set to 12 days since the previous message,
to leave some leeway for possible accidents
(the freeze happens after 14 days of inactivity).

There is no interactive interface to the bot;
create a pull request if you would like to add a room
to Sloshy's watch list.

In the YAML configuration file, add the server's name
to the `rooms` key if it is missing (though that's unlikely)
and create a new entry with information about the room you want to add;

* The `id` is the room's numeric identifier.
  This (together with the server's name) is the way Sloshy finds the room.
* The `name` field is just a display string for Sloshy's status messages.
  It can be anything, but should describe the room
  reasonably unambiguously to humans.
* The `contact` field indicates who requested the room to be added,
  in case we would need to touch base with you later on
  to assess whether the room still needs to be on the list, etc.
  The format should be your user name,
  followed by the network account id in round parentheses.
  The network id number can be found by clicking "Network profile"
  on any profile page for your account.
  (For example, Sloshy is user 16115299 on Stack Overflow,
  but network user 21818820.)

In brief, if your chatroom's URL is
https://chat.stackexchange.com/rooms/12345/my-room,
and your network account ID is 21818820, you would add
```
rooms:
 - chat.stackexchange.com:
   - name: "my room's name"
     id: 12345
     contact: Sloshy the Thawman (21818820)
```
in the configuration file.
(This is showing the complete YAML structure;
the `rooms` top-level key
and the server `chat.stackexchange.com` obviously already exist
in the file.)

Perhaps notice also that there are two main chat servers
with very similar names,
where one contains "overflow" and the other contains "exchange".

Besides `rooms`, there are some other configuration options
which can be specified in the YAML file.
For the most part, these are undocuemented options
for use in internal testing,
but the following are expected to remain stable and supported:

* `local`: boolean; set to `true` to disable connecting to chat.
  Sloshy will still need to open network connections
  to fetch chat transcripts, but will not emit any chat messages.
* `nodename`: string; set to the name you would like to display
  as Sloshy's location in the startup message.
* `threshold`: expression indicating after how much inactivity
  to emit an anti-freeze message to a room.
  The default is 12 days; set to a different number to override.
  (See the source for advanced and possibly unstable options.)

## Deploy

There is a simple Github Action which runs nightly.


## Bot Profiles

* [Main profile](https://stackoverflow.com/users/16115299/sloshy)
* [Chat profile](https://chat.stackoverflow.com/users/16115299/sloshy)


## Author

tripleee
