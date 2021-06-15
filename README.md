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

In the YAML configuration file, add the server if it is missing
(though that's unlikely)
and add information about the room you want to addd;

* The `id` is the room's numeric identifier.
  This (together with the server) is the way Sloshy finds the room.
* The `name` field is just a display string for Sloshy's status messages.
  It can be anything, but should describe the room
  reasonably unambiguously to humans.
* The `contact` field indicates who requested the room to be added.
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


## Deploy

There is a simple Github Action which runs nightly.


## Bot Profiles

* [Main profile](https://stackoverflow.com/users/16115299/sloshy)
* [Chat profile](https://chat.stackoverflow.com/users/16115299/sloshy)


## Author

tripleee
