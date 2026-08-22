.PHONY: install fetch fetch-extra refresh run dashboard centres trend validate test clean

install:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

fetch:
	.venv/bin/python -m src.gbs_fetch

fetch-extra:
	.venv/bin/python -m src.gbs_fetch --jooble

refresh:
	@echo "== fetching a new snapshot =="
	@$(MAKE) --no-print-directory fetch
	@echo
	@echo "== rebuilding analysis and dashboard =="
	@$(MAKE) --no-print-directory run
	@$(MAKE) --no-print-directory dashboard
	@echo
	@echo "== direction since the last snapshot =="
	@$(MAKE) --no-print-directory trend

run:
	.venv/bin/python -m src.analyze

dashboard:
	.venv/bin/python -m src.dashboard

centres:
	.venv/bin/python -m src.centres

trend:
	.venv/bin/python -m src.trend

validate:
	.venv/bin/python -m src.validate

test:
	.venv/bin/python -m pytest tests -q

clean:
	rm -rf data/cache data/chart_stability.png dashboard.html
