# discord-channel-reader 設計・実装メモ

Antigravity CLI に渡す設計・実装メモ。Discord の `ai-agent-messages` チャンネルに届いたメッセージを、ローカル Ubuntu 上の VOICEVOX で読み上げる。ボイスチャンネルには参加しない。

---

## 0. このメモの使い方(Antigravity CLI への指示)

- 実装の前に「3. 事前確認」を実行して結果を報告する。前提と違う点があれば、実装を進める前に報告する。
- Discord bot のトークンは、チャット・ログ・リポジトリ・Terraform の state のどこにも出さない。値を聞かれても貼らない。
- 「9. 手動で行う作業」に当たる箇所はコマンドで代行しようとせず、手順だけをユーザーに提示する。
- 「11. 受け入れ条件」を満たすまでを 1 つの区切りとする。

---

## 1. 目的とスコープ

**目的**: `ai-agent-messages` チャンネルに入ってきたメッセージを、すべてではなく「読ませたいもの」を中心に、自動で読み上げる。

**スコープ内**
- 特定の 1 チャンネルの新着メッセージ監視(人間・他の bot・Webhook の投稿を含められる)
- VOICEVOX エンジン(ローカル)による音声合成と、ローカルスピーカーでの再生
- systemd (user) による常時稼働。VOICEVOX との依存関係を設定する
- 可能な範囲の IaC(Terraform)

**スコープ外**
- ボイスチャンネルへの参加・配信(ユーザーは常時 VC に入れないため採用しない)
- クラウド / VM でのホスティング(ホストはローカルの Ubuntu)
- 複数チャンネル・複数サーバー対応(将来の拡張)

---

## 2. 前提(ユーザーから聞いた内容)

- ホストは Ubuntu で、常時起動している。
- VOICEVOX は常に起動している。ただし起動方法(Docker か、バイナリか、systemd か)は未確認。
- ユーザーは Discord サーバーに bot を招待する権限(サーバー管理)を持っている想定。未確認なら確認する。
- ユーザーは Ubuntu・Arch Linux・Mac を併用していて、このサービスは Ubuntu で動かす。

---

## 3. 事前確認(実装前にやること)

次を確認し、結果を短くまとめて報告する。

1. `python3 --version`(3.11 以上が望ましい)、`uv --version` の有無
2. VOICEVOX エンジンの起動方法: `systemctl --user list-units | grep -i voicevox`、`docker ps`、`ss -ltnp | grep 50021`
3. VOICEVOX の疎通: `curl -s http://127.0.0.1:50021/version`
4. 音声サーバー: `pactl info`(PipeWire の PulseAudio 互換か PulseAudio か)、`which paplay pw-play aplay`
5. 再生テスト: VOICEVOX で短い文を合成した WAV を `paplay` で鳴らして、音が出ることをユーザーに確認してもらう
6. `loginctl show-user $USER | grep Linger`(linger の状態)
7. `terraform version` の有無

---

## 4. 命名

| 項目 | 名前 |
|---|---|
| リポジトリ / ディレクトリ(推奨) | `discord-channel-reader` |
| Python パッケージ | `discord_channel_reader` |
| systemd unit(本体) | `discord-channel-reader.service` |
| systemd unit(VOICEVOX。未管理の場合のみ作る) | `voicevox-engine.service` |
| 設定ディレクトリ | `~/.config/discord-channel-reader/` |
| 状態ディレクトリ | `~/.local/state/discord-channel-reader/` |

**別案**: `ai-agent-messages-reader`(チャンネル名に寄せる)、`channel-voice-reader`(Discord 以外にも広げる)、`chanvox`(短い)。
配置場所の推奨は `~/src/discord-channel-reader`。ユーザーに既存の置き場の慣習があればそれに合わせる。

---

## 5. アーキテクチャ

```
Discord Gateway ──(WebSocket)──> discord.py bot (on_message)
                                      │ 対象チャンネルID のみ通す
                                      ▼
                              text_normalize(整形・省略)
                                      ▼
                              asyncio.Queue(上限あり)
                                      ▼ (1 件ずつ)
                      VOICEVOX /audio_query → /synthesis (WAV)
                                      ▼
                         paplay / pw-play で再生(ローカル)
```

