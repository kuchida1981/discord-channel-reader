import pytest

from discord_channel_reader.config import Config, ConfigError


def test_defaults():
    c = Config.from_env({"DISCORD_BOT_TOKEN": "t", "TARGET_CHANNEL_ID": "42"})
    assert c.target_channel_id == 42
    assert c.voicevox_url == "http://127.0.0.1:50021"
    assert c.voicevox_speaker_id == 1
    assert c.read_bot_messages is True
    assert c.read_author_name is False
    assert c.max_chars == 200
    assert c.queue_max == 20
    assert c.player_command == "paplay"


def test_overrides():
    c = Config.from_env(
        {
            "DISCORD_BOT_TOKEN": "t",
            "TARGET_CHANNEL_ID": "1",
            "VOICEVOX_URL": "http://h:1/",
            "READ_BOT_MESSAGES": "false",
            "READ_AUTHOR_NAME": "true",
            "MAX_CHARS": "50",
        }
    )
    assert c.voicevox_url == "http://h:1"
    assert c.read_bot_messages is False
    assert c.read_author_name is True
    assert c.max_chars == 50


@pytest.mark.parametrize(
    "env",
    [
        {"TARGET_CHANNEL_ID": "1"},
        {"DISCORD_BOT_TOKEN": "t"},
        {"DISCORD_BOT_TOKEN": "t", "TARGET_CHANNEL_ID": "x"},
        {"DISCORD_BOT_TOKEN": "t", "TARGET_CHANNEL_ID": "1", "READ_BOT_MESSAGES": "maybe"},
        {"DISCORD_BOT_TOKEN": "t", "TARGET_CHANNEL_ID": "1", "QUEUE_MAX": "0"},
    ],
)
def test_invalid(env):
    with pytest.raises(ConfigError):
        Config.from_env(env)


def test_token_not_in_repr():
    c = Config.from_env({"DISCORD_BOT_TOKEN": "SECRET", "TARGET_CHANNEL_ID": "1"})
    assert "SECRET" not in repr(c)
