import asyncio

from discord_channel_reader.worker import SpeechWorker


def make(tmp_path, synth=None, queue_max=3):
    played: list[bytes] = []

    async def default_synth(t: str) -> bytes:
        return t.encode()

    async def play(b: bytes) -> None:
        played.append(b)

    w = SpeechWorker(synth or default_synth, play, queue_max=queue_max, mute_file=tmp_path / "muted")
    return w, played


def test_drops_oldest(tmp_path):
    w, _ = make(tmp_path, queue_max=2)
    for t in "abc":
        w.enqueue(t)
    assert list(w._items) == ["b", "c"]


def test_mute_toggle(tmp_path):
    w, _ = make(tmp_path)
    (tmp_path / "muted").touch()
    assert w.enqueue("a") is False
    (tmp_path / "muted").unlink()
    assert w.enqueue("a") is True


async def test_run_serial_order(tmp_path):
    w, played = make(tmp_path)
    for t in "abc":
        w.enqueue(t)
    task = asyncio.create_task(w.run())
    for _ in range(50):
        if len(played) == 3:
            break
        await asyncio.sleep(0.01)
    task.cancel()
    assert played == [b"a", b"b", b"c"]


async def test_error_does_not_stop_worker(tmp_path):
    async def synth(t: str) -> bytes:
        if t == "bad":
            raise RuntimeError("boom")
        return t.encode()

    w, played = make(tmp_path, synth=synth)
    w.enqueue("bad")
    w.enqueue("ok")
    task = asyncio.create_task(w.run())
    for _ in range(50):
        if played:
            break
        await asyncio.sleep(0.01)
    assert not task.done()
    task.cancel()
    assert played == [b"ok"]
