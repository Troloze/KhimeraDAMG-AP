# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.

# The test package is deliberately empty, per Archipelago's own guidance in
# Archipelago/docs/tests.md ("Defining anything inside test/__init__.py is deprecated").
# Shared setup lives in bases.py and support/.
#
# This package is excluded from the built .apworld by /tests/ in .apignore, so it never
# reaches a player. Start with bases.py, then the per-area folders:
#   generation/ - the world itself: items, locations, regions, options, slot data
#   client/     - the client: storage, contract, agent, connection state, patcher
#   guards/     - cheap consistency checks: versions, packaging, python compatibility
