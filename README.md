# discord-channel-reader

Discord の特定チャンネル(`ai-agent-messages`)に届いたメッセージを、ローカルの VOICEVOX で読み上げる常駐サービス。ボイスチャンネルには参加せず、メッセージも送信しない。

- 構成: discord.py (on_message) → 整形 → 上限付きキュー → VOICEVOX → `paplay`
- 常駐: systemd (user)。unit は `make install` で配置
- 手順: [docs/setup.md](docs/setup.md)

## 開発

```
uv sync
make test
make say TEXT="動作確認です"
```

## 常駐サービス

```
make install     # unit を展開・配置し enable --now
make status / make logs
make uninstall
```

変数は上書き可能: `make install REPO_PATH=... UNIT_DIR=... VOICEVOX_URL=... VOICEVOX_UNIT=...`

## ミュート

```
make mute     # 停止 (再起動不要)
make unmute   # 再開
```

## 設定

`deploy/env.example` を参照。トークンは `~/.config/discord-channel-reader/env` (`chmod 600`) のみに置く。

特定ユーザーの発言だけ読み上げるには `ALLOWED_USER_IDS` にカンマ区切りでユーザー ID を指定する(空なら全員対象)。ID は Discord の開発者モードをオンにし、ユーザーを右クリック →「ユーザーIDをコピー」で取得できる。

## Terraform を採用しなかった理由

- Discord Bot の作成・サーバーへの招待には API がなく、手動作業になる(`docs/setup.md` 参照)。Terraform で管理できる範囲が実質ない。
- ローカルの systemd unit を 1 つ配置するだけなら、`Makefile` + `install` の方がシンプル。
- state ファイルの管理(トークン等が紛れ込むリスクを含む)が不要になる。
