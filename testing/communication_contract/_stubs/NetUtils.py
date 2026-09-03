# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Minimal stand-in for Archipelago's NetUtils.

Only the pieces game_communication.py touches are defined here, copied field-for-field
from Archipelago/NetUtils.py so the tests stay independent of an AP install.
"""

from __future__ import annotations

import typing


class NetworkItem(typing.NamedTuple):
    item: int
    location: int
    player: int
    flags: int = 0
