.PHONY: setup dev test import

setup:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

import:
	python scripts/import_municipalities_csv.py data/municipalities.csv
