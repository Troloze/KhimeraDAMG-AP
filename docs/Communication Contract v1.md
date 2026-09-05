# Communication Contract V1
# Meta
This specification is supposed to be changed and adapted to the needs of newer features that are introduced as the apworld is developed. However, since the game will support retrocompatibility, any changes made to the contract need to be documented. 
Compatibility breaking changes will be written to a new document and stored as `Communication Contract v<X>.md`; the latest version will be in the `docs` folder, and the older version will be kept in `docs/communication` (if there are any).

The client will maintain the logic for older versions of the communication contract, using it when necessary.
# Contract Specification.
The client and the game will communicate via flag files dropped in the game's files.
## Relevant locations
The game will store information per room and seed, currently only the last ack received from the game, but in the future more might come.
Stored information will stay in `Utils.user_path("khimera_damg")`.

The file communication will happen at the GameMaker sandbox folder, namely `%LOCALAPPDATA%\khimera_ap`.
## Consumption policy.
Files will be deleted after consumption unless stated otherwise. 'Consumption' refers to both the reading and the application of the data, files should only be deleted once the data is truly no longer needed. 

Both the client and the game will buffer their data and write the files at a fixed time rate, compiling the information buffered during the tick on the file. Consumption from one side should happen on a faster rate than writing from the other side.
### Suffixes
Files will have a `.tmp` attached to the end of their name on creation, and only renamed to their actual name after the file has been fully written. 

Files that are currently being read will have a `.rd` appended by the consumer before reading.
- If a leftover `.rd` file exists, delete it and try again, the contract is resistant against information loss.

The existence of the file means that it hasn't been consumed, if the file still exists at the end of a tick, buffer the data and wait for the next tick.
## Memory Policy
The client will store a per seed and slot file with the last index the game has acknowledged on the user's local files, on a folder next to where the patched game will live.
## File Structure
There will be two main file structures used in the contract: JSON and State Flags
Files are to be encoded in ASCII, without characters from \x00 to \x1F and \x7F.
### JSON
- These files will be structured as a single line of json, with no line breaks between items.
- The root will be a dictionary with a single field called "message" holding a dict that contains all information. 
	- This is so we can detect a malformed json from the gamemaker's side and treat it as such.
		- GameMaker will read the entire malformed json as a string, and place it as a value to a "default" field on a dictionary. If "default" is present in the place of "message", then the json was malformed.
- Any missing expected fields are to be treated as "null", "empty", or "not informed" and handled as such.
### State Flags.
- Name of the file is its value, extension is its meaning.
	- E.g., `103.gshb` means the game's heartbeat value is 103
- Value should have meaning on its own, do not use multiple state flags for tracking single bit of information. 
	- Avoid using for more than one bit of information as well, unless they're related boolean values that can be made into a bitwise flag integer.
- These files will be completely empty
- No side should attempt to read any file of this type.
- They should all be created on launch, no creating mid-session.
- They will not be deleted during a session, only renamed.
	- Always verify if the renamed file exists after renaming.
- As per OS limitations, maximum file name size is 255, keep that in mind.
- Both sides will hold a heartbeat, that's the main source of truth if one side is alive or not
	- Other flags' information is only valid if its owner's heartbeat is progressing.
- The owner side is responsible to manage and remove stray copies and ensure there is only one flag file of a give type.
- When a reading is ambiguous (i.e., there are multiple files of the same flag) it should be read as no-data
- When a reading is of unexpected type, it should be read as no-data
## Game Maker
Rules specific to game maker needed to ensure this contract works as expected.
- Rename and Delete don't return errors, therefore a `file_exists` check is needed to check for success.
- `find_file_first` must always be closed after used, and never nested.
- All strings sent by game maker must escape for `\` and `"` in this order.
# Files
## Client Side Files:
### Connection Context: `ap.cctx`
This will list connection information. Will be sent when the client first launches the game, on reconnection, and while the game has not consumed the file yet (tracked via `.csreq`).

This message will be a json with:
- `"meta"`: (dict)
	- holds `"archipelago_version"`, `"host_world_version"`, `"client_world_version"`, and `"slot_name"` fields, each with a string value.