- bot は **メッセージを受け取るだけ**で、メッセージの送信・VC への接続はしない。
- 再生は 1 件ずつ直列にして、音声が重ならないようにする。

---

## 6. 実装方針

**技術**: Python 3.12 目安、`uv` で管理、`discord.py`、`aiohttp`(VOICEVOX API)、標準の `asyncio.subprocess`(再生)。

**ディレクトリ構成**

```
discord-channel-reader/
├─ README.md
├─ pyproject.toml
├─ .gitignore                  # .env, *.tfstate*, .terraform/ など
├─ src/discord_channel_reader/
│  ├─ __main__.py              # エントリポイント
│  ├─ config.py                # 環境変数の読み込みと検証
│  ├─ bot.py                   # discord.Client、on_message
│  ├─ text_normalize.py        # 読み上げ用の文章整形
│  ├─ voicevox.py              # VOICEVOX API クライアント
│  ├─ player.py                # WAV の再生
│  └─ worker.py                # キューと直列再生
├─ tests/
│  ├─ test_text_normalize.py
│  └─ test_voicevox.py         # HTTP はモックする
├─ scripts/
│  └─ say.py                   # VOICEVOX + 再生だけの動作確認用
├─ deploy/
│  ├─ env.example              # 値は空。トークンは書かない
│  └─ systemd/
│     ├─ discord-channel-reader.service.tftpl
│     └─ voicevox-engine.service.tftpl   # VOICEVOX が未管理の場合のみ使う
├─ infra/
│  └─ terraform/
│     ├─ host/                 # systemd unit の配置と有効化
│     └─ discord/              # (任意)チャンネル・権限の管理
└─ docs/
   └─ setup.md                 # 手動手順(bot 作成、招待など)
```

**設定項目(環境変数)**

| 変数 | 内容 | 既定 |
|---|---|---|
| `DISCORD_BOT_TOKEN` | bot トークン(必須。env ファイルのみ) | なし |
| `TARGET_CHANNEL_ID` | 対象チャンネル ID(必須) | なし |
| `VOICEVOX_URL` | VOICEVOX のベース URL | `http://127.0.0.1:50021` |
| `VOICEVOX_SPEAKER_ID` | 話者 ID | `1` |
| `READ_BOT_MESSAGES` | bot・Webhook の投稿を読むか | `true` |
| `READ_AUTHOR_NAME` | 投稿者名を前置きで読むか | `false` |
| `MAX_CHARS` | 1 件あたりの読み上げ文字数の上限 | `200` |
| `QUEUE_MAX` | キューの上限。超えたら古いものを捨てる | `20` |
| `PLAYER_COMMAND` | 再生コマンド | `paplay` |

