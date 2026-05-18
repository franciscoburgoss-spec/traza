.PHONY: setup test test-cov run db-init clean

PYTHON=python
PIP=pip

setup:
	$(PIP) install -r requirements.txt

test:
	pytest app/ -v

test-cov:
	pytest app/ -v --cov=app --cov-report=term-missing --cov-report=html

run:
	uvicorn app.main:app --reload --port 8000

db-init:
	$(PYTHON) -c "from app.database import init_db; init_db()"

clean:
	rm -f traza.db
	rm -rf __pycache__ app/__pycache__ app/*/__pycache__
	rm -rf .pytest_cache htmlcov .coverage