- `"options"`: (dict)
	- `"names"` Option names (list)
	- `"types"` Option types (list)
	- `"values"` Option values (list)
	- `"count"` Number of entries
	- The lists will be built so that name, type and value can be obtained from the index.
	- Option names not contained here should be assumed as "not included" and a default value should be used.
	- Type of `"value"` will be dictated by `"type"` (following the type treatment section at the end of the document)
	- All three lists must have the same length.
- `"slot_data"`: (dict)
	- `"names"` Data names (list)
	- `"types"` Data types (list)
	- `"values"` Data values (list)
	- `"count"` Number of entries
	- The lists will be built so that name, type and value can be obtained from the index.
	- Data names not contained here should be assumed as "not included" and a default value should be used.
	- Type of `"value"` will be dictated by `"type"` (following the type treatment section at the end of the document)
	- All three lists must have the same length.
- `"session"`: (dict)
	- holds the following fields:
		- `"last_ack"` with an int value, this is the last ack the game has sent to the client.
		- `"item_list"` with a dict value:
			- `"item_ids"` with a list of all item ids (int)
			- `"player_ids"` with a list of all the player ids (int) that sent the items
			- `"count"` number of item entries, not the number of elements on the list
				- E.g., if there are 3 items, count will be 3 despite there being 4 elements on each list (due to the rule below).
			- The list is ordered by the item index, so `item_ids[1]` is item 1.
				- `item_ids[0]` will always have -1, and the same goes for player.
			- The two lists must have the same length.
		- `"location_ids"` with a list of all location ids that were checked (int)
		- `"is_win"` (optional) holding a 1 (int). Tells the game it has been goaled.
### Location Information: `ap.li`
Information regarding each individual location, including item owner and item classification.
Will be sent when the client first launches the game, on reconnection, and while the game has not consumed the file yet (tracked via `.csreq`).

This message will be a json with:
1. `"enabled"` a zero or one value.
2. `"locations"` a dictionary:
	- `"location_ids"` a list of all location ids (int)
	- `"location_classifications"` a list of all location classifications (int)
	- `"player_ids"` a list with all player ids (int)
	- `"count"` number of entries
	- Lists will be built so location_ids, location_classifications and player_id scan be obtained from an index.
	- All three lists must have the same length.

The game should not require this file to work; if it isn't available the game should continue normally without the location information.
### Host information:  `ap.hi`
A list of data sent by the host to the client.

This message will be a json with:
- `"messages"` a dict with:
	- `"senders"` a list with the sender player id (int)
	- `"messages"` a list with the messages (str)
	- `"count"` number of entries
	- The two lists must have the same length.
- `"death_links"` a dict with:
	- `"senders"` a list with the death link sender player id (int)
	- `"death_ids"` a list with the death link ids (int)
		- these are managed by the client, not the host.
	- `"messages"` a list with the death link messages (str)
	- `"count"` number of entries
	- The two lists must have the same length.
- `"item_list"` with a dict value:
	- `"item_ids"` with a list of all item ids (int)
	- `"player_ids"` with a list of all the player ids (int) that sent the items
	- `"item_indexes"` with a list of all the item indexes (int)
	- Deliberately a diferent structure than `ap.cctx`'s item_list.
	- All three lists must have the same length.
- `"location_ids"` with a list of all location ids that were checked (either by the game or via collect commands)
	- Sends these every time until acked by the game.
- `"death_ack"` with a death link id (int), confirming a received death link
	- Death link id is managed by the game.
	- Whichever id it sends, the client just needs to send it back, no need to track state.
	- If received multiple ids in between ticks, send the latest.

The client will limit the amount of messages sent to the game on a tick, passing only the most recent ones to the game and discarding the rest. On file update, the client will append all items and death links; the messages, however, will be appended and if more than the set amount are present in the file, the older messages will be pruned so that the message count is back to the set amount.

The game will have no way of "scrolling up" the list of messages so any message that would not be displayed (because they were pushed up by others) are not relevant. The exact value of the limit will be determined by the in-game message viewer implementation.

