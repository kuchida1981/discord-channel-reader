from __future__ import annotations

import re
from collections.abc import Mapping

_CODE_BLOCK = re.compile(r"```.*?(?:```|$)", re.DOTALL)
_URL = re.compile(r"https?://\S+")
_MENTION = re.compile(r"<(@[!&]?|#)(\d+)>")
_CUSTOM_EMOJI = re.compile(r"<a?:\w+:\d+>")
_SPECIAL_MENTION = re.compile(r"@(everyone|here)")
_INLINE_CODE = re.compile(r"`+([^`]*)`+")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_QUOTE = re.compile(r"^\s*>{1,3}\s?", re.MULTILINE)
_DECOR = re.compile(r"(\*\*|__|~~|\|\||\*|_(?=\S)|(?<=\S)_)")
_SPACES = re.compile(r"\s+")

CODE_PLACEHOLDER = "コードブロックを省略"
URL_PLACEHOLDER = "リンク"
ATTACHMENT_TEXT = "添付ファイルがあります"
TRUNCATED_SUFFIX = "以下省略"


def normalize(
    text: str,
    *,
    mentions: Mapping[str, str] | None = None,
    has_attachments: bool = False,
    max_chars: int = 200,
) -> str:
    """Discord メッセージを読み上げ用に整形する。空文字なら読み上げ不要。

    mentions: "<@123>" のような原文トークン → 表示名。解決できないものは省略する。
    """
    mentions = mentions or {}
    text = _CODE_BLOCK.sub(f" {CODE_PLACEHOLDER} ", text)
    text = _URL.sub(f" {URL_PLACEHOLDER} ", text)

    def _mention(m: re.Match[str]) -> str:
        name = mentions.get(m.group(0))
        return f" {name} " if name else " "

    text = _MENTION.sub(_mention, text)
    text = _CUSTOM_EMOJI.sub(" ", text)
    text = _SPECIAL_MENTION.sub(" ", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _HEADING.sub("", text)
    text = _QUOTE.sub("", text)
    text = _DECOR.sub("", text)
    text = _SPACES.sub(" ", text).strip()

    if not text:
        return ATTACHMENT_TEXT if has_attachments else ""
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "、" + TRUNCATED_SUFFIX
    return text