**読み上げ前の整形(`text_normalize`)**
- コードブロック(```)は「コードブロックを省略」に置き換える
- URL は「リンク」に置き換える
- メンション(`<@id>`、`<#id>`)は表示名に直す。解決できなければ省略する
- カスタム絵文字(`<:name:id>`)と装飾記号は取り除く
- 添付ファイルのみの投稿は「添付ファイルがあります」と読む
- `MAX_CHARS` を超えたら切り詰めて「以下省略」を付ける
- 空になったら読み上げない

**挙動**
- メッセージの編集・削除は無視する(編集後の再読み上げはしない)
- 自分自身(bot 自身)の投稿は必ず除外する
- VOICEVOX が応答しないときは、そのメッセージを破棄してログに残す。数回のリトライ後も駄目なら破棄して次へ進み、サービス全体は落とさない
- ミュート手段: `~/.local/state/discord-channel-reader/muted` ファイルがあるあいだは読み上げない。`touch` と `rm` で切り替えられる(再起動不要)
- ログは stdout に出して journald で見る(`journalctl --user -u discord-channel-reader`)

**VOICEVOX API の流れ**
1. `POST /audio_query?text=<text>&speaker=<id>` → クエリ JSON
2. `POST /synthesis?speaker=<id>` に JSON を渡す → WAV
3. WAV を一時ファイル(または標準入力)経由で再生コマンドに渡す

---

## 7. systemd (user) 設計

**配置**: `~/.config/systemd/user/`

**`discord-channel-reader.service`(方針)**

```ini
[Unit]
Description=Discord channel reader (VOICEVOX)
# VOICEVOX が systemd 管理下にあるなら Requires/After を設定する
Requires=voicevox-engine.service
After=voicevox-engine.service network-online.target
Wants=network-online.target
# 音声サーバー(PipeWire の場合の例。pactl info で確認して合わせる)
Wants=pipewire-pulse.service
After=pipewire-pulse.service

[Service]
Type=simple
WorkingDirectory=%h/src/discord-channel-reader
EnvironmentFile=%h/.config/discord-channel-reader/env
# VOICEVOX の疎通を待つ(最大 60 秒程度)
ExecStartPre=/bin/sh -c 'for i in $(seq 1 30); do curl -sf http://127.0.0.1:50021/version >/dev/null && exit 0; sleep 2; done; exit 1'
ExecStart=%h/src/discord-channel-reader/.venv/bin/python -m discord_channel_reader
Restart=always
RestartSec=5
# 起動を連打しすぎない
StartLimitIntervalSec=300
StartLimitBurst=10

[Install]
WantedBy=default.target
```

**VOICEVOX との依存関係の扱い**
- **すでに systemd (user) で管理されている場合**: そのユニット名を `Requires=` と `After=` に指定する。VOICEVOX を再起動すると本サービスも追従する(`Requires=`)。
- **Docker などで systemd の外にある場合**: `Requires=` は使えないので、`ExecStartPre` の疎通待ちに加えて、起動後は VOICEVOX 側の応答がなくても本サービスは落とさない作りにする(上の「VOICEVOX が応答しないとき」参照)。
- **管理を systemd に寄せたい場合(任意の提案)**: `voicevox-engine.service` を新しく作る。ユーザーの現在の起動方法を壊さないよう、必ずユーザーに確認してから行う。

**常時稼働のための設定**
- `loginctl enable-linger $USER` で、ログインしなくてもユーザーの systemd が起動するようにする。
- 音声は、そのユーザーの PipeWire/PulseAudio が動いている必要がある。linger のみで音が出るか、再起動後に実機で確認する(受け入れ条件)。

**env ファイル**: `~/.config/discord-channel-reader/env`、パーミッションは `600`。`deploy/env.example` をひな形にする。

---

## 8. IaC(Terraform)の方針

Terraform に任せられる範囲は限られている。無理に全部入れず、次のように分ける。

| 対象 | Terraform | 備考 |
|---|---|---|
| systemd (user) unit の生成・配置・有効化 | ○(`infra/terraform/host`) | 下記の方式 |
| Discord チャンネルや権限の管理 | △ 任意(`infra/terraform/discord`) | 下記の注意 |
| Discord アプリケーション(bot)の作成、トークン発行 | × | Developer Portal で手動 |
| bot のサーバーへの招待 | × | OAuth2 の URL を開いて手動 |
| トークンを入れた env ファイル | × | state にトークンが残るので Terraform には入れない |

**`infra/terraform/host`(ローカルホスト)**
- `hashicorp/local` の `local_file` で、`.tftpl` テンプレートから unit ファイルを `~/.config/systemd/user/` に生成する。
- `terraform_data`(`null_resource` でも可)の `local-exec` で `systemctl --user daemon-reload` と `enable --now` を実行する。ユニット内容のハッシュを `triggers_replace` に入れて、変更時だけ再実行する。
- 変数: リポジトリの配置パス、VOICEVOX の URL、依存先のユニット名、VOICEVOX を systemd 管理にするかどうか。
- これは Terraform の標準的な使い方ではない(ローカル構成管理)。扱いにくい場合は `deploy/install.sh` か `Makefile` にフォールバックしてよい。その場合は理由を README に書く。

**`infra/terraform/discord`(任意)**
- Discord 用のコミュニティ製プロバイダ(Terraform Registry に複数ある。採用前に、メンテ状況、対応する機能、最新バージョンを実際に確認すること)で、`ai-agent-messages` チャンネルが存在すること、および bot のロールの閲覧権限を管理できる。
- 注意: プロバイダ自体も bot トークンが要る。読み上げ用の bot の権限は最小(後述)にしたいので、管理用に別の bot / 別トークンを使うのが筋。手間に見合わなければこのモジュールは作らず、手動手順に回す。
- トークンは `DISCORD_TOKEN` などの環境変数で渡し、`.tfvars` にも書かない。

**共通**
- state はローカル(`terraform.tfstate`)で、`.gitignore` に入れる。
- `terraform fmt`、`terraform validate` が通る状態にする。

---

## 9. 手動で行う作業(ユーザー)

ここは自動化せず、`docs/setup.md` に手順として書く。

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成し、Bot を追加する。
2. Bot の設定で **Message Content Intent** をオンにする(メッセージ本文の取得に必要)。
3. Bot のトークンを発行し、`~/.config/discord-channel-reader/env` に貼る(チャットや Git に貼らない)。
4. 招待 URL でサーバーに追加する:
   `https://discord.com/oauth2/authorize?client_id=<CLIENT_ID>&scope=bot&permissions=66560`
   (`66560` = チャンネルを見る `1024` + メッセージ履歴を読む `65536`。送信権限は付けない)
5. 対象チャンネルの権限で、bot が `ai-agent-messages` を見られることを確認する。
6. Discord の開発者モードをオンにして、チャンネルを右クリックして ID をコピーし、`TARGET_CHANNEL_ID` に設定する。

---

## 10. 実装の順序

1. **事前確認**(第 3 章)
2. `scripts/say.py` で「VOICEVOX → 再生」を単体で通す
3. `text_normalize` とテスト
4. `bot.py` で対象チャンネルのメッセージをログに出すだけの版を動かす(手動手順の確認も兼ねる)
5. キューと再生をつないで、通しで動かす
6. `systemd` 化(まずは手書きの unit で動作確認し、その後 Terraform に載せる)
7. 再起動耐性の確認(VOICEVOX の再起動、ネットワーク断、ホストの再起動)
8. README と `docs/setup.md` の整備

---

## 11. 受け入れ条件

- [ ] `ai-agent-messages` に人間が投稿すると、数秒以内に読み上げられる
- [ ] bot / Webhook の投稿も読み上げられる(`READ_BOT_MESSAGES=true` のとき)
- [ ] 他のチャンネルの投稿は読み上げられない
- [ ] 長文、コードブロック、URL、メンション、添付ファイルのみの投稿でも、破綻せず読み上げる(または省略する)
- [ ] 連続投稿でも音声が重ならず、順番に再生される。キュー上限を超えたら古いものから捨てる
- [ ] `muted` ファイルの作成と削除で、読み上げの停止と再開ができる
- [ ] VOICEVOX を再起動しても、本サービスが復帰する(落ちたままにならない)
- [ ] ホストを再起動すると、ログインしなくても自動で起動し、音が出る(linger と音声サーバーの確認)
- [ ] bot トークンが、リポジトリ、Terraform の state、ログのどこにも出ていない
- [ ] `terraform validate` が通り、`docs/setup.md` の手順で他の環境でも再現できる

---

## 12. 未確定事項(実装中にユーザーへ確認する)

- VOICEVOX の起動方法と、systemd 管理に寄せてよいか
- 読み上げる範囲: 人間のみか、bot や Webhook も含めるか。投稿者名を前置きするか
- 話者(キャラクター)と速度・音量
- 夜間など、読み上げを止めたい時間帯があるか
- Discord 側の Terraform(第 8 章の後半)を作るか、手動のままにするか
- リポジトリの置き場所と、Git の運用(公開 / 非公開)

---

## 13. 将来の拡張(今回はやらない)

- 複数チャンネルへの対応と、チャンネルごとの話者の切り替え
- メッセージ内容による除外ルール(特定のプレフィックスの投稿を読まない、など)
- 辞書機能(固有名詞の読みを登録する)
- ヘルスチェックのエンドポイントと、異常時の通知
