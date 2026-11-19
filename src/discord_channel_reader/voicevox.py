from __future__ import annotations

import asyncio
import logging

import aiohttp

log = logging.getLogger(__name__)


class VoicevoxError(Exception):
    pass


class VoicevoxClient:
    def __init__(
        self,
        base_url: str,
        speaker_id: int,
        *,
        retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._speaker = speaker_id
        self._retries = max(1, retries)
        self._retry_delay = retry_delay
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        if self._session is not None and self._owns_session:
            await self._session.close()

    async def _synthesize_once(self, text: str) -> bytes:
        session = await self._get_session()
        params = {"text": text, "speaker": str(self._speaker)}
        async with session.post(f"{self._base_url}/audio_query", params=params) as r:
            r.raise_for_status()
            query = await r.json()
        async with session.post(
            f"{self._base_url}/synthesis",
            params={"speaker": str(self._speaker)},
            json=query,
        ) as r:
            r.raise_for_status()
            return await r.read()

    async def synthesize(self, text: str) -> bytes:
        """text を WAV に合成する。リトライしても失敗したら VoicevoxError。"""
        last: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                return await self._synthesize_once(text)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                last = e
                log.warning("VOICEVOX 合成失敗 (%d/%d): %s", attempt, self._retries, e)
                if attempt < self._retries:
                    await asyncio.sleep(self._retry_delay)
        raise VoicevoxError(f"VOICEVOX 合成に失敗: {last}") from last
