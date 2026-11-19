from discord_channel_reader.text_normalize import normalize


def test_plain():
    assert normalize("こんにちは") == "こんにちは"


def test_code_block():
    assert normalize("前\n```py\nprint(1)\n```\n後") == "前 コードブロックを省略 後"


def test_unclosed_code_block():
    assert "print" not in normalize("```py\nprint(1)")


def test_url():
    assert normalize("見て https://example.com/a?b=1 これ") == "見て リンク これ"


def test_mentions_resolved_and_unresolved():
    m = {"<@1>": "太郎", "<#2>": "general"}
    assert normalize("<@1> <#2> <@3> おはよう", mentions=m) == "太郎 general おはよう"


def test_custom_emoji_and_decoration():
    assert normalize("**太字** <:smile:123> ~~取消~~ `code`") == "太字 取消 code"


def test_attachment_only():
    assert normalize("", has_attachments=True) == "添付ファイルがあります"


def test_empty():
    assert normalize("   ") == ""
    assert normalize("<:a:1>") == ""


def test_truncate():
    out = normalize("あ" * 300, max_chars=10)
    assert out == "あ" * 10 + "、以下省略"
