# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Shared bases and option presets for the generation-side tests.

Nothing in here may import the client package: the generation tests should stay cheap, and
``client/__init__.py`` pulls in ``CommonClient``. Client bases live in ``support/sandbox.py``.
"""

from collections.abc import Mapping
from typing import Any

from BaseClasses import Location  # type: ignore
from test.bases import WorldTestBase  # type: ignore

from .. import GAME_FULL_NAME, KhimeraDAMGWorld

# The four option toggles that decide which locations exist. Every count in the suite is a
# function of these, so they are named once here.
SHUFFLE_KEYS: tuple[str, ...] = (
    "shuffle_books",
    "shuffle_fairies",
    "shuffle_detonators",
    "shuffle_gourmet_gal"
)

NO_SHUFFLES: dict[str, Any] = dict.fromkeys(SHUFFLE_KEYS, False)
ALL_SHUFFLES: dict[str, Any] = dict.fromkeys(SHUFFLE_KEYS, True)

# Books on with fairies off is the combination that creates the fairy event locations,
# so it gets a name of its own.
BOOKS_WITHOUT_FAIRIES: dict[str, Any] = {
    **NO_SHUFFLES,
    "shuffle_books": True
}


def describe_options(options: Mapping[str, Any]) -> str:
    """Render an option dict for a failure message, shortest first so it stays readable."""
    if not options:
        return "default options"
    return ", ".join(f"{key}={options[key]}" for key in sorted(options))


class KhimeraTestBase(WorldTestBase):
    """Base for every generation test.

    Subclasses that set ``options`` also re-run Archipelago's own ``test_all_state_can_reach_everything``,
    ``test_empty_state_can_reach_something`` and ``test_fill`` under those options, which is where most of
    the option-combination coverage comes from.
    """

    game = GAME_FULL_NAME
    world: KhimeraDAMGWorld

    def option_description(self) -> str:
        """The options this test class ran with, for use in assertion messages."""
        return describe_options(self.options)

    def real_locations(self) -> list[Location]:
        """Locations that hold an id, i.e. everything except events."""
        return [loc for loc in self.multiworld.get_locations(self.player) if loc.address is not None]

    def event_locations(self) -> list[Location]:
        """Locations without an id, i.e. the fairy events and the victory event."""
        return [loc for loc in self.multiworld.get_locations(self.player) if loc.address is None]
