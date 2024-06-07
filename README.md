# Sloshy the Thawman


[![Github Actions: Test pushed code][1]][2]
[![Github Actions: Nightly][3]][4]
[![Healthckecks.io status][5]][6]

  [1]: https://github.com/tripleee/sloshy/actions/workflows/test-pushed.yml/badge.svg
  [2]: https://github.com/tripleee/sloshy/actions/workflows/test-pushed.yml
  [3]: https://github.com/tripleee/sloshy/actions/workflows/nightly.yml/badge.svg
  [4]: https://github.com/tripleee/sloshy/actions/workflows/nightly.yml
  [5]: https://healthchecks.io/badge/1c6e4a7e-e3ba-4ea6-bd6a-4a7ba6/Dc19IJOD-2.svg
  [6]: https://ntfy.sh/sloshy-is-alive

This is a simple Stack Overflow / Stack Exchange chat bot
which keeps an eye on a selected list of rooms,
and makes sure they are not frozen.

To prevent a room from freezing,
Sloshy enters the room and writes a message,
which marks the room as active again.

The threshold is currently set to 12 days since the previous message,
to leave some leeway for possible accidents
(the freeze happens after 14 days of inactivity;
the threshold is lower for rooms with only very few messages).


## Configuring Sloshy

There is no interactive interface to the bot;
create a pull request
if you would like to add a room to Sloshy's watch list.

(If this feels too challenging,
create an issue to request your room to be added.
We'll still need the details which are specified below.)


### Configuration File Format

Sloshy's operation is driven by a simple YAML file,
[`sloshy.yaml`](sloshy.yaml).

This is basically a human-readable text file,
though the YAML format imposes some structuring conventions
to also ensure that the file is properly machine-readable.
For more information, perhaps see
[Wikipedia's YAML article](https://en.wikipedia.org/wiki/YAML)
and/or https://yaml.org/;
but you really don't need to be very familiar with the format
to make simple changes.

| :warning:      | Configuration file format changed in PR #23 (August 2023) |
|----------------|:----------------------------------------------------------|

In the YAML configuration file, add the server's name
to the `servers` key if it is missing (though that's unlikely)
and create a new `rooms` entry with information about the room
you want to add;

* A line with a dash at the front starts a new entry.
* The `contact` field indicates who requested the room to be added,
  in case we would need to touch base with you later on
  to assess whether the room still needs to be on the list, etc.
  The format should be your user name,
  followed by the network account id in round parentheses.
  The network id number can be found by clicking "Network profile"
  on any profile page for your account.
  (For example, Sloshy is [user 16115299 on Stack Overflow][7],
  but [network user 21818820][8].)
* The `id` is the room's numeric identifier.
  This (together with the server's name) is the way Sloshy finds the room.
* The `name` field is just a display string for Sloshy's status messages.
  It can be anything, but should describe the room
  reasonably unambiguously to humans.

 [7]: https://chat.stackoverflow.com/users/16115299/sloshy
 [8]: https://stackexchange.com/users/21818820/sloshy

In brief, if your chatroom's URL is
https://chat.stackexchange.com/rooms/12345/my-room,
and your network account ID is 123456789,
the configuration file would look something like
```yaml
servers:
 chat.stackexchange.com:
   rooms:
   - contact: your name (123456789)
     id: 12345
     name: "my room's name"
   sloshy_id: 514718
```

(This is showing the complete YAML structure;
the `servers` top-level key
and the server `chat.stackexchange.com` with the corresponding `sloshy_id`
obviously already exist in the file.
Thus the three lines starting from the `- contact:` line
are what you would normally add for a new room.)

Perhaps notice also that there are two main chat servers
with very similar names,
where one contains "overflow" and the other contains "exchange".
You want to make sure you add the room in the section belonging
to the correct server for this particular room.


### Requesting a New Room or a Configuration Change

The previous section explains what
technically needs to go into your pull request.
Creating the required code change for a pull request
should be easy if you are familiar with the basics of
[GitHub's PR process](https://docs.github.com/en/pull-requests)
and YAML (or at the very least, making changes to a text file. :-)

Before you propose a change,

* Please make sure you have the approval of the room's users,
  typically by asking a room owner or a moderator for approval.

* Please also separately make sure that Sloshy has write access
  to any privileged room you want to add to the list.

For adding an individual room owned by yourself,
the process is pretty relaxed; just say so in the description
of the pull request which you fill in when you create it.
(As always, including a good rationale for the change
is considered good practice; pull requests with no information
about the rationale and/or context can and will be rejected summarily,
not just by the Sloshy maintainer, but more generally.)

If you add more rooms (in a single pull request, or over time),
getting moderator approval for individual rooms may not be sufficient.
Then, it's probably better if you can anchor the decision with
a discussion about the guiding motivation
for adding these rooms to Sloshy's configuration
(probably with a moderator;
but if you can adequately poll the users of those rooms
and other pertinent stakeholders
e.g. with a meta post about this topic,
and reach a reasonable consensus among them,
that would probably be fine, too).

If you think this is too old-school, perhaps check out
[the competition.][9]

 [9]: https://stackapps.com/questions/10422/toasty-a-better-chat-antifreeze-bot


### Migrating Old Configurations

This is only relevant if you cloned Sloshy's Git ropository
a long time ago,
and need to update your configuration to adhere to the
current YAML schema.

There is an option `--migrate` which accepts a YAML file argument
and rewrites it from the old schema to the new.

Example:

```sh
python3 sloshy.py --migrate sloshy.yaml
```

The original configuration file format did not have a schema identifier.
The migration code simply assumes that your file uses the old schema.


### Configuration Options

Besides `servers`, there are some other configuration options
which can be specified in the YAML file.
For the most part, these are undocumented options
for use in internal testing,
but the following are expected to remain stable and supported:

* `schema`: top-level key which identifies the YAML schema version
  (currently 20230827, corresponding to the date 2023-08-27).
* `local`: boolean; set to `true` to disable connecting to chat.
  Sloshy will still need to open network connections
  to fetch chat transcripts, but will not emit any chat messages.
* `nodename`: string; set to the name you would like to display
  as Sloshy's location in the startup message.
* `threshold`: expression indicating after how much inactivity
  to emit an anti-freeze message to a room.
  The default is 12 days; set to a different number to override.

(See the source for advanced and possibly unstable options.)

### Schema Changes

* 20230827: add "role: cc"
* 20211215: first schema with a version number; split into
  top-level servers and include Sloshy's chat ID for each
  in preparation for the `--announce` feature.

## Deploy

There is a simple Github Action which runs nightly.
Pushing a new version to the `master` branch deploys it.


## Bot Profiles

* [Main profile](https://stackoverflow.com/users/16115299/sloshy)
* [Chat profile](https://chat.stackoverflow.com/users/16115299/sloshy)

From the chat profile, you can see
links to Sloshy's recent activities
in different chat rooms.

## Author

[tripleee](https://stackoverflow.com/users/874188/tripleee)
