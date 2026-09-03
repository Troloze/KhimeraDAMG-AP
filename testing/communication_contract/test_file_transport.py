# AI-GENERATED FILE: written by Claude (Anthropic), not hand-written by the developer.
"""The file transport: AgentV1's reads, writes, lifecycle and status probing.

Everything in the other modules tests the *contract* -- turning events into rows and back.
This one tests the layer that moves those rows through the GameMaker sandbox, which is
where the process-to-process races live. It drives a real temporary directory rather than
mocking the filesystem, because the behaviours that matter are Windows filesystem
semantics (``os.replace`` overwrites, ``Path.rename`` refuses, an open handle raises
``PermissionError``) and a mock would only re-state the assumption.

A stray ``.rd`` is not hypothetical -- the spec calls it out directly:

    "OSErrors, human interference, or outside factors can result in a stray .rd or .up
     file during runtime. An attempt to recover the information is to be made [...] any
     information that can create inconsistencies if received more than once should be
     stripped. Namely, death links and messages."

so the recovery paths get the same weight as the happy path.

The ``sandbox`` and ``agent`` fixtures live in conftest.py; they redirect
``get_sandbox_folder`` before construction, because ``AgentV1.__init__`` probes the
sandbox and would otherwise write into the directory a running game is using.
"""

from __future__ import annotations

import asyncio
import pathlib
import queue
import threading
import time
from typing import Any

import pytest
from harness import ConnectionContext, Interface, LocationInformation, RuntimeInformation


def make_context() -> ConnectionContext:
    return ConnectionContext("0.6.7", "0.0.0", "0.0.0", "Chelshia", 0, {}, {}, set(), [], False)


def names(path: pathlib.Path) -> list[str]:
    return sorted(p.name for p in path.iterdir())


def opened(agent: Any) -> Any:
    """Give an agent the queues open_communication would have handed it."""
    agent.htg_q = queue.Queue()
    agent.gth_q = queue.Queue()
    return agent


def run_worker(agent: Any) -> threading.Thread:
    """Start the consumer loop the way open_communication does, but keep the handle.

    The agent deliberately drops its reference to the worker -- it is daemon, self
    stopping, and signals completion through ``thread_exit`` -- so a test that needs to
    join on it has to own the handle itself.
    """
    thread = threading.Thread(target=agent._consume_incomming, daemon=True)
    thread.start()
    return thread


@pytest.fixture
def interface(sandbox: pathlib.Path) -> Interface:
    return Interface()


# --- construction -----------------------------------------------------------

def test_agent_is_constructible(agent: Any) -> None:
    assert agent.inspect_communication() is False


def test_a_fresh_agent_has_no_queues(agent: Any) -> None:
    # They arrive with open_communication; the consumer guards on them being absent.
    assert agent.htg_q is None
    assert agent.gth_q is None


def test_the_consumer_is_inert_before_communication_opens(agent: Any) -> None:
    assert agent._consumer(0) is None


# --- write_file -------------------------------------------------------------

def test_write_file_creates_the_document(agent: Any, sandbox: pathlib.Path) -> None:
    assert agent._write_file("ap.hi", "MSG hi\n$") is True
    assert (sandbox / "ap.hi").read_text(encoding="ascii") == "MSG hi\n$"


def test_write_file_leaves_no_tmp_behind(agent: Any, sandbox: pathlib.Path) -> None:
    agent._write_file("ap.hi", "MSG hi\n$")
    assert names(sandbox) == ["ap.hi"]


def test_write_file_refuses_to_clobber_an_unconsumed_document(agent: Any, sandbox: pathlib.Path) -> None:
    # Presence means the game has not consumed it yet; overwriting would lose those rows.
    (sandbox / "ap.hi").write_text("MSG first\n$", encoding="ascii")
    assert agent._write_file("ap.hi", "MSG second\n$") is False
    assert (sandbox / "ap.hi").read_text(encoding="ascii") == "MSG first\n$"


def test_status_write_always_replaces(agent: Any, sandbox: pathlib.Path) -> None:
    # ap.cs is never consumed by the game, so it must be overwritten every tick.
    (sandbox / "ap.cs").write_text("STATUS 0\nHBEAT 1\n$", encoding="ascii")
    assert agent._write_file("ap.cs", "STATUS 0\nHBEAT 2\n$", status=True) is True
    assert (sandbox / "ap.cs").read_text(encoding="ascii") == "STATUS 0\nHBEAT 2\n$"