Messages sent by the user via the client will also be placed in the `ap.hi` and sent to the game.
### State flags.
All client state flags will have an extension that starts with `.cs`.
- `.cshb`: Client side heartbeat
	- Goes up by 1 every tick
- `.csc`: Client side connected
	- 1 if connected to host
	- 0 if not connected to host
	- The game will only consider the client as disconnected from host if the state is disconnected for a time period after first disconnect, no-data, or if the heartbeat is detected as stale.
## Game Side Files:
### Game information: `ap.gi`
A list of data sent by the game to the client.

This message will be a json with:
- `"location_ids"` with a list of all location checked. (int)
	- ids will be sent several times until acked.
- `"death_link"` a dict with:
	- `"id"` (int)
		- Managed by the game, it should be a number that hasn't been sent yet during the session.
	- `"message"` (string)
		- The pattern, not the final message. The client will build the final message.
			- E.g., "%s fell on a pit." rather than "Player1 fell on a pit."
	- Sent every time until acked.
	- If a new death link happens while another is still yet to be acked, send with the new information; archipelago should only take one death link from the same source at a time, so we should keep the latest one.
	- The two lists must have the same length.
- `"location_acks"` a list with all locations the game acknowledges (int)
	- Sent every time the game receives a location message from the client.
- `"death_ack"` the latest death link id received.
	- Death link id is managed by the client.
	- Whichever id it sends, the game just needs to send it back, no need to track state.
	- If received multiple ids in between ticks, send the latest.
### State Flags
All client state flags will have an extension that starts with `.gs`.
- `.gsreq`: Game requires connection information.
	- bit flag integer
		- 2 means game has not loaded `ap.cctx` yet
		- 1 means game has not loaded `ap.li` yet
	-  If the game hasn't loaded those files yet, but they're gone, the client will need to write them again.
- `.gshb`: Game side heartbeat.
	- Value goes up by 1 every tick
- `.gsack`: Game side (item) ack
	- Index of the last item the game acknowledged.
	- The client will store the last ack ever issued by the game on disk as per the Memory Policy.
- `.gswin`: Game side win.
	- 1 if win, 0 otherwise.
## Ownership information
`ap.cctx`, `ap.li` and `ap.hi` files will be created by the client and deleted by the game
`ap.gi` files will be created by the game and deleted by the client

All state flags are completely controlled by their writers.

All leftover files from previous sessions will be cleaned up by their owners on game launch.
- Includes state flags.
- The client will clear up all files on its own on launch if a game is not running.
# Type treatment specification
The communication contract specifies 5 types:
- **SV** String Value: a single string. 
- **NV** Number Value: a single number. 
- **SL** String List: a list of string values.
- **NL** Number List: a list of number values.
- **D** Dictionary: Hosts keys and values. Keys are always strings, values can be string or number.
	- Value types will need to be inferred.
## Options
This section will list individual archipelago option types that are intended to be used and how they should be treated.
### Choice (NV)
A basic enum.
- Value must be a non negative integer.
### Toggle or DefaultOnToggle (NV)
A basic boolean.
- Value must be an integer, either 0 or 1.
### Range or NamedRange (NV)
A basic integer.
- Value must be an integer.
### OptionList (SL or NL)
A list. of either type
### OptionSet (SL or NL)
A set. Works similarly to OptionList, but has no repeats.
- values must be sorted
### OptionCount (D)
A dictionary where all values are integers.
- All keys must be strings
## Data
This section will list individual data types that are intended to be used and how they should be treated.
### Boolean (NV)
A basic boolean
- Integer value, either 0 or 1.
### Integer (NV)
A basic integer.
### String (SV)
A basic string.
- Must follow the contract's rules for encoding.
### Number List (NL)
A basic list of numbers.
### String List (SL)
A basic list of strings.
### Dictionary (D)
A basic dictionary.
- All keys must be strings
- Values must be either integer, string, or lists
- lists can have either integers or strings, but never both.
# Changelog
## V1
Introduced json and flag state files for communication.