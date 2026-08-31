This is a document to write down feature ideas that I wish to implement, they will each be placed in a section named after where the idea is relevant.
These will be implemented eventually.

# Generation
- Sort options and any OptionCounter output before placing in slot data.
- Merge empty values in any OptionCounter output before placing in slot data.
- Lock locations behind hidden walls behind the wicked eye item.

# Launcher
- Launcher will store the pid, auth information (name, password, room url, port), and host apworld version of the latest successful game launch + connection
  - This will be used for reconnection when the client is closed but the game stays open.
  - Launcher will to verify if the pid is still running. 
  - Then the communication handler will verify the game's heartbeat.
  - An automatic reconnection attempt will be made.