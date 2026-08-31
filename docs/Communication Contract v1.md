# Meta
This specification is supposed to be changed and adapted to the needs of newer features that are introduced as the apworld is developed. However, since the game will support retrocompatibility, any changes made to the contract need to be documented. 
Compatibility breaking changes will be written to a new document and stored as `Communication Contract v<X>.md`; the latest version will be in the `docs` folder, and the older version will be kept in `docs/communication`.

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

If a tick cycle is over and the file is still there, the sender will append a `.up` to the file name, rewrite the file with the old and new data, and then rename it back to its original name. A crash mid rewrite will leave the file behind, which will be cleaned up on a new launch of the client.
## Memory Policy
The client will store a per seed and slot file with the last index the game has acknowledged on the user's local files, on a folder next to where the patched game will live.
## File Structure
All files are encoded in ASCII, and structured as a list of rows, each composed by an identifier and a series of parameters:
``` python
IDENTIFIER PARAM
IDENTIFIER PARAM PARAM
IDENTIFIER PARAM PARAM PARAM ... PARAM
IDENTIFIER PARAM
...
$
```
Other than that, the following items should be followed: 
- Due to GameMaker limitations, all instances of an octothorpe (`#`) should be preceded by a backslash.
- Unknown identifiers should be skipped silently.
- Number params will be plain integer decimals, signs must be connected to the number without a whitespace between them.
- String params will not contain whitespaces
- Line endings should accept CRLF or LF on both the client and the game.
- Other than the line/file endings at their correct places and the whitespace, no characters without glyphs should be written.
- The last line on every file will be a sole dollar sign.
# Files
## Client Side Files:
### Connection Context: `ap.cctx`
This will list connection information. Will be sent when the client first launches the game, on reconnection, and when the player issues a "sync" command on the client.

Message Identifiers are:
1. `APV <version: str>` 
	Archipelago version.
2. `APW <version: str>` 
	Apworld version used when generating the multiworld game the client connected to.
3. `CAPW <version: str>`
	Apworld version of the client.
4. `SLOT <name: str>`
	Name of the slot.
	- SLOT consumes the entire rest of the row until linebreak.
5. `OPTION <option: str> <type: str> <...: ...>`
	Generation options used.
	- There are 3 option types:
		- `type = "S"`: "Single" - will hold a single value, either integer or string.
		- `type = "L"`: "List" - will be followed by a value count, and then several values.
			- Value types can be integer or string.
			- All values on the list have to be of the same type.
		- `type = "D"`: "Dictionary - will be followed by a field count, and then several instances of field name followed by field value.
			- Value types can be integer or string.
			- Values can have differenty types.
	- Types will be inferred by the option name.
	- This list will be determined by the randomizer logic and should be similar to the yaml.
6. `DATA <type: str> <...: ...>`
	Generation information the game needs to know, relevant for when entrance/map randomizer gets implemented
	- New `type` definitions are to be appended bellow as the game is developped, without the need to create a new contract version. 
7. `LACK <index: int>`
	Last ACK index the game has sent to the client. The index is 0 excluded.
8. `ITEM <item_id: int> <index: int>`
	An item sent to the game. The index is 0 excluded.
9. `LOC <loc_id: int>`
	A location the game has already marked as checked.
	This is for reconstruction only, the game should not re-send these locations to the client.
10. `WIN`
	Informs the game that it has already reached its goal.
### Location Information: `ap.li`
Information regarding each individual location, including item owner and item classification.
This list will be made available to the game after it is launched.

The identifiers are:
1. `LCPV <enabled: int>`
	- Always the first row
	- If enabled is 1 (on), the following rows will contain location information;
	- Otherwise, there will be no following rows.
2. `LC <location_id> <class: int> <player: int>`
	- The classification and player of the item at a location.

The game should not require this file to work; if it isn't available the game should continue normally without the location information.
### Connection State: `ap.cs` 
The source of truth regarding connection between the client and the host.

This file will not be deleted upon consumption, it will be written by the client and only read by the game, not written to. 
The game will not append the `.rd` suffix when reading this file.
Instead of having `.up` suffixed to the file on update, the client will instead create a new `ap.cs.tmp` file and replace the previous `ap.cs`; OS failure will simply result in another attempt after some time has passed.

Message Identifiers are:
1. `STATUS <status: int>`
	Connection status; 0 if connected, 1 if disconnected.
