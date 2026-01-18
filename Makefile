PYTHON = /home/devbox/anaconda3/envs/twinquery/bin/python

.PHONY: setup dev test import

setup:
	$(PYTHON) -m pip install --upgrade pip
	pip install -r requirements.txt

dev:
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest

import:
	$(PYTHON) scripts/import_municipalities_csv.py data/municipalities.csv
