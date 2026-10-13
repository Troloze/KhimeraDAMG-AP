This is a document to write down feature ideas that I wish to implement, they will each be placed in a section named after where the idea is relevant.
These will be implemented eventually.

# Generation

### Only once we implement the gates
- Sort options and any OptionCounter output before placing in slot data.
- Merge empty values in any OptionCounter output before placing in slot data.

### After v0.1.0
- Lock locations behind hidden walls behind the wicked eye item.
  - Requires changing region logic to allow sub-regions.
  - If I am going to do that, I'd rather make every single screen a region.
  - For that I will need to make a structured view of all stages in the game, big and time consuming task. 

# Client

### After v0.1.0
- CLI support.
- Rework the apworld packages and modules in favour of maintainability.
  - Specifically the client/client.py module is in dire need of splitting.
  - Remove definitions other than `__all__` from all `__init__.py` files as well.

# Launcher

### For future versions, very low priority
- Detect a copy of the game on the user's steam library and ask to use it before the regular build prompts (both startup and on launch).