from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from pathlib import Path

log = logging.getLogger(__name__)

Synthesizer = Callable[[str], Awaitable[bytes]]
Player = Callable[[bytes], Awaitable[None]]


class SpeechWorker:
    """上限付きキュー + 1 件ずつの直列再生。あふれたら古いものを捨てる。"""

    def __init__(
        self,
        synthesize: Synthesizer,
        play: Player,
        *,
        queue_max: int = 20,
        mute_file: Path | None = None,
    ) -> None:
        self._synthesize = synthesize
        self._play = play
        self._queue_max = queue_max
        self._mute_file = mute_file
        self._items: deque[str] = deque()
        self._wakeup = asyncio.Event()

    def is_muted(self) -> bool:
        return self._mute_file is not None and self._mute_file.exists()

    def enqueue(self, text: str) -> bool:
        if self.is_muted():
            log.info("ミュート中のため破棄")
            return False
        while len(self._items) >= self._queue_max:
            dropped = self._items.popleft()
            log.warning("キュー上限超過のため古い発言を破棄: %.30s", dropped)
        self._items.append(text)
        self._wakeup.set()
        return True

    def pending(self) -> int:
        return len(self._items)

    async def process_one(self, text: str) -> None:
        if self.is_muted():
            log.info("ミュート中のため破棄")
            return
        try:
            wav = await self._synthesize(text)
            await self._play(wav)
        except asyncio.CancelledError:
            raise
        except Exception:
            # サービス全体は落とさず、このメッセージだけ破棄して次へ進む
            log.exception("読み上げに失敗したため破棄: %.30s", text)

    async def run(self) -> None:
        while True:
            while not self._items:
                self._wakeup.clear()
                await self._wakeup.wait()
            await self.process_one(self._items.popleft())
