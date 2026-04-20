.PHONY: install bridge agent watchlist buy load unload logs status

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	cd whatsapp_bridge && npm install

bridge:
	cd whatsapp_bridge && node src/index.js

agent:
	.venv/bin/python -m agent.main

watchlist:
	.venv/bin/python -m agent.main --run watchlist

buy:
	.venv/bin/python -m agent.main --run buy

load:
	./scripts/load_launchd.sh

unload:
	./scripts/unload_launchd.sh

logs:
	tail -f logs/*.log

status:
	launchctl list | grep com.user.stockagent || echo "not loaded"
