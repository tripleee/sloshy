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


## Deploy

There is a simple Github Action which runs nightly.


## Bot Profiles

* [Main profile](https://stackoverflow.com/users/16115299/sloshy)
* [Chat profile](https://chat.stackoverflow.com/users/16115299/sloshy)


## Author

tripleee
