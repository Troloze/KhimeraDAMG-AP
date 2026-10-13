<!-- AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer. -->
# Live

There are no known live issues currently.

# Latent

## Losing psutil: process identification would drop to pid and exe name, which is not exact

### Cause:

`psutil` is shipped with Archipelago but is not one of its direct requirements. It is absent
from `Archipelago/requirements.txt` and arrives transitively:
`Archipelago/worlds/_sc2common/requirements.txt` asks for `portpicker>=1.5.2`, and portpicker
declares `Requires-Dist: psutil`. So the package is present only for as long as that whole
chain holds. Dropping the SC2 world, SC2 changing its own requirements, or portpicker dropping
psutil would each remove it, and none of those are decisions this repository takes part in.

Upstream is aware that indirect requirements have caused this class of problem before:
<https://github.com/ArchipelagoMW/Archipelago/issues/6507> asks for psutil to be required
explicitly.

### Description:

The client uses psutil to decide whether the game it launched is still running, by storing the
process id together with `Process.create_time()` and checking both. The creation time is what
makes that identification exact — a process id on its own is recycled by the operating system,
so a pid alone cannot distinguish the game this client launched from an unrelated process that
later inherited the same number.

`pymem`, which is a direct Archipelago requirement, offers no equivalent of `create_time()`.
That is the whole reason psutil is used here.

If a future Archipelago release ships without psutil, the deliberate fallback is to check the
pid and the executable name only, accepting the narrower bug that comes with it: a running
`khimera_damg_ap_randomizer.exe` that this client did not launch — started by hand, or left
over from a session whose client has since been replaced — can be mistaken for the client's own
game. The exe-name check keeps ordinary pid recycling from matching, so the remaining window is
small, and it fails in the safe direction: the user is offered a reconnect they can dismiss.
