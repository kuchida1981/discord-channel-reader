# セットアップ手順

## 1. Discord 側(手動)

1. [Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成し、Bot を追加する。
2. Bot 設定で **Message Content Intent** をオンにする。
3. Bot トークンを発行する(チャット・Git に貼らない。手順 4 の env ファイルにのみ貼る)。
4. 招待 URL でサーバーに追加する(送信権限なし):
   `https://discord.com/oauth2/authorize?client_id=<CLIENT_ID>&scope=bot&permissions=66560`
5. 対象チャンネルの権限で、bot が `ai-agent-messages` を見られることを確認する。
6. Discord の開発者モードをオンにし、チャンネルを右クリックして ID をコピーする。

## 2. env ファイル

```
mkdir -p ~/.config/discord-channel-reader
cp deploy/env.example ~/.config/discord-channel-reader/env
chmod 600 ~/.config/discord-channel-reader/env
$EDITOR ~/.config/discord-channel-reader/env   # DISCORD_BOT_TOKEN と TARGET_CHANNEL_ID を設定
```

特定ユーザーのメッセージだけ読み上げたい場合は、任意で `ALLOWED_USER_IDS` を設定する(カンマ区切り。空なら制限なし)。
ユーザー ID は、開発者モードをオンにした状態でユーザーを右クリックし「ユーザーIDをコピー」で取得できる。

```
ALLOWED_USER_IDS=123456789012345678,987654321098765432
```

## 3. 環境構築と動作確認

```
uv sync
make test
make say TEXT="動作確認です"
```

## 4. systemd への配置 (Makefile)

VOICEVOX は既存の `voicevox-engine.service` (systemd user) を前提にしている。env ファイル(手順 2)作成後に実行する。

```
make install
```

パスや VOICEVOX の設定が異なる場合は変数を指定する。

```
make install REPO_PATH=... UNIT_DIR=... VOICEVOX_URL=... VOICEVOX_UNIT=...
```

```
loginctl enable-linger $USER   # ログインなしで常駐させる
make status
make logs
```

削除は `make uninstall`。

## 5. ミュート切替

```
make mute     # 停止 (再起動不要)
make unmute   # 再開
```