def test_status_write_does_not_duplicate_its_own_content(agent: Any, sandbox: pathlib.Path) -> None:
    for beat in range(3):
        agent._write_file("ap.cs", f"STATUS 0\nHBEAT {beat}\n$", status=True)
    assert (sandbox / "ap.cs").read_text(encoding="ascii") == "STATUS 0\nHBEAT 2\n$"
    assert names(sandbox) == ["ap.cs"]


# --- read_file --------------------------------------------------------------

def test_read_file_consumes_the_document(agent: Any, sandbox: pathlib.Path) -> None:
    (sandbox / "ap.gi").write_text("LOC 5\n$", encoding="ascii")
    assert agent._read_file("ap.gi") == "LOC 5\n$"
    assert names(sandbox) == [], "a consumed document must be deleted"


def test_read_file_returns_none_when_absent(agent: Any) -> None:
    assert agent._read_file("ap.gi") is None


def test_status_read_does_not_consume(agent: Any, sandbox: pathlib.Path) -> None:
    # ap.gs is owned by the game; the client reads it without claiming or deleting it.
    (sandbox / "ap.gs").write_text("HBEAT 3\n$", encoding="ascii")
    assert agent._read_file("ap.gs", status=True) == "HBEAT 3\n$"
    assert names(sandbox) == ["ap.gs"]


# --- stray .rd recovery -----------------------------------------------------

def test_stray_rd_is_recovered(agent: Any, sandbox: pathlib.Path) -> None:
    (sandbox / "ap.gi.rd").write_text("LOC 100\n$", encoding="ascii")
    (sandbox / "ap.gi").write_text("LOC 200\n$", encoding="ascii")
    got = agent._read_file("ap.gi")
    assert got is not None
    assert "LOC 100" in got, "the stray document was dropped"
    assert "LOC 200" in got, "the fresh document was dropped"


def test_stray_rd_recovery_drops_death_links(agent: Any, sandbox: pathlib.Path) -> None:
    # Re-delivering a death link would kill the player twice for one game-side death.
    (sandbox / "ap.gi.rd").write_text("LOC 100\nDLINK ouch\n$", encoding="ascii")
    (sandbox / "ap.gi").write_text("LOC 200\n$", encoding="ascii")
    got = agent._read_file("ap.gi")
    assert got is not None
    assert "DLINK" not in got
    assert "LOC 100" in got


def test_stray_rd_recovery_leaves_nothing_behind(agent: Any, sandbox: pathlib.Path) -> None:
    (sandbox / "ap.gi.rd").write_text("LOC 100\n$", encoding="ascii")
    (sandbox / "ap.gi").write_text("LOC 200\n$", encoding="ascii")
    agent._read_file("ap.gi")
    assert names(sandbox) == []


