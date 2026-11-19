from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    pass


def default_mute_file() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "discord-channel-reader" / "muted"


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    v = value.strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    raise ConfigError(f"真偽値として解釈できません: {value!r}")


def _int(env: Mapping[str, str], key: str, default: int, minimum: int = 1) -> int:
    raw = env.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        v = int(raw)
    except ValueError:
        raise ConfigError(f"{key} は整数で指定してください") from None
    if v < minimum:
        raise ConfigError(f"{key} は {minimum} 以上にしてください")
    return v


def _user_ids(env: Mapping[str, str], key: str) -> frozenset[int]:
    raw = env.get(key)
    if raw is None or raw.strip() == "":
        return frozenset()
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            raise ConfigError(f"{key} は整数のカンマ区切りで指定してください") from None
    return frozenset(ids)


@dataclass(frozen=True)
class Config:
    # トークンは repr に出さない
    discord_bot_token: str = field(repr=False)
    target_channel_id: int
    voicevox_url: str = "http://127.0.0.1:50021"
    voicevox_speaker_id: int = 1
    read_bot_messages: bool = True
    read_author_name: bool = False
    max_chars: int = 200
    queue_max: int = 20
    player_command: str = "paplay"
    mute_file: Path = field(default_factory=default_mute_file)
    allowed_user_ids: frozenset[int] = frozenset()

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        env = os.environ if env is None else env
        token = env.get("DISCORD_BOT_TOKEN", "").strip()
        if not token:
            raise ConfigError("DISCORD_BOT_TOKEN が未設定です")
        channel = env.get("TARGET_CHANNEL_ID", "").strip()
        if not channel:
            raise ConfigError("TARGET_CHANNEL_ID が未設定です")
        try:
            channel_id = int(channel)
        except ValueError:
            raise ConfigError("TARGET_CHANNEL_ID は整数で指定してください") from None
        url = (env.get("VOICEVOX_URL") or "http://127.0.0.1:50021").strip().rstrip("/")
        return cls(
            discord_bot_token=token,
            target_channel_id=channel_id,
            voicevox_url=url,
            voicevox_speaker_id=_int(env, "VOICEVOX_SPEAKER_ID", 1, minimum=0),
            read_bot_messages=_bool(env.get("READ_BOT_MESSAGES"), True),
            read_author_name=_bool(env.get("READ_AUTHOR_NAME"), False),
            max_chars=_int(env, "MAX_CHARS", 200),
            queue_max=_int(env, "QUEUE_MAX", 20),
            player_command=(env.get("PLAYER_COMMAND") or "paplay").strip(),
            allowed_user_ids=_user_ids(env, "ALLOWED_USER_IDS"),
        )
