The client and the game will communicate via flag files dropped in the game's files.
# Meta
This specification deliberately does not cover implementation specific information such as pooling time, among other things. These should be determined by what suits the platform this will implemented in best. 
# General Specification
## Production and consumption policy.
All files will be encoded as plain ASCII text, files will be deleted after consumption unless stated otherwise. 'Consumption' refers to both the reading and the application of the data, files should only be deleted once the data is truly no longer needed. 

Both the client and the game will buffer their data and write the files at a fixed time rate, compiling the information buffered during the tick on the file. Consumption should happen on a faster rate than writing.

### Suffixes
Files will have a `.tmp` attached to the end of their name on creation, and only renamed to their actual name after the file has been fully written. 

Files that are currently being read will have a `.rd` appended by the consumer before reading.

If a tick cycle is over and the file is still there, the sender will append a `.up` to the file name, rewrite the file with the old and new data, and then rename it back to its original name. A crash mid rewrite will leave the file behind, which will be cleaned up on a new launch of the client.
## Memory Policy
The client will store a per seed and slot file with the last index the game has acknowledged on the user's local files, on a folder next to where the patched game will live.

## File Structure
All files are a list of rows, each row with a message, like bellow:
``` python
IDENTIFIER PARAM
IDENTIFIER PARAM PARAM
IDENTIFIER PARAM PARAM PARAM ... PARAM
IDENTIFIER PARAM
...
```
Messages are structured with an identifier and a number of parameters.

Unknown identifiers should be skipped silently.

Numbers will be plain non-negative decimals with no sign and no floats.

Line endings should accept CRLF or LF on both the client and the game.
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
5. `OPTION <option: str> <...: ...>`
	YAML option and value set during generation 
	- Options will usually hold only 2 parameters (the option name and value), but options that receive a list will hold the option name, the list size (int) and the values.
	- Type of the values will be inferred by the option name.
	- This list will be determined by the randomizer logic and should be similar to the yaml.
	- All tokens will be either whitespace free, or between double quotes.
6. `LACK <index: int>`
	Last ACK index the game has sent to the client. The index is 0 excluded.
7. `ITEM <item_id: int> <index: int>`
	An item sent to the game. The index is 0 excluded.
8. `LOC <loc_id: int>`
	A location the game has already marked as checked.
	This is for reconstruction only, the game should not re-send these locations to the client.
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
3. `DLINK  <message: str>`
	A death link.
	`<message>` consumes the entire rest of the row until line break.

The client will limit the amount of messages sent to the game on a tick, passing only the most recent ones to the game and discarding the rest. On file update, the client will append all items and death links; the messages, however, will be appended and if more than the set amount are present in the file, the older messages will be pruned so that the message count is back to the set amount.

The game will have no way of "scrolling up" the list of messages so any message that would not be displayed (because they were pushed up by others) are not relevant. The exact value of the limit will be determined by the in-game message viewer implementation.

Messages sent by the user via the client will also be placed in the `ap.in` and sent to the game.
## Game Side Files:
### Game information: `ap.out`
A list of data sent by the game to the client.

Identifiers are:
1. LOC <loc_id: int>
	A checked location.
2. `DLINK  <message: str>`
	A death link the game has sent, sends a custom death message.
	`<message>` consumes the entire rest of the row until line break.
3. `WIN`
	Sent every tick after the win condition has been reached.
4. `ACK <index: int>`
	The highest index that was consumed by the game. Sent every tick, Placed at the end of the file.  The index is 0-excluded.
## Ownership information
`ap.cctx` and `ap.in` files will be created by the client and deleted by the game
`ap.out` files will be created by the game and deleted by the client
`ap.cs` files will be created by the client and deleted by the client (on exit)

All leftover files from previous sessions will be cleaned up by the client on launch.