def test_an_unreadable_stray_does_not_destroy_the_fresh_document(
    agent: Any, sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A locked stray must not cost us the document the game just wrote.

    GameMaker holding a handle makes every rename/unlink raise PermissionError. That is
    transient, so the correct response is to leave the fresh document alone and retry --
    never to consume it into a .rd that then gets abandoned.
    """
    (sandbox / "ap.gi.rd").write_text("LOC 100\n$", encoding="ascii")
    (sandbox / "ap.gi").write_text("LOC 200\n$", encoding="ascii")

    real_read_text = pathlib.Path.read_text

    def blocked(self: pathlib.Path, *args: Any, **kwargs: Any) -> str:
        if self.name.endswith(".rd"):
            raise PermissionError(32, "held by the game")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", blocked)
    agent._read_file("ap.gi")
    monkeypatch.undo()

    recovered = "".join(agent._read_file("ap.gi") or "" for _ in range(3))
    assert "LOC 200" in recovered, "the reader never recovers; LOC 200 is lost forever"


# --- host information buffering ---------------------------------------------

def test_host_information_is_written_when_the_game_is_keeping_up(agent: Any, sandbox: pathlib.Path) -> None:
    agent._send_host_information(RuntimeInformation([], set(), ["hello"], [], -1, False))
    assert (sandbox / "ap.hi").read_text(encoding="ascii") == "MSG hello\n$"
    assert agent.host_information_buffer is None


def test_unconsumed_ticks_accumulate_rather_than_duplicate(agent: Any, sandbox: pathlib.Path) -> None:
    """Every message must survive exactly once while the game is behind."""
    (sandbox / "ap.hi").write_text("MSG stale\n$", encoding="ascii")
    for i in range(4):
        agent._send_host_information(RuntimeInformation([], set(), [f"m{i}"], [], -1, False))
    buffered = agent.host_information_buffer
    assert buffered is not None
    assert buffered.messages == ["m0", "m1", "m2", "m3"], f"buffer holds {buffered.messages}"


def test_the_buffer_flushes_once_the_game_catches_up(agent: Any, sandbox: pathlib.Path) -> None:
    (sandbox / "ap.hi").write_text("MSG stale\n$", encoding="ascii")
    agent._send_host_information(RuntimeInformation([], set(), ["queued"], [], -1, False))
    (sandbox / "ap.hi").unlink()  # the game consumed it
    agent._send_host_information(RuntimeInformation([], set(), ["fresh"], [], -1, False))
    written = (sandbox / "ap.hi").read_text(encoding="ascii")
    assert "MSG queued" in written, "the buffered message was never flushed"
    assert "MSG fresh" in written
    assert agent.host_information_buffer is None


def test_the_buffer_is_pruned_to_the_message_cap(agent: Any, sandbox: pathlib.Path) -> None:
    """Without pruning the buffer, a frozen game makes the client hoard the whole session."""
    cap = agent.contract.max_messages_per_tick
    (sandbox / "ap.hi").write_text("MSG stale\n$", encoding="ascii")
    total = cap * 2 + 10
    for i in range(total):
        agent._send_host_information(RuntimeInformation([], set(), [f"m{i}"], [], -1, False))
    buffered = agent.host_information_buffer
    assert buffered is not None
    assert len(buffered.messages) <= cap, f"buffer grew to {len(buffered.messages)} messages"
    assert buffered.messages[-1] == f"m{total - 1}", "pruning kept the oldest instead of the newest"


def test_an_idle_tick_writes_no_file(agent: Any, sandbox: pathlib.Path) -> None:
    """An empty document is ten pointless writes a second, and it blocks the next real one."""
    agent._send_host_information(RuntimeInformation([], set(), [], [], -1, False))
    assert names(sandbox) == [], "an empty ap.hi was written"


def test_an_idle_tick_does_not_stall_the_next_real_payload(agent: Any, sandbox: pathlib.Path) -> None:
    agent._send_host_information(RuntimeInformation([], set(), [], [], -1, False))
    agent._send_host_information(RuntimeInformation([], set(), ["real"], [], -1, False))
    assert (sandbox / "ap.hi").read_text(encoding="ascii") == "MSG real\n$"


# --- connection status ------------------------------------------------------

def status_row(text: str) -> str:
    return next(r for r in text.splitlines() if r.startswith("STATUS "))


def test_status_row_round_trips_through_the_contract(agent: Any, sandbox: pathlib.Path) -> None:
    opened(agent)
    agent._send_connection_status(agent._consumer(0)[1])
    written = (sandbox / "ap.cs").read_text(encoding="ascii")
    events, exit_code = agent.contract.parse_message(written)
    assert exit_code == 0, f"the contract rejects the row it just wrote: {written!r}"
    assert any(type(e).__name__ == "ConnectionStatus" for e in events)


def test_default_status_is_disconnected(agent: Any, sandbox: pathlib.Path) -> None:
    # Spec: "In its absence, the game will consider STATUS as disconnected."
    opened(agent)
    agent._send_connection_status(agent._consumer(0)[1])
    assert status_row((sandbox / "ap.cs").read_text(encoding="ascii")) == "STATUS 1"


def test_explicit_status_is_reported(agent: Any, sandbox: pathlib.Path) -> None:
    opened(agent)
    agent.htg_q.put(("status", 0))
    agent._send_connection_status(agent._consumer(0)[1])
    assert status_row((sandbox / "ap.cs").read_text(encoding="ascii")) == "STATUS 0"

    agent.htg_q.put(("status", 1))
    agent._send_connection_status(agent._consumer(1)[1])
    assert status_row((sandbox / "ap.cs").read_text(encoding="ascii")) == "STATUS 1"


# --- launch and shutdown cleanup --------------------------------------------

CLIENT_OWNED = [
    "ap.cctx", "ap.cctx.tmp", "ap.cctx.rd",
    "ap.li", "ap.li.tmp", "ap.li.rd",
    "ap.hi", "ap.hi.tmp", "ap.hi.rd",
    "ap.gi", "ap.gi.rd",
    "ap.cs", "ap.cs.tmp",
]


def test_on_start_clears_leftovers_from_a_previous_session(agent: Any, sandbox: pathlib.Path) -> None:
    """Spec: "All leftover files from previous sessions will be cleaned up by the client"."""
    for name in [*CLIENT_OWNED, "ap.gi.tmp", "ap.gs"]:
        (sandbox / name).write_text("stale", encoding="ascii")
    agent._on_start()
    assert names(sandbox) == ["ap.gs"], f"left behind: {[n for n in names(sandbox) if n != 'ap.gs']}"


def test_on_exit_removes_every_client_owned_file(agent: Any, sandbox: pathlib.Path) -> None:
    for name in [*CLIENT_OWNED, "ap.gs"]:
        (sandbox / name).write_text("x", encoding="ascii")
    agent._on_exit()
    assert names(sandbox) == ["ap.gs"], f"leaked: {[n for n in names(sandbox) if n != 'ap.gs']}"


def test_on_exit_leaves_game_owned_files_alone(agent: Any, sandbox: pathlib.Path) -> None:
    # ap.gi.tmp is the game mid-write; deleting it would corrupt a document in flight.
    (sandbox / "ap.gs").write_text("HBEAT 4\n$", encoding="ascii")
    (sandbox / "ap.gi.tmp").write_text("LOC 1\n", encoding="ascii")
    agent._on_exit()
    assert names(sandbox) == ["ap.gi.tmp", "ap.gs"]


def test_on_exit_tolerates_an_empty_sandbox(agent: Any, sandbox: pathlib.Path) -> None:
    agent._on_exit()
    assert names(sandbox) == []


def test_the_loop_cleans_up_after_itself(agent: Any, sandbox: pathlib.Path) -> None:
    """on_exit runs in the worker's own finally, so nothing can recreate files after it."""
    opened(agent)
    agent.contract.tick_time = 0.01
    thread = run_worker(agent)
    time.sleep(0.05)
    agent.close_communication()
    thread.join(timeout=2.0)
    assert not thread.is_alive(), "the loop ignored close_communication"
    assert names(sandbox) == [], f"left behind: {names(sandbox)}"


# --- the start/stop lifecycle -----------------------------------------------

def test_start_leaves_the_handshake_files_for_the_game(interface: Interface, sandbox: pathlib.Path) -> None:
    """ap.cctx and ap.li are what the game reads on launch; they must survive start().

    on_start clears the sandbox of leftovers, so it has to run before the handshake
    writes, not after them.
    """
    try:
        asyncio.run(interface.start(make_context(), LocationInformation(False, {})))
        written = names(sandbox)
    finally:
        if interface.agent is not None:
            interface.agent.close_communication()

    assert "ap.cctx" in written, f"the connection context was deleted after being written: {written}"
    assert "ap.li" in written, f"the location information was deleted after being written: {written}"


def test_start_marks_communication_open(interface: Interface, sandbox: pathlib.Path) -> None:
    try:
        asyncio.run(interface.start(make_context(), LocationInformation(False, {})))
        assert interface.agent.inspect_communication() is True
        assert interface.running is True
    finally:
        if interface.agent is not None:
            interface.agent.close_communication()


def test_stop_shuts_down_cleanly(interface: Interface, sandbox: pathlib.Path) -> None:
    async def run() -> Any:
        await interface.start(make_context(), LocationInformation(False, {}))
        agent = interface.agent
        await interface.stop()
        return agent

    agent = asyncio.run(run())
    # The agent no longer keeps a handle on its worker, so thread_exit -- set in the
    # loop's own finally -- is the only observable that the loop actually ended.
    assert agent.thread_exit.is_set(), "the worker thread outlived stop()"
    assert interface.agent is None
    assert not interface.running


def test_stop_removes_the_sandbox_files(interface: Interface, sandbox: pathlib.Path) -> None:
    async def run() -> None:
        await interface.start(make_context(), LocationInformation(False, {}))
        await interface.stop()

    asyncio.run(run())
    assert names(sandbox) == [], f"left behind: {names(sandbox)}"


def test_stop_is_idempotent(interface: Interface, sandbox: pathlib.Path) -> None:
    async def run() -> None:
        await interface.start(make_context(), LocationInformation(False, {}))
        await interface.stop()
        await interface.stop()

    asyncio.run(run())


def test_a_failed_start_is_reported_not_swallowed_silently(
    interface: Interface, sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A start that cannot complete must leave a detectable failure state.

    The except clause in ``start`` has to be a tuple; ``except A | B | C`` builds a union
    object and Python rejects it at raise time with "catching classes that do not inherit
    from BaseException is not allowed", turning any handshake error into a TypeError.

    A non-ASCII slot name used to be the trigger here. It no longer is -- the normaliser
    repairs it and the handshake succeeds -- so the failure is injected at the contract
    instead, which keeps the test about the recovery path rather than about any one
    input that happens to be rejected today.
    """
    from harness import ContractV1

    def refuse(cls: type, content_type: str, params: dict[str, Any]) -> tuple[str, int]:
        raise ValueError("injected write_content failure")

    monkeypatch.setattr(ContractV1, "write_content", classmethod(refuse))

    raised: BaseException | None = None
    try:
        asyncio.run(interface.start(make_context(), LocationInformation(False, {})))
    except BaseException as err:  # noqa: BLE001
        raised = err
    finally:
        if interface.agent is not None:
            interface.agent.close_communication()

    assert not isinstance(raised, TypeError), f"the except clause itself failed: {raised}"
    assert not interface.running, "interface still reports running after a failed start"


def test_a_non_ascii_slot_name_no_longer_fails_the_handshake(
    interface: Interface, sandbox: pathlib.Path
) -> None:
    """The policy change, from the interface's side.

    A player does not choose their YAML name with the wire format in mind, and refusing
    the connection over an accent is a worse outcome than transliterating it.
    """
    context = ConnectionContext("0.6.7", "0.0.0", "0.0.0", "Reneé", 0, {}, {}, set(), [], False)
    try:
        asyncio.run(interface.start(context, LocationInformation(False, {})))
        assert interface.running is True
        slot = [
            row for row in (sandbox / "ap.cctx").read_text(encoding="ascii").splitlines()
            if row.startswith("SLOT ")
        ]
        assert slot, "no SLOT row was written"
        assert slot[0].isascii()
    finally:
        if interface.agent is not None:
            interface.agent.close_communication()



# --- game status probing ----------------------------------------------------

def test_probe_returns_false_when_the_game_never_writes(interface: Interface, sandbox: pathlib.Path) -> None:
    assert asyncio.run(interface.probe_game_status("0.0.0", timeout=0.3)) is False


def test_probe_returns_true_when_the_heartbeat_advances(interface: Interface, sandbox: pathlib.Path) -> None:
    (sandbox / "ap.gs").write_text("HBEAT 1\n$", encoding="ascii")

    async def run() -> bool:
        async def bump() -> None:
            await asyncio.sleep(0.15)
            (sandbox / "ap.gs").write_text("HBEAT 2\n$", encoding="ascii")

        task = asyncio.create_task(bump())
        result = await interface.probe_game_status("0.0.0", timeout=2.0)
        await task
        return result

    assert asyncio.run(run()) is True


def test_probe_ignores_a_stale_unchanging_heartbeat(interface: Interface, sandbox: pathlib.Path) -> None:
    """A dead game leaves ap.gs behind. Its mere presence must not read as alive."""
    (sandbox / "ap.gs").write_text("HBEAT 7\n$", encoding="ascii")
    assert asyncio.run(interface.probe_game_status("0.0.0", timeout=0.3)) is False


def test_probe_does_not_report_a_change_from_a_transient_read_failure(
    interface: Interface, sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A locked-then-readable stale file must not read as a live game.

    read_file collapses "absent" and "unreadable" into None, so a failed read cannot be
    told apart from a game that has not started. The loop guards this by skipping None
    entirely -- neither end of the comparison is ever established from a read that
    failed -- so a transient lock costs a poll interval and nothing else. Pinned because
    the earlier shape took its baseline before the loop, where a single PermissionError
    made the next successful read of the *same stale file* look like a change.
    """
    (sandbox / "ap.gs").write_text("HBEAT 7\n$", encoding="ascii")

    real_read_text = pathlib.Path.read_text
    calls = {"n": 0}

    def flaky(self: pathlib.Path, *args: Any, **kwargs: Any) -> str:
        if self.name == "ap.gs":
            calls["n"] += 1
            if calls["n"] == 1:
                raise PermissionError(32, "held by the game")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", flaky)
    result = asyncio.run(interface.probe_game_status("0.0.0", timeout=0.5))
    monkeypatch.undo()

    assert result is False, "a transient read error was reported as the game coming alive"


def test_probe_does_not_report_a_change_from_a_torn_read(
    interface: Interface, sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A half-written ap.gs parses to heartbeat -1, which also differs from the baseline.

    Skipping None closes the unreadable path, but a torn read is not unreadable -- it
    returns a string, so read_content parses it and hands back the -1 failure sentinel.
    That is an int, so it clears the None guard and lands in the comparison as if it were
    a heartbeat value.
    """
    (sandbox / "ap.gs").write_text("HBEAT 7\n$", encoding="ascii")

    real_read_text = pathlib.Path.read_text
    calls = {"n": 0}

    def torn(self: pathlib.Path, *args: Any, **kwargs: Any) -> str:
        if self.name == "ap.gs":
            calls["n"] += 1
            if calls["n"] == 2:
                return "HBEA"  # caught mid-write
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", torn)
    result = asyncio.run(interface.probe_game_status("0.0.0", timeout=0.5))
    monkeypatch.undo()

    assert result is False, "a torn read was reported as the game coming alive"


def test_probe_leaves_no_files_behind(interface: Interface, sandbox: pathlib.Path) -> None:
    # Probing builds a whole agent; it must not disturb the sandbox a live game may own.
    (sandbox / "ap.gs").write_text("HBEAT 7\n$", encoding="ascii")
    asyncio.run(interface.probe_game_status("0.0.0", timeout=0.2))
    assert names(sandbox) == ["ap.gs"], f"probing changed the sandbox: {names(sandbox)}"


def test_probe_does_not_leave_a_poller_running(interface: Interface, sandbox: pathlib.Path) -> None:
    """The timeout must cancel the polling task, not just stop awaiting it."""
    async def run() -> int:
        await interface.probe_game_status("0.0.0", timeout=0.2)
        await asyncio.sleep(0.2)
        return len([t for t in asyncio.all_tasks() if t is not asyncio.current_task()])

    assert asyncio.run(run()) == 0


# --- incoming queue ---------------------------------------------------------

def test_consume_outgoing_drains_everything_queued(interface: Interface) -> None:
    for i in range(5):
        interface._get_queue.put(("location", i))
    interface._get_queue.put(("ack", 3))
    result = interface.consume_outgoing()
    assert result is not None
    assert result[0].locations == {0, 1, 2, 3, 4}
    assert result[0].ack == 3
    assert interface._get_queue.qsize() == 0


def test_incoming_data_survives_stop(interface: Interface, sandbox: pathlib.Path) -> None:
    """Game-side state is NOT reconstructible -- the game does not remember it."""
    async def run() -> None:
        await interface.start(make_context(), LocationInformation(False, {}))
        interface._get_queue.put(("location", 99))
        await interface.stop()

    asyncio.run(run())
    result = interface.consume_outgoing()
    assert result is not None
    assert 99 in result[0].locations


def test_receiving_never_raises_shutdown_into_the_worker(agent: Any, sandbox: pathlib.Path) -> None:
    opened(agent)
    (sandbox / "ap.gi").write_text("LOC 5\n$", encoding="ascii")
    agent.gth_q.shutdown()
    try:
        agent._receive_game_information()
    except queue.ShutDown:
        pytest.fail("queue.ShutDown escaped into the communication thread")


def test_the_worker_survives_a_serialization_failure(agent: Any, sandbox: pathlib.Path) -> None:
    """One bad payload must not kill the thread and silence the channel for the session."""
    opened(agent)
    agent.contract.tick_time = 0.01
    thread = run_worker(agent)
    agent.htg_q.put(("message", "Reneé"))  # non-ASCII: the event validator rejects it
    time.sleep(0.1)
    alive = thread.is_alive()
    agent.close_communication()
    thread.join(timeout=2.0)
    assert alive, "a rejected message killed the communication thread"


def test_heartbeat_advances_across_ticks(agent: Any, sandbox: pathlib.Path) -> None:
    """Spec: "Heartbeat, starts with zero and increases by 1 on every write tick"."""
    opened(agent)
    agent.contract.tick_time = 0.01
    thread = run_worker(agent)
    beats: list[int] = []
    deadline = time.perf_counter() + 2.0
    while time.perf_counter() < deadline and len(beats) < 3:
        try:
            rows = (sandbox / "ap.cs").read_text(encoding="ascii").splitlines()
        except OSError:
            continue
        beat = next((int(r.split()[1]) for r in rows if r.startswith("HBEAT ")), None)
        if beat is not None and (not beats or beat != beats[-1]):
            beats.append(beat)
    agent.close_communication()
    thread.join(timeout=2.0)

    assert len(beats) >= 2, f"heartbeat never advanced past {beats}; the game will treat the client as frozen"
    assert beats == sorted(beats)
