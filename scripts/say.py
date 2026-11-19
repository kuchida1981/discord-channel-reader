"""VOICEVOX 合成 + 再生の単体動作確認: uv run python scripts/say.py "テキスト" """
import argparse
import asyncio
import os

from discord_channel_reader.player import play_wav
from discord_channel_reader.voicevox import VoicevoxClient


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("text")
    p.add_argument("--url", default=os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021"))
    p.add_argument("--speaker", type=int, default=int(os.environ.get("VOICEVOX_SPEAKER_ID", "1")))
    p.add_argument("--player", default=os.environ.get("PLAYER_COMMAND", "paplay"))
    a = p.parse_args()
    client = VoicevoxClient(a.url, a.speaker)
    try:
        wav = await client.synthesize(a.text)
        print(f"合成完了: {len(wav)} bytes")
        await play_wav(wav, a.player)
        print("再生完了")
    finally:
        await client.close()


asyncio.run(main())
