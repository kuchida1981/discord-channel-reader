from __future__ import annotations

import asyncio
import logging
import os
import shlex
import tempfile

log = logging.getLogger(__name__)


class PlayerError(Exception):
    pass


async def play_wav(wav: bytes, command: str = "paplay") -> None:
    """WAV を一時ファイル経由で再生コマンドに渡し、終了まで待つ。"""
    argv = shlex.split(command)
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="dcr-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(wav)
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as e:
            raise PlayerError(f"再生コマンドを起動できません: {e}") from e
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            msg = stderr.decode(errors="replace").strip()
            raise PlayerError(f"再生コマンドが異常終了 ({proc.returncode}): {msg}")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
