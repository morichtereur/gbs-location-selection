# Three targets reached for an undefined $(PY) and failed with "-m: command
# not found". One variable, used everywhere, so the next target cannot.
PY := .venv/bin/python

.PHONY: install fetch fetch-extra refresh run dashboard shot centres operators trend validate leverage correlation provenance og test clean

install:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

fetch:
	$(PY) -m src.gbs_fetch

fetch-extra:
	$(PY) -m src.gbs_fetch --jooble

refresh:
	@echo "== fetching a new snapshot =="
	@$(MAKE) --no-print-directory fetch
	@echo
	@echo "== rebuilding analysis and dashboard =="
	@$(MAKE) --no-print-directory run
	@$(MAKE) --no-print-directory dashboard
	@$(MAKE) --no-print-directory og
	@echo
	@echo "== direction since the last snapshot =="
	@$(MAKE) --no-print-directory trend

run:
	$(PY) -m src.analyze

dashboard:
	$(PY) -m src.dashboard

shot:
	./scripts/shoot.sh

centres:
	$(PY) -m src.centres

operators:
	$(PY) -m src.operators

excel:
	$(PY) -m src.excel

beyond:
	$(PY) -m src.beyond

baselines:
	$(PY) -m src.baselines

trend:
	$(PY) -m src.trend

validate:
	$(PY) -m src.validate

leverage:
	$(PY) -m src.leverage

correlation:
	$(PY) -m src.correlation

provenance:
	$(PY) -m src.provenance

og:
	$(PY) -m src.og

test:
	$(PY) -m pytest tests -q

clean:
	rm -rf data/cache data/chart_stability.png dashboard.html
