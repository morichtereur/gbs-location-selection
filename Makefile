.PHONY: install run test clean

install:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

run:
	.venv/bin/python -m src.analyze

test:
	.venv/bin/python -m pytest tests -q

clean:
	rm -rf data/cache data/chart_stability.png
