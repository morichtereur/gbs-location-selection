.PHONY: install fetch run dashboard centres test clean

install:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

fetch:
	.venv/bin/python -m src.gbs_fetch

run:
	.venv/bin/python -m src.analyze

dashboard:
	.venv/bin/python -m src.dashboard

centres:
	.venv/bin/python -m src.centres

test:
	.venv/bin/python -m pytest tests -q

clean:
	rm -rf data/cache data/chart_stability.png dashboard.html