2. `HBEAT <beat: int>`
	Heartbeat, starts with zero and increases by 1 on every write tick
In its absence, the game will consider STATUS as disconnected.

If the heartbeat doesn't change in a set amount of time (in seconds, not ticks), the game will treat the client as dead.
### Host information:  `ap.in`
A list of data sent by the host to the client.

Message Identifiers are:
1. `MSG <message: str>`
	A message the client has received, this will be displayed verbatim by the game after (the client parses and removes potential injections before sending this). 
	`<message>` consumes the entire rest of the row until line break.
2. `ITEM <item_id: int> <index: int>`
	An item received from the server. The index is 0-excluded.
3. `DLINK <message: str>`
	A death link.
	`<message>` consumes the entire rest of the row until line break.
4. `LOC <location_id: int>`
	Notifies the game when a location is collected by the server (autocollect on, or collect command)

The client will limit the amount of messages sent to the game on a tick, passing only the most recent ones to the game and discarding the rest. On file update, the client will append all items and death links; the messages, however, will be appended and if more than the set amount are present in the file, the older messages will be pruned so that the message count is back to the set amount.

The game will have no way of "scrolling up" the list of messages so any message that would not be displayed (because they were pushed up by others) are not relevant. The exact value of the limit will be determined by the in-game message viewer implementation.

Messages sent by the user via the client will also be placed in the `ap.in` and sent to the game.
## Game Side Files:
### Game information: `ap.out`
A list of data sent by the game to the client.

Identifiers are:
1. `LOC <loc_id: int>`
	A checked location.
2. `DLINK <message: str>`
	A death link the game has sent, sends a custom death message.
	`<message>` consumes the entire rest of the row until line break.
3. `WIN`
	Sent every tick after the win condition has been reached.
4. `ACK <index: int>`
	The highest index that was consumed by the game. Sent every tick, Placed at the end of the file.  The index is 0-excluded.
### Game State: `ap.gs` 
The game's own heartbeat.

This file will not be deleted upon consumption, it will be written by the game and only read by the client, not written to. 
The client will not append the `.rd` suffix when reading this file.
Instead of having `.up` suffixed to the file on update, the game will instead create a new `ap.gs.tmp` file and replace the previous `ap.gs`; OS failure will simply result in another attempt after some time has passed.

Message Identifiers are:
1. `HBEAT <beat: int>`
	Heartbeat, starts with zero and increases by 1 on every write tick
In its absence, the game will consider STATUS as disconnected.

This is mainly used for the purpose of reconnection when the client is closed and the game is kept running.
Detecting a change in here will tell the client it is still alive and attempt to reconnect.

This can also be used to detect a game freeze (process doesn't return, but isn't updating the heartbeat).
## Ownership information
`ap.cctx` and `ap.in` files will be created by the client and deleted by the game
`ap.out` files will be created by the game and deleted by the client
`ap.cs` files will be created by the client and deleted by the client (on exit)

All leftover files from previous sessions will be cleaned up by the client on launch.
# Type treatment specification
The communication contract specifies 3 main types:
- **S**ingle values: Can be either integer or strings. 
- **L**ist of values: The list can host integer or string values, as long as all of them are of the same type.
- **D**ictionary: Hosts keys and values. Keys are always strings, values can be string or integer.
## Options
This section will list individual archipelago option types that are intended to be used and how they should be treated.
### Choice (S)
A basic enum.
- Value must be a non negative integer.
### Toggle or DefaultOnToggle (S)
A basic boolean.
- Value must be an integer, either 0 or 1.
### Range or NamedRange (S)
A basic integer.
- Value must be an integer.
### OptionList (L)
A list.
### OptionSet (L)
A set. Works similarly to OptionList, but has no repeats.
- string values must be sorted (done by default)
### OptionCount (D)
A dictionary where all values are integers.
- Keys must be sorted 
- All keys in the definition must be present.
## Data
This section will list individual data types that are intended to be used and how they should be treated.
### Boolean (S)
A basic boolean
- Integer value, either 0 or 1.
### Integer (S)
A basic integer.
### String (S)
A basic string.
- Must follow the contract's rules for encoding.
- Must not use line breaks.
### List (L)
A basic list.
### Dictionary (D)
A basic dictionary.
- Keys must be sorted.