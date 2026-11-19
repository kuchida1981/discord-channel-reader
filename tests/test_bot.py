from types import SimpleNamespace

from discord_channel_reader.bot import ReaderClient
from discord_channel_reader.config import Config

CHANNEL = 100
SELF_ID = 999


def make_client(**kw):
    cfg = Config(discord_bot_token="t", target_channel_id=CHANNEL, **kw)
    client = ReaderClient(cfg)
    client._connection.user = SimpleNamespace(id=SELF_ID)
    return client


def msg(author_id=1, channel_id=CHANNEL, bot=False, webhook_id=None):
    return SimpleNamespace(
        channel=SimpleNamespace(id=channel_id),
        author=SimpleNamespace(id=author_id, bot=bot),
        webhook_id=webhook_id,
    )


def test_no_restriction_reads_anyone():
    c = make_client()
    assert c.should_read(msg(author_id=1))
    assert c.should_read(msg(author_id=2))


def test_allowed_user_passes():
    c = make_client(allowed_user_ids=frozenset({1}))
    assert c.should_read(msg(author_id=1))


def test_non_allowed_user_blocked():
    c = make_client(allowed_user_ids=frozenset({1}))
    assert not c.should_read(msg(author_id=2))


def test_other_channel_blocked():
    c = make_client(allowed_user_ids=frozenset({1}))
    assert not c.should_read(msg(author_id=1, channel_id=CHANNEL + 1))


def test_self_blocked_even_if_allowed():
    c = make_client(allowed_user_ids=frozenset({SELF_ID}))
    assert not c.should_read(msg(author_id=SELF_ID))


def test_bot_message_follows_read_bot_messages():
    assert make_client(read_bot_messages=True).should_read(msg(bot=True))
    assert not make_client(read_bot_messages=False).should_read(msg(bot=True))


def test_bot_not_in_allowlist_blocked():
    c = make_client(allowed_user_ids=frozenset({1}), read_bot_messages=True)
    assert not c.should_read(msg(author_id=2, bot=True))


def test_allowed_bot_respects_read_bot_messages():
    allowed = frozenset({2})
    assert make_client(allowed_user_ids=allowed, read_bot_messages=True).should_read(
        msg(author_id=2, bot=True)
    )
    assert not make_client(allowed_user_ids=allowed, read_bot_messages=False).should_read(
        msg(author_id=2, bot=True)
    )
