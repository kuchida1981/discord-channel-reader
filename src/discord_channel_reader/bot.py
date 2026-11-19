from __future__ import annotations

import asyncio
import logging

import discord

from .config import Config
from .player import play_wav
from .text_normalize import normalize
from .voicevox import VoicevoxClient
from .worker import SpeechWorker

log = logging.getLogger(__name__)


def build_mentions(message: discord.Message) -> dict[str, str]:
    table: dict[str, str] = {}
    for u in message.mentions:
        table[f"<@{u.id}>"] = u.display_name
        table[f"<@!{u.id}>"] = u.display_name
    for r in message.role_mentions:
        table[f"<@&{r.id}>"] = r.name
    for c in message.channel_mentions:
        table[f"<#{c.id}>"] = c.name
    return table


class ReaderClient(discord.Client):
    def __init__(self, config: Config) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.config = config
        self.voicevox = VoicevoxClient(config.voicevox_url, config.voicevox_speaker_id)

        async def _play(wav: bytes) -> None:
            await play_wav(wav, config.player_command)

        self.worker = SpeechWorker(
            self.voicevox.synthesize,
            _play,
            queue_max=config.queue_max,
            mute_file=config.mute_file,
        )
        self._worker_task: asyncio.Task[None] | None = None

    async def setup_hook(self) -> None:
        self._worker_task = asyncio.create_task(self.worker.run())

    async def close(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
        await self.voicevox.close()
        await super().close()

    async def on_ready(self) -> None:
        allowed = self.config.allowed_user_ids
        log.info(
            "ログイン完了: %s / 対象チャンネル=%s / 対象ユーザー=%s",
            self.user,
            self.config.target_channel_id,
            f"{len(allowed)}人 {sorted(allowed)}" if allowed else "制限なし",
        )

    def should_read(self, message: discord.Message) -> bool:
        if message.channel.id != self.config.target_channel_id:
            return False
        if self.user is not None and message.author.id == self.user.id:
            return False
        allowed = self.config.allowed_user_ids
        if allowed and message.author.id not in allowed:
            return False
        if message.author.bot or message.webhook_id is not None:
            return self.config.read_bot_messages
        return True

    async def on_message(self, message: discord.Message) -> None:
        if not self.should_read(message):
            return
        text = normalize(
            message.content,
            mentions=build_mentions(message),
            has_attachments=bool(message.attachments),
            max_chars=self.config.max_chars,
        )
        if not text:
            return
        if self.config.read_author_name:
            text = f"{message.author.display_name}、{text}"
        log.info("受信: %d 文字を読み上げキューへ", len(text))
        self.worker.enqueue(text)


def run(config: Config) -> None:
    client = ReaderClient(config)
    # log_handler=None: __main__ で設定済みの stdout ログを使う
    client.run(config.discord_bot_token, log_handler=None)
