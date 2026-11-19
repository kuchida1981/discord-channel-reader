REPO_PATH     ?= $(CURDIR)
UNIT_DIR      ?= $(HOME)/.config/systemd/user
VOICEVOX_URL  ?= http://127.0.0.1:50021
VOICEVOX_UNIT ?= voicevox-engine.service
STATE_DIR     ?= $(or $(XDG_STATE_HOME),$(HOME)/.local/state)/discord-channel-reader
TEXT          ?= 動作確認です

UNIT_NAME := discord-channel-reader.service
UNIT_TMPL := deploy/systemd/discord-channel-reader.service.in

.PHONY: install uninstall test say status logs mute unmute

install:
	sed -e 's|@REPO_PATH@|$(REPO_PATH)|g' \
	    -e 's|@VOICEVOX_URL@|$(VOICEVOX_URL)|g' \
	    -e 's|@VOICEVOX_UNIT@|$(VOICEVOX_UNIT)|g' \
	    $(UNIT_TMPL) | install -Dm644 /dev/stdin $(UNIT_DIR)/$(UNIT_NAME)
	systemctl --user daemon-reload
	systemctl --user enable --now $(UNIT_NAME)

uninstall:
	systemctl --user disable --now $(UNIT_NAME) || true
	rm -f $(UNIT_DIR)/$(UNIT_NAME)
	systemctl --user daemon-reload

test:
	uv run pytest

say:
	uv run python scripts/say.py "$(TEXT)"

status:
	systemctl --user status $(UNIT_NAME)

logs:
	journalctl --user -u $(UNIT_NAME) -f

mute:
	mkdir -p $(STATE_DIR)
	touch $(STATE_DIR)/muted

unmute:
	rm -f $(STATE_DIR)/muted
