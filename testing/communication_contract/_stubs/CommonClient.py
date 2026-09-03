# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""Minimal stand-in for Archipelago's CommonClient."""

from __future__ import annotations

import enum


class ClientStatus(enum.IntEnum):
    CLIENT_UNKNOWN = 0
    CLIENT_CONNECTED = 5
    CLIENT_READY = 10
    CLIENT_PLAYING = 20
    CLIENT_GOAL = 30
