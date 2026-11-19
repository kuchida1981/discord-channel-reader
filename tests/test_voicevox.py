import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from discord_channel_reader.voicevox import VoicevoxClient, VoicevoxError


async def _server(fail_first: int = 0):
    state = {"n": 0, "seen": {}}

    async def audio_query(request: web.Request):
        state["n"] += 1
        if state["n"] <= fail_first:
            return web.Response(status=500)
        state["seen"]["query"] = dict(request.query)
        return web.json_response({"q": 1})

    async def synthesis(request: web.Request):
        state["seen"]["synth"] = dict(request.query)
        state["seen"]["body"] = await request.json()
        return web.Response(body=b"RIFFwav")

    app = web.Application()
    app.router.add_post("/audio_query", audio_query)
    app.router.add_post("/synthesis", synthesis)
    server = TestServer(app)
    await server.start_server()
    return server, state


async def test_synthesize_ok():
    server, state = await _server()
    client = VoicevoxClient(str(server.make_url("")), 3, retry_delay=0)
    try:
        assert await client.synthesize("テスト") == b"RIFFwav"
    finally:
        await client.close()
        await server.close()
    assert state["seen"]["query"] == {"text": "テスト", "speaker": "3"}
    assert state["seen"]["synth"] == {"speaker": "3"}
    assert state["seen"]["body"] == {"q": 1}


async def test_retry_then_success():
    server, state = await _server(fail_first=2)
    client = VoicevoxClient(str(server.make_url("")), 1, retries=3, retry_delay=0)
    try:
        assert await client.synthesize("x") == b"RIFFwav"
    finally:
        await client.close()
        await server.close()
    assert state["n"] == 3


async def test_retries_exhausted():
    server, _ = await _server(fail_first=99)
    client = VoicevoxClient(str(server.make_url("")), 1, retries=2, retry_delay=0)
    try:
        with pytest.raises(VoicevoxError):
            await client.synthesize("x")
    finally:
        await client.close()
        await server.close()


async def test_connection_refused():
    client = VoicevoxClient("http://127.0.0.1:1", 1, retries=2, retry_delay=0)
    try:
        with pytest.raises(VoicevoxError):
            await client.synthesize("x")
    finally:
        await client.close()
