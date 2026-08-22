.PHONY: install fetch fetch-extra run dashboard centres trend test clean

install:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

fetch:
	.venv/bin/python -m src.gbs_fetch

fetch-extra:
	.venv/bin/python -m src.gbs_fetch --jooble

run:
	.venv/bin/python -m src.analyze

dashboard:
	.venv/bin/python -m src.dashboard

centres:
	.venv/bin/python -m src.centres

trend:
	.venv/bin/python -m src.trend

test:
	.venv/bin/python -m pytest tests -q

clean:
	rm -rf data/cache data/chart_stability.png dashboard.html
