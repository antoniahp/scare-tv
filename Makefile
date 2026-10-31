# Scare-TV · everything starts from here.   make  → list of commands
#
#   make install        first time (or after an update)
#   make run            the haunted TV               (make run SCREEN=1 for an external TV)
#   make run2           Scare-TV 2: realistic faces  (run make realistic first)
#   make web / mobile   the mirror in the browser / on your phone with a QR code

PYTHON    ?= python3
VENV      := .venv
PY        := $(VENV)/bin/python
MANAGE    := $(PY) manage.py
SCREEN    ?= 0
APP_LANG  ?= es
REPEAT    ?= 15
PORT      ?= 8010
ARGS      ?=

.DEFAULT_GOAL := help
.PHONY: help install realistic-install migrate run run2 try displays scares realistic voices voices-elevenlabs \
        web mobile summary test lint

help: ## This list
	@grep -hE '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[33mmake %-17s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Options: SCREEN=$(SCREEN) APP_LANG=$(APP_LANG) REPEAT=$(REPEAT) ARGS=\"...\"   (e.g. make run SCREEN=1 APP_LANG=en)"

$(PY):
	$(PYTHON) -m venv $(VENV)

install: $(PY) ## Install everything with Poetry into .venv and set up the database
	$(PY) -m pip install -q --upgrade pip poetry
	$(VENV)/bin/poetry install --no-root
	$(MANAGE) migrate -v0
	@echo "Done. Now: make run"

realistic-install: install
	$(VENV)/bin/poetry install --no-root --extras realistic

migrate: ## Apply the night log migrations
	$(MANAGE) migrate

run: ## Start Scare-TV (live scares with your own face + classics)
	$(MANAGE) scare_tv --display $(SCREEN) --lang $(APP_LANG) --repeat $(REPEAT) $(ARGS)

run2: ## Start Scare-TV 2 (realistic faces from make realistic + live scares)
	@test -n "$$(ls media_real/*.mp4 2>/dev/null)" || { echo "Create the faces first: make realistic"; exit 1; }
	$(MANAGE) scare_tv --display $(SCREEN) --lang $(APP_LANG) --repeat $(REPEAT) --media media_real --live-chance 0.5 $(ARGS)

try: ## Scare-TV in a window, showing what the camera detects (SPACE = scare)
	$(MANAGE) scare_tv --windowed --debug --lang $(APP_LANG) $(ARGS)

displays: ## List connected displays (for SCREEN=)
	$(MANAGE) scare_tv --list-displays

scares: ## Rebuild the 20 classic scares (video + sound)
	$(MANAGE) make_scares $(ARGS)

realistic: realistic-install ## Scare-TV 2: SD-Turbo imagines realistic faces (~10 min the first time)
	$(MANAGE) make_real_scares $(ARGS)

voices: ## Rebuild the live-scare voices (Mac: `say` + effects)
	$(MANAGE) prepare_voices --lang $(APP_LANG) --again

voices-elevenlabs: ## Voices with ElevenLabs (asks for your key; never stored)
	$(MANAGE) make_voices_elevenlabs --lang $(APP_LANG)

web: ## Web mirror + API at http://localhost:8010
	@( sleep 1.5; command -v open >/dev/null && open "http://localhost:$(PORT)" ) &
	$(MANAGE) runserver 127.0.0.1:$(PORT)

mobile: ## Web mirror on your phone: https link + QR code
	$(MANAGE) mobile --port $(PORT)

summary: ## Summary of the last night (scares, jump-o-meter…)
	$(MANAGE) night_summary

test: ## Run all the tests
	$(PY) -m pytest -q

lint: ## Check code style (ruff)
	$(PY) -m ruff check .
