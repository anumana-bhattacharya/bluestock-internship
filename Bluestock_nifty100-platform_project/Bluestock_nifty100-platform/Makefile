PYTHON ?= python3
export PYTHONPATH := .deps:$(CURDIR):$(PYTHONPATH)
export MPLCONFIGDIR := $(CURDIR)/tmp/matplotlib
export LOKY_MAX_CPU_COUNT := 4

.PHONY: load ratios sprint3 sprint456 dashboard api reports clustering test explore all reset lint

load:
	$(PYTHON) -m src.orchestration.run_all --through load

ratios:
	$(PYTHON) -m src.orchestration.run_all --through ratios

sprint3:
	$(PYTHON) -m src.orchestration.run_all --through sprint3

sprint456:
	$(PYTHON) -m src.orchestration.run_all --through all

dashboard:
	$(PYTHON) -m streamlit run src/dashboard/app.py

api:
	$(PYTHON) -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000

reports:
	$(PYTHON) -m src.orchestration.run_all --through all

clustering:
	$(PYTHON) -m src.orchestration.run_all --through all

test:
	N100_TEST_REBUILD=1 $(PYTHON) -m pytest

explore:
	$(PYTHON) -m src.orchestration.explore

lint:
	$(PYTHON) -m black --check src tests
	$(PYTHON) -m ruff check src tests

all:
	$(PYTHON) -m src.orchestration.run_all --through all

reset:
	rm -f nifty100.db
	rm -f output/*.csv output/*.xlsx output/*.png output/*.json
	rm -f reports/tearsheets/*.pdf reports/sector/*.pdf
	rm -f reports/portfolio/*.pdf
	rm -f data/processed/*.csv